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
    tcp_logger = setup_logger("AlphaGames.tcp", "tcp")
    web_logger = setup_logger("AlphaGames.web", "web")

    tcp_logger.info("AlphaGames 中台启动中...")

    # 初始化数据库表
    from core.database import init_db_sync
    init_db_sync()

    from core.database import SyncSessionFactory
    from models import Admin
    from werkzeug.security import generate_password_hash
    with SyncSessionFactory() as session:
        admin = session.query(Admin).filter_by(userName="admin").first()
        if not admin:
            # 目前默认为admin，admin，后期更改
            session.add(Admin(
                userName="admin",
                password=generate_password_hash("admin"),
            ))
            session.commit()
            web_logger.info("已创建系统管理员: admin/admin")

    # Flask 后台线程
    flask_thread = threading.Thread(target=_start_flask, daemon=True)
    flask_thread.start()
    web_logger.info(f"Flask Web 已启动 http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")

    # TCP 服务
    server = TcpServer(
        host=Config.TCP_HOST,
        port=Config.TCP_PORT,
        logger=tcp_logger,
    )
    await server.start()
    tcp_logger.info("AlphaGames 中台已启动，等待棋盘连接...")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        tcp_logger.info("收到停止信号")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
