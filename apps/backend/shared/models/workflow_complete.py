"""
Complete Workflow Models - New specification implementation

This module combines all workflow-related models following the new specification:
- Port and Connection models with proper validation
- Node and Workflow definitions
- Execution tracking with detailed status
- Real-time event handling
- API request/response models
- Legacy compatibility layers

This is the complete implementation of the workflow specification and should be
the primary import for all new code.
"""

from .execution_new import (  # Execution enums; Basic structures; Node execution; Main execution model; Summary models
    Execution,
    ExecutionError,
    ExecutionEventType,
    ExecutionStatus,
    ExecutionSummary,
    LogEntry,
    LogLevel,
    NodeError,
    NodeExecution,
    NodeExecutionDetails,
    NodeExecutionStatus,
    TokenUsage,
    TriggerInfo,
)

# Re-export all models from the new specification modules
from .workflow_new import (  # Enums; Core models; API models; WebSocket events
    Connection,
    ExecutionActionRequest,
    ExecutionActionResponse,
    ExecutionUpdateData,
    ExecutionUpdateEvent,
    GetExecutionResponse,
    GetExecutionsResponse,
    Node,
    Port,
    SubscriptionResponse,
    UserInputRequest,
    Workflow,
    WorkflowDeploymentStatus,
    WorkflowExecutionSummary,
    WorkflowMetadata,
    WorkflowStatistics,
)

# Export everything for easy importing
__all__ = [
    # Workflow enums
    "WorkflowDeploymentStatus",
    "ExecutionStatus",  # Use ExecutionStatus instead of WorkflowExecutionStatus
    # Core workflow models
    "Port",
    "Connection",
    "Node",
    "WorkflowStatistics",
    "WorkflowMetadata",
    "Workflow",
    # Execution enums
    "ExecutionStatus",
    "NodeExecutionStatus",
    "ExecutionEventType",
    "LogLevel",
    # Execution data structures
    "TriggerInfo",
    "TokenUsage",
    "LogEntry",
    "ExecutionError",
    "NodeError",
    "NodeExecutionDetails",
    "NodeExecution",
    "Execution",
    "ExecutionSummary",
    # API models
    "WorkflowExecutionSummary",
    "GetExecutionResponse",
    "GetExecutionsResponse",
    "SubscriptionResponse",
    "ExecutionActionRequest",
    "UserInputRequest",
    "ExecutionActionResponse",
    # WebSocket events
    "ExecutionUpdateData",
    "ExecutionUpdateEvent",
]
