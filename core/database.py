from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config import Config

_engine, _session_factory = None, None

def _get_engine():
    """ 获取数据库引擎 """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            Config.DB_URL,
            echo=False,
            pool_size=20,
            max_overflow=40,
        )
    return _engine


def _get_session_factory():
    """ 获取会话工厂 """
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(), expire_on_commit=False
        )
    return _session_factory


def AsyncSessionFactory():
    """ 创建数据库会话 """
    return _get_session_factory()()


async def init_db():
    """ 初始化数据库 """
    from models import Base
    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
