"""
This __init__.py file serves as the central hub for all Pydantic models
in the 'shared' directory. By importing and exposing all models here,
we can simplify imports in other parts of the application.

Instead of writing:
from shared.models.workflow import WorkflowData
from shared.models.agent import WorkflowGenerationRequest

You can simply write:
from shared.models import WorkflowData, WorkflowGenerationRequest

This approach offers several advantages:
1.  **Simplified Imports**: Reduces the verbosity and complexity of import statements.
2.  **Centralized Management**: Provides a single place to see all available shared models.
3.  **Refactoring Ease**: If model files are restructured, only this file needs to be
    updated, not every file that imports them.
4.  **Clear Public API**: Explicitly defines which models are part of the shared public
    interface of this module.
"""

from .agent import *
from .auth import *
from .chat import *

# Import all models from the respective files
from .common import *
from .conversation import *
from .db_models import *
from .execution import *
from .mcp import *
from .node import *
from .session import *
from .trigger import *
from .workflow import *

# Use __all__ to explicitly define the public API of this module
__all__ = [
    # common.py - 基础模型
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
    # Workflow models
    # workflow.py
    "PositionData",
    "RetryPolicyData",
    "NodeData",
    "ConnectionData",
    "ConnectionArrayData",
    "NodeConnectionsData",
    "ConnectionsMapData",
    "WorkflowSettingsData",
    "WorkflowData",
    "CreateWorkflowRequest",
    "CreateWorkflowResponse",
    "GetWorkflowRequest",
    "GetWorkflowResponse",
    "UpdateWorkflowRequest",
    "UpdateWorkflowResponse",
    "DeleteWorkflowRequest",
    "DeleteWorkflowResponse",
    "ListWorkflowsRequest",
    "ListWorkflowsResponse",
    "ExecuteWorkflowRequest",
    "ExecuteWorkflowResponse",
    # API Gateway工作流模型
    "WorkflowStatus",
    "WorkflowType",
    "NodeType",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowCreateRequest",
    "WorkflowUpdateRequest",
    "WorkflowEntity",
    "WorkflowExecutionRecord",
    "WorkflowResponse",
    "WorkflowListResponse",
    "WorkflowExecutionRequest",
    "WorkflowExecutionResponse",
    "NodeTemplate",
    "NodeTemplateListResponse",
    # Conversation models (ProcessConversation interface)
    "WorkflowContext",
    "ConversationRequest",
    "ConversationResponse",
    "ResponseType",
    "ErrorContent",
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
    # MCP models
    "MCPTool",
    "MCPInvokeRequest",
    "MCPInvokeResponse",
    "MCPContentItem",
    "MCPToolsResponse",
    "MCPHealthCheck",
    "MCPErrorResponse",
    # agent.py
    "WorkflowGenerationRequest",
    "WorkflowGenerationResponse",
    "WorkflowRefinementRequest",
    "WorkflowRefinementResponse",
    "WorkflowValidationRequest",
    "WorkflowValidationResponse",
    # execution.py
    "ExecutionStatus",
    "ExecutionLog",
    "Execution",
    # trigger.py
    "TriggerType",
    "Trigger",
    # node.py
    "NodeTemplate",
    # db_models.py - SQLAlchemy数据库模型
    "Base",
    "WorkflowExecution",
    "WorkflowDB",
    "NodeTemplateDB",
]
