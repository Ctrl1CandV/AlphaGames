from sqlalchemy import String, Integer, Text, DateTime, LargeBinary, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class ChessRecord(Base):
    __tablename__ = "chessrecord"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    userName: Mapped[str | None] = mapped_column(String(255), index=True)
    createTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    data: Mapped[bytes | None] = mapped_column(LargeBinary)

    def __repr__(self):
        return f"<ChessRecord {self.id}: {self.userName}>"

class ChessUser(Base):
    __tablename__ = "chessuser"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    userName: Mapped[str | None] = mapped_column(String(255), index=True)
    battlePlatform: Mapped[str | None] = mapped_column(String(255), index=True)
    info: Mapped[str | None] = mapped_column(Text)
    createTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updateTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<ChessUser {self.id}: {self.userName}>"

class Device(Base):
    __tablename__ = "device"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    userName: Mapped[str | None] = mapped_column(String(255))
    sn: Mapped[str | None] = mapped_column(String(255), index=True, unique=True)
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

class ChessUploadMode(Base):
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
