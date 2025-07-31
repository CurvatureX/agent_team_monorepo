"""
Session Models
会话相关的数据模型
"""

from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from .common import BaseModel, EntityModel


class SessionCreate(BaseModel):
    """
    会话创建请求模型
    """

    action: Optional[str] = Field(default="create", description="会话动作类型 (create, edit, copy)")
    workflow_id: Optional[str] = Field(default=None, description="关联的工作流ID")

    @model_validator(mode="after")
    def validate_session_data(self):
        """验证会话数据的完整性和一致性"""
        # 验证 action 类型
        valid_actions = ["create", "edit", "copy"]
        if self.action and self.action not in valid_actions:
            raise ValueError(f"Invalid action. Must be one of: {valid_actions}")

        # 验证 edit/copy 动作需要 workflow_id
        if self.action in ["edit", "copy"] and not self.workflow_id:
            raise ValueError(f"workflow_id is required for {self.action} actions")

        return self


class SessionUpdate(BaseModel):
    """
    会话更新请求模型
    """

    status: Optional[str] = Field(default=None, description="会话状态")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="更新的元数据")
    last_activity: Optional[str] = Field(default=None, description="最后活动时间")

    @field_validator("status")
    @classmethod
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
    表示一个用户会话实例
    """

    user_id: str = Field(description="会话所属用户ID")
    workflow_id: Optional[str] = Field(default=None, description="关联的工作流ID")
    status: str = Field(default="active", description="会话状态")
    title: Optional[str] = Field(default=None, description="会话标题")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="会话元数据")
    last_activity: Optional[str] = Field(default=None, description="最后活动时间")

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

    sessions: List[Session] = Field(default_factory=list, description="会话列表")
    total_count: int = Field(default=0, description="总数量")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")
