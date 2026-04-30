from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from config import Config

_engine = None
_session_factory = None
_sync_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            Config.DB_URL, echo=False, pool_size=20, max_overflow=40,
        )
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(_get_engine(), expire_on_commit=False)
    return _session_factory


def AsyncSessionFactory():
    return _get_session_factory()()


def _get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        url = Config.DB_URL.replace("+aiomysql", "+pymysql")
        _sync_engine = create_engine(url=url, pool_size=10, max_overflow=20)
    return _sync_engine


def SyncSessionFactory():
    return Session(_get_sync_engine())


async def init_db():
    from models import Base
    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db_sync():
    from models import Base
    Base.metadata.create_all(_get_sync_engine())
