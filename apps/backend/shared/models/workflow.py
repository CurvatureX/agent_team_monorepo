from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from enum import Enum


class PositionData(BaseModel):
    x: float
    y: float


class RetryPolicyData(BaseModel):
    max_tries: int = Field(default=3, ge=1, le=10)
    wait_between_tries: int = Field(default=5, ge=1, le=300)  # seconds


class NodeData(BaseModel):
    id: str
    name: str
    type: Optional[str] = None
    subtype: Optional[str] = None
    type_version: int = Field(default=1)
    position: PositionData
    parameters: Dict[str, str] = Field(default_factory=dict)
    credentials: Dict[str, str] = Field(default_factory=dict)
    disabled: bool = False
    on_error: str = Field(default="continue", pattern="^(continue|stop)$")
    retry_policy: Optional[RetryPolicyData] = None
    notes: Dict[str, str] = Field(default_factory=dict)
    webhooks: List[str] = Field(default_factory=list)


class ConnectionData(BaseModel):
    node: str
    type: str
    index: int = Field(default=0)


class ConnectionArrayData(BaseModel):
    connections: List[ConnectionData] = Field(default_factory=list)


class NodeConnectionsData(BaseModel):
    connection_types: Dict[str, ConnectionArrayData] = Field(default_factory=dict)


class ConnectionsMapData(BaseModel):
    connections: Dict[str, NodeConnectionsData] = Field(default_factory=dict)


class WorkflowSettingsData(BaseModel):
    timezone: Dict[str, str] = Field(default_factory=dict)
    save_execution_progress: bool = True
    save_manual_executions: bool = True
    timeout: int = Field(default=3600, ge=60, le=86400)  # 1 hour default, max 24 hours
    error_policy: str = Field(default="continue", pattern="^(continue|stop)$")
    caller_policy: str = Field(default="workflow", pattern="^(workflow|user)$")

    @validator('timezone', pre=True)
    def validate_timezone(cls, v):
        if isinstance(v, str):
            return {"name": v}
        return v


class WorkflowData(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    nodes: List[NodeData]
    connections: ConnectionsMapData
    settings: WorkflowSettingsData
    static_data: Dict[str, str] = Field(default_factory=dict)
    pin_data: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    active: bool = True
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    version: str = Field(default="1.0")

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Workflow name cannot be empty')
        return v.strip()

    @validator('nodes')
    def validate_nodes(cls, v):
        if not v:
            raise ValueError('Workflow must contain at least one node')
        node_ids = [node.id for node in v]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError('Node IDs must be unique')
        return v


# Engine specific models
class CreateWorkflowRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    nodes: List[NodeData] = Field(..., min_items=1)
    connections: ConnectionsMapData
    settings: Optional[WorkflowSettingsData] = None
    static_data: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None


class CreateWorkflowResponse(BaseModel):
    workflow: WorkflowData
    success: bool = True
    message: str = "Workflow created successfully"


class GetWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)


class GetWorkflowResponse(BaseModel):
    workflow: Optional[WorkflowData] = None
    found: bool
    message: str = ""


class UpdateWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    nodes: Optional[List[NodeData]] = None
    connections: Optional[ConnectionsMapData] = None
    settings: Optional[WorkflowSettingsData] = None
    static_data: Optional[Dict[str, str]] = None
    tags: Optional[List[str]] = None
    active: Optional[bool] = None
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None


class UpdateWorkflowResponse(BaseModel):
    workflow: WorkflowData
    success: bool = True
    message: str = "Workflow updated successfully"


class DeleteWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)


class DeleteWorkflowResponse(BaseModel):
    success: bool = True
    message: str = "Workflow deleted successfully"


class ListWorkflowsRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    active_only: bool = True
    tags: List[str] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ListWorkflowsResponse(BaseModel):
    workflows: List[WorkflowData]
    total_count: int
    has_more: bool


class ExecuteWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1)
    trigger_data: Dict[str, str] = Field(default_factory=dict)
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None


class ExecuteWorkflowResponse(BaseModel):
    execution_id: str
    status: str = "running"
    success: bool = True
    message: str = "Workflow execution started" 