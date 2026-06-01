from datetime import datetime
import logging
import os
import re

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


class DailyFileHandler(logging.Handler):
    """每天自动切换文件，只产生 logs/{sub}/{name}.log.{YYYY-MM-DD} 格式的文件"""

    def __init__(self, sub_dir, basename, backup_count=30):
        super().__init__()
        self._dir = os.path.join(LOG_DIR, sub_dir)
        self._base = basename
        self._backup = backup_count
        self._date = None
        self._fh = None

    def _rotate(self, today):
        os.makedirs(self._dir, exist_ok=True)
        if self._fh:
            self._fh.close()
        self._fh = open(os.path.join(self._dir, f"{self._base}.log.{today}"), "a", encoding="utf-8")
        self._date = today
        self._cleanup()

    def _cleanup(self):
        prefix = f"{self._base}.log."
        files = sorted(
            [f for f in os.listdir(self._dir) if f.startswith(prefix)],
            reverse=True,
        )
        for old in files[self._backup:]:
            os.remove(os.path.join(self._dir, old))

    def emit(self, record):
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._date:
            self._rotate(today)
        self._fh.write(self.format(record) + "\n")
        self._fh.flush()

    def close(self):
        if self._fh:
            self._fh.close()
        super().close()


def _new_logger(name):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


def setup_logger(name, log_basename, sub_dir="tcp"):
    """logs/{sub_dir}/{log_basename}.log.{date}"""
    logger = _new_logger(name)
    if len(logger.handlers) > 1:
        return logger
    fh = DailyFileHandler(sub_dir, log_basename)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logger.handlers[0].formatter)
    logger.addHandler(fh)
    return logger


def setup_sn_logger(sn_code):
    """logs/sn/{sn_code}.log.{date}"""
    safe = re.sub(r"[^\w\-]", "_", sn_code) if sn_code else "unknown"
    logger = _new_logger(f"AlphaGames.sn.{safe}")
    if len(logger.handlers) > 1:
        return logger
    fh = DailyFileHandler("sn", safe)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logger.handlers[0].formatter)
    logger.addHandler(fh)
    return logger
