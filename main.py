from core.tcp_server import TcpServer
from utils.logger import setup_logger
from config import Config
import threading
import asyncio


def _start_flask():
    from web import create_app
    app = create_app()
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=False,
        use_reloader=False,
    )


async def main():
    logger = setup_logger("AlphaGames")
    logger.info("AlphaGames 中台启动中...")

    # 初始化数据库表
    from core.database import init_db_sync
    init_db_sync()

    # Flask 后台线程
    flask_thread = threading.Thread(target=_start_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Flask Web 已启动 http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")

    # TCP 服务
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
