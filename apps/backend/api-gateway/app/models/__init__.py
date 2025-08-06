"""
Data Models for API Gateway
统一的数据模型定义 - 现在使用shared模型
"""

# 从shared模型导入所有需要的模型
try:
    # 尝试直接导入（当PYTHONPATH设置正确时）
    from shared.models import (
        AuthClient,
        AuthResult,
        AuthUser,
        BaseModel,
        ChatHistory,
        ChatMessage,
        ChatRequest,
        ChatSSEEvent,
        SSEEventType,
        MessageEventData,
        StatusChangeEventData,
        WorkflowEventData,
        ErrorEventData,
        DebugEventData,
        ChatStreamResponse,
        ConversationRequest,
        ConversationResponse,
        ResponseType,
        ErrorContent,
        ErrorModel,
        HealthCheckModel,
        MCPContentItem,
        MCPErrorResponse,
        MCPHealthCheck,
        MCPInvokeRequest,
        MCPInvokeResponse,
        MCPTool,
        MCPToolsResponse,
        MessageType,
        ResponseModel,
        Session,
        SessionCreate,
        SessionListResponse,
        SessionResponse,
        SessionUpdate,
        WorkflowExecutionRequest,
        WorkflowExecutionResponse,
        WorkflowResponse,
        NodeTemplateListResponse,
    )
    # 使用 Workflow Engine 的模型定义
    from shared.models import CreateWorkflowRequest as WorkflowCreate
    from shared.models import WorkflowData as Workflow
    from shared.models import UpdateWorkflowRequest as WorkflowUpdate
    from shared.models import NodeData, PositionData, WorkflowSettingsData
except ImportError:
    # 如果直接导入失败，尝试添加路径后导入
    import sys
    from pathlib import Path
    
    # 添加backend目录到Python路径
    backend_dir = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(backend_dir))
    
    from shared.models import (
        AuthClient,
        AuthResult,
        AuthUser,
        BaseModel,
        ChatHistory,
        ChatMessage,
        ChatRequest,
        ChatSSEEvent,
        SSEEventType,
        MessageEventData,
        StatusChangeEventData,
        WorkflowEventData,
        ErrorEventData,
        DebugEventData,
        ChatStreamResponse,
        ConversationRequest,
        ConversationResponse,
        ResponseType,
        ErrorContent,
        ErrorModel,
        HealthCheckModel,
        MCPContentItem,
        MCPErrorResponse,
        MCPHealthCheck,
        MCPInvokeRequest,
        MCPInvokeResponse,
        MCPTool,
        MCPToolsResponse,
        MessageType,
        ResponseModel,
        Session,
        SessionCreate,
        SessionListResponse,
        SessionResponse,
        SessionUpdate,
        WorkflowExecutionRequest,
        WorkflowExecutionResponse,
        WorkflowResponse,
        NodeTemplateListResponse,
    )
    # 使用 Workflow Engine 的模型定义
    from shared.models import CreateWorkflowRequest as WorkflowCreate
    from shared.models import WorkflowData as Workflow
    from shared.models import UpdateWorkflowRequest as WorkflowUpdate
    from shared.models import NodeData, PositionData, WorkflowSettingsData

# 向后兼容别名
HealthResponse = HealthCheckModel
ErrorResponse = ErrorModel

__all__ = [
    # Base models
    "BaseModel",
    "ResponseModel",
    "ErrorModel",
    "HealthCheckModel",
    "HealthResponse",  # 向后兼容
    "SessionResponse",  # 向后兼容
    "ErrorResponse",  # 向后兼容
    # Authentication models
    "AuthUser",
    "AuthClient",
    "AuthResult",
    # Session models
    "Session",
    "SessionCreate",
    "SessionUpdate",
    "SessionResponse",
    "SessionListResponse",
    # Workflow models
    "Workflow",
    "WorkflowCreate",
    "WorkflowUpdate",
    "WorkflowExecutionRequest",
    "WorkflowExecutionResponse",
    "WorkflowResponse",
    "NodeTemplateListResponse",
    "NodeData",
    "PositionData",
    "WorkflowSettingsData",
    # Conversation models
    "ConversationRequest",
    "ConversationResponse",
    "ResponseType",
    "ErrorContent",
    # MCP models
    "MCPTool",
    "MCPToolsResponse",
    "MCPInvokeRequest",
    "MCPInvokeResponse",
    "MCPContentItem",
    "MCPErrorResponse",
    "MCPHealthCheck",
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
]
