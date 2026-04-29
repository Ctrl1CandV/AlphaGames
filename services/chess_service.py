from core.message_proto import MessageProto
from core.session import BaseSession
from protocol.constants import (
    EnumCommandCode,
    EnumCommonCommandCode,
    EnumKeyInfo,
    EnumChessFlag,
    TAG_HEADER_LENGTH,
)

from chess_core.move_handler import binary_to_uci, uci_to_binary
from protocol.chess_opening_proto import build_opening_data
from protocol.chess_step_proto import ChessStepProto
from chess_core.engine import StockfishEngine
from chess_core.board import ChessBoard

import traceback
import asyncio
import random

class ChessService(BaseSession):
    def __init__(self, reader, writer, logger=None):
        super().__init__(reader, writer, logger)
        self.sn_code = None                                 # 设备序列号
        self.chess_board_camp = None                        # 棋盘阵营
        self.board = ChessBoard(logger=self.logger)         # 棋盘逻辑
        self.engine = StockfishEngine(logger=self.logger)   # AI引擎
        self._state = "IDLE"                                # 初始状态
        self._running = True                                # 运行标志

    async def handle(self):
        self._log("会话开始")
        dynamic_buffer = bytearray()

        # 请求设备序列号
        await self.send_data(EnumCommonCommandCode.SnCode.value, None)
        try:
            while self._running:
                data = await self.reader.read(65536)
                if not data or len(data) == 0:
                    self._log("客户端断开连接")
                    break

                dynamic_buffer.extend(data)
                while len(dynamic_buffer) >= MessageProto.HEAD_LENGTH:
                    _, _, data_length = MessageProto.get_head_info(dynamic_buffer)
                    if data_length == 0:
                        dynamic_buffer = bytearray()
                        break
                    
                    # 缓存区数据小于数据长度，表明数据不完整
                    if len(dynamic_buffer) < data_length:
                        break
                    
                    # 解码信息获取命令及具体指令，并实行分发处理命令
                    mp = MessageProto(dynamic_buffer)
                    dynamic_buffer = mp.MoreData
                    try:
                        await self._dispatch(mp.Command, mp.get_message())
                    except Exception as e:
                        self._log(f"命令处理异常: {e}\n{traceback.format_exc()}", "error")

        except ConnectionResetError:
            self._connected = False
            self._log("客户端断开连接")
        except ConnectionAbortedError:
            self._connected = False
        except BrokenPipeError:
            self._connected = False
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._log(f"会话异常: {e}", "error")
        finally:
            self._connected = False
            await self._cleanup()

    async def _dispatch(self, command, message):
        """
        根据命令码调用对应的处理方法
        SnCode  接收设备序列号
        StepUpload  处理步步上传模式
        AllUpload   处理整局上传模式
        EnableKey   处理按键事件
        Opening 处理开局数据
        BoardCamp   处理棋盘阵营
        BoardLayout 处理棋盘布局完成
        MoveOn  处理行棋确认
        MoveVerify  处理走棋验证
        """
        cmd = command

        if cmd == EnumCommonCommandCode.SnCode.value:
            await self._handle_sn_code(message)

        elif cmd == EnumCommandCode.StepUpload.value:
            await self._handle_step_upload(message)

        elif cmd == EnumCommandCode.AllUpload.value:
            await self._handle_all_upload(message)

        elif cmd == EnumCommandCode.NotifyOpenUpload.value:
            await self._handle_notify_open_upload(message)

        elif cmd == EnumCommandCode.EnableKey.value:
            await self._handle_enable_key(message)

        elif cmd == EnumCommandCode.Opening.value:
            await self._handle_opening(message)

        elif cmd == EnumCommandCode.BoardCamp.value:
            await self._handle_board_camp(message)

        elif cmd == EnumCommandCode.BoardLayout.value:
            await self._handle_board_layout(message)

        elif cmd == EnumCommandCode.MoveOn.value:
            await self._handle_move_on(message)

        elif cmd == EnumCommandCode.MoveVerify.value:
            await self._handle_move_verify(message)

        else:
            self._log(f"未处理的命令: 0x{command:02X}")

    async def _handle_sn_code(self, message):
        self.sn_code = message.decode("utf-8").replace("\x00", "").strip()
        self._log(f"收到SN码: {self.sn_code}")

        self._log("下发步步上传模式")
        await self.send_data(EnumCommandCode.StepUpload.value, None)

        self._state = "WAIT_UPLOAD_MODE"

    async def _handle_step_upload(self, message):
        if message is None or len(message) <= 1:
            self._log("棋盘确认步步上传模式")
            await self.send_data(
                EnumCommandCode.NotifyOpenUpload.value,
                bytes([EnumCommandCode.OkStatusCode.value]),
            )
            self._state = "WAIT_GAME_MODE"
            return

        if self._state != "PLAYING":
            self._log(f"非对弈状态收到行棋数据, 当前状态={self._state}")
            return

        step_data = self._extract_step_data(message)
        if step_data is None:
            return

        await self._process_player_move(step_data)

    async def _handle_all_upload(self, message):
        if message is None or len(message) <= 1:
            self._log("棋盘确认整局上传模式")
            await self.send_data(
                EnumCommandCode.NotifyOpenUpload.value,
                bytes([EnumCommandCode.OkStatusCode.value]),
            )
            self._state = "WAIT_GAME_MODE"
            return

    async def _handle_notify_open_upload(self, message):
        if message and len(message) == 1 and message[0] == EnumCommandCode.OkStatusCode.value:
            self._log("棋盘成功配置上传模式")

    async def _handle_enable_key(self, message):
        if message is None:
            return

        key = message[0]

        if key in (
            EnumKeyInfo.ManVsRemoteMachine.value,
            EnumKeyInfo.ManVsRemoteMan.value,
            EnumKeyInfo.ManVsLocalMachine.value,
            EnumKeyInfo.ManVsFaceMan.value,
        ):
            if self._state not in ("WAIT_GAME_MODE",):
                self._log(f"非预期状态收到模式选择: state={self._state}，忽略")
                return
            self._log(f"棋盘选择对战模式: 0x{key:02X}")
            mode = key
            battle_bytes = bytes([mode, EnumCommandCode.OkStatusCode.value])
            await self.send_data(EnumCommandCode.EnableKey.value, battle_bytes)
            await self._send_opening_data()
            self._state = "WAIT_OPENING"

        elif key == EnumKeyInfo.StartChess.value:
            if len(message) >= 2 and message[1] == EnumCommandCode.OkStatusCode.value:
                self._log("棋盘确认开始游戏")
            else:
                self._log("棋盘开始游戏")

        elif key == EnumKeyInfo.EndChess.value:
            if self._state != "PLAYING":
                return
            self._log("棋盘请求结束游戏")
            await self._on_game_ended(is_surrender=True)
            end_bytes = bytes([EnumKeyInfo.EndChess.value, EnumCommandCode.OkStatusCode.value])
            await self.send_data(EnumCommandCode.EnableKey.value, end_bytes)

    async def _handle_opening(self, message):
        self._log("棋盘已按开局数据摆好棋子")

        self.chess_board_camp = random.choice([True, False])

        camp_name = "白方" if self.chess_board_camp else "黑方"
        self._log(f"随机分配阵营: {camp_name}")

        camp_byte = (
            EnumChessFlag.White.value
            if self.chess_board_camp
            else EnumChessFlag.Black.value
        )
        await self.send_data(EnumCommandCode.BoardCamp.value, bytes([camp_byte]))
        self._state = "WAIT_CAMP"

    async def _handle_board_camp(self, message):
        if len(message) >= 2 and message[1] == EnumCommandCode.OkStatusCode.value:
            self._log("棋盘已按阵营信息设置完成")

    async def _handle_board_layout(self, message):
        if message and len(message) == 1 and message[0] == EnumCommandCode.BoardLayoutComplete.value:
            self._log("棋盘布局完成，开始对弈")

            self._state = "PLAYING"

            start_bytes = bytes([EnumKeyInfo.StartChess.value, EnumCommandCode.OkStatusCode.value])
            await self.send_data(EnumCommandCode.EnableKey.value, start_bytes)

            try:
                await asyncio.wait_for(self.engine.start(), timeout=8.0)
            except (Exception, asyncio.TimeoutError) as e:
                self._log(f"Stockfish 启动失败: {e}", "error")

            if not self.chess_board_camp:
                await self._engine_move()

    async def _handle_move_on(self, message):
        if message and len(message) > 1:
            self._log("棋盘确认收到行棋数据")

    async def _handle_move_verify(self, message):
        pass

    async def _send_opening_data(self):
        data = build_opening_data()
        await self.send_data(EnumCommandCode.Opening.value, data)

    def _extract_step_data(self, message):
        """ 从接收到的消息中提取行棋数据，并解析为ChessStepProto对象 """
        if len(message) >= TAG_HEADER_LENGTH + 6:
            move_bytes = message[TAG_HEADER_LENGTH : TAG_HEADER_LENGTH + 6]
        elif len(message) == 6:
            move_bytes = message
        else:
            self._log(f"行棋数据长度异常: {len(message)}")
            return None

        try:
            return ChessStepProto(move_bytes)
        except Exception as e:
            self._log(f"行棋数据解析失败: {e}")
            return None

    async def _process_player_move(self, step_data):
        """
        处理玩家走棋的完整流程：
        1. 转换UCI格式 → 2. 验证合法性 → 3. 更新棋盘 → 4. 发送确认 → 5. 检查游戏结束 → 6. AI走棋
        """
        try:
            uci = binary_to_uci(step_data)
        except Exception as e:
            self._log(f"行棋数据转UCI失败: {e}")
            await self.send_data(
                EnumCommandCode.MoveVerify.value,
                bytes([EnumCommandCode.MoveFail.value]),
            )
            return

        self._log(f"棋盘走棋: {uci}")

        if not self.board.is_legal(uci):
            self._log(f"非法行棋: {uci}")
            await self.send_data(
                EnumCommandCode.MoveVerify.value,
                bytes([EnumCommandCode.MoveFail.value]),
            )
            return

        self.board.push_uci(uci)

        await self.send_data(
            EnumCommandCode.MoveVerify.value,
            bytes([EnumCommandCode.MoveSucess.value]),
        )

        if self.board.is_game_over():
            await self._on_game_ended()
            return

        await self._engine_move()

    async def _engine_move(self):
        """
        AI引擎走棋完整流程：
        1. 调用Stockfish计算最佳走棋 → 2. 转换为二进制格式 → 3. 更新棋盘 → 4. 发送走棋数据 → 5. 检查游戏结束
        """
        try:
            ai_uci = await self.engine.get_best_move(self.board)
        except Exception as e:
            self._log(f"Stockfish 走棋失败: {e}", "error")
            return

        ai_color = self.board.board.turn
        try:
            move_data = uci_to_binary(self.board, ai_uci, move_color=ai_color)
        except Exception as e:
            self._log(f"UCI转二进制失败: {e}", "error")
            return

        self.board.push_uci(ai_uci)

        await self.send_data(EnumCommandCode.MoveOn.value, move_data)
        await self.send_data(
            EnumCommandCode.MoveVerify.value,
            bytes([EnumCommandCode.MoveSucess.value]),
        )

        if self.board.is_game_over():
            await self._on_game_ended()

    async def _on_game_ended(self, is_surrender=False):
        """
        游戏结束处理流程：
        1. 记录游戏结果 → 2. 清理AI引擎 → 3. 通知设备 → 4. 重置游戏状态
        """
        self._log(f"游戏结束, 结果={self.board.result()}")

        if self.engine:
            try:
                await self.engine.quit()
            except Exception:
                pass
            self.engine = None

        await self.send_data(
            EnumCommandCode.EnableKey.value,
            bytes([EnumKeyInfo.EndChess.value, EnumCommandCode.OkStatusCode.value]),
        )

        self._state = "WAIT_GAME_MODE"
        self.board.reset()
        self.engine = StockfishEngine(logger=self.logger)

    async def _cleanup(self):
        """ 异常结束国际象棋服务 """
        self._running = False
        if self.engine:
            try:
                await self.engine.quit()
            except Exception:
                pass
        await self.close()
