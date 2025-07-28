"""
Execution-related Pydantic models
执行相关的Pydantic模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .base import BaseResponse


class ExecutionStatus(BaseModel):
    """Execution status model"""

    execution_id: str = Field(..., description="Unique execution identifier")
    workflow_id: str = Field(..., description="Associated workflow identifier")
    user_id: str = Field(..., description="User who initiated the execution")
    status: str = Field(
        ..., description="Current execution status (pending, running, completed, failed, cancelled)"
    )
    progress: Optional[float] = Field(None, description="Execution progress percentage (0-100)")

    # Timestamps
    created_at: datetime = Field(..., description="Execution creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Execution completion timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Execution details
    inputs: Optional[Dict[str, Any]] = Field(None, description="Execution input parameters")
    outputs: Optional[Dict[str, Any]] = Field(None, description="Execution output results")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")

    # Execution metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional execution metadata")
    duration_seconds: Optional[float] = Field(
        None, description="Total execution duration in seconds"
    )

    # Step-by-step execution details
    current_step: Optional[str] = Field(None, description="Currently executing step")
    total_steps: Optional[int] = Field(None, description="Total number of steps")
    completed_steps: Optional[int] = Field(None, description="Number of completed steps")
    step_details: Optional[List[Dict[str, Any]]] = Field(
        None, description="Details of individual steps"
    )


class ExecutionStatusResponse(BaseResponse):
    """Response model for execution status queries"""

    execution: ExecutionStatus = Field(..., description="Execution status information")


class ExecutionCancelRequest(BaseModel):
    """Request model for execution cancellation"""

    reason: Optional[str] = Field(None, description="Reason for cancellation")
    force: bool = Field(False, description="Whether to force cancellation")


class ExecutionCancelResponse(BaseResponse):
    """Response model for execution cancellation"""

    execution_id: str = Field(..., description="ID of the cancelled execution")
    cancelled: bool = Field(..., description="Whether the cancellation was successful")
    previous_status: Optional[str] = Field(None, description="Status before cancellation")
    cancellation_reason: Optional[str] = Field(None, description="Reason for cancellation")
    cancelled_at: datetime = Field(..., description="Cancellation timestamp")


class ExecutionListResponse(BaseResponse):
    """Response model for listing executions"""

    executions: List[ExecutionStatus] = Field(..., description="List of executions")
    total_count: int = Field(..., description="Total number of executions")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(20, description="Number of items per page")
    has_next: bool = Field(False, description="Whether there are more pages")


class ExecutionLogEntry(BaseModel):
    """Individual execution log entry"""

    timestamp: datetime = Field(..., description="Log entry timestamp")
    level: str = Field(..., description="Log level (debug, info, warning, error)")
    message: str = Field(..., description="Log message")
    component: Optional[str] = Field(None, description="Component that generated the log")
    step: Optional[str] = Field(None, description="Execution step context")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional log data")


class ExecutionLogResponse(BaseResponse):
    """Response model for execution logs"""

    execution_id: str = Field(..., description="Execution identifier")
    logs: List[ExecutionLogEntry] = Field(..., description="Execution log entries")
    total_entries: int = Field(..., description="Total number of log entries")


class ExecutionMetrics(BaseModel):
    """Execution performance metrics"""

    execution_id: str = Field(..., description="Execution identifier")

    # Performance metrics
    cpu_usage_percent: Optional[float] = Field(None, description="Average CPU usage percentage")
    memory_usage_mb: Optional[float] = Field(None, description="Peak memory usage in MB")
    network_bytes_sent: Optional[int] = Field(None, description="Network bytes sent")
    network_bytes_received: Optional[int] = Field(None, description="Network bytes received")

    # Step timing
    step_durations: Optional[Dict[str, float]] = Field(
        None, description="Duration of each step in seconds"
    )
    bottleneck_steps: Optional[List[str]] = Field(
        None, description="Steps that took longest to execute"
    )

    # Resource utilization
    resources_used: Optional[Dict[str, Any]] = Field(
        None, description="Resources consumed during execution"
    )

    # Quality metrics
    success_rate: Optional[float] = Field(
        None, description="Success rate for this type of execution"
    )
    average_duration: Optional[float] = Field(
        None, description="Average duration for similar executions"
    )


class ExecutionMetricsResponse(BaseResponse):
    """Response model for execution metrics"""

    metrics: ExecutionMetrics = Field(..., description="Execution performance metrics")


# Re-export commonly used models
__all__ = [
    "ExecutionStatus",
    "ExecutionStatusResponse",
    "ExecutionCancelRequest",
    "ExecutionCancelResponse",
    "ExecutionListResponse",
    "ExecutionLogEntry",
    "ExecutionLogResponse",
    "ExecutionMetrics",
    "ExecutionMetricsResponse",
]
