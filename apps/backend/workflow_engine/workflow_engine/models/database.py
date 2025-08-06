"""
Database connection and session management - now using shared models.
"""

# Import Base from shared models
import sys
from pathlib import Path
from typing import Generator
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from workflow_engine.core.config import get_settings

backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.db_models import Base

# Get settings
settings = get_settings()

# Ensure database_url is not None
database_url = settings.database_url
if not database_url:
    raise ValueError("Database URL is required but not configured")

# Parse the database URL to reliably identify the hostname
parsed_url = urlparse(database_url)

# Default connect_args for remote connections (like Supabase)
connect_args = {
    "sslmode": settings.database_ssl_mode,
    "application_name": "workflow_engine",
    "connect_timeout": 30,
}

# If connecting to the local Docker service, disable SSL.
if parsed_url.hostname == "postgres":
    connect_args = {
        "application_name": "workflow_engine",
        "connect_timeout": 30,
    }

# Create engine with enhanced configuration
# Temporarily enable SQL echo for debugging
engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_recycle=settings.database_pool_recycle,
    pool_pre_ping=True,
    echo=True,  # Force SQL logging for debugging
    connect_args=connect_args,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    import sys
    print(f"[DB] Creating database session", file=sys.stderr, flush=True)
    db = SessionLocal()
    print(f"[DB] Database session created: {type(db)}", file=sys.stderr, flush=True)
    try:
        yield db
    finally:
        print(f"[DB] Closing database session", file=sys.stderr, flush=True)
        db.close()


def get_db_session() -> Session:
    """Get database session (direct)."""
    return SessionLocal()


def init_db():
    """Initialize database tables."""
    try:
        # Test connection first
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"Database connection successful: {result.fetchone()}")

        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully")

    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise


def test_db_connection():
    """Test database connection."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"Connected to PostgreSQL: {version}")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


def close_db():
    """Close database connections."""
    engine.dispose()
    print("Database connections closed")
