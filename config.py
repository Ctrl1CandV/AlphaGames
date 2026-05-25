import os

class Config:
    TCP_HOST = os.environ.get("TCP_HOST", "0.0.0.0")
    TCP_PORT = int(os.environ.get("TCP_PORT", "8082"))

    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "mysql")
    MYSQL_DB = os.environ.get("MYSQL_DB", "alpha_platform")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
    DB_URL = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

    STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "stockfish-windows-x86-64-avx2.exe")
    STOCKFISH_THINK_TIME = float(os.environ.get("STOCKFISH_THINK_TIME", "0.5"))

    DEFAULT_UPLOAD_MODE = int(os.environ.get("DEFAULT_UPLOAD_MODE", "0"))
    DEFAULT_BATTLE_PLATFORM = os.environ.get("DEFAULT_BATTLE_PLATFORM", "stockfish")

    LICHESS_SEEK_TIME = int(os.environ.get("LICHESS_SEEK_TIME", "10"))
    LICHESS_SEEK_INCREMENT = int(os.environ.get("LICHESS_SEEK_INCREMENT", "5"))

    FLASK_HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
    FLASK_PORT = int(os.environ.get("FLASK_PORT", "8081"))
    SECRET_KEY = os.environ.get("SECRET_KEY", "alpha-games-secret-key")

    XUNFEI_APPID = os.environ.get("XUNFEI_APPID", "914a5257")
    XUNFEI_API_KEY = os.environ.get("XUNFEI_API_KEY", "dbe4766077d66c698524cd1314cf2c3f")
    XUNFEI_API_SECRET = os.environ.get("XUNFEI_API_SECRET", "YWE4NWRjMzg5OWRiZWU4ZWNjMmEwMTlh")
    XUNFEI_STT_URL = os.environ.get("XUNFEI_STT_URL", "wss://ws-api.xfyun.cn/v2/iat")

    XUNFEI_LLM_APPID = os.environ.get("XUNFEI_LLM_APPID", "914a5257")
    XUNFEI_LLM_URL = os.environ.get("XUNFEI_LLM_URL", "wss://spark-api.xf-yun.com/v1.1/chat")

    ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "sk_e638cbf8d1ca252e249fe97ea881e0653a84e3219f22ddeb")
    ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "sIirIlcPrAxbvQM9Icwj")
    ELEVENLABS_TTS_URL = os.environ.get("ELEVENLABS_TTS_URL", "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream")
