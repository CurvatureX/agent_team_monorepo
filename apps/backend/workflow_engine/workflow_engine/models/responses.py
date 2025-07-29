"""
Response models for Workflow Engine FastAPI endpoints.
Replaces protobuf definitions with Pydantic models for better type safety and documentation.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .execution import ExecutionData, ExecutionStatus
from .workflow import NodeData, WorkflowData


class CreateWorkflowResponse(BaseModel):
    """Response model for workflow creation."""

    workflow: WorkflowData = Field(..., description="Created workflow")
    success: bool = Field(True, description="Operation success status")
    message: str = Field("Workflow created successfully", description="Operation message")

    class Config:
        schema_extra = {
            "example": {
                "workflow": {
                    "id": "workflow_123",
                    "name": "Email Processing Workflow",
                    "description": "Process incoming emails with AI analysis",
                    "active": True,
                },
                "success": True,
                "message": "Workflow created successfully",
            }
        }


class GetWorkflowResponse(BaseModel):
    """Response model for getting a workflow."""

    workflow: Optional[WorkflowData] = Field(None, description="Retrieved workflow")
    found: bool = Field(..., description="Whether workflow was found")
    message: str = Field(..., description="Operation message")


class UpdateWorkflowResponse(BaseModel):
    """Response model for workflow update."""

    workflow: WorkflowData = Field(..., description="Updated workflow")
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")


class DeleteWorkflowResponse(BaseModel):
    """Response model for workflow deletion."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")


class ListWorkflowsResponse(BaseModel):
    """Response model for listing workflows."""

    workflows: List[WorkflowData] = Field(..., description="List of workflows")
    total_count: int = Field(..., description="Total number of workflows")
    has_more: bool = Field(False, description="Whether there are more results")

    class Config:
        schema_extra = {
            "example": {
                "workflows": [
                    {
                        "id": "workflow_123",
                        "name": "Email Processing Workflow",
                        "description": "Process incoming emails",
                        "active": True,
                        "created_at": 1640995200,
                        "updated_at": 1640995200,
                    }
                ],
                "total_count": 1,
                "has_more": False,
            }
        }


class ExecuteWorkflowResponse(BaseModel):
    """Response model for workflow execution."""

    execution_id: str = Field(..., description="Unique execution ID")
    workflow_id: str = Field(..., description="Executed workflow ID")
    status: ExecutionStatus = Field(..., description="Initial execution status")
    message: str = Field(..., description="Execution start message")
    started_at: int = Field(..., description="Execution start timestamp")


class GetExecutionStatusResponse(BaseModel):
    """Response model for execution status."""

    execution: ExecutionData = Field(..., description="Execution details")
    found: bool = Field(..., description="Whether execution was found")
    message: str = Field(..., description="Operation message")


class CancelExecutionResponse(BaseModel):
    """Response model for execution cancellation."""

    execution_id: str = Field(..., description="Cancelled execution ID")
    success: bool = Field(..., description="Cancellation success status")
    message: str = Field(..., description="Cancellation message")


class GetExecutionHistoryResponse(BaseModel):
    """Response model for execution history."""

    executions: List[ExecutionData] = Field(..., description="List of executions")
    total_count: int = Field(..., description="Total number of executions")
    has_more: bool = Field(False, description="Whether there are more results")


