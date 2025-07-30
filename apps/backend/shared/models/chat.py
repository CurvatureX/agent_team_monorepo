"""
Chat Models
聊天相关的数据模型
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from .common import BaseModel, EntityModel


class MessageType(str, Enum):
    """消息类型枚举"""

    USER = "user"
    ASSISTANT = "assistant"


class ChatRequest(BaseModel):
    """
    聊天请求模型
    """

    session_id: str = Field(description="会话ID")
    user_message: str = Field(description="用户消息内容")

    @field_validator("user_message")
    @classmethod
    def validate_user_message(cls, v):
        """验证消息内容"""
        if not v or not v.strip():
            raise ValueError("User message cannot be empty")
        return v.strip()


class ChatMessage(BaseModel):
    """
    聊天消息模型 - 符合 chats 表结构
    """

    id: Optional[int] = Field(default=None, description="消息ID")
    session_id: str = Field(description="会话ID")
    user_id: str = Field(description="用户ID")
    message_type: MessageType = Field(description="消息类型")
    content: str = Field(default="", description="消息内容")
    sequence_number: Optional[int] = Field(default=None, description="消息序号")
    created_at: Optional[str] = Field(default=None, description="创建时间")


class ChatSSEEvent(BaseModel):
    """
    聊天SSE事件模型
    """

    event: str = Field(description="事件类型")
    data: Dict[str, Any] = Field(description="事件数据")
    id: Optional[str] = Field(default=None, description="事件ID")
    retry: Optional[int] = Field(default=None, description="重试间隔(毫秒)")


class ChatHistory(BaseModel):
    """
    聊天历史模型
    """

    messages: List[ChatMessage] = Field(default_factory=list, description="聊天消息列表")
    session_id: str = Field(description="会话ID")
    total_count: int = Field(default=0, description="消息总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=50, description="每页大小")
