from collections.abc import AsyncGenerator
import logging
from typing import Optional
from urllib.parse import urlparse, urlunparse
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.database.models import Base

logger = logging.getLogger("freshguard.database")


def _mask_db_url(url: str) -> str:
    """Returns the database URL with any password replaced by '***'.

    Safe to pass to logging calls. Preserves scheme, host, port, and database
    name so the log entry still identifies the target without exposing credentials.

    Examples:
        postgresql+asyncpg://user:secret@host/db  ->  postgresql+asyncpg://user:***@host/db
        sqlite+aiosqlite:///./freshguard.db       ->  sqlite+aiosqlite:///./freshguard.db
    """
    try:
        parsed = urlparse(url)
        if parsed.password:
            # Replace netloc credentials while keeping the rest intact
            masked_netloc = parsed.hostname or ""
            if parsed.port:
                masked_netloc = f"{masked_netloc}:{parsed.port}"
            if parsed.username:
                masked_netloc = f"{parsed.username}:***@{masked_netloc}"
            masked = parsed._replace(netloc=masked_netloc)
            return urlunparse(masked)
    except Exception:
        # If URL parsing fails, return a safe placeholder rather than risking exposure
        return "<db-url-parse-error>"
    return url

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine(database_url: Optional[str] = None) -> AsyncEngine:
    """Returns or initializes the singleton AsyncEngine."""
    global _engine
    if _engine is None:
        url = database_url or get_settings().DATABASE_URL
        # SQLite async connection setup
        connect_args = {"check_same_thread": False} if "sqlite" in url else {}
        if "sqlite" in url and "///" in url and ":memory:" not in url:
            from pathlib import Path
            db_path_str = url.split("///", 1)[1]
            if db_path_str:
                db_path = Path(db_path_str).resolve()
                db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_async_engine(
            url,
            echo=False,
            future=True,
            connect_args=connect_args,
        )
        logger.info("Initialized async database engine with URL: %s", _mask_db_url(url))
    return _engine


def get_sessionmaker(engine: Optional[AsyncEngine] = None) -> async_sessionmaker[AsyncSession]:
    """Returns or initializes the singleton async_sessionmaker."""
    global _sessionmaker
    if _sessionmaker is None:
        eng = engine or get_engine()
        _sessionmaker = async_sessionmaker(
            bind=eng,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _sessionmaker


async def init_db(engine: Optional[AsyncEngine] = None) -> None:
    """Initializes tables in database schema."""
    eng = engine or get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified and initialized.")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for scoped transactional database sessions."""
    sm = get_sessionmaker()
    async with sm() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
