"""
Chat Models
聊天相关的数据模型
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator

from .base import BaseModel, EntityModel


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


class SSEEventType(str, Enum):
    """SSE事件类型枚举"""
    MESSAGE = "message"
    STATUS_CHANGE = "status_change"
    WORKFLOW = "workflow"
    ERROR = "error"
    DEBUG = "debug"


class MessageEventData(BaseModel):
    """消息事件数据"""
    text: str = Field(description="消息文本内容")
    role: str = Field(default="assistant", description="消息角色")
    status: Optional[str] = Field(default=None, description="处理状态")
    message: Optional[str] = Field(default=None, description="状态消息")


class StatusChangeEventData(BaseModel):
    """状态变更事件数据"""
    previous_stage: Optional[str] = Field(description="前一阶段")
    current_stage: str = Field(description="当前阶段")
    stage_state: Optional[Dict[str, Any]] = Field(default=None, description="阶段状态详情")
    node_name: Optional[str] = Field(default=None, description="节点名称")


class WorkflowEventData(BaseModel):
    """工作流事件数据"""
    text: str = Field(description="工作流生成消息")
    workflow: Dict[str, Any] = Field(description="工作流定义")


class ErrorEventData(BaseModel):
    """错误事件数据"""
    error: Optional[str] = Field(default=None, description="错误消息")
    error_type: Optional[str] = Field(default=None, description="错误类型")
    error_code: Optional[str] = Field(default=None, description="错误代码")
    message: Optional[str] = Field(default=None, description="错误消息")
    details: Optional[str] = Field(default=None, description="错误详情")
    is_recoverable: Optional[bool] = Field(default=True, description="是否可恢复")


class DebugEventData(BaseModel):
    """调试事件数据"""
    message: str = Field(description="调试消息")
    raw_response: Optional[Dict[str, Any]] = Field(default=None, description="原始响应")


# Union type for event data
EventDataType = Union[
    MessageEventData,
    StatusChangeEventData,
    WorkflowEventData,
    ErrorEventData,
    DebugEventData,
    Dict[str, Any]
]


class ChatSSEEvent(BaseModel):
    """
    聊天SSE事件模型 - 用于流式响应
    
    不同类型的事件会有不同的data结构:
    - message: MessageEventData
    - status_change: StatusChangeEventData
    - workflow: WorkflowEventData
    - error: ErrorEventData
    - debug: DebugEventData
    """

    type: SSEEventType = Field(description="事件类型")
    data: Dict[str, Any] = Field(description="事件数据，结构根据type而定")
    session_id: str = Field(description="会话ID")
    timestamp: str = Field(description="ISO格式时间戳")
    is_final: Optional[bool] = Field(default=False, description="是否为最终响应")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "message",
                    "data": {
                        "text": "What specific conditions should trigger the sync?",
                        "role": "assistant"
                    },
                    "session_id": "2800ed2b-d902-4151-b68d-5c3381d06e46",
                    "timestamp": "2025-07-31T06:48:08.473674+00:00",
                    "is_final": True
                },
                {
                    "type": "status_change",
                    "data": {
                        "previous_stage": "clarification",
                        "current_stage": "negotiation",
                        "stage_state": {},
                        "node_name": "negotiation_node"
                    },
                    "session_id": "2800ed2b-d902-4151-b68d-5c3381d06e46",
                    "timestamp": "2025-07-31T06:48:08.473674+00:00",
                    "is_final": False
                },
                {
                    "type": "workflow",
                    "data": {
                        "text": "Workflow generated successfully!",
                        "workflow": {
                            "name": "Gmail to Slack Sync",
                            "nodes": []
                        }
                    },
                    "session_id": "2800ed2b-d902-4151-b68d-5c3381d06e46",
                    "timestamp": "2025-07-31T06:48:08.473674+00:00",
                    "is_final": False
                }
            ]
        }


class ChatStreamResponse(BaseModel):
    """
    聊天流式响应包装模型
    用于Swagger文档展示SSE响应格式
    """
    event_stream: List[ChatSSEEvent] = Field(
        description="SSE事件流，实际响应为text/event-stream格式"
    )
    
    class Config:
        json_schema_extra = {
            "description": "注意：实际响应为SSE (Server-Sent Events) 流式格式，此模型仅用于文档展示"
        }


class ChatHistory(BaseModel):
    """
    聊天历史模型
    """

    session_id: str = Field(description="会话ID")
    messages: List[ChatMessage] = Field(default_factory=list, description="消息列表")
    total_count: int = Field(default=0, description="消息总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=50, description="每页大小")

