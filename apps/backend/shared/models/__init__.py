"""
This __init__.py file serves as the central hub for all Pydantic models
in the 'shared' directory. By importing and exposing all models here,
we can simplify imports in other parts of the application.

Instead of writing:
from shared.models.workflow_new import Workflow
from shared.models.execution_new import Execution

You can simply write:
from shared.models import Workflow, Execution

This approach offers several advantages:
1.  **Simplified Imports**: Reduces the verbosity and complexity of import statements.
2.  **Centralized Management**: Provides a single place to see all available shared models.
3.  **Refactoring Ease**: If model files are restructured, only this file needs to be
    updated, not every file that imports them.
4.  **Clear Public API**: Explicitly defines which models are part of the shared public
    interface of this module.
"""

# Import current models only - legacy models removed
from .auth import *
from .chat import *
from .common import *
from .conversation import *
from .execution_new import *  # Current execution models
from .external_actions import *
from .human_in_loop import *
from .mcp import *
from .node_enums import *  # Authoritative node type definitions
from .session import *
from .supabase import *
from .trigger import *
from .workflow_complete import *  # Consolidated API
from .workflow_new import *  # Current workflow models

# SQLAlchemy-dependent models (import only when SQLAlchemy is available)
try:
    from .db_models import *
    from .trigger_index import *
except ImportError:
    # SQLAlchemy not available, skip database models
    pass

# Use __all__ to explicitly define the public API of this module
__all__ = [
    # common.py - Base models
    "BaseModel",
    "TimestampedModel",
    "IDModel",
    "EntityModel",
    "ResponseModel",
    "BaseResponse",
    "ErrorModel",
    "ErrorResponse",
    "HealthStatus",
    "HealthCheckModel",
    "HealthResponse",
    "PaginationModel",
    "PaginatedResponseModel",
    "ServiceStatus",
    "ServiceHealthCheck",
    "NodeTemplate",
    # node_enums.py - Authoritative node type definitions
    "NodeType",
    "TriggerSubtype",
    "AIAgentSubtype",
    "ExternalActionSubtype",
    "ActionSubtype",
    "FlowSubtype",
    "HumanLoopSubtype",
    "ToolSubtype",
    "MemorySubtype",
    "VALID_SUBTYPES",
    "get_valid_subtypes",
    "is_valid_node_subtype_combination",
    "get_all_node_types",
    "get_all_subtypes",
    # workflow_new.py - Current workflow models
    "WorkflowDeploymentStatus",
    "Port",
    "Connection",
    "Node",
    "WorkflowStatistics",
    "WorkflowMetadata",
    "CreateWorkflowRequest",
    "UpdateWorkflowRequest",
    "NodeTemplateListResponse",
    "WorkflowExecutionRequest",
    "WorkflowExecutionResponse",
    "WorkflowResponse",
    "Workflow",
    "WorkflowData",
    # execution_new.py - Current execution models
    "ExecutionStatus",
    "NodeExecutionStatus",
    "ExecutionEventType",
    "LogLevel",
    "TriggerInfo",
    "TokenUsage",
    "LogEntry",
    "ExecutionError",
    "NodeError",
    "NodeExecutionDetails",
    "NodeExecution",
    "Execution",
    "ExecutionUpdateData",
    "ExecutionUpdateEvent",
    "ExecutionSummary",
    "GetExecutionResponse",
    "GetExecutionsResponse",
    "ExecutionActionRequest",
    "UserInputRequest",
    "ExecutionActionResponse",
    "SubscriptionResponse",
    # trigger.py - Trigger and deployment models
    "TriggerStatus",
    "DeploymentStatus",
    "TriggerSpec",
    "CronTriggerSpec",
    "ManualTriggerSpec",
    "WebhookTriggerSpec",
    "EmailTriggerSpec",
    # Authentication models
    "AuthUser",
    "AuthClient",
    "AuthResult",
    # Session models
    "SessionCreate",
    "SessionUpdate",
    "Session",
    "SessionResponse",
    "SessionListResponse",
    # Chat models
    "MessageType",
    "ChatRequest",
    "ChatMessage",
    "ChatSSEEvent",
    "SSEEventType",
    "MessageEventData",
    "StatusChangeEventData",
    "WorkflowEventData",
    "ErrorEventData",
    "DebugEventData",
    "ChatStreamResponse",
    "ChatHistory",
    # Conversation models
    "WorkflowContext",
    "ConversationRequest",
    "ConversationResponse",
    "ResponseType",
    "ErrorContent",
    # MCP models
    "MCPTool",
    "MCPInvokeRequest",
    "MCPInvokeResponse",
    "MCPContentItem",
    "MCPToolsResponse",
    "MCPHealthCheck",
    "MCPErrorResponse",
    # External action models
    "NotionActionType",
    "GitHubActionType",
    "NotionExternalActionParams",
    "GitHubExternalActionParams",
    "SlackExternalActionParams",
    "EmailExternalActionParams",
    "ExternalActionInputData",
    "ExternalActionOutputData",
    # Human-in-the-loop models
    "HILInteractionType",
    "HILChannelType",
    "HILPriority",
    "HILStatus",
    "HILApprovalRequest",
    "HILInputRequest",
    "HILSelectionRequest",
    "HILResponseData",
    "HILOutputData",
    # Database models (SQLAlchemy)
    "Base",
    "WorkflowExecution",
    "WorkflowDB",
    "WorkflowExecutionLog",
    "DeploymentStatusEnum",
    "TriggerStatusEnum",
    "WorkflowStatusEnum",
]
