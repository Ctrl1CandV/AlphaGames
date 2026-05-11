from config import Config
import chess.engine
import asyncio
import logging

class StockfishEngine:
    """
    Stockfish国际象棋AI引擎处理器
    功能：异步调用Stockfish引擎计算最佳走棋
    主要方法：start(): 启动引擎、get_best_move(): 计算最佳走棋、quit(): 关闭引擎
    配置项：
    - STOCKFISH_PATH: 引擎路径
    - STOCKFISH_THINK_TIME: 思考时间（秒）
    使用场景：人机对战、AI分析、走棋建议
    """
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("AlphaGames")
        self._engine = None

    async def start(self):
        # 获取当前运行的事件循环
        loop = asyncio.get_running_loop()

        # 初始化stockfish引擎
        self._engine = await loop.run_in_executor(
            None,
            lambda: chess.engine.SimpleEngine.popen_uci(Config.STOCKFISH_PATH),
        )
        self._log("Stockfish 已启动")

    async def get_best_move(self, board):
        if self._engine is None:
            self._log("Stockfish 未启动，无法走棋", "error")
            return "e2e4"
        
        loop = asyncio.get_running_loop()
        coro = loop.run_in_executor(
            None,
            lambda: self._engine.play(
                board.board,
                chess.engine.Limit(time=Config.STOCKFISH_THINK_TIME),
            ),
        )
        result = await asyncio.wait_for(coro, timeout=10.0)
        uci = result.move.uci()
        self._log(f"Stockfish 走棋: {uci}")
        return uci

    def set_skill_level(self, level):
        if self._engine:
            self._engine.configure({"Skill Level": level})

    async def quit(self):
        if self._engine:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._engine.quit)
            self._engine = None
            self._log("Stockfish 已关闭")

    def _log(self, msg):
        self.logger.info(f"[Stockfish] {msg}")

class StockfishPool:
    """
    Stockfish引擎池 — 按需借用，用完归还
    避免每个会话长期占用一个子进程，降低内存，提高并发量
    """
    def __init__(self, pool_size=4, logger=None):
        self._pool_size = pool_size
        self._logger = logger or logging.getLogger("AlphaGames")
        self._available = []        # 空闲引擎栈
        self._lock = asyncio.Lock() # 保护_available的并发读写安全

    async def acquire(self):
        """ 从池中获取一个已启动的引擎，池空则新建 """
        async with self._lock:
            if self._available:
                engine = self._available.pop()
                self._log(f"复用引擎 (剩余{len(self._available)})")
                return engine
            
        engine = StockfishEngine(logger=self._logger)
        try:
            # 防止出现内存或CPU空间不足导致的引擎加载失败
            await engine.start()
        except Exception as e:
            self._log(f"引擎创建失败: {e}", "error")
            raise RuntimeError(f"无法启动 Stockfish 引擎: {e}") from e
        self._log(f"新建引擎 (池容量{self._pool_size})")
        return engine

    async def release(self, engine):
        """ 归还引擎到池中，超出容量则关闭 """
        async with self._lock:
            if len(self._available) < self._pool_size:
                self._available.append(engine)
                self._log(f"归还引擎 (池内{len(self._available)})")
            else:
                await engine.quit()

    async def shutdown(self):
        """ 关闭池内所有引擎，通常在应用退出时调用 """
        async with self._lock:
            for engine in self._available:
                await engine.quit()
            self._available.clear()
            self._log("引擎池已关闭")

    def _log(self, msg):
        self._logger.info(f"[StockfishPool] {msg}")

# 模块级单例：整个应用共享一个引擎池，避免重复创建
_stockfish_pool = None
def get_stockfish_pool(logger=None):
    """
    获取全局唯一的 StockfishPool 实例（懒汉式单例）。
    注意：此实现非线程安全，适合在 asyncio 单线程事件循环中使用。
    """
    global _stockfish_pool
    if _stockfish_pool is None:
        _stockfish_pool = StockfishPool(logger=logger)
    return _stockfish_pool