class ValidationResult(BaseModel):
    """Workflow validation result."""

    valid: bool = Field(..., description="Whether workflow is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


class ValidateWorkflowResponse(BaseModel):
    """Response model for workflow validation."""

    validation_result: ValidationResult = Field(..., description="Validation results")
    success: bool = Field(..., description="Validation operation success")
    message: str = Field(..., description="Validation message")


class TestNodeResponse(BaseModel):
    """Response model for node testing."""

    node_id: str = Field(..., description="Tested node ID")
    success: bool = Field(..., description="Test success status")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Node output data")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    errors: List[str] = Field(default_factory=list, description="Test errors")
    message: str = Field(..., description="Test result message")


# Trigger-related response models
class TriggerData(BaseModel):
    """Trigger data model."""

    id: str = Field(..., description="Trigger ID")
    type: str = Field(..., description="Trigger type")
    node_name: str = Field(..., description="Target node name")
    workflow_id: str = Field(..., description="Associated workflow ID")
    configuration: Dict[str, str] = Field(default_factory=dict, description="Trigger configuration")
    schedule: Optional[Dict[str, str]] = Field(None, description="Schedule configuration")
    conditions: List[Dict[str, str]] = Field(default_factory=list, description="Trigger conditions")
    active: bool = Field(True, description="Active status")
    created_at: int = Field(..., description="Creation timestamp")
    updated_at: int = Field(..., description="Last update timestamp")
    last_triggered_at: Optional[int] = Field(None, description="Last trigger timestamp")
    trigger_count: int = Field(0, description="Total trigger count")


class CreateTriggerResponse(BaseModel):
    """Response model for trigger creation."""

    trigger: TriggerData = Field(..., description="Created trigger")
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")


class GetTriggerResponse(BaseModel):
    """Response model for getting a trigger."""

    trigger: Optional[TriggerData] = Field(None, description="Retrieved trigger")
    found: bool = Field(..., description="Whether trigger was found")
    message: str = Field(..., description="Operation message")


class UpdateTriggerResponse(BaseModel):
    """Response model for trigger update."""

    trigger: TriggerData = Field(..., description="Updated trigger")
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")


class DeleteTriggerResponse(BaseModel):
    """Response model for trigger deletion."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")


class ListTriggersResponse(BaseModel):
    """Response model for listing triggers."""

    triggers: List[TriggerData] = Field(..., description="List of triggers")
    total_count: int = Field(..., description="Total number of triggers")
    has_more: bool = Field(False, description="Whether there are more results")


class FireTriggerResponse(BaseModel):
    """Response model for firing a trigger."""

    event_id: str = Field(..., description="Generated event ID")
    execution_id: Optional[str] = Field(None, description="Started execution ID if applicable")
    success: bool = Field(..., description="Trigger fire success status")
    message: str = Field(..., description="Trigger fire message")


class TriggerEventData(BaseModel):
    """Trigger event data model."""

    id: str = Field(..., description="Event ID")
    trigger_id: str = Field(..., description="Associated trigger ID")
    event_data: Dict[str, str] = Field(default_factory=dict, description="Event data")
    source: Optional[str] = Field(None, description="Event source")
    status: str = Field(..., description="Event processing status")
    execution_id: Optional[str] = Field(None, description="Associated execution ID")
    created_at: int = Field(..., description="Event creation timestamp")
    processed_at: Optional[int] = Field(None, description="Event processing timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class GetTriggerEventsResponse(BaseModel):
    """Response model for getting trigger events."""

    events: List[TriggerEventData] = Field(..., description="List of trigger events")
    total_count: int = Field(..., description="Total number of events")
    has_more: bool = Field(False, description="Whether there are more results")


class HealthStatus(str, Enum):
    """Health status values."""

    UNKNOWN = "unknown"
    SERVING = "serving"
    NOT_SERVING = "not_serving"
    SERVICE_UNKNOWN = "service_unknown"


class HealthCheckResponse(BaseModel):
    """Response model for health check."""

    status: HealthStatus = Field(..., description="Service health status")
    message: str = Field(..., description="Health status message")
    details: Dict[str, str] = Field(default_factory=dict, description="Additional health details")
    timestamp: int = Field(..., description="Health check timestamp")

    class Config:
        schema_extra = {
            "example": {
                "status": "serving",
                "message": "Workflow Engine is healthy",
                "details": {"database": "connected", "redis": "connected", "version": "1.0.0"},
                "timestamp": 1640995200,
            }
        }


# Error response models
class ErrorDetail(BaseModel):
    """Error detail model."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Associated field if applicable")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: List[ErrorDetail] = Field(
        default_factory=list, description="Detailed error information"
    )
    timestamp: int = Field(..., description="Error timestamp")

    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": "ValidationError",
                "message": "Request validation failed",
                "details": [
                    {"code": "value_error.missing", "message": "field required", "field": "name"}
                ],
                "timestamp": 1640995200,
            }
        }
