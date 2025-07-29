"""
Data Models for API Gateway
统一的数据模型定义
"""

from .base import BaseModel, ResponseModel, ErrorModel, HealthCheckModel
from .auth import AuthUser, AuthClient, AuthResult
from .session import Session, SessionCreate, SessionUpdate, SessionResponse, SessionListResponse
from .workflow import Workflow, WorkflowCreate, WorkflowUpdate
from .mcp import MCPTool, MCPInvokeRequest, MCPInvokeResponse
from .chat import (
    MessageType,
    ChatRequest,
    ChatMessage,
    ChatSSEEvent,
    ChatHistory,
)

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
    "MCPInvokeRequest",
    "MCPInvokeResponse",
    # Chat models
    "MessageType",
    "ChatRequest",
    "ChatMessage",
    "ChatSSEEvent",
    "ChatHistory",
]
