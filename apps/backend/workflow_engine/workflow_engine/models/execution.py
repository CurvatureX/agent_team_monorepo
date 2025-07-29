"""
Execution models for Workflow Engine.
Defines Pydantic models for workflow execution tracking and status.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Execution status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class NodeExecutionStatus(str, Enum):
    """Node execution status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class NodeExecutionData(BaseModel):
    """Node execution data model."""

    node_id: str = Field(..., description="Node ID")
    node_name: str = Field(..., description="Node name")
    status: NodeExecutionStatus = Field(..., description="Node execution status")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Node input data")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Node output data")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[int] = Field(None, description="Node execution start timestamp")
    completed_at: Optional[int] = Field(None, description="Node execution completion timestamp")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    retry_count: int = Field(0, description="Number of retry attempts")
    logs: List[str] = Field(default_factory=list, description="Execution logs")


class ExecutionData(BaseModel):
    """Complete execution data model."""

    id: str = Field(..., description="Unique execution ID")
    workflow_id: str = Field(..., description="Associated workflow ID")
    workflow_name: str = Field(..., description="Workflow name at execution time")
    user_id: str = Field(..., description="User who triggered the execution")
    status: ExecutionStatus = Field(..., description="Overall execution status")

    # Execution metadata
    trigger_type: Optional[str] = Field(None, description="What triggered the execution")
    trigger_data: Dict[str, Any] = Field(default_factory=dict, description="Trigger event data")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Execution input data")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Final execution output")

    # Timing information
    started_at: int = Field(..., description="Execution start timestamp")
    completed_at: Optional[int] = Field(None, description="Execution completion timestamp")
    execution_time_ms: Optional[int] = Field(
        None, description="Total execution time in milliseconds"
    )

    # Node execution details
    node_executions: List[NodeExecutionData] = Field(
        default_factory=list, description="Individual node executions"
    )
    current_node_id: Optional[str] = Field(None, description="Currently executing node ID")

    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    error_node_id: Optional[str] = Field(None, description="Node ID where error occurred")

    # Progress tracking
    total_nodes: int = Field(0, description="Total number of nodes in workflow")
    completed_nodes: int = Field(0, description="Number of completed nodes")
    progress_percentage: float = Field(0.0, description="Execution progress percentage")

    # Execution context
    session_id: Optional[str] = Field(None, description="Associated session ID")
    execution_context: Dict[str, Any] = Field(
        default_factory=dict, description="Execution context variables"
    )

    class Config:
        schema_extra = {
            "example": {
                "id": "exec_123",
                "workflow_id": "workflow_456",
                "workflow_name": "Email Processing Workflow",
                "user_id": "user_789",
                "status": "running",
                "trigger_type": "schedule",
                "started_at": 1640995200,
                "total_nodes": 5,
                "completed_nodes": 2,
                "progress_percentage": 40.0,
                "node_executions": [
                    {
                        "node_id": "node_1",
                        "node_name": "Email Trigger",
                        "status": "completed",
                        "started_at": 1640995200,
                        "completed_at": 1640995210,
                        "execution_time_ms": 10000,
                    }
                ],
            }
        }


class ExecutionSummary(BaseModel):
    """Simplified execution summary for list views."""

    id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID")
    workflow_name: str = Field(..., description="Workflow name")
    status: ExecutionStatus = Field(..., description="Execution status")
    started_at: int = Field(..., description="Start timestamp")
    completed_at: Optional[int] = Field(None, description="Completion timestamp")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    trigger_type: Optional[str] = Field(None, description="Trigger type")
    progress_percentage: float = Field(0.0, description="Progress percentage")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class ExecutionMetrics(BaseModel):
    """Execution metrics and statistics."""

    total_executions: int = Field(0, description="Total number of executions")
    successful_executions: int = Field(0, description="Number of successful executions")
    failed_executions: int = Field(0, description="Number of failed executions")
    average_execution_time_ms: float = Field(0.0, description="Average execution time")
    success_rate: float = Field(0.0, description="Success rate percentage")
    most_common_errors: List[str] = Field(
        default_factory=list, description="Most common error messages"
    )
    peak_execution_times: List[int] = Field(
        default_factory=list, description="Peak execution time periods"
    )

    class Config:
        schema_extra = {
            "example": {
                "total_executions": 100,
                "successful_executions": 85,
                "failed_executions": 15,
                "average_execution_time_ms": 5000.0,
                "success_rate": 85.0,
                "most_common_errors": ["API timeout", "Invalid input data"],
            }
        }
