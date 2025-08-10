"""
Database Models (SQLAlchemy) for shared use across services.
数据库模型 - 跨服务共享的SQLAlchemy模型
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from sqlalchemy import (
        JSON,
        Boolean,
        Column,
        DateTime,
        Enum,
        Integer,
        String,
        Text,
        create_engine,
    )
    from sqlalchemy.dialects.postgresql import ARRAY, UUID
    from sqlalchemy.engine import Engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.sql import func, text

    # Create base class for database models
    Base = declarative_base()
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    # SQLAlchemy not available, create dummy implementation
    Base = type("Base", (), {})
    SQLALCHEMY_AVAILABLE = False

    # Dummy types for when SQLAlchemy is not available
    class DummyColumn:
        def __init__(self, *args, **kwargs):
            pass

    Column = DummyColumn
    String = lambda *args, **kwargs: None
    Integer = lambda *args, **kwargs: None
    Boolean = lambda *args, **kwargs: None
    Text = lambda *args, **kwargs: None
    JSON = lambda *args, **kwargs: None
    ARRAY = lambda *args, **kwargs: None
    UUID = lambda *args, **kwargs: None
    Enum = lambda *args, **kwargs: None
    DateTime = lambda *args, **kwargs: None

    class DummyFunc:
        @staticmethod
        def now():
            return None

    func = DummyFunc()
    text = lambda *args, **kwargs: None
    create_engine = lambda *args, **kwargs: None
    sessionmaker = lambda *args, **kwargs: None
    declarative_base = lambda *args, **kwargs: type("Base", (), {})

    # Dummy types
    Engine = type("Engine", (), {})
    Session = type("Session", (), {})


# Enums for workflow_scheduler models
class DeploymentStatusEnum(str, enum.Enum):
    """Deployment status enumeration"""

    PENDING = "pending"
    DEPLOYED = "deployed"
    FAILED = "failed"
    UNDEPLOYED = "undeployed"


class TriggerStatusEnum(str, enum.Enum):
    """Trigger status enumeration"""

    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class TriggerTypeEnum(str, enum.Enum):
    """Trigger type enumeration - UPDATED TO UNIFIED FORMAT"""

    CRON = "CRON"  # Updated from "TRIGGER_CRON"
    MANUAL = "MANUAL"  # Updated from "TRIGGER_MANUAL"
    WEBHOOK = "WEBHOOK"  # Updated from "TRIGGER_WEBHOOK"
    EMAIL = "EMAIL"  # Updated from "TRIGGER_EMAIL"
    GITHUB = "GITHUB"  # Updated from "TRIGGER_GITHUB"
    SLACK = "SLACK"  # Updated from "TRIGGER_SLACK"

    # Legacy aliases for backward compatibility
    TRIGGER_CRON = "CRON"
    TRIGGER_MANUAL = "MANUAL"
    TRIGGER_WEBHOOK = "WEBHOOK"
    TRIGGER_EMAIL = "EMAIL"
    TRIGGER_GITHUB = "GITHUB"
    TRIGGER_SLACK = "SLACK"


class WorkflowStatusEnum(str, enum.Enum):
    """Workflow execution status enumeration"""

    NEW = "NEW"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CANCELED = "CANCELED"
    WAITING = "WAITING"


class WorkflowModeEnum(str, enum.Enum):
    """Workflow execution mode enumeration"""

    MANUAL = "MANUAL"
    TRIGGER = "TRIGGER"
    WEBHOOK = "WEBHOOK"
    RETRY = "RETRY"


# Base model class with common fields and methods
class BaseModel:
    """Base model with common fields and methods"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, uuid.UUID):
                result[column.name] = str(value)
            elif isinstance(value, datetime):
                result[column.name] = value.isoformat()
            elif isinstance(value, enum.Enum):
                result[column.name] = value.value
            else:
                result[column.name] = value
        return result


