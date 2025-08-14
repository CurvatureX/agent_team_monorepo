import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Import unified enums - no more legacy support
from .node_enums import NodeType
from .node_enums import TriggerSubtype as TriggerType


class TriggerStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class DeploymentStatus(str, Enum):
    PENDING = "pending"
    DEPLOYED = "deployed"
    FAILED = "failed"
    UNDEPLOYED = "undeployed"


class TriggerSpec(BaseModel):
    node_type: str = NodeType.TRIGGER.value  # Use unified enum value
    subtype: TriggerType
    parameters: Dict[str, Any]
    enabled: bool = True


class CronTriggerSpec(BaseModel):
    cron_expression: str
    timezone: str = "UTC"
    enabled: bool = True


class ManualTriggerSpec(BaseModel):
    enabled: bool = True


class WebhookTriggerSpec(BaseModel):
    webhook_path: Optional[str] = None
    methods: List[str] = ["POST"]
    require_auth: bool = False
    enabled: bool = True


class EmailTriggerSpec(BaseModel):
    email_filter: str
    folder: str = "INBOX"
    mark_as_read: bool = True
    attachment_processing: str = "include"
    enabled: bool = True


class GitHubTriggerSpec(BaseModel):
    github_app_installation_id: str
    repository: str
    event_config: Dict[str, Any]  # Changed from separate parameters to unified event configuration
    author_filter: Optional[str] = None
    ignore_bots: bool = True
    require_signature_verification: bool = True
    enabled: bool = True


class SlackTriggerSpec(BaseModel):
    workspace_id: Optional[str] = None
    channel_filter: Optional[str] = None
    event_types: List[str] = ["message", "app_mention"]
    mention_required: bool = False
    command_prefix: Optional[str] = None
    user_filter: Optional[str] = None
    ignore_bots: bool = True
    require_thread: bool = False
    enabled: bool = True


class DeploymentResult(BaseModel):
    deployment_id: str
    status: DeploymentStatus
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutionResult(BaseModel):
    execution_id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4()}")
    status: str
    message: str
    trigger_data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
