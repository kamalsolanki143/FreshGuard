"""Database schema migration and verification script for FreshGuard.

Supports both SQLite (local development) and PostgreSQL (Neon / Render production).
Ensures all required tables, indexes, and constraints exist.
"""

import asyncio
import logging
import sys
from typing import Optional
from sqlalchemy import text
from app.config import get_settings
from app.database.database import _mask_db_url, get_engine, init_db, normalize_database_url
from app.database.models import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("freshguard.migrate")


async def run_migrations(database_url: Optional[str] = None) -> bool:
    """Runs schema initialization and validates database connectivity."""
    settings = get_settings()
    raw_url = database_url or settings.DATABASE_URL
    norm_url = normalize_database_url(raw_url)
    masked = _mask_db_url(norm_url)

    logger.info("Starting FreshGuard database schema migration for: %s", masked)

    try:
        engine = get_engine(norm_url)

        # 1. Connectivity test
        logger.info("Testing database connection...")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            if val != 1:
                raise RuntimeError(f"Unexpected ping result: {val}")
        logger.info("Database connection test succeeded (SELECT 1 returned 1).")

        # 2. Table creation / migration
        logger.info("Verifying and applying schema tables...")
        await init_db(engine)

        # 3. Report discovered tables
        table_names = list(Base.metadata.tables.keys())
        logger.info(
            "Schema verification complete. Verified tables (%d): %s",
            len(table_names),
            ", ".join(table_names),
        )

        await engine.dispose()
        logger.info("Database migration finished successfully.")
        return True

    except Exception as exc:
        logger.error("Database migration failed: %s", exc, exc_info=True)
        return False


def main() -> None:
    """Entry point for CLI execution."""
    db_url = sys.argv[1] if len(sys.argv) > 1 else None
    success = asyncio.run(run_migrations(db_url))
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
