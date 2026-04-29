from logging.handlers import TimedRotatingFileHandler
import logging
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

def setup_logger(name="AlphaGames"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 — 按天切割，生成 server.log + server.log.2025-04-28
    os.makedirs(LOG_DIR, exist_ok=True)

    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, "server.log"),
        when="midnight",
        interval=1,
        backupCount=30,        # 保留最近 30 天
        encoding="utf-8",
        utc=False,
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.extMatch = r"^\d{4}-\d{2}-\d{2}$"
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
