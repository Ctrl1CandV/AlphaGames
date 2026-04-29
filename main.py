from core.tcp_server import TcpServer
from utils.logger import setup_logger
from config import Config
import asyncio

async def main():
    logger = setup_logger("AlphaGames")

    logger.info("AlphaGames 中台启动中...")

    server = TcpServer(
        host=Config.TCP_HOST,
        port=Config.TCP_PORT,
        logger=logger,
    )
    await server.start()

    logger.info("AlphaGames 中台已启动，等待棋盘连接...")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("收到停止信号")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
