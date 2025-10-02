"""
Shared Request/Response Models for Workflow Engine V2 API

All Pydantic models used across different API versions.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# ============================================================================
# Workflow Models
# ============================================================================


class CreateWorkflowRequest(BaseModel):
    """Request to create a workflow"""

    workflow_id: Optional[str] = None
    name: str
    created_by: str
    created_time_ms: Optional[int] = None
    nodes: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    triggers: Optional[List[str]] = []


class CreateWorkflowResponse(BaseModel):
    """Response from creating a workflow"""

    workflow: Dict[str, Any]


class GetWorkflowResponse(BaseModel):
    """Response from getting a workflow"""

    found: bool
    workflow: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class UpdateWorkflowRequest(BaseModel):
    """Request to update a workflow"""

    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    connections: Optional[List[Dict[str, Any]]] = None
    triggers: Optional[List[str]] = None


class DeleteWorkflowResponse(BaseModel):
    """Response from deleting a workflow"""

    success: bool
    message: str


# ============================================================================
# Execution Models
# ============================================================================


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute a workflow"""

    workflow: Dict[str, Any]  # Workflow data as dict
    trigger: Dict[str, Any]  # Trigger info as dict
    trace_id: Optional[str] = None


class ExecuteWorkflowResponse(BaseModel):
    """Response from workflow execution"""

    success: bool
    execution_id: str
    execution: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ExecutionStatusResponse(BaseModel):
    """Response for execution status"""

    id: str
    execution_id: str
    workflow_id: str
    status: str
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class ExecutionProgressResponse(BaseModel):
    """Response for execution progress"""

    execution_id: str
    progress: Dict[str, Any]


class CancelExecutionResponse(BaseModel):
    """Response from canceling execution"""

    success: bool
    message: str
    execution_id: str


class ResumeExecutionResponse(BaseModel):
    """Response from resuming execution"""

    message: str
    execution_id: str


# ============================================================================
# Credentials Models
# ============================================================================


class CheckCredentialsRequest(BaseModel):
    """Request to check credentials"""

    user_id: str
    provider: str


class CheckCredentialsResponse(BaseModel):
    """Response from checking credentials"""

    success: bool
    has_credentials: bool
    provider: str
    user_id: str
    message: str


class GetCredentialsRequest(BaseModel):
    """Request to get credentials"""

    user_id: str
    provider: str


class GetCredentialsResponse(BaseModel):
    """Response from getting credentials"""

    success: bool
    provider: str
    user_id: str
    credentials: Optional[Dict[str, Any]] = None
    message: str


class StoreCredentialsRequest(BaseModel):
    """Request to store credentials"""

    user_id: str
    provider: str
    credentials: Dict[str, Any]


class StoreCredentialsResponse(BaseModel):
    """Response from storing credentials"""

    success: bool
    provider: str
    user_id: str
    message: str


class CredentialsStatusRequest(BaseModel):
    """Request to get credentials status"""

    user_id: str
    providers: List[str]


class CredentialsStatusResponse(BaseModel):
    """Response from getting credentials status"""

    success: bool
    user_id: str
    credentials_status: Dict[str, Dict[str, Any]]


class DeleteCredentialsResponse(BaseModel):
    """Response from deleting credentials"""

    success: bool
    provider: str
    user_id: str
    message: str


# ============================================================================
# Node Specs Models
# ============================================================================


class NodeSpecResponse(BaseModel):
    """Response containing node specifications"""

    specs: List[Dict[str, Any]]


# ============================================================================
# Health Check Models
# ============================================================================


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    version: str
    uptime_seconds: float
    service: str


# ============================================================================
# Logs Models
# ============================================================================


class LogMilestoneRequest(BaseModel):
    """Request to log a milestone"""

    message: str
    user_message: str
    data: Optional[Dict[str, Any]] = None


class LogMilestoneResponse(BaseModel):
    """Response from logging a milestone"""

    success: bool
    execution_id: str
