from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()
engine = create_async_engine(
    settings.effective_database_url,
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def _migrate_admin_users(sync_conn):
    """Add name, email to admin_users if missing (for existing DBs)."""
    from sqlalchemy import text
    try:
        sync_conn.execute(text("ALTER TABLE admin_users ADD COLUMN name VARCHAR(128) DEFAULT ''"))
    except Exception:
        pass
    try:
        sync_conn.execute(text("ALTER TABLE admin_users ADD COLUMN email VARCHAR(256) DEFAULT ''"))
    except Exception:
        pass


def _migrate_chat_systems(sync_conn):
    """Add dify_chatbot_token to chat_systems (existing DBs). api_key column left for compat, not used."""
    from sqlalchemy import text
    try:
        sync_conn.execute(text("ALTER TABLE chat_systems ADD COLUMN dify_chatbot_token VARCHAR(128) DEFAULT ''"))
    except Exception:
        pass
    try:
        sync_conn.execute(text("ALTER TABLE chat_systems ADD COLUMN created_by VARCHAR(64)"))
    except Exception:
        pass


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_admin_users)
        await conn.run_sync(_migrate_chat_systems)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
