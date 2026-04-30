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

    async def seek_until_found(self, time=10, increment=5):
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
        if stype == "gameFull":
            if not self._my_color:
                self._my_color = state.get("color") if isinstance(state, dict) else getattr(state, "color", None)
            inner = state.get("state") if isinstance(state, dict) else getattr(state, "state", None)
            moves_str = inner.get("moves", "") if isinstance(inner, dict) else getattr(inner, "moves", "")
            self._move_count = len(moves_str.split()) if moves_str else 0
            self._log(f"对局开始 color={self._my_color} initial_moves={self._move_count}")
        else:
            self._log(f"未预期的初始状态: {stype}", "error")

    async def make_move(self, uci):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self._client.board.make_move(self._game_id, uci))
        self._log(f"走棋: {uci}")

    async def resign(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self._client.board.resign_game(self._game_id))
        self._log("投降")

    async def wait_for_opponent_move(self):
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

    def shutdown(self):
        self._running = False

    def _log(self, msg, level="info"):
        getattr(self._logger, level)(f"[Lichess] {msg}")
