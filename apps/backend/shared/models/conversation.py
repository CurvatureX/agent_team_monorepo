"""
ProcessConversation 接口的 Pydantic 模型
严格按照 workflow_agent.proto 定义
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkflowContext(BaseModel):
    """工作流上下文 - 对应 proto WorkflowContext"""

    origin: str = Field(..., description="工作流来源: create, edit, copy")
    source_workflow_id: str = Field(default="", description="源工作流ID")


class ConversationRequest(BaseModel):
    """对话请求 - 严格对应 proto ConversationRequest"""

    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    access_token: str = Field(..., description="访问令牌")
    user_message: str = Field(..., description="用户消息")
    workflow_context: Optional[WorkflowContext] = Field(default=None, description="工作流上下文")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess_123456",
                "user_id": "user_123",
                "access_token": "jwt_token_here",
                "user_message": "帮我创建一个处理邮件的工作流",
                "workflow_context": {"origin": "create", "source_workflow_id": ""},
            }
        }
    )


class ResponseType(str, Enum):
    """响应类型 - 对应 proto ResponseType"""

    UNKNOWN = "RESPONSE_TYPE_UNKNOWN"
    MESSAGE = "RESPONSE_TYPE_MESSAGE"
    WORKFLOW = "RESPONSE_TYPE_WORKFLOW"
    ERROR = "RESPONSE_TYPE_ERROR"
    STATUS_CHANGE = "RESPONSE_TYPE_STATUS_CHANGE"


class ErrorContent(BaseModel):
    """错误内容 - 对应 proto ErrorContent"""

    error_code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    details: str = Field(..., description="错误详情")
    is_recoverable: bool = Field(..., description="是否可恢复")


class StatusChangeContent(BaseModel):
    """状态变化内容 - 用于前端调试"""

    previous_stage: Optional[str] = Field(default=None, description="之前的阶段")
    current_stage: str = Field(..., description="当前阶段")
    stage_state: Dict[str, Any] = Field(..., description="完整的阶段状态结构体")
    node_name: str = Field(..., description="执行的节点名称")


class ConversationResponse(BaseModel):
    """对话响应 - 严格对应 proto ConversationResponse"""

    session_id: str = Field(..., description="会话ID")
    response_type: ResponseType = Field(..., description="响应类型")
    is_final: bool = Field(..., description="是否为最终响应")

    # oneof response - 根据 response_type 只有一个会被设置
    message: Optional[str] = Field(default=None, description="消息文本")
    workflow: Optional[str] = Field(default=None, description="工作流JSON字符串")
    error: Optional[ErrorContent] = Field(default=None, description="错误内容")
    status_change: Optional[StatusChangeContent] = Field(default=None, description="状态变化内容")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess_123456",
                "response_type": "RESPONSE_TYPE_MESSAGE",
                "is_final": False,
                "message": "我来帮您创建邮件处理工作流...",
                "workflow": None,
                "error": None,
            }
        }
    )
