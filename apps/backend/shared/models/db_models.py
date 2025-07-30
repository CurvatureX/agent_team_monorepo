"""
Database Models (SQLAlchemy) for shared use across services.
数据库模型 - 跨服务共享的SQLAlchemy模型
"""

import uuid

try:
    from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
    from sqlalchemy.dialects.postgresql import ARRAY, UUID
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.sql import func

    # Create base class for database models
    Base = declarative_base()
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    # SQLAlchemy not available, create dummy classes
    Base = None
    SQLALCHEMY_AVAILABLE = False

    # Dummy functions for when SQLAlchemy is not available
    def Column(*args, **kwargs):
        return None

    def String(*args, **kwargs):
        return None

    def Integer(*args, **kwargs):
        return None

    def Boolean(*args, **kwargs):
        return None

    def Text(*args, **kwargs):
        return None

    def JSON(*args, **kwargs):
        return None

    def ARRAY(*args, **kwargs):
        return None

    def UUID(*args, **kwargs):
        return None


if SQLALCHEMY_AVAILABLE:

    class WorkflowExecution(Base):
        """Workflow execution database model."""

        __tablename__ = "workflow_executions"

        # Primary key
        execution_id = Column(String(36), primary_key=True, index=True)

        # Workflow reference
        workflow_id = Column(String(36), nullable=False, index=True)

        # Execution information
        status = Column(
            String(50), nullable=False, default="NEW"
        )  # NEW, RUNNING, COMPLETED, FAILED, CANCELED
        mode = Column(String(50), nullable=False, default="SYNC")  # SYNC, ASYNC

        # Execution metadata
        triggered_by = Column(String(255), nullable=True)
        start_time = Column(Integer, nullable=True)  # Unix timestamp
        end_time = Column(Integer, nullable=True)  # Unix timestamp
        execution_metadata = Column(
            JSON, default=dict
        )  # Additional metadata (avoid SQLAlchemy reserved word)

        # Execution results
        run_data = Column(JSON, nullable=True)  # Runtime data
        error_message = Column(Text, nullable=True)  # Error message
        error_details = Column(JSON, nullable=True)  # Error details

        def __repr__(self):
            return f"<WorkflowExecution(execution_id='{self.execution_id}', workflow_id='{self.workflow_id}', status='{self.status}')>"

        def to_dict(self):
            """Convert model to dictionary."""
            return {
                "execution_id": self.execution_id,
                "workflow_id": self.workflow_id,
                "status": self.status,
                "mode": self.mode,
                "triggered_by": self.triggered_by,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "metadata": self.execution_metadata,
                "run_data": self.run_data,
                "error_message": self.error_message,
                "error_details": self.error_details,
            }

    class WorkflowDB(Base):
        """Workflow database model."""

        __tablename__ = "workflows"

        # Primary key
        id = Column(String(36), primary_key=True, index=True)

        # User information
        user_id = Column(String(36), nullable=False, index=True)
        session_id = Column(String(36), nullable=True, index=True)  # 会话ID

        # Basic workflow information
        name = Column(String(255), nullable=False)
        description = Column(Text, nullable=True)
        version = Column(String(50), default="1.0.0")

        # Status and metadata
        active = Column(Boolean, default=True)
        workflow_data = Column(JSON, nullable=False)  # Store protobuf as JSONB
        tags = Column(ARRAY(Text), default=list)  # Store tags as PostgreSQL text array

        # Timestamps
        created_at = Column(Integer, nullable=False)  # Unix timestamp
        updated_at = Column(Integer, nullable=False)  # Unix timestamp

        def __repr__(self):
            return f"<WorkflowDB(id='{self.id}', name='{self.name}', user_id='{self.user_id}')>"

        def to_dict(self):
            """Convert model to dictionary."""
            return {
                "id": self.id,
                "user_id": self.user_id,
                "session_id": self.session_id,
                "name": self.name,
                "description": self.description,
                "version": self.version,
                "active": self.active,
                "workflow_data": self.workflow_data,
                "tags": self.tags,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }

    class NodeTemplateDB(Base):
        """Node Template Database Model."""

        __tablename__ = "node_templates"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        template_id = Column(String, unique=True, nullable=False)
        name = Column(String, nullable=False)
        description = Column(String)
        category = Column(String)
        node_type = Column(String, nullable=False)
        node_subtype = Column(String, nullable=False)
        version = Column(String, default="1.0.0")
        is_system_template = Column(Boolean, default=False)
        default_parameters = Column(JSON)
        required_parameters = Column(ARRAY(String))
        parameter_schema = Column(JSON)

        def __repr__(self):
            return f"<NodeTemplateDB(template_id='{self.template_id}', name='{self.name}', node_type='{self.node_type}')>"

        def to_dict(self):
            """Convert model to dictionary."""
            return {
                "id": str(self.id),
                "template_id": self.template_id,
                "name": self.name,
                "description": self.description,
                "category": self.category,
                "node_type": self.node_type,
                "node_subtype": self.node_subtype,
                "version": self.version,
                "is_system_template": self.is_system_template,
                "default_parameters": self.default_parameters,
                "required_parameters": self.required_parameters,
                "parameter_schema": self.parameter_schema,
            }

else:
    # Dummy classes when SQLAlchemy is not available
    class WorkflowExecution:
        """Dummy WorkflowExecution class when SQLAlchemy is not available."""

        pass

    class WorkflowDB:
        """Dummy WorkflowDB class when SQLAlchemy is not available."""

        pass

    class NodeTemplateDB:
        """Dummy NodeTemplateDB class when SQLAlchemy is not available."""

        pass
