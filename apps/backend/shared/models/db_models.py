"""
Database Models (SQLAlchemy) for shared use across services.
数据库模型 - 跨服务共享的SQLAlchemy模型
"""

import uuid

try:
    from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
    from sqlalchemy.dialects.postgresql import ARRAY, UUID
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.sql import func, text

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

        # Primary key - UUID in database
        id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
        
        # Unique execution identifier
        execution_id = Column(String(255), nullable=False, unique=True, index=True)

        # Workflow reference - UUID in database
        workflow_id = Column(UUID(as_uuid=True), nullable=False, index=True)

        # Execution information
        status = Column(
            String(50), nullable=False, default="NEW"
        )  # NEW, RUNNING, SUCCESS, ERROR, CANCELED, WAITING
        mode = Column(String(50), nullable=False, default="MANUAL")  # MANUAL, TRIGGER, WEBHOOK, RETRY

        # Execution metadata
        triggered_by = Column(String(255), nullable=True)
        parent_execution_id = Column(String(255), nullable=True)
        start_time = Column(Integer, nullable=True)  # Unix timestamp
        end_time = Column(Integer, nullable=True)  # Unix timestamp
        
        # JSON fields
        run_data = Column(JSON, nullable=True)  # Runtime data
        # NOTE: "metadata" is mapped to workflow_metadata to avoid conflict with SQLAlchemy's metadata attribute
        workflow_metadata = Column("metadata", JSON, default=dict, nullable=True)  # General metadata
        execution_metadata = Column(
            JSON, default=dict
        )  # Additional metadata (avoid SQLAlchemy reserved word)
        error_message = Column(Text, nullable=True)  # Error message
        error_details = Column(JSON, nullable=True)  # Error details
        
        # Timestamps
        created_at = Column(DateTime(timezone=True), server_default=func.now())

        def __repr__(self):
            return f"<WorkflowExecution(id='{self.id}', execution_id='{self.execution_id}', workflow_id='{self.workflow_id}', status='{self.status}')>"

        def to_dict(self):
            """Convert model to dictionary."""
            # Use getattr to safely access attributes that might conflict with SQLAlchemy internals
            workflow_metadata = getattr(self, 'workflow_metadata', None)
            execution_metadata = getattr(self, 'execution_metadata', None)
            run_data = getattr(self, 'run_data', None)
            error_details = getattr(self, 'error_details', None)
            
            return {
                "id": str(self.id) if self.id else None,
                "execution_id": self.execution_id,
                "workflow_id": str(self.workflow_id) if self.workflow_id else None,
                "status": self.status,
                "mode": self.mode,
                "triggered_by": self.triggered_by,
                "parent_execution_id": self.parent_execution_id,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "metadata": dict(workflow_metadata) if workflow_metadata is not None else {},
                "execution_metadata": dict(execution_metadata) if execution_metadata is not None else {},
                "run_data": dict(run_data) if run_data is not None else None,
                "error_message": self.error_message,
                "error_details": dict(error_details) if error_details is not None else None,
                "created_at": self.created_at.isoformat() if self.created_at else None,
            }

    class WorkflowDB(Base):
        """Workflow database model."""

        __tablename__ = "workflows"

        # Primary key - Note: This should be UUID if the database uses UUID
        id = Column(String(36), primary_key=True, index=True)  # Keep as String for now to avoid breaking changes

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
