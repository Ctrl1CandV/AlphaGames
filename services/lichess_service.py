import threading
import berserk
import asyncio
import logging


class LichessSession:
    def __init__(self, token, logger=None):
        self._client = berserk.Client(berserk.TokenSession(token))
        self._logger = logger or logging.getLogger("AlphaGames")
        self._events = asyncio.Queue()
        self._states = asyncio.Queue()
        self._running = False
        self._game_id = None
        self._my_color = None
        self._move_count = 0
        self._event_thread = None
        self._state_thread = None

    @property
    def my_color(self):
        return self._my_color

    @property
    def game_id(self):
        return self._game_id

    async def _check_and_abort_ongoing(self):
        from requests import get, post

        token = self._client.session.token
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

        await loop.run_in_executor(None, _check)

    async def seek_until_found(self, time=10, increment=5):
        await self._check_and_abort_ongoing()
        self._running = True
        loop = asyncio.get_running_loop()

        def _stream():
            try:
                for event in self._client.board.stream_incoming_events():
                    if not self._running:
                        break
                    etype = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
                    if etype in ("gameStart", "gameFinish", "challenge"):
                        asyncio.run_coroutine_threadsafe(self._events.put(event), loop)
            except Exception as e:
                self._log(f"事件流异常: {e}", "error")

        self._event_thread = threading.Thread(target=_stream, daemon=True)
        self._event_thread.start()

        attempt = 0
        while self._running:
            attempt += 1
            self._log(f"第{attempt}次寻找对手...")
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self._client.board.seek(time=time, increment=increment),
                )
            except Exception as e:
                self._log(f"Seek异常: {e}", "error")
                await asyncio.sleep(2)
                continue

            found = False
            while not self._events.empty():
                event = self._events.get_nowait()
                etype = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
                if etype == "gameStart":
                    game = event.get("game") if isinstance(event, dict) else getattr(event, "game", {})
                    game_data = game if isinstance(game, dict) else game.__dict__ if hasattr(game, '__dict__') else {}
                    self._game_id = game_data.get("id") or getattr(game, "id", None)
                    self._my_color = game_data.get("color") or getattr(game, "color", None)
                    found = True
                    break
            if found:
                self._log(f"匹配成功 game_id={self._game_id} color={self._my_color}")
                return

    async def challenge_ai(self, level=3, time_min=10, increment_sec=5, color="random"):
        await self._check_and_abort_ongoing()
        self._running = True
        loop = asyncio.get_running_loop()

        def _challenge():
            return self._client.challenges.create_ai(
                level=level,
                clock_limit=time_min * 60,
                clock_increment=increment_sec,
                color=color,
                variant="standard",
            )

        game = await loop.run_in_executor(None, _challenge)
        game_data = game if isinstance(game, dict) else game.__dict__ if hasattr(game, '__dict__') else {}
        self._game_id = game_data.get("id") or getattr(game, "id", None)
        self._my_color = game_data.get("color") or getattr(game, "color", None)
        self._log(f"AI挑战成功 game_id={self._game_id} color={self._my_color}")

    async def start_game_stream(self):
        loop = asyncio.get_running_loop()

        def _stream():
            try:
                for state in self._client.board.stream_game_state(self._game_id):
                    if not self._running:
                        break
                    asyncio.run_coroutine_threadsafe(self._states.put(state), loop)
            except Exception as e:
                self._log(f"对局状态流异常: {e}", "error")

        self._state_thread = threading.Thread(target=_stream, daemon=True)
        self._state_thread.start()

        state = await asyncio.wait_for(self._states.get(), timeout=15)
        stype = state.get("type") if isinstance(state, dict) else getattr(state, "type", None)
        if stype != "gameFull":
            self._log(f"未预期的初始状态: {stype}", "error")
            return

        if not self._my_color:
            self._resolve_color_from_players(state)
        inner = state.get("state") if isinstance(state, dict) else getattr(state, "state", None)
        moves_str = inner.get("moves", "") if isinstance(inner, dict) else getattr(inner, "moves", "")
        status = inner.get("status", "") if isinstance(inner, dict) else getattr(inner, "status", "")
        self._move_count = len(moves_str.split()) if moves_str else 0
        self._log(f"gameFull color={self._my_color} status={status} moves={self._move_count}")

        if status != "started":
            state2 = await asyncio.wait_for(self._states.get(), timeout=15)
            stype2 = state2.get("type") if isinstance(state2, dict) else getattr(state2, "type", None)
            if stype2 == "gameState":
                inner2 = state2.get("status") if isinstance(state2, dict) else getattr(state2, "status", None)
                moves_str2 = state2.get("moves", "") if isinstance(state2, dict) else getattr(state2, "moves", "")
                moves = moves_str2.split()
                if len(moves) > self._move_count:
                    self._move_count = len(moves)
                self._log(f"gameState status={inner2} moves={self._move_count}")
            else:
                self._log(f"等待gameState但收到: {stype2}", "error")

    def _resolve_color_from_players(self, state):
        white = state.get("white") if isinstance(state, dict) else getattr(state, "white", None)
        black = state.get("black") if isinstance(state, dict) else getattr(state, "black", None)
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
        await loop.run_in_executor(None, lambda: self._client.board.make_move(self._game_id, uci))
        self._move_count += 1
        self._log(f"走棋: {uci}")

    async def resign(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self._client.board.resign_game(self._game_id))
        self._log("投降")

    async def wait_for_opponent_move(self):
        for retry in range(3):
            try:
                while self._running:
                    state = await asyncio.wait_for(self._states.get(), timeout=60)
                    stype = state.get("type") if isinstance(state, dict) else getattr(state, "type", None)
                    if stype == "gameState":
                        moves_str = state.get("moves", "") if isinstance(state, dict) else getattr(state, "moves", "")
                        moves = moves_str.split()
                        if len(moves) > self._move_count:
                            new_moves = moves[self._move_count:]
                            self._move_count = len(moves)
                            opp_uci = new_moves[-1]
                            self._log(f"对手走棋: {opp_uci}")
                            return opp_uci
                    elif stype == "gameFinish":
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
        self._running = True
        loop = asyncio.get_running_loop()

        def _stream():
            try:
                for state in self._client.board.stream_game_state(self._game_id):
                    if not self._running:
                        break
                    asyncio.run_coroutine_threadsafe(self._states.put(state), loop)
            except Exception as e:
                self._log(f"状态流重连异常: {e}", "error")

        self._state_thread = threading.Thread(target=_stream, daemon=True)
        self._state_thread.start()

    def shutdown(self):
        self._running = False

    def _log(self, msg, level="info"):
        getattr(self._logger, level)(f"[Lichess] {msg}")
