from models import Device, ChessUploadMode, ChessRecord, ChessUser
from core.database import AsyncSessionFactory
from sqlalchemy import select
import logging

class DbService:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("AlphaGames")

    async def get_user_by_sn(self, sn: str) -> str | None:
        """ 根据设备SN获取用户名称 """
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(Device).where(Device.sn == sn)
            )
            device = result.scalars().first()
            if device:
                return device.userName
            return None

    async def get_upload_mode(self, username: str) -> int:
        """ 获取上传模式 """
        if not username:
            return 0
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(ChessUploadMode).where(ChessUploadMode.userName == username)
            )
            mode_record = result.scalars().first()
            if mode_record:
                return mode_record.uploadMode
            return 0

    async def save_chess_record(self, username: str, data: bytes):
        """ 保存棋谱 """
        async with AsyncSessionFactory() as session:
            record = ChessRecord(userName=username, data=data)
            session.add(record)
            await session.commit()
            self.logger.info(f"棋谱已保存: user={username} size={len(data)}")

    async def get_bind_info(self, user_id: int, platform: str) -> dict:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(ChessUser).where(
                    ChessUser.userId == user_id,
                    ChessUser.battlePlatform == platform,
                )
            )
            user = result.scalars().first()
            if user:
                return {
                    "lichess_username": user.userName,
                    "token": user.token,
                }
            return {}
