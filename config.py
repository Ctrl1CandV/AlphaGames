class Config:
    TCP_HOST = "0.0.0.0"
    TCP_PORT = 8480

    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'mysql'        # 开发环境暂时明文硬编码
    MYSQL_DB = 'alpha_platform'
    DB_URL = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@127.0.0.1:3306/{MYSQL_DB}"

    STOCKFISH_PATH = "stockfish-windows-x86-64-avx2.exe"
    STOCKFISH_THINK_TIME = 0.5

    DEFAULT_UPLOAD_MODE = 0
    DEFAULT_BATTLE_PLATFORM = "stockfish"

    LICHESS_SEEK_TIME = 10
    LICHESS_SEEK_INCREMENT = 5

    FLASK_HOST = "127.0.0.1"
    FLASK_PORT = 5000
    SECRET_KEY = "alpha-games-secret-key"   # 开发环境暂时明文硬编码

    XUNFEI_APPID = "914a5257"
    XUNFEI_API_KEY = "dbe4766077d66c698524cd1314cf2c3f"
    XUNFEI_API_SECRET = "YWE4NWRjMzg5OWRiZWU4ZWNjMmEwMTlh"
    XUNFEI_STT_URL = "wss://ws-api.xfyun.cn/v2/iat"

    XUNFEI_LLM_APPID = "914a5257"
    XUNFEI_LLM_URL = "wss://spark-api.xf-yun.com/v1.1/chat"

    ELEVENLABS_API_KEY = "sk_e638cbf8d1ca252e249fe97ea881e0653a84e3219f22ddeb"
    ELEVENLABS_VOICE_ID = "sIirIlcPrAxbvQM9Icwj"
    ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
