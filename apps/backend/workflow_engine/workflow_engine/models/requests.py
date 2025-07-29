"""
Request models for Workflow Engine FastAPI endpoints.
Replaces protobuf definitions with Pydantic models for better type safety and validation.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator

from .workflow import ConnectionsMapData, NodeData, WorkflowData, WorkflowSettingsData


class CreateWorkflowRequest(BaseModel):
    """Request model for creating a new workflow."""

    name: str = Field(..., min_length=1, max_length=255, description="Workflow name")
    description: Optional[str] = Field(None, max_length=1000, description="Workflow description")
    nodes: List[NodeData] = Field(..., min_items=1, description="At least one node required")
    connections: ConnectionsMapData = Field(..., description="Node connections configuration")
    settings: Optional[WorkflowSettingsData] = Field(
        None, description="Workflow execution settings"
    )
    static_data: Dict[str, str] = Field(default_factory=dict, description="Static workflow data")
    tags: List[str] = Field(default_factory=list, description="Workflow tags")
    user_id: str = Field(..., min_length=1, description="User ID who owns the workflow")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")

    @validator("name")
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return v.strip()

    @validator("nodes")
    def validate_nodes(cls, v):
        if not v:
            raise ValueError("At least one node is required")
        node_ids = {node.id for node in v}
        if len(node_ids) != len(v):
            raise ValueError("All node IDs must be unique")
        return v

    class Config:
        schema_extra = {
            "example": {
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
                "connections": {"node_1": ["node_2"]},
                "settings": {"timeout": 300, "max_retries": 3},
                "tags": ["email", "automation"],
                "user_id": "user_123",
            }
        }


class GetWorkflowRequest(BaseModel):
    """Request model for getting a workflow by ID."""

    workflow_id: str = Field(..., min_length=1, description="Workflow ID")
    user_id: str = Field(..., min_length=1, description="User ID for authorization")


class UpdateWorkflowRequest(BaseModel):
    """Request model for updating an existing workflow."""

    workflow_id: str = Field(..., min_length=1, description="Workflow ID")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="New workflow name")
    description: Optional[str] = Field(
        None, max_length=1000, description="New workflow description"
    )
    nodes: Optional[List[NodeData]] = Field(None, description="Updated nodes")
    connections: Optional[ConnectionsMapData] = Field(None, description="Updated connections")
    settings: Optional[WorkflowSettingsData] = Field(None, description="Updated settings")
    static_data: Optional[Dict[str, str]] = Field(None, description="Updated static data")
    tags: Optional[List[str]] = Field(None, description="Updated tags")
    active: Optional[bool] = Field(None, description="Active status")
    user_id: str = Field(..., min_length=1, description="User ID for authorization")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")

    @validator("name")
    def name_must_not_be_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return v.strip() if v else v


class DeleteWorkflowRequest(BaseModel):
    """Request model for deleting a workflow."""

    workflow_id: str = Field(..., min_length=1, description="Workflow ID")
    user_id: str = Field(..., min_length=1, description="User ID for authorization")


class ListWorkflowsRequest(BaseModel):
    """Request model for listing workflows."""

    user_id: str = Field(..., min_length=1, description="User ID")
    active_only: bool = Field(False, description="Filter to active workflows only")
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    limit: int = Field(50, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Pagination offset")


class ExecuteWorkflowRequest(BaseModel):
    """Request model for executing a workflow."""

    workflow_id: str = Field(..., min_length=1, description="Workflow ID")
    user_id: str = Field(..., min_length=1, description="User ID for authorization")
    input_data: Dict[str, str] = Field(default_factory=dict, description="Input data for execution")
    execution_options: Dict[str, str] = Field(
        default_factory=dict, description="Execution configuration"
    )


class GetExecutionStatusRequest(BaseModel):
    """Request model for getting execution status."""

    execution_id: str = Field(..., min_length=1, description="Execution ID")
    user_id: str = Field(..., min_length=1, description="User ID for authorization")


class CancelExecutionRequest(BaseModel):
    """Request model for canceling an execution."""

    execution_id: str = Field(..., min_length=1, description="Execution ID")
    user_id: str = Field(..., min_length=1, description="User ID for authorization")
    reason: Optional[str] = Field(None, description="Cancellation reason")


class GetExecutionHistoryRequest(BaseModel):
    """Request model for getting execution history."""

    workflow_id: Optional[str] = Field(None, description="Filter by workflow ID")
    user_id: str = Field(..., min_length=1, description="User ID for authorization")
    limit: int = Field(50, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Pagination offset")


class ValidateWorkflowRequest(BaseModel):
    """Request model for validating a workflow."""

    workflow: WorkflowData = Field(..., description="Workflow to validate")
    strict_mode: bool = Field(False, description="Enable strict validation")


class TestNodeRequest(BaseModel):
    """Request model for testing a single node."""

    node: NodeData = Field(..., description="Node to test")
    input_data: Dict[str, str] = Field(default_factory=dict, description="Test input data")
    user_id: str = Field(..., min_length=1, description="User ID for authorization")


# Trigger-related request models
class TriggerType(str, Enum):
    """Trigger types."""

    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    EMAIL = "email"
    FILE_WATCH = "file_watch"
    DATABASE = "database"
    API = "api"


class CreateTriggerRequest(BaseModel):
    """Request model for creating a trigger."""

    type: TriggerType = Field(..., description="Trigger type")
    node_name: str = Field(..., min_length=1, description="Target node name")
    workflow_id: str = Field(..., min_length=1, description="Associated workflow ID")
    configuration: Dict[str, str] = Field(default_factory=dict, description="Trigger configuration")
    schedule: Optional[Dict[str, str]] = Field(
        None, description="Schedule configuration for cron triggers"
    )
    conditions: List[Dict[str, str]] = Field(default_factory=list, description="Trigger conditions")
    user_id: str = Field(..., min_length=1, description="User ID for authorization")


class GetTriggerRequest(BaseModel):
    """Request model for getting a trigger."""

    trigger_id: str = Field(..., min_length=1, description="Trigger ID")
    user_id: str = Field(..., min_length=1, description="User ID for authorization")


class UpdateTriggerRequest(BaseModel):
    """Request model for updating a trigger."""

    trigger_id: str = Field(..., min_length=1, description="Trigger ID")
    configuration: Optional[Dict[str, str]] = Field(None, description="Updated configuration")
    schedule: Optional[Dict[str, str]] = Field(None, description="Updated schedule")
    conditions: Optional[List[Dict[str, str]]] = Field(None, description="Updated conditions")
    active: Optional[bool] = Field(None, description="Active status")
    user_id: str = Field(..., min_length=1, description="User ID for authorization")


class DeleteTriggerRequest(BaseModel):
    """Request model for deleting a trigger."""

    trigger_id: str = Field(..., min_length=1, description="Trigger ID")
    user_id: str = Field(..., min_length=1, description="User ID for authorization")


class ListTriggersRequest(BaseModel):
    """Request model for listing triggers."""

    workflow_id: Optional[str] = Field(None, description="Filter by workflow ID")
    type: Optional[TriggerType] = Field(None, description="Filter by trigger type")
    active_only: bool = Field(False, description="Filter to active triggers only")
    user_id: str = Field(..., min_length=1, description="User ID")
    limit: int = Field(50, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Pagination offset")


class FireTriggerRequest(BaseModel):
    """Request model for firing a trigger."""

    trigger_id: str = Field(..., min_length=1, description="Trigger ID")
    event_data: Dict[str, str] = Field(default_factory=dict, description="Event data")
    source: Optional[str] = Field(None, description="Event source")


class GetTriggerEventsRequest(BaseModel):
    """Request model for getting trigger events."""

    trigger_id: str = Field(..., min_length=1, description="Trigger ID")
    status: Optional[str] = Field(None, description="Filter by event status")
    limit: int = Field(50, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Pagination offset")


class HealthCheckRequest(BaseModel):
    """Request model for health check."""

    service: Optional[str] = Field(None, description="Specific service to check")
