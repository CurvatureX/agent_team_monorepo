"""
Trigger index database models for fast trigger matching
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import ARRAY, JSON, BigInteger, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from workflow_scheduler.models.database import Base


class TriggerIndex(Base):
    """
    Trigger index table for fast reverse lookup and matching using unified design

    This table provides optimized indexing for all trigger types using a single
    index_key field for fast lookup and detailed matching in trigger_config:
    - TRIGGER_CRON: index_key = cron_expression
    - TRIGGER_WEBHOOK: index_key = webhook_path
    - TRIGGER_SLACK: index_key = workspace_id
    - TRIGGER_EMAIL: index_key = email_address
    - TRIGGER_GITHUB: index_key = repository_name
    - TRIGGER_MANUAL: index_key = null (no fast lookup needed)
    """

    __tablename__ = "trigger_index"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    trigger_type = Column(
        String(50), nullable=False, index=True
    )  # 'TRIGGER_CRON', 'TRIGGER_WEBHOOK', etc.
    trigger_config = Column(JSON, nullable=False)  # Complete trigger configuration

    # Unified fast matching field
    index_key = Column(Text, nullable=True, index=True)  # Single field for fast lookup

    # Metadata
    deployment_status = Column(
        String(20), nullable=False, default="active", index=True
    )  # 'active', 'paused', 'stopped'
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TriggerIndex(workflow_id={self.workflow_id}, type={self.trigger_type}, status={self.deployment_status})>"


class GitHubWebhookEvent(Base):
    """
    GitHub webhook events log for debugging and analysis
    """

    __tablename__ = "github_webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_id = Column(Text, nullable=False, unique=True, index=True)  # GitHub delivery ID
    event_type = Column(String(50), nullable=False, index=True)  # push, pull_request, etc.
    installation_id = Column(BigInteger, nullable=True, index=True)
    repository_id = Column(BigInteger, nullable=True, index=True)
    payload = Column(JSON, nullable=False)  # Complete GitHub payload
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<GitHubWebhookEvent(delivery_id={self.delivery_id}, event_type={self.event_type})>"


class GitHubInstallation(Base):
    """
    GitHub App installations for access management
    """

    __tablename__ = "github_installations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Associated user
    installation_id = Column(BigInteger, nullable=False, unique=True, index=True)
    account_id = Column(BigInteger, nullable=False)
    account_login = Column(String(255), nullable=False)
    account_type = Column(String(20), nullable=False)  # 'User' or 'Organization'
    repositories = Column(JSON, nullable=True)  # Array of accessible repo info
    permissions = Column(JSON, nullable=True)  # Installation permissions
    access_token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GitHubInstallation(installation_id={self.installation_id}, account={self.account_login})>"
