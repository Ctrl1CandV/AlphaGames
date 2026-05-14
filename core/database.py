from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from config import Config

# 惰性初始化
_engine, _session_factory, _sync_engine = None, None, None

def _get_engine():
    """ 初始化一个全局的异步数据库引擎 """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            Config.DB_URL, echo=False, pool_size=20, max_overflow=40,
        )
    return _engine

def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        # 返回一个会话工厂类，expire_on_commit=False表示事务提交后不销毁对象上的属性缓存
        _session_factory = async_sessionmaker(_get_engine(), expire_on_commit=False)
    return _session_factory

def AsyncSessionFactory():
    return _get_session_factory()()

def _get_sync_engine():
    """ 初始化一个全局的同步数据库引擎 """
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
        # 在异步连接上同步执行建表操作
        await conn.run_sync(Base.metadata.create_all)

def _migrate_elo():
    """将 gameconfig.aiLevel 从旧 1-8 约束迁移到 800-2900"""
    from sqlalchemy import text
    _ELO_MAP = {1: 800, 2: 1100, 3: 1500, 4: 1800, 5: 2100, 6: 2400, 7: 2700, 8: 2900}
    with SyncSessionFactory() as s:
        try:
            s.execute(text("ALTER TABLE gameconfig DROP CHECK check_ai_level"))
        except Exception:
            pass
        for old, new in _ELO_MAP.items():
            s.execute(text("UPDATE gameconfig SET aiLevel = :n WHERE aiLevel = :o"), {"n": new, "o": old})
        s.execute(text("ALTER TABLE gameconfig ADD CONSTRAINT check_ai_level CHECK (aiLevel BETWEEN 800 AND 2900)"))
        s.commit()

def init_db_sync():
    from models import Base
    Base.metadata.create_all(_get_sync_engine())
    # _migrate_elo()

def init_default_admin():
    from werkzeug.security import generate_password_hash
    from models import Admin
    with SyncSessionFactory() as session:
        if not session.query(Admin).filter_by(userName="admin").first():
            session.add(Admin(
                userName="admin",
                password=generate_password_hash("admin"),
            ))
            session.commit()
            return True
    return False
