"""
Data Models for API Gateway
统一的数据模型定义 - 现在使用shared模型
"""

# 从shared模型导入所有需要的模型
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
)
from shared.models import WorkflowCreateRequest as WorkflowCreate
from shared.models import WorkflowEntity as Workflow  # 基础模型; 认证模型; 会话模型; 工作流模型; MCP模型; 聊天模型
from shared.models import WorkflowUpdateRequest as WorkflowUpdate

# 向后兼容别名
HealthResponse = HealthCheckModel
SessionCreateRequest = SessionCreate
ErrorResponse = ErrorModel

__all__ = [
    # Base models
    "BaseModel",
    "ResponseModel",
    "ErrorModel",
    "HealthCheckModel",
    "HealthResponse",  # 向后兼容
    "SessionCreateRequest",  # 向后兼容
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
    "ChatHistory",
]
