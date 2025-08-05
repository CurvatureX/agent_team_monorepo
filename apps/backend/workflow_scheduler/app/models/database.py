"""
Database models for workflow_scheduler
Using SQLAlchemy for data persistence
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class DeploymentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    DEPLOYED = "deployed"
    FAILED = "failed"
    UNDEPLOYED = "undeployed"


class TriggerStatusEnum(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class TriggerTypeEnum(str, enum.Enum):
    CRON = "TRIGGER_CRON"
    MANUAL = "TRIGGER_MANUAL"
    WEBHOOK = "TRIGGER_WEBHOOK"
    EMAIL = "TRIGGER_EMAIL"
    GITHUB = "TRIGGER_GITHUB"


class WorkflowDeployment(Base):
    """Workflow deployment records"""

    __tablename__ = "workflow_deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(String(255), unique=True, nullable=False, index=True)
    workflow_id = Column(String(255), nullable=False, index=True)

    # Deployment metadata
    status = Column(
        Enum(DeploymentStatusEnum), nullable=False, default=DeploymentStatusEnum.PENDING
    )
    workflow_spec = Column(JSON, nullable=False)
    trigger_specs = Column(JSON, nullable=False)

    # Audit fields
    deployed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Optional user context
    deployed_by = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<WorkflowDeployment(id={self.deployment_id}, workflow_id={self.workflow_id}, status={self.status})>"


class TriggerExecution(Base):
    """Trigger execution history"""

    __tablename__ = "trigger_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(String(255), unique=True, nullable=False, index=True)
    workflow_id = Column(String(255), nullable=False, index=True)

    # Trigger information
    trigger_type = Column(Enum(TriggerTypeEnum), nullable=False)
    trigger_data = Column(JSON, nullable=True)

    # Execution status
    status = Column(String(50), nullable=False)  # started, completed, failed, error
    message = Column(Text, nullable=True)

    # Timing information
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Engine response
    engine_response = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<TriggerExecution(id={self.execution_id}, workflow_id={self.workflow_id}, type={self.trigger_type})>"


class GitHubInstallation(Base):
    """GitHub App installation records"""

    __tablename__ = "github_installations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    installation_id = Column(String(50), unique=True, nullable=False, index=True)

    # GitHub account information
    account_id = Column(String(50), nullable=False)
    account_login = Column(String(255), nullable=False)
    account_type = Column(String(50), nullable=False)  # User or Organization

    # Installation metadata
    repositories = Column(JSON, nullable=True)  # Array of accessible repo info
    permissions = Column(JSON, nullable=True)

    # Token management
    access_token = Column(Text, nullable=True)  # Encrypted access token
    access_token_expires_at = Column(DateTime, nullable=True)

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Optional user association
    user_id = Column(String(255), nullable=True, index=True)

    def __repr__(self):
        return f"<GitHubInstallation(id={self.installation_id}, account={self.account_login})>"


class GitHubWebhookEvent(Base):
    """GitHub webhook event records"""

    __tablename__ = "github_webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_id = Column(String(255), unique=True, nullable=False, index=True)

    # Event information
    event_type = Column(String(100), nullable=False, index=True)
    installation_id = Column(String(50), nullable=True, index=True)
    repository_id = Column(String(50), nullable=True)

    # Payload
    payload = Column(JSON, nullable=False)

    # Processing status
    processed_at = Column(DateTime, nullable=True)
    processing_status = Column(String(50), nullable=True)  # pending, processed, failed
    processing_error = Column(Text, nullable=True)

    # Triggered workflows
    triggered_workflows = Column(JSON, nullable=True)  # Array of workflow_ids that were triggered

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<GitHubWebhookEvent(id={self.delivery_id}, type={self.event_type})>"


class EmailMessage(Base):
    """Email message records for email triggers"""

    __tablename__ = "email_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(String(255), unique=True, nullable=False, index=True)

    # Email metadata
    subject = Column(Text, nullable=True)
    sender = Column(String(500), nullable=True)
    recipient = Column(String(500), nullable=True)
    date_received = Column(DateTime, nullable=True)

    # Content
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)  # Array of attachment info

    # Processing information
    workflow_id = Column(String(255), nullable=True, index=True)
    processed_at = Column(DateTime, nullable=True)
    processing_status = Column(String(50), nullable=True)  # pending, processed, filtered_out

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<EmailMessage(id={self.message_id}, subject={self.subject[:50]}...)>"


class TriggerStatus(Base):
    """Current status of active triggers"""

    __tablename__ = "trigger_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(String(255), nullable=False, index=True)
    trigger_type = Column(Enum(TriggerTypeEnum), nullable=False)

    # Status information
    status = Column(Enum(TriggerStatusEnum), nullable=False, default=TriggerStatusEnum.PENDING)
    last_execution = Column(DateTime, nullable=True)
    next_execution = Column(DateTime, nullable=True)  # For cron triggers

    # Configuration
    trigger_config = Column(JSON, nullable=False)

    # Health information
    error_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TriggerStatus(workflow_id={self.workflow_id}, type={self.trigger_type}, status={self.status})>"
