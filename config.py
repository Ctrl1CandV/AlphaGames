class Config:
    TCP_HOST = "0.0.0.0"
    TCP_PORT = 8480

    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'mysql'
    MYSQL_DB = 'alpha_platform'
    DB_URL = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@127.0.0.1:3306/{MYSQL_DB}"

    STOCKFISH_PATH = "stockfish-windows-x86-64-avx2.exe"
    STOCKFISH_SKILL_LEVEL = 10
    STOCKFISH_THINK_TIME = 0.5

    DEFAULT_UPLOAD_MODE = 0
    DEFAULT_BATTLE_PLATFORM = "stockfish"

    LICHESS_SEEK_TIME = 10
    LICHESS_SEEK_INCREMENT = 5

    FLASK_HOST = "127.0.0.1"
    FLASK_PORT = 5000
    SECRET_KEY = "alpha-games-secret-key"
