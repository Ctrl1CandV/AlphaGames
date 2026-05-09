from sqlalchemy import String, Integer, DateTime, LargeBinary, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class ChessRecord(Base):
    """ UserName: 中台用户名 CreateTime: 创建时间 Data: 棋谱数据 """
    __tablename__ = "chessrecord"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    userName: Mapped[str | None] = mapped_column(String(255), index=True)
    createTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    data: Mapped[bytes | None] = mapped_column(LargeBinary)

    def __repr__(self):
        return f"<ChessRecord {self.id}: {self.userName}>"

class ChessUser(Base):
    """
    userId: Python中台用户ID
    userName: Lichess 用户名
    token: Lichess API Token
    battlePlatform: 对战平台名称，如lichess
    """
    __tablename__ = "chessuser"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    userId: Mapped[int] = mapped_column(Integer, index=True)
    userName: Mapped[str | None] = mapped_column(String(255), index=True)
    token: Mapped[str | None] = mapped_column(String(255))
    battlePlatform: Mapped[str | None] = mapped_column(String(255), index=True)
    createTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updateTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<ChessUser {self.id}: {self.userName}>"

class Device(Base):
    """ SN: 棋谱SN码 """
    __tablename__ = "device"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    userName: Mapped[str | None] = mapped_column(String(255))
    sn: Mapped[str | None] = mapped_column(String(255), index=True)
    createTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updateTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Device {self.id}: {self.sn}>"

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    userName: Mapped[str | None] = mapped_column(String(255), index=True)
    password: Mapped[str] = mapped_column(String(255))
    createTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<User {self.id}: {self.userName}>"

class Admin(Base):
    __tablename__ = "admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    userName: Mapped[str | None] = mapped_column(String(255), index=True, unique=True)
    password: Mapped[str] = mapped_column(String(255))
    createTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Admin {self.id}: {self.userName}>"

class ChessUploadMode(Base):
    """ Type: 棋谱类型 UploadMode: 上传模式，代表步步上传，代表整局上传 """
    __tablename__ = "chessuploadmode"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    userName: Mapped[str | None] = mapped_column(String(255), index=True)
    createTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updateTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    type: Mapped[str | None] = mapped_column(String(255))
    uploadMode: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        CheckConstraint("uploadMode IN (0, 1)", name="check_upload_mode"),
    )

    def __repr__(self):
        return f"<ChessUploadMode {self.id}: {self.userName}>"

class GameConfig(Base):
    """
    对局配置：用户偏好设置，适用于本地AI、Lichess AI及人人对战
    engineColor: white/black/random
    aiLevel: AI难度 Lichess 1-8，Stockfish按比例映射
    time: 对局时间(分钟)
    increment: 每步加秒
    """
    __tablename__ = "gameconfig"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    userName: Mapped[str | None] = mapped_column(String(255), index=True, unique=True)
    engineColor: Mapped[str] = mapped_column(String(16), default="random")
    aiLevel: Mapped[int] = mapped_column(Integer, default=3)
    time: Mapped[int] = mapped_column(Integer, default=10)
    increment: Mapped[int] = mapped_column(Integer, default=5)
    createTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updateTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("engineColor IN ('white', 'black', 'random')", name="check_engine_color"),
        CheckConstraint("aiLevel BETWEEN 1 AND 8", name="check_ai_level"),
    )

    def __repr__(self):
        return f"<GameConfig {self.id}: {self.userName}>"
