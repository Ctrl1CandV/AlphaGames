import threading
import berserk
import asyncio
import logging


class LichessSession:
    def __init__(self, token, logger=None):
        self._token = token
        self._client = berserk.Client(berserk.TokenSession(token))
        self._logger = logger or logging.getLogger("AlphaGames")
        self._events = asyncio.Queue()
        self._states = asyncio.Queue()
        self._running = False
        self._stop_event = threading.Event()       # 线程停止信号（替代 _running 布尔值，避免 TOCTOU 竞态）
        self._game_id = None
        self._my_color = None
        self._move_count = 0                # 已落到物理棋盘上的半回合数
        self._pending_opponent_moves = []   # gameFull中订阅前已走、待转发给棋盘的步
        self._event_thread = None
        self._state_thread = None
        self._game_ended = asyncio.Event()

    @property
    def my_color(self):
        return self._my_color

    @property
    def game_id(self):
        return self._game_id

    @property
    def game_ended(self):
        return self._game_ended.is_set()

    async def wait_game_end(self):
        """阻塞等待对局自然结束"""
        await self._game_ended.wait()

    @staticmethod
    def _attr(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    async def _check_and_abort_ongoing(self):
        from requests import get, post

        token = self._token
        loop = asyncio.get_running_loop()

        def _check():
            headers = {"Authorization": f"Bearer {token}"}
            try:
                resp = get("https://lichess.org/api/account/playing", headers=headers, timeout=10)
                if resp.status_code != 200:
                    return
                data = resp.json()
                for game in data.get("nowPlaying", []):
                    gid = game.get("gameId")
                    if not gid:
                        continue
                    post(f"https://lichess.org/api/board/game/{gid}/resign", headers=headers, timeout=10)
                    self._log(f"已关闭进行中的对局: {gid}")
            except Exception as e:
                self._log(f"检查进行中对局异常: {e}")

        await asyncio.wait_for(loop.run_in_executor(None, _check), timeout=60)

    async def seek_until_found(self, time=10, increment=5):
        await self._check_and_abort_ongoing()
        self._running = True
        self._stop_event.clear()
        loop = asyncio.get_running_loop()

        def _stream():
            try:
                for event in self._client.board.stream_incoming_events():
                    if self._stop_event.is_set():
                        break
                    etype = self._attr(event, "type")
                    if etype in ("gameStart", "gameFinish", "challenge"):
                        asyncio.run_coroutine_threadsafe(self._events.put(event), loop)
            except Exception as e:
                self._log(f"事件流异常: {e}", "error")

        self._event_thread = threading.Thread(target=_stream, daemon=True)
        self._event_thread.start()

        attempt = 0
        while self._running and not self._stop_event.is_set():
            attempt += 1
            self._log(f"第{attempt}次寻找对手...")
            # 清空前先检查是否已有 gameStart 事件，避免丢弃
            game_start_event = None
            while not self._events.empty():
                evt = self._events.get_nowait()
                if self._attr(evt, "type") == "gameStart":
                    game_start_event = evt
            if game_start_event:
                game = self._attr(game_start_event, "game", {})
                self._game_id = self._attr(game, "id")
                self._my_color = self._attr(game, "color")
                self._log(f"匹配成功 game_id={self._game_id} color={self._my_color}")
                return

            try:
                await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self._client.board.seek(time=time, increment=increment),
                    ),
                    timeout=30,
                )
            except asyncio.TimeoutError:
                self._log("Seek 请求超时", "warning")
                continue
            except Exception as e:
                self._log(f"Seek异常: {e}", "error")
                await asyncio.sleep(2)
                continue

            try:
                event = await asyncio.wait_for(self._events.get(), timeout=15)
            except asyncio.TimeoutError:
                continue
            etype = self._attr(event, "type")
            if etype == "gameStart":
                game = self._attr(event, "game", {})
                self._game_id = self._attr(game, "id")
                self._my_color = self._attr(game, "color")
                self._log(f"匹配成功 game_id={self._game_id} color={self._my_color}")
                return

    async def challenge_user(self, username, time=10, increment=5, color="random"):
        """向指定 Lichess 用户发起对战，等待对方接受"""
        await self._check_and_abort_ongoing()
        self._running = True
        self._stop_event.clear()
        loop = asyncio.get_running_loop()

        def _stream():
            try:
                for event in self._client.board.stream_incoming_events():
                    if self._stop_event.is_set():
                        break
                    etype = self._attr(event, "type")
                    if etype in ("gameStart", "gameFinish", "challenge"):
                        asyncio.run_coroutine_threadsafe(self._events.put(event), loop)
            except Exception as e:
                self._log(f"事件流异常: {e}", "error")

        self._event_thread = threading.Thread(target=_stream, daemon=True)
        self._event_thread.start()

        def _challenge():
            return self._client.challenges.create(
                username=username,
                rated=False,
                clock_limit=time * 60,
                clock_increment=increment,
                color=color,
            )

        last_error = None
        for attempt in range(1, 4):
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, _challenge),
                    timeout=30,
                )
                self._log(f"已向 {username} 发起挑战，等待对方接受...")
                break
            except asyncio.TimeoutError:
                self._log(f"挑战请求超时(第{attempt}/3次)", "warning")
                if attempt == 3:
                    raise RuntimeError(f"挑战 {username} 超时")
                await asyncio.sleep(2)
            except Exception as e:
                last_error = e
                error_msg = str(e)
                if "404" in error_msg or "not found" in error_msg.lower():
                    raise RuntimeError(f"Lichess 用户不存在: {username}")
                if attempt == 3:
                    raise last_error
                await asyncio.sleep(2)

        try:
            event = await asyncio.wait_for(self._events.get(), timeout=120)
        except asyncio.TimeoutError:
            raise RuntimeError(f"挑战 {username} 超时，对方未响应")

        etype = self._attr(event, "type")
        if etype != "gameStart":
            if etype == "challenge":
                decline = self._attr(event, "challenge", {})
                reason = self._attr(decline, "declineReason", "未知")
                raise RuntimeError(f"挑战被拒绝: {reason}")
            raise RuntimeError(f"未预期的挑战响应: {etype}")

        game = self._attr(event, "game", {})
        self._game_id = self._attr(game, "id")
        self._my_color = self._attr(game, "color")
        self._log(f"对手已接受 game_id={self._game_id} color={self._my_color}")

    async def challenge_ai(self, level=3, time_min=10, increment_sec=5, color="random"):
        await self._check_and_abort_ongoing()
        self._running = True
        self._stop_event.clear()
        loop = asyncio.get_running_loop()

        def _challenge():
            return self._client.challenges.create_ai(
                level=level,
                clock_limit=time_min * 60,
                clock_increment=increment_sec,
                color=color,
                variant="standard",
            )

        last_error = None
        for attempt in range(1, 4):
            try:
                game = await asyncio.wait_for(
                    loop.run_in_executor(None, _challenge),
                    timeout=30,
                )
                self._game_id = self._attr(game, "id")
                self._my_color = self._attr(game, "color")
                if attempt > 1:
                    self._log(f"AI挑战成功(第{attempt}次) game_id={self._game_id} color={self._my_color}")
                else:
                    self._log(f"AI挑战成功 game_id={self._game_id} color={self._my_color}")
                return
            except asyncio.TimeoutError:
                self._log(f"AI挑战超时(第{attempt}/3次)", "warning")
                if attempt == 3:
                    raise RuntimeError("AI挑战超时")
                await asyncio.sleep(2)
            except Exception as e:
                last_error = e
                self._log(f"AI挑战网络异常(第{attempt}/3次): {e}", "error" if attempt == 3 else "info")
                if attempt < 3:
                    await asyncio.sleep(2)
        raise last_error

    async def start_game_stream(self):
        loop = asyncio.get_running_loop()
        stop = self._stop_event  # 捕获引用，确保线程始终检查创建时的 event

        def _stream():
            try:
                for state in self._client.board.stream_game_state(self._game_id):
                    if stop.is_set():
                        break
                    stype = self._attr(state, "type")
                    if stype == "gameState":
                        status = self._attr(state, "status", "started")
                        if status != "started":
                            self._game_ended.set()
                    asyncio.run_coroutine_threadsafe(self._states.put(state), loop)
            except Exception as e:
                self._log(f"对局状态流异常: {e}", "error")
                self._game_ended.set()

        self._state_thread = threading.Thread(target=_stream, daemon=True)
        self._state_thread.start()

        state = await asyncio.wait_for(self._states.get(), timeout=15)
        stype = self._attr(state, "type")
        if stype != "gameFull":
            self._log(f"未预期的初始状态: {stype}", "error")
            # 抛异常让调用方能感知失败，避免静默 return 导致 my_color 为 None
            raise RuntimeError(f"未预期的初始状态: {stype}，期望 gameFull")

        if not self._my_color:
            self._resolve_color_from_players(state)
        inner = self._attr(state, "state")
        moves_str = self._attr(inner, "moves", "")
        status = self._attr(inner, "status", "")
        existing_moves = moves_str.split() if moves_str else []
        """
        gameFull是订阅时刻的棋局快照：订阅前对手已走的步只在此出现，之后不会再单独推gameState
        此刻物理棋盘仍是初始局面，已同步步数记为0，并把快照中已有的步暂存
        交由wait_for_opponent_move依次转发给棋盘，避免对手首步丢失导致双方互等卡死
        """
        self._move_count = 0
        self._pending_opponent_moves = existing_moves
        self._log(f"gameFull color={self._my_color} status={status} moves={len(existing_moves)}")

        if status != "started" and not existing_moves:
            state2 = await asyncio.wait_for(self._states.get(), timeout=15)
            stype2 = self._attr(state2, "type")
            if stype2 == "gameState":
                inner2 = self._attr(state2, "status")
                moves_str2 = self._attr(state2, "moves", "")
                self._pending_opponent_moves = moves_str2.split()
                self._log(f"gameState status={inner2} moves={len(self._pending_opponent_moves)}")
            else:
                self._log(f"等待gameState但收到: {stype2}", "error")

    def _resolve_color_from_players(self, state):
        white = self._attr(state, "white")
        black = self._attr(state, "black")
        if not white or not black:
            return
        white_is_bot = self._is_bot(white)
        black_is_bot = self._is_bot(black)
        if white_is_bot and not black_is_bot:
            self._my_color = "black"
        elif black_is_bot and not white_is_bot:
            self._my_color = "white"

    @staticmethod
    def _is_bot(player):
        if isinstance(player, dict):
            return player.get("user", {}).get("title") == "BOT" or \
                   player.get("aiLevel") is not None or \
                   player.get("ai", False) is not False
        if hasattr(player, "title"):
            return player.title == "BOT"
        if hasattr(player, "aiLevel"):
            return player.aiLevel is not None
        return False

    async def make_move(self, uci):
        loop = asyncio.get_running_loop()
        last_error = None
        for attempt in range(1, 4):
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(
                        None, lambda: self._client.board.make_move(self._game_id, uci)
                    ),
                    timeout=15,
                )
                self._move_count += 1
                if attempt > 1:
                    self._log(f"走棋成功(第{attempt}次): {uci}")
                else:
                    self._log(f"走棋: {uci}")
                return
            except asyncio.TimeoutError:
                self._log(f"走棋超时(第{attempt}/3次): {uci}", "warning")
                if attempt == 3:
                    raise RuntimeError(f"走棋超时(已重试3次): {uci}")
                await asyncio.sleep(2)
            except Exception as e:
                last_error = e
                self._log(f"走棋网络异常(第{attempt}/3次): {e}", "error" if attempt == 3 else "info")
                if attempt < 3:
                    await asyncio.sleep(2)
        raise last_error

    async def resign(self):
        loop = asyncio.get_running_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._client.board.resign_game(self._game_id)),
                timeout=10,
            )
            self._log("投降")
        except asyncio.TimeoutError:
            self._log("投降请求超时", "warning")
        except Exception as e:
            self._log(f"投降异常: {e}", "error")

    async def wait_for_opponent_move(self):
        # 优先转发 gameFull 快照中订阅前已走、尚未同步到棋盘的步
        if self._pending_opponent_moves:
            opp_uci = self._pending_opponent_moves.pop(0)
            self._move_count += 1
            self._log(f"对手走棋(快照补发): {opp_uci}")
            return opp_uci

        for retry in range(3):
            try:
                while self._running and not self._stop_event.is_set():
                    state = await asyncio.wait_for(self._states.get(), timeout=60)
                    stype = self._attr(state, "type")
                    if stype == "gameState":
                        status = self._attr(state, "status", "started")
                        if status != "started":
                            self._game_ended.set()
                            self._log(f"对局结束 ({status})")
                            raise ConnectionAbortedError(f"gameFinish: {status}")
                        moves_str = self._attr(state, "moves", "")
                        moves = moves_str.split()
                        if len(moves) > self._move_count:
                            new_moves = moves[self._move_count:]
                            self._move_count = len(moves)
                            opp_uci = new_moves[-1]
                            self._log(f"对手走棋: {opp_uci}")
                            return opp_uci
                    elif stype == "gameFinish":
                        self._game_ended.set()
                        self._log("对局结束")
                        raise ConnectionAbortedError("gameFinish")
            except asyncio.TimeoutError:
                self._log(f"等待对手走棋超时，尝试重连第{retry + 1}次")
                await self._restart_state_stream()
            except Exception as e:
                self._log(f"状态流异常: {e}，尝试重连第{retry + 1}次")
                await self._restart_state_stream()
        raise ConnectionAbortedError("对手超时无响应")

    async def _restart_state_stream(self):
        # 通知旧线程退出（旧 event 保持 set 状态，旧线程会在下次迭代检查时退出）
        self._stop_event.set()

        # 清空队列中旧数据，避免乱序
        while not self._states.empty():
            self._states.get_nowait()

        # 为新线程创建独立的 stop event，避免与旧线程冲突
        self._stop_event = threading.Event()
        stop = self._stop_event
        loop = asyncio.get_running_loop()

        def _stream():
            try:
                for state in self._client.board.stream_game_state(self._game_id):
                    if stop.is_set():
                        break
                    stype = self._attr(state, "type")
                    if stype == "gameState":
                        status = self._attr(state, "status", "started")
                        if status != "started":
                            self._game_ended.set()
                    asyncio.run_coroutine_threadsafe(self._states.put(state), loop)
            except Exception as e:
                self._log(f"状态流重连异常: {e}", "error")
                self._game_ended.set()

        self._state_thread = threading.Thread(target=_stream, daemon=True)
        self._state_thread.start()

    def shutdown(self):
        self._running = False
        self._stop_event.set()
        self._game_ended.set()
        # 不调用 join()：此方法可能从 async 上下文调用，join 会阻塞事件循环。
        # 线程是 daemon 线程，在 stop_event 触发后的下一次流迭代中自然退出。

    def _log(self, msg, level="info"):
        getattr(self._logger, level)(f"[Lichess] {msg}")
