"""
Chat Models
聊天相关的数据模型
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from .base import BaseModel, EntityModel


class MessageType(str, Enum):
    """消息类型枚举"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    ERROR = "error"


class ChatRequest(BaseModel):
    """
    聊天请求模型
    """

    session_id: str = Field(description="会话ID")
    message: str = Field(description="用户消息内容")
    message_type: MessageType = Field(default=MessageType.USER, description="消息类型")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        """验证消息内容"""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class ChatMessage(EntityModel):
    """
    聊天消息模型
    """

    session_id: str = Field(description="会话ID")
    user_id: str = Field(description="用户ID")
    message_type: MessageType = Field(description="消息类型")
    content: str = Field(description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="消息元数据")
    parent_message_id: Optional[str] = Field(default=None, description="父消息ID（用于回复链）")
    tokens_used: Optional[int] = Field(default=None, description="使用的token数量")
    processing_time_ms: Optional[int] = Field(default=None, description="处理时间（毫秒）")


class ChatSSEEvent(BaseModel):
    """
    聊天SSE事件模型
    """

    type: str = Field(description="事件类型 (message, status, error, workflow_stage)")
    data: Dict[str, Any] = Field(description="事件数据")
    session_id: str = Field(description="会话ID")
    timestamp: Optional[str] = Field(default=None, description="时间戳")

    @field_validator("type")
    @classmethod
    def validate_event_type(cls, v):
        """验证事件类型"""
        valid_types = ["message", "status", "error", "workflow_stage", "tool_call", "completion"]
        if v not in valid_types:
            raise ValueError(f"Invalid event type. Must be one of: {valid_types}")
        return v


class ChatResponse(BaseModel):
    """
    聊天响应模型
    """

    message_id: str = Field(description="消息ID")
    session_id: str = Field(description="会话ID")
    content: str = Field(description="响应内容")
    message_type: MessageType = Field(default=MessageType.ASSISTANT, description="消息类型")
    tokens_used: Optional[int] = Field(default=None, description="使用的token数量")
    processing_time_ms: Optional[int] = Field(default=None, description="处理时间（毫秒）")


class ChatHistory(BaseModel):
    """
    聊天历史模型
    """

    session_id: str = Field(description="会话ID")
    messages: List[ChatMessage] = Field(default_factory=list, description="消息列表")
    total_count: int = Field(default=0, description="消息总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=50, description="每页大小")


class WorkflowGenerationEvent(BaseModel):
    """
    工作流生成事件模型
    """

    stage: str = Field(description="生成阶段")
    progress: float = Field(ge=0.0, le=1.0, description="进度（0-1）")
    message: str = Field(description="阶段消息")
    workflow_data: Optional[Dict[str, Any]] = Field(default=None, description="工作流数据（完成时提供）")

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v):
        """验证生成阶段"""
        valid_stages = [
            "analyzing",
            "planning",
            "generating_nodes",
            "connecting_flows",
            "optimizing",
            "completed",
            "error",
        ]
        if v not in valid_stages:
            raise ValueError(f"Invalid stage. Must be one of: {valid_stages}")
        return v
