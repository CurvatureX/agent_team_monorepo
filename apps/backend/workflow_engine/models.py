"""
Simple Pydantic models for Workflow Engine

Clean, simple data models without complex inheritance.
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# ExecutionStatus enum for compatibility with services
class ExecutionStatus(Enum):
    """Execution status for workflows and nodes."""

    NEW = "NEW"
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    CANCELED = "cancelled"  # Alias for CANCELLED
    PAUSED = "paused"


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute a workflow"""

    workflow_id: str = Field(..., description="ID of the workflow to execute")
    user_id: str = Field(..., description="ID of the user executing the workflow")
    trigger_data: Dict[str, str] = Field(default_factory=dict, description="Trigger data")
    async_execution: bool = Field(default=False, description="Whether to execute asynchronously")


class ExecuteWorkflowResponse(BaseModel):
    """Response from workflow execution"""

    execution_id: str = Field(..., description="ID of the execution")
    status: str = Field(..., description="Execution status")
    success: bool = Field(..., description="Whether execution was successful")
    message: str = Field(..., description="Human-readable message")


class GetExecutionRequest(BaseModel):
    """Request to get execution status"""

    execution_id: str = Field(..., description="ID of the execution to retrieve")


class GetExecutionResponse(BaseModel):
    """Response for execution status"""

    execution_id: str = Field(..., description="ID of the execution")
    status: str = Field(..., description="Execution status")
    success: bool = Field(..., description="Whether execution was successful")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")


class ExecutionStatusResponse(BaseModel):
    """Execution status response (legacy compatibility)"""

    execution_id: str
    workflow_id: str
    status: str
    created_at: str
    updated_at: Optional[str] = None
    error_message: Optional[str] = None
