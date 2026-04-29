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
    - STOCKFISH_SKILL_LEVEL: AI技能等级 (0-20)
    - STOCKFISH_THINK_TIME: 思考时间（秒）
    使用场景：人机对战、AI分析、走棋建议
    """
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("AlphaGames")
        self._engine = None

    async def start(self):
        # 获取当前运行的事件循环
        loop = asyncio.get_running_loop()

        # 初始化stockfish引擎并设置难度等级
        self._engine = await loop.run_in_executor(
            None,
            lambda: chess.engine.SimpleEngine.popen_uci(Config.STOCKFISH_PATH),
        )
        self._engine.configure({"Skill Level": Config.STOCKFISH_SKILL_LEVEL})
        self._log(f"Stockfish 已启动 难度级别={Config.STOCKFISH_SKILL_LEVEL}")

    async def get_best_move(self, board):
        if self._engine is None:
            self._log("Stockfish 未启动，无法走棋", "error")
            return "e2e4"
        
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(        # 使用线程来启动stockfish引擎，防止阻塞
            None,
            lambda: self._engine.play(
                board.board,
                chess.engine.Limit(time=Config.STOCKFISH_THINK_TIME),
            ),
        )
        uci = result.move.uci()
        self._log(f"Stockfish 走棋: {uci}")
        return uci

    async def quit(self):
        if self._engine:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._engine.quit)
            self._engine = None
            self._log("Stockfish 已关闭")

    def _log(self, msg):
        self.logger.info(f"[Stockfish] {msg}")
