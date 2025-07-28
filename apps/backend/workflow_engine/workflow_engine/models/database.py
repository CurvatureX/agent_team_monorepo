"""
Database connection and session management.
"""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from workflow_engine.core.config import get_settings

# Get settings
settings = get_settings()

# Ensure database_url is not None
database_url = settings.database_url
if not database_url:
    raise ValueError("Database URL is required but not configured")

# Default connect_args
connect_args = {
    "sslmode": settings.database_ssl_mode,
    "application_name": "workflow_engine",
    "connect_timeout": 30,
}

# In our Docker environment, we connect to the 'postgres' service directly without SSL.
# We can detect this and disable SSL arguments.
if "postgres" in database_url:
    connect_args = {
        "application_name": "workflow_engine",
        "connect_timeout": 30,
    }

# Create engine with enhanced configuration
engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_recycle=settings.database_pool_recycle,
    pool_pre_ping=True,
    echo=settings.database_echo,
    connect_args=connect_args
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
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