# Existing shared models (improved)
class WorkflowExecution(Base, BaseModel):
    """Workflow execution database model."""

    __tablename__ = "workflow_executions"

    # Primary key - UUID in database
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))

    # Unique execution identifier
    execution_id = Column(String(255), nullable=False, unique=True, index=True)

    # Workflow reference - UUID in database
    workflow_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Execution information
    status = Column(Enum(WorkflowStatusEnum), nullable=False, default=WorkflowStatusEnum.NEW)
    mode = Column(Enum(WorkflowModeEnum), nullable=False, default=WorkflowModeEnum.MANUAL)

    # Execution metadata
    triggered_by = Column(String(255), nullable=True)
    parent_execution_id = Column(String(255), nullable=True, index=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # JSON fields with default factory
    run_data = Column(JSON, nullable=True, default=dict)
    workflow_metadata = Column("metadata", JSON, nullable=False, default=dict)
    execution_metadata = Column(JSON, nullable=False, default=dict)

    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<WorkflowExecution(id='{self.id}', execution_id='{self.execution_id}', workflow_id='{self.workflow_id}', status='{self.status}')>"

    @property
    def duration(self) -> Optional[float]:
        """Calculate execution duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def is_running(self) -> bool:
        """Check if execution is currently running"""
        return self.status == WorkflowStatusEnum.RUNNING

    @property
    def is_completed(self) -> bool:
        """Check if execution has completed (success or error)"""
        return self.status in [
            WorkflowStatusEnum.SUCCESS,
            WorkflowStatusEnum.ERROR,
            WorkflowStatusEnum.CANCELED,
        ]


class WorkflowDB(Base, BaseModel):
    """Workflow database model."""

    __tablename__ = "workflows"

    # Primary key - UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User information
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=True, index=True)

    # Basic workflow information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False, default="1.0.0")

    # Status and metadata
    active = Column(Boolean, nullable=False, default=True, index=True)
    workflow_data = Column(JSON, nullable=False, default=dict)
    tags = Column(ARRAY(String), nullable=False, default=list)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<WorkflowDB(id='{self.id}', name='{self.name}', user_id='{self.user_id}')>"

    def add_tag(self, tag: str) -> None:
        """Add a tag to the workflow"""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the workflow"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)


class NodeTemplateDB(Base, BaseModel):
    """Node Template Database Model."""

    __tablename__ = "node_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    node_type = Column(String(100), nullable=False, index=True)
    node_subtype = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False, default="1.0.0")
    is_system_template = Column(Boolean, nullable=False, default=False)

    # JSON fields with defaults
    default_parameters = Column(JSON, nullable=False, default=dict)
    required_parameters = Column(ARRAY(String), nullable=False, default=list)
    parameter_schema = Column(JSON, nullable=False, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<NodeTemplateDB(template_id='{self.template_id}', name='{self.name}', node_type='{self.node_type}')>"


# Workflow Scheduler models
class WorkflowDeployment(Base, BaseModel):
    """Workflow deployment records"""

    __tablename__ = "workflow_deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(String(255), unique=True, nullable=False, index=True)
    workflow_id = Column(String(255), nullable=False, index=True)

    # Deployment metadata
    status = Column(
        Enum(DeploymentStatusEnum), nullable=False, default=DeploymentStatusEnum.PENDING, index=True
    )
    workflow_spec = Column(JSON, nullable=False, default=dict)
    trigger_specs = Column(JSON, nullable=False, default=dict)

    # Audit fields
    deployed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Optional user context
    deployed_by = Column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<WorkflowDeployment(id={self.deployment_id}, workflow_id={self.workflow_id}, status={self.status.value})>"

    @property
    def is_active(self) -> bool:
        """Check if deployment is currently active"""
        return self.status == DeploymentStatusEnum.DEPLOYED


class TriggerExecution(Base, BaseModel):
    """Trigger execution history"""

    __tablename__ = "trigger_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(String(255), unique=True, nullable=False, index=True)
    workflow_id = Column(String(255), nullable=False, index=True)

    # Trigger information
    trigger_type = Column(Enum(TriggerTypeEnum), nullable=False, index=True)
    trigger_data = Column(JSON, nullable=True, default=dict)

    # Execution status
    status = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=True)

    # Timing information
    triggered_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Engine response
    engine_response = Column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<TriggerExecution(id={self.execution_id}, workflow_id={self.workflow_id}, type={self.trigger_type.value})>"

    @property
    def duration(self) -> Optional[float]:
        """Calculate execution duration in seconds"""
        if self.triggered_at and self.completed_at:
            return (self.completed_at - self.triggered_at).total_seconds()
        return None


class EmailMessage(Base, BaseModel):
    """Email message records for email triggers"""

    __tablename__ = "email_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(String(255), unique=True, nullable=False, index=True)

    # Email metadata
    subject = Column(Text, nullable=True)
    sender = Column(String(500), nullable=True, index=True)
    recipient = Column(String(500), nullable=True, index=True)
    date_received = Column(DateTime(timezone=True), nullable=True)

    # Content
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True, default=list)

    # Processing information
    workflow_id = Column(String(255), nullable=True, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_status = Column(String(50), nullable=True, index=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        subject_preview = self.subject[:50] if self.subject else "No Subject"
        return f"<EmailMessage(id={self.message_id}, subject={subject_preview}...)>"

    @property
    def is_processed(self) -> bool:
        """Check if email has been processed"""
        return self.processing_status == "processed"


class TriggerStatus(Base, BaseModel):
    """Current status of active triggers"""

    __tablename__ = "trigger_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(String(255), nullable=False, unique=True, index=True)
    trigger_type = Column(Enum(TriggerTypeEnum), nullable=False, index=True)

    # Status information
    status = Column(
        Enum(TriggerStatusEnum), nullable=False, default=TriggerStatusEnum.PENDING, index=True
    )
    last_execution = Column(DateTime(timezone=True), nullable=True)
    next_execution = Column(DateTime(timezone=True), nullable=True)

    # Configuration
    trigger_config = Column(JSON, nullable=False, default=dict)

    # Health information
    error_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<TriggerStatus(workflow_id={self.workflow_id}, type={self.trigger_type.value}, status={self.status.value})>"

    def increment_error(self, error_message: str) -> None:
        """Increment error count and update error information"""
        self.error_count += 1
        self.last_error = error_message
        self.last_error_at = datetime.utcnow()

    def reset_errors(self) -> None:
        """Reset error tracking"""
        self.error_count = 0
        self.last_error = None
        self.last_error_at = None


# Database connection utilities
def get_database_engine(
    database_url: str, echo: bool = False, pool_size: int = 5, max_overflow: int = 10
) -> Engine:
    """
    Create database engine with connection pooling.

    Args:
        database_url: Database connection URL
        echo: Enable SQL query logging
        pool_size: Number of connections to maintain in pool
        max_overflow: Maximum overflow connections allowed

    Returns:
        SQLAlchemy Engine instance
    """
    if not SQLALCHEMY_AVAILABLE:
        raise ImportError(
            "SQLAlchemy is not installed. Please install it to use database features."
        )

    return create_engine(
        database_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,  # Enable connection health checks
    )


def get_database_session(database_url: str, **engine_kwargs) -> Session:
    """
    Create database session.

    Args:
        database_url: Database connection URL
        **engine_kwargs: Additional arguments for engine creation

    Returns:
        SQLAlchemy Session instance
    """
    engine = get_database_engine(database_url, **engine_kwargs)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return SessionLocal()


def create_tables(engine: Optional[Engine] = None, database_url: Optional[str] = None) -> None:
    """
    Create all database tables.

    Args:
        engine: Existing database engine (optional)
        database_url: Database connection URL (required if engine not provided)

    Raises:
        ValueError: If neither engine nor database_url is provided
        ImportError: If SQLAlchemy is not available
    """
    if not SQLALCHEMY_AVAILABLE:
        raise ImportError(
            "SQLAlchemy is not installed. Please install it to use database features."
        )

    if engine is None:
        if database_url is None:
            raise ValueError("Either engine or database_url must be provided")
        engine = get_database_engine(database_url)

    Base.metadata.create_all(bind=engine)


def drop_tables(engine: Optional[Engine] = None, database_url: Optional[str] = None) -> None:
    """
    Drop all database tables. Use with caution!

    Args:
        engine: Existing database engine (optional)
        database_url: Database connection URL (required if engine not provided)

    Raises:
        ValueError: If neither engine nor database_url is provided
        ImportError: If SQLAlchemy is not available
    """
    if not SQLALCHEMY_AVAILABLE:
        raise ImportError(
            "SQLAlchemy is not installed. Please install it to use database features."
        )

    if engine is None:
        if database_url is None:
            raise ValueError("Either engine or database_url must be provided")
        engine = get_database_engine(database_url)

    Base.metadata.drop_all(bind=engine)


# Export all models and utilities
__all__ = [
    # Base classes
    "Base",
    "BaseModel",
    # Enums
    "DeploymentStatusEnum",
    "TriggerStatusEnum",
    "TriggerTypeEnum",
    "WorkflowStatusEnum",
    "WorkflowModeEnum",
    # Models
    "WorkflowExecution",
    "WorkflowDB",
    "NodeTemplateDB",
    "WorkflowDeployment",
    "TriggerExecution",
    "EmailMessage",
    "TriggerStatus",
    # Utilities
    "get_database_engine",
    "get_database_session",
    "create_tables",
    "drop_tables",
    "SQLALCHEMY_AVAILABLE",
]
