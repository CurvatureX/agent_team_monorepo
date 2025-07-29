"""
Workflow database model and Pydantic models.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func

from workflow_engine.workflow_engine.models.database import Base


class Workflow(Base):
    """Workflow database model."""

    __tablename__ = "workflows"

    # Primary key
    id = Column(String(36), primary_key=True, index=True)

    # User information
    user_id = Column(String(36), nullable=False, index=True)
    session_id = Column(String(36), nullable=True, index=True)  # 新增：会话ID

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
        return f"<Workflow(id='{self.id}', name='{self.name}', user_id='{self.user_id}')>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,  # 新增：session_id
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "active": self.active,
            "workflow_data": self.workflow_data,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# Pydantic models for API serialization
class NodeType(str, Enum):
    """Node types for workflow nodes."""

    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    AI_AGENT = "ai_agent"
    TOOL = "tool"
    FLOW = "flow"
    MEMORY = "memory"
    HUMAN_LOOP = "human_loop"
    EXTERNAL_ACTION = "external_action"


class PositionData(BaseModel):
    """Position data for workflow nodes."""

    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class NodeData(BaseModel):
    """Node data model for workflow nodes."""

    id: str = Field(..., description="Unique node ID")
    name: str = Field(..., description="Node display name")
    type: str = Field(..., description="Node type")
    subtype: Optional[str] = Field(None, description="Node subtype")
    position: PositionData = Field(..., description="Node position in workflow")
    parameters: Dict[str, str] = Field(default_factory=dict, description="Node parameters")
    disabled: bool = Field(False, description="Whether node is disabled")
    on_error: str = Field("continue", description="Error handling strategy")

    @validator("id")
    def validate_id(cls, v):
        if not v.strip():
            raise ValueError("Node ID cannot be empty")
        return v.strip()

    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Node name cannot be empty")
        return v.strip()


class ConnectionsMapData(BaseModel):
    """Connections map for workflow nodes."""

    # This is a flexible model that can handle various connection patterns
    connections: Dict[str, List[str]] = Field(
        default_factory=dict, description="Node connections mapping"
    )

    def __init__(self, **data):
        # Handle direct dict input
        if "connections" not in data and data:
            data = {"connections": data}
        super().__init__(**data)


class WorkflowSettingsData(BaseModel):
    """Workflow execution settings."""

    timeout: int = Field(300, ge=1, description="Execution timeout in seconds")
    max_retries: int = Field(3, ge=0, description="Maximum retry attempts")
    retry_delay: int = Field(5, ge=0, description="Delay between retries in seconds")
    parallel_execution: bool = Field(False, description="Enable parallel node execution")
    error_handling: str = Field("stop", description="Global error handling strategy")
    execution_mode: str = Field("sequential", description="Execution mode")
    variables: Dict[str, str] = Field(default_factory=dict, description="Workflow variables")


class WorkflowData(BaseModel):
    """Complete workflow data model."""

    id: Optional[str] = Field(None, description="Workflow ID")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    nodes: List[NodeData] = Field(..., description="Workflow nodes")
    connections: ConnectionsMapData = Field(..., description="Node connections")
    settings: WorkflowSettingsData = Field(
        default_factory=WorkflowSettingsData, description="Workflow settings"
    )
    static_data: Dict[str, str] = Field(default_factory=dict, description="Static workflow data")
    tags: List[str] = Field(default_factory=list, description="Workflow tags")
    active: bool = Field(True, description="Whether workflow is active")
    version: str = Field("1.0.0", description="Workflow version")
    created_at: Optional[int] = Field(None, description="Creation timestamp")
    updated_at: Optional[int] = Field(None, description="Last update timestamp")
    session_id: Optional[str] = Field(None, description="Associated session ID")

    @validator("nodes")
    def validate_nodes(cls, v):
        if not v:
            raise ValueError("At least one node is required")
        node_ids = {node.id for node in v}
        if len(node_ids) != len(v):
            raise ValueError("All node IDs must be unique")
        return v

    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Workflow name cannot be empty")
        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "id": "workflow_123",
                "name": "Email Processing Workflow",
                "description": "Process incoming emails with AI analysis",
                "nodes": [
                    {
                        "id": "node_1",
                        "name": "Email Trigger",
                        "type": "trigger",
                        "subtype": "email",
                        "position": {"x": 100, "y": 100},
                        "parameters": {"email_filter": "*.@company.com"},
                    }
                ],
                "connections": {"connections": {"node_1": ["node_2"]}},
                "settings": {"timeout": 300, "max_retries": 3, "parallel_execution": False},
                "tags": ["email", "automation"],
                "active": True,
            }
        }
