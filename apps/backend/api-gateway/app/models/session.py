"""
Session Models
会话相关的数据模型
"""

from typing import Optional, Dict, Any
from pydantic import Field, validator

from .base import EntityModel, BaseModel


class SessionCreate(BaseModel):
    """
    会话创建请求模型
    """

    action: Optional[str] = Field(default="chat", description="会话动作类型")
    workflow_id: Optional[str] = Field(default=None, description="关联的工作流ID")
    session_type: str = Field(default="user", description="会话类型 (user, guest, system)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="会话元数据")

    @validator("action")
    def validate_action(cls, v):
        """验证动作类型"""
        valid_actions = ["chat", "workflow_generation", "workflow_execution", "tool_invocation"]
        if v and v not in valid_actions:
            raise ValueError(f"Invalid action. Must be one of: {valid_actions}")
        return v

    @validator("session_type")
    def validate_session_type(cls, v):
        """验证会话类型"""
        valid_types = ["user", "guest", "system"]
        if v not in valid_types:
            raise ValueError(f"Invalid session type. Must be one of: {valid_types}")
        return v


class SessionUpdate(BaseModel):
    """
    会话更新请求模型
    """

    status: Optional[str] = Field(default=None, description="会话状态")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="更新的元数据")
    last_activity: Optional[str] = Field(default=None, description="最后活动时间")

    @validator("status")
    def validate_status(cls, v):
        """验证会话状态"""
        if v is not None:
            valid_statuses = ["active", "inactive", "completed", "error", "archived"]
            if v not in valid_statuses:
                raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v


class Session(EntityModel):
    """
    会话模型
    表示用户或系统的交互会话
    """

    user_id: Optional[str] = Field(default=None, description="用户ID（None表示游客会话）")
    session_type: str = Field(default="user", description="会话类型")
    action: Optional[str] = Field(default="chat", description="会话动作类型")
    workflow_id: Optional[str] = Field(default=None, description="关联的工作流ID")
    status: str = Field(default="active", description="会话状态")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="会话元数据")
    last_activity: Optional[str] = Field(default=None, description="最后活动时间")

    def is_guest_session(self) -> bool:
        """判断是否为游客会话"""
        return self.user_id is None or self.session_type == "guest"

    def is_active(self) -> bool:
        """判断会话是否活跃"""
        return self.status == "active"


class SessionResponse(BaseModel):
    """
    会话响应模型
    """

    session: Session = Field(description="会话信息")
    message: Optional[str] = Field(default=None, description="响应消息")


class SessionListResponse(BaseModel):
    """
    会话列表响应模型
    """

    sessions: list[Session] = Field(default_factory=list, description="会话列表")
    total_count: int = Field(default=0, description="总数量")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")
