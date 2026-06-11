from core.message_proto import MessageProto
from core.session import BaseSession
from protocol.constants import (
    EnumCommandCode,
    EnumCommonCommandCode,
    EnumKeyInfo,
    EnumChessFlag,
    TAG_HEADER_LENGTH,
)

from protocol.chess_opening_proto import build_opening_data
from core.move_handler import binary_to_uci, uci_to_binary
from protocol.chess_step_proto import ChessStepProto
from services.lichess_service import LichessSession
from services.voice_service import VoiceService
from core.engine import get_stockfish_pool
from services.db_service import DbService
from utils.logger import setup_sn_logger
from core.board import ChessBoard
from config import Config

_ELO_TO_LICHESS   = lambda e: max(1, min(8, round((e - 800) / 262.5) + 1))

from datetime import datetime, timezone
import traceback
import tempfile
import asyncio
import random
import struct
import json
import os

class ChessService(BaseSession):
    def __init__(self, reader, writer, logger=None):
        super().__init__(reader, writer, logger)
        self.sn_code = None                                 # 设备序列号
        self.user_id = None                                 # 注册用户ID
        self.chess_board_camp = None                        # 棋盘阵营
        self.board = ChessBoard(logger=self.logger)         # 棋盘逻辑
        self._pool = get_stockfish_pool(self.logger)        # AI引擎池（全局共享）
        self._db = DbService(logger=self.logger)
        self._game_mode = None                              # "stockfish" | "lichess"
        self._lichess = None                                # LichessSession
        self._state = "IDLE"                                # 初始状态
        self._running = True                                # 运行标志
        self._voice_buffer = bytearray()                    # 语音数据缓冲区
        self._voice_total = 0                               # 语音总长度
        self._voice_service = VoiceService(logger=self.logger)
        self._auto_moving = False
        self._game_config = {}
        self._last_sent_uci = None
        self._ai_first_move_pending = False  # 标记AI是否需要在棋盘就绪后走首步
        self._lichess_task = None            # 后台对局任务引用，取消匹配时可 cancel
        self._monitor_task = None            # Lichess 对局结束监控任务引用
        self._game_ended_lock = asyncio.Lock()  # 防重入锁

    async def handle(self):
        self._log("会话开始")
        dynamic_buffer = bytearray()

        # 请求设备序列号
        await self.send_data(EnumCommonCommandCode.SnCode.value, None)
        try:
            while self._running:
                # 读取超时保护，防止连接假死（1800s 足够覆盖 Lichess 长对局的等待间隔）
                try:
                    data = await asyncio.wait_for(self.reader.read(65536), timeout=1800)
                except asyncio.TimeoutError:
                    self._log("读取超时(1800s)，视为连接断开")
                    break
                if not data or len(data) == 0:
                    self._log("客户端断开连接")
                    break

                dynamic_buffer.extend(data)
                # 缓冲区大小限制，防止异常数据导致内存无限增长
                if len(dynamic_buffer) > 1024 * 1024:  # 1MB
                    self._log(f"缓冲区超过1MB({len(dynamic_buffer)}字节)，重置", "error")
                    dynamic_buffer = bytearray()
                    continue
                while len(dynamic_buffer) >= MessageProto.HEAD_LENGTH:
                    _, _, data_length = MessageProto.get_head_info(dynamic_buffer)
                    if data_length == 0:
                        dynamic_buffer = bytearray()
                        break
                    
                    # 缓存区数据小于数据长度，表明数据不完整
                    if len(dynamic_buffer) < data_length:
                        break
                    
                    # 解码信息获取命令及具体指令，并实行分发处理命令
                    raw = dynamic_buffer[:data_length]
                    mp = MessageProto(dynamic_buffer)
                    dynamic_buffer = mp.MoreData
                    self._log(f"接收 命令=0x{mp.Command:02X} 数据={self._hex_str(raw)}")
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
        elif cmd == EnumCommandCode.StartMove.value:
            await self._handle_start_move(message)
        elif cmd == EnumCommandCode.EndMove.value:
            await self._handle_end_move(message)
        elif cmd == EnumCommandCode.AudioFile.value:
            await self._handle_audio_file(message)
        else:
            self._log(f"未处理的命令: 0x{command:02X}")

    async def _handle_sn_code(self, message):
        self.sn_code = message.decode("utf-8").replace("\x00", "").strip()
        self.logger = setup_sn_logger(self.sn_code)
        self._log(f"收到SN码: {self.sn_code}")

        try:
            self.user_id, self.user_name = await self._db.get_user_by_sn(self.sn_code)
        except Exception:
            self._log("查询SN绑定失败", "error")
            self.user_id, self.user_name = None, None

        if self.user_name:
            self._log(f"关联用户: {self.user_name}")
        else:
            self._log("SN未绑定用户")

        upload_mode = await self._db.get_upload_mode(self.user_name)
        if upload_mode == 1:
            self._log("下发整局上传模式")
            await self.send_data(EnumCommandCode.AllUpload.value, None)
        else:
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

        self._log(f"收到整局上传数据，长度={len(message)}")
        if self.user_name:
            try:
                await self._db.save_chess_record(self.user_name, bytes(message))
            except Exception:
                self._log("整局棋谱保存失败", "error")

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

            if key == EnumKeyInfo.ManVsRemoteMachine.value:
                self._game_config = await self._db.get_game_config(self.user_name)
                await self._start_lichess(key, is_ai=True)
                return
            if key == EnumKeyInfo.ManVsRemoteMan.value:
                self._game_config = await self._db.get_game_config(self.user_name)
                await self._start_lichess(key, is_ai=False)
                return

            self._game_config = await self._db.get_game_config(self.user_name)
            self._game_mode = "stockfish"
            battle_bytes = bytes([key, EnumCommandCode.OkStatusCode.value])
            await self.send_data(EnumCommandCode.EnableKey.value, battle_bytes)
            await self._send_opening_data()
            self._state = "WAIT_OPENING"
            # 启动握手超时监控
            self._start_handshake_monitor("WAIT_OPENING", self._send_opening_data)

        elif key == EnumKeyInfo.StartChess.value:
            if len(message) >= 2 and message[1] == EnumCommandCode.OkStatusCode.value:
                self._log("棋盘确认开始游戏")
                # 棋盘已就绪：进入对弈状态，若 AI 先手则此刻才推送首步，避免棋盘漏接
                if self._state == "WAIT_BOARD_READY":
                    self._state = "PLAYING"
                    if self._ai_first_move_pending:
                        self._ai_first_move_pending = False
                        if self._game_mode == "lichess":
                            await self._lichess_wait_and_forward_move()
                        else:
                            await self._engine_move()
            else:
                self._log("棋盘开始游戏")

        elif key == EnumKeyInfo.EndChess.value:
            if self._state == "LICHESS_SEEKING":
                self._log("棋盘取消匹配")
                # 取消后台对局任务，防止"复活"
                if self._lichess_task and not self._lichess_task.done():
                    self._lichess_task.cancel()
                    self._lichess_task = None
                if self._lichess:
                    self._lichess.shutdown()
                    self._lichess = None
                if self._monitor_task and not self._monitor_task.done():
                    self._monitor_task.cancel()
                    self._monitor_task = None
                self._game_mode = None
                await self.send_data(
                    EnumCommandCode.EnableKey.value,
                    bytes([EnumKeyInfo.EndChess.value]),
                )
                self._state = "WAIT_GAME_MODE"
                return
            if self._state != "PLAYING":
                # 握手阶段也可直接终止，无需等待监控超时
                if self._state in ("WAIT_OPENING", "WAIT_CAMP", "WAIT_LAYOUT", "WAIT_BOARD_READY"):
                    await self._on_game_ended()
                return
            if self._game_mode == "lichess" and self._lichess:
                try:
                    await asyncio.wait_for(self._lichess.resign(), timeout=5)
                except Exception:
                    pass
            self._log("棋盘请求投降")
            await self._on_game_ended(is_surrender=True)

    async def _handle_opening(self, message):
        # 状态守卫：防止过期/重复消息覆盖状态
        if self._state != "WAIT_OPENING":
            self._log(f"非 WAIT_OPENING 状态收到 Opening 确认, state={self._state}，忽略")
            return
        self._log("棋盘已按开局数据摆好棋子")

        if self._game_mode != "lichess":
            cfg_color = self._game_config.get("engineColor", "random")
            if cfg_color == "white":
                self.chess_board_camp = True
            elif cfg_color == "black":
                self.chess_board_camp = False
            else:
                self.chess_board_camp = random.choice([True, False])

        camp_name = "白方" if self.chess_board_camp else "黑方"
        self._log(f"分配阵营: {camp_name}")

        camp_byte = (
            EnumChessFlag.White.value
            if self.chess_board_camp
            else EnumChessFlag.Black.value
        )
        await self.send_data(EnumCommandCode.BoardCamp.value, bytes([camp_byte]))
        self._state = "WAIT_CAMP"
        # 启动握手超时监控
        self._start_handshake_monitor("WAIT_CAMP", lambda: self.send_data(EnumCommandCode.BoardCamp.value, bytes([camp_byte])))

    async def _handle_board_camp(self, message):
        # 状态守卫：防止过期/重复消息覆盖状态
        if self._state != "WAIT_CAMP":
            self._log(f"非 WAIT_CAMP 状态收到 BoardCamp 确认, state={self._state}，忽略")
            return
        if len(message) >= 2 and message[1] == EnumCommandCode.OkStatusCode.value:
            self._log("棋盘已按阵营信息设置完成")
            self._state = "WAIT_LAYOUT"

    async def _handle_board_layout(self, message):
        if self._state not in ("WAIT_CAMP", "WAIT_LAYOUT"):
            return
        if message and len(message) == 1 and message[0] == EnumCommandCode.BoardLayoutComplete.value:
            self._log("棋盘布局完成，下发开始指令，等待棋盘就绪")

            # 先等棋盘回 EnableKey(StartChess)+OK 再推送 AI 首步，
            # 否则棋盘未就绪会丢掉首步走子数据导致对弈卡死
            self._ai_first_move_pending = not self.chess_board_camp
            self._state = "WAIT_BOARD_READY"

            start_bytes = bytes([EnumKeyInfo.StartChess.value])
            await self.send_data(EnumCommandCode.EnableKey.value, start_bytes)

            # 启动握手超时监控
            self._start_handshake_monitor(
                "WAIT_BOARD_READY",
                lambda: self.send_data(EnumCommandCode.EnableKey.value, start_bytes),
            )

            if self._game_mode == "lichess" and self._lichess:
                # 保存任务引用，cleanup 时可取消
                self._monitor_task = asyncio.create_task(self._lichess_monitor_end())

    async def _handle_move_on(self, message):
        if message and len(message) > 1:
            self._log("棋盘确认收到行棋数据")

    async def _handle_move_verify(self, message):
        if not message or len(message) < 1:
            return
        status = message[0]
        if status == EnumCommandCode.MoveSucess.value:
            self._log("棋盘确认走棋成功")
        elif status == EnumCommandCode.MoveFail.value:
            self._log("棋盘拒绝走棋", "error")
        else:
            self._log(f"棋盘走棋确认: 0x{status:02X}")

    async def _handle_start_move(self, message):
        self._log("棋盘自动行棋中")
        self._auto_moving = True

    async def _handle_end_move(self, message):
        self._log("棋盘自动行棋结束")
        self._auto_moving = False

    async def _handle_audio_file(self, message):
        if message is None or len(message) < 2:
            return

        file_id = struct.unpack("<H", message[:2])[0]

        if file_id == 0 and len(message) >= 6:
            self._voice_buffer = bytearray()
            self._voice_total = struct.unpack("<I", message[2:6])[0]
            data = message[6:]
            self._log(f"语音接收开始 总长度={self._voice_total}")
        else:
            data = message[2:]

        self._voice_buffer.extend(data)
        if self._voice_total > 0 and len(self._voice_buffer) >= self._voice_total:
            self._log("语音接收完成，开始识别")
            await self._process_voice()

    async def _process_voice(self):
        temp_path = None
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            with open(temp_path, "wb") as f:
                f.write(self._voice_buffer[:self._voice_total])

            text = await self._voice_service.speech_to_text(temp_path)
            if not text:
                await self.send_data(
                    EnumCommandCode.AudioFile.value,
                    bytes([EnumCommandCode.FailStatusCode.value]),
                )
                return

            intent = self._voice_service.parse_intent(text)

            if intent == "start_game_ai":
                if self._state != "WAIT_GAME_MODE":
                    self._log(f"非等待模式忽略语音指令, state={self._state}")
                    return
                self._log("语音指令：开始人机对战")
                await self.send_data(
                    EnumCommandCode.AudioFile.value,
                    bytes([EnumCommandCode.OkStatusCode.value]),
                )
                await self._start_lichess(EnumKeyInfo.ManVsRemoteMachine.value, is_ai=True)

            elif intent == "start_game_human":
                if self._state != "WAIT_GAME_MODE":
                    self._log(f"非等待模式忽略语音指令, state={self._state}")
                    return
                self._log("语音指令：开始人人对战")
                await self.send_data(
                    EnumCommandCode.AudioFile.value,
                    bytes([EnumCommandCode.OkStatusCode.value]),
                )
                await self._start_lichess(EnumKeyInfo.ManVsRemoteMan.value, is_ai=False)

            elif intent == "query_opening":
                moves = self.board.move_stack()
                opening = self._voice_service.lookup_opening(moves)
                if opening:
                    await self.send_data(
                        EnumCommandCode.TextResponse.value,
                        opening.encode("utf-8"),
                    )
                else:
                    await self.send_data(
                        EnumCommandCode.AudioFile.value,
                        bytes([EnumCommandCode.FailStatusCode.value]),
                    )

            elif intent == "query_moves":
                fen = self.board.fen()
                await self.send_data(
                    EnumCommandCode.TextResponse.value,
                    fen.encode("utf-8"),
                )

            else:
                response = await self._voice_service.ai_chat(text)
                if not response:
                    await self.send_data(
                        EnumCommandCode.AudioFile.value,
                        bytes([EnumCommandCode.FailStatusCode.value]),
                    )
                    return
                pcm = await self._voice_service.text_to_speech(response)
                if not pcm:
                    await self.send_data(
                        EnumCommandCode.AudioFile.value,
                        bytes([EnumCommandCode.FailStatusCode.value]),
                    )
                    return
                await self._stream_audio_response(pcm)

        except Exception as e:
            self._log(f"语音处理异常: {e}", "error")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    async def _stream_audio_response(self, pcm_data):
        total = len(pcm_data)
        self._log(f"TTS音频总长度={total}")

        header = struct.pack("<HI", 0, total)
        await self.send_data(EnumCommandCode.AudioFile.value, header)

        chunk_size = 1024
        offset = 0
        seq = 1
        while offset < total:
            end = min(offset + chunk_size, total)
            chunk = struct.pack("<H", seq) + pcm_data[offset:end]
            await self.send_data(EnumCommandCode.AudioFile.value, chunk)
            offset = end
            seq += 1
            await asyncio.sleep(0.02)
        self._log("音频流发送完毕")

    async def _start_lichess(self, mode_key, is_ai):
        if not self.user_id:
            self._log("Lichess对战需要绑定用户")
            await self._send_open_fail()
            return
        bind = await self._db.get_bind_info(self.user_id, "lichess")
        if not bind.get("token"):
            self._log("未绑定Lichess账号")
            await self._send_open_fail()
            return
        self._game_mode = "lichess"
        await self.send_data(
            EnumCommandCode.EnableKey.value,
            bytes([mode_key, EnumCommandCode.OkStatusCode.value]),
        )
        self._state = "LICHESS_SEEKING"
        # 保存任务引用，取消匹配时可 cancel
        self._lichess_task = asyncio.create_task(self._lichess_game_loop(bind["token"], is_ai))

    async def _lichess_game_loop(self, token, is_ai):
        cfg = self._game_config
        try:
            self._lichess = LichessSession(token, logger=self.logger)
            if is_ai:
                await self._lichess.challenge_ai(
                    level=max(1, min(8, round((cfg.get("aiLevel", 1500) - 800) / 262.5) + 1)),
                    time_min=cfg.get("time", Config.LICHESS_SEEK_TIME),
                    increment_sec=cfg.get("increment", Config.LICHESS_SEEK_INCREMENT),
                    color=cfg.get("engineColor", "random"),
                )
            elif cfg.get("pvpMode") == "designated" and cfg.get("pvpOpponent"):
                await self._lichess.challenge_user(
                    username=cfg["pvpOpponent"],
                    time=cfg.get("time", Config.LICHESS_SEEK_TIME),
                    increment=cfg.get("increment", Config.LICHESS_SEEK_INCREMENT),
                    color=cfg.get("engineColor", "random"),
                )
            else:
                await self._lichess.seek_until_found(
                    time=Config.LICHESS_SEEK_TIME,
                    increment=Config.LICHESS_SEEK_INCREMENT,
                )
            await self._lichess.start_game_stream()
            my_color = self._lichess.my_color
            self.chess_board_camp = (my_color == "white")
            label = "AI" if is_ai else ""
            self._log(f"Lichess{label}开局成功 阵营={'白' if self.chess_board_camp else '黑'}")
            await self._send_opening_data()
            self._state = "WAIT_OPENING"
            # 启动握手超时监控
            self._start_handshake_monitor("WAIT_OPENING", self._send_opening_data)
        except asyncio.CancelledError:
            # 用户取消匹配时正常退出
            self._log("Lichess 对局任务已取消")
            raise
        except Exception as e:
            label = "AI" if is_ai else ""
            self._log(f"Lichess{label}开局失败: {type(e).__name__}: {e}", "error")
            import traceback
            self._log(traceback.format_exc(), "error")
            if self._lichess:
                self._lichess.shutdown()
                self._lichess = None
            self._game_mode = None
            self._ai_first_move_pending = False
            # _send_open_fail 会发送 EndChess 给棋盘并将 state 置为 WAIT_GAME_MODE
            await self._send_open_fail()

    async def _send_open_fail(self):
        # 无需防重入锁：此方法仅在开局失败时调用，与 _on_game_ended（对局结束时调用）不会并发
        await self.send_data(
            EnumCommandCode.EnableKey.value,
            bytes([EnumKeyInfo.EndChess.value]),
        )
        self._state = "WAIT_GAME_MODE"

    async def _lichess_send_and_wait(self, uci):
        try:
            await self._lichess.make_move(uci)
        except Exception as e:
            self._log(f"[网络] Lichess走棋失败(已重试3次): {type(e).__name__}: {e}", "error")
            await self._on_game_ended()
            return

        if self.board.is_game_over():
            await self._on_game_ended()
            return

        await self._lichess_wait_and_forward_move()

    async def _lichess_wait_and_forward_move(self):
        try:
            opp_uci = await self._lichess.wait_for_opponent_move()
        except Exception as e:
            self._log(f"[网络] 等待对手走棋失败(已重试3次): {e}", "error")
            await self._on_game_ended()
            return

        opp_color = self.board.turn()
        move_data = uci_to_binary(self.board, opp_uci, move_color=opp_color)
        self.board.push_uci(opp_uci)

        await self.send_data(EnumCommandCode.MoveOn.value, move_data)
        await self.send_data(
            EnumCommandCode.MoveVerify.value,
            bytes([EnumCommandCode.MoveSucess.value]),
        )

        if self.board.is_game_over():
            await self._on_game_ended()

    async def _lichess_monitor_end(self):
        """后台监控 Lichess 对局结束事件"""
        try:
            if not self._lichess:
                return
            await self._lichess.wait_game_end()
            if self._state == "PLAYING":
                self._log("Lichess 对局结束")
                await self._on_game_ended()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._log(f"Lichess 对局结束监控异常: {e}", "error")

    async def _send_opening_data(self):
        data = build_opening_data()
        await self.send_data(EnumCommandCode.Opening.value, data)

    async def _handshake_retry(self, expected_state, send_func, max_retries=3, timeout=10.0):
        """握手超时监控：sleep 后检查状态是否已离开 expected_state，未离开则重发，超限则终止对局。"""
        for attempt in range(max_retries):
            await asyncio.sleep(timeout)
            if self._state != expected_state:
                return  # 握手成功或对局已结束，均无需处理
            self._log(f"握手超时(第{attempt + 1}/{max_retries}次)，状态={expected_state}，重发指令")
            await send_func()
        if self._state == expected_state:
            self._log(f"握手重试{max_retries}次后仍无响应，终止对局", "error")
            await self._on_game_ended()

    def _start_handshake_monitor(self, expected_state, send_func, max_retries=3, timeout=10.0):
        """启动后台握手超时监控任务"""
        asyncio.create_task(
            self._handshake_retry(expected_state, send_func, max_retries, timeout)
        )

    def _extract_step_data(self, message):
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
            self._log(f"非法行棋: {uci}  FEN={self.board.fen()}")
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

        if self._game_mode == "lichess":
            await self._lichess_send_and_wait(uci)
        else:
            await self._engine_move()

    async def _engine_move(self):
        engine = None
        elo = self._game_config.get("aiLevel", 1500)
        stockfish_level = max(0, min(20, round((elo - 800) / 105)))
        for attempt in (1, 2):
            engine = await self._pool.acquire()
            engine.set_skill_level(stockfish_level)
            try:
                ai_uci = await engine.get_best_move(self.board)
                break
            except Exception as e:
                self._log(f"Stockfish 走棋失败(第{attempt}次): {e}", "error")
                await engine.quit()
                engine = None
        else:
            self._log("Stockfish 连续走棋失败，结束对局", "error")
            await self._on_game_ended()
            return

        ai_color = self.board.turn()
        try:
            move_data = uci_to_binary(self.board, ai_uci, move_color=ai_color)
        except Exception as e:
            self._log(f"UCI转二进制失败: {e}", "error")
            await self._pool.release(engine)
            await self._on_game_ended()
            return

        self.board.push_uci(ai_uci)
        await self._pool.release(engine)

        await self.send_data(EnumCommandCode.MoveOn.value, move_data)
        await self.send_data(
            EnumCommandCode.MoveVerify.value,
            bytes([EnumCommandCode.MoveSucess.value]),
        )

        if self.board.is_game_over():
            await self._on_game_ended()

    async def _on_game_ended(self, is_surrender=False):
        # 锁内仅做状态切换和结果捕获，使并发调用被 state 检查拦截
        async with self._game_ended_lock:
            if self._state == "WAIT_GAME_MODE":
                return
            self._state = "WAIT_GAME_MODE"
            result = self.board.result()

        reason = "投降" if is_surrender else f"终局({result})"
        self._log(f"游戏结束: {reason}")

        if self._auto_moving:
            self._log("等待棋盘自动行棋完成...")
            for _ in range(30):
                await asyncio.sleep(0.5)
                if not self._auto_moving:
                    break

        await self.send_data(
            EnumCommandCode.EnableKey.value,
            bytes([EnumKeyInfo.EndChess.value]),
        )

        if self.user_name:
            try:
                record_data = json.dumps({
                    "moves": self.board.move_stack(),
                    "result": result,
                    "final_fen": self.board.fen(),
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                }, ensure_ascii=False).encode("utf-8")
                await self._db.save_chess_record(self.user_name, record_data)
            except Exception:
                self._log("棋谱保存失败", "error")

        if self._lichess:
            self._lichess.shutdown()
            self._lichess = None
        self._game_mode = None
        self._ai_first_move_pending = False
        self.board.reset()

    async def _cleanup(self):
        self._running = False
        # 取消所有后台 asyncio 任务
        if self._lichess_task and not self._lichess_task.done():
            self._lichess_task.cancel()
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        if self._lichess:
            self._lichess.shutdown()
        await self.close()