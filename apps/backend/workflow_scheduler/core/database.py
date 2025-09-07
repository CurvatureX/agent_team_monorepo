"""
Database configuration and session management
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable

import asyncpg
from sqlalchemy.engine.events import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.models.db_models import Base
from workflow_scheduler.core.config import settings

logger = logging.getLogger(__name__)

import uuid

# Create clean database URL without any problematic parameters
from sqlalchemy.pool import NullPool

# Generate unique application name to avoid conflicts
unique_suffix = str(uuid.uuid4())[:8]

# Create simple asyncpg URL without URL parameters that might cause issues
base_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

# Remove any existing URL parameters to avoid conflicts
if "?" in base_url:
    base_url = base_url.split("?")[0]

engine = create_async_engine(
    base_url,
    echo=settings.debug,
    # Use NullPool to avoid connection reuse issues with pgbouncer
    poolclass=NullPool,
    # Disable prepared statements for pgbouncer compatibility
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "command_timeout": 30,
        "server_settings": {
            "application_name": f"workflow_scheduler_{unique_suffix}",
        },
    },
    # Additional SQLAlchemy-level settings
    execution_options={
        "compiled_cache": {},  # Disable compiled statement cache
        "autocommit": False,
    },
)


# Add event listener to ensure prepared statements are disabled on every connection
@event.listens_for(engine.sync_engine, "connect")
def set_asyncpg_pragmas(dbapi_connection, connection_record):
    """Disable prepared statements on connection"""
    if hasattr(dbapi_connection, "_connection"):
        # This is an asyncpg connection wrapper
        conn = dbapi_connection._connection
        if hasattr(conn, "_statement_cache"):
            conn._statement_cache.clear()
        if hasattr(conn, "_prepared_stmt_cache"):
            conn._prepared_stmt_cache.clear()


# Create session factory with pgbouncer-compatible settings
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    # Prevent session-level prepared statement caching
    autoflush=False,
)


async def create_tables():
    """Create database tables"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}", exc_info=True)
        raise


async def drop_tables():
    """Drop database tables (for testing)"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("Database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}", exc_info=True)
        raise


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic cleanup"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session"""
    async with get_db_session() as session:
        yield session


class DatabaseManager:
    """Database manager for workflow_scheduler"""

    def __init__(self):
        self.engine = engine
        self.session_factory = async_session_factory

    async def initialize(self):
        """Initialize database connection and create tables"""
        try:
            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute("SELECT 1")

            # Create tables if they don't exist
            await create_tables()

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    async def health_check(self) -> dict:
        """Check database health"""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute("SELECT 1")
                result.fetchone()

            return {"status": "healthy", "database": "postgresql", "engine": "asyncpg"}

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "database": "postgresql",
                "engine": "asyncpg",
            }

    async def cleanup(self):
        """Cleanup database connections"""
        try:
            await self.engine.dispose()
            logger.info("Database connections disposed")
        except Exception as e:
            logger.error(f"Error disposing database connections: {e}", exc_info=True)
