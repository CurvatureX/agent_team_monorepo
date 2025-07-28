"""
Authentication Models
认证相关的数据模型
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from .base import BaseModel, TimestampedModel


class AuthUser(BaseModel):
    """
    认证用户模型
    表示通过Supabase认证的用户
    """

    sub: str = Field(description="用户唯一标识符（Supabase用户ID）")
    email: Optional[str] = Field(default=None, description="用户邮箱")
    email_verified: bool = Field(default=False, description="邮箱是否已验证")
    phone: Optional[str] = Field(default=None, description="用户电话")
    role: Optional[str] = Field(default="authenticated", description="用户角色")
    aud: Optional[str] = Field(default=None, description="JWT audience")
    iat: Optional[int] = Field(default=None, description="JWT issued at")
    exp: Optional[int] = Field(default=None, description="JWT expires at")
    user_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="用户元数据")
    app_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="应用元数据")


class AuthClient(TimestampedModel):
    """
    MCP API客户端模型
    表示通过API Key认证的客户端
    """

    id: str = Field(description="客户端唯一标识符")
    client_name: str = Field(description="客户端名称")
    scopes: List[str] = Field(default_factory=list, description="客户端权限范围")
    rate_limit_tier: str = Field(
        default="standard", description="限流级别 (development, standard, premium)"
    )
    active: bool = Field(default=True, description="客户端是否激活")
    last_used: Optional[datetime] = Field(default=None, description="最后使用时间")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")

    @field_validator("rate_limit_tier")
    @classmethod
    def validate_rate_limit_tier(cls, v):
        """验证限流级别"""
        valid_tiers = ["development", "standard", "premium", "enterprise"]
        if v not in valid_tiers:
            raise ValueError(f"Invalid rate limit tier. Must be one of: {valid_tiers}")
        return v


class AuthResult(BaseModel):
    """
    认证结果模型
    表示认证过程的结果
    """

    success: bool = Field(description="认证是否成功")
    auth_type: Optional[str] = Field(default=None, description="认证类型 (supabase, mcp_api_key, none)")
    user: Optional[AuthUser] = Field(default=None, description="认证用户信息（Supabase认证）")
    client: Optional[AuthClient] = Field(default=None, description="认证客户端信息（API Key认证）")
    token: Optional[str] = Field(default=None, description="访问令牌")
    error: Optional[str] = Field(default=None, description="认证错误信息")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="详细错误信息")


class TokenInfo(BaseModel):
    """
    令牌信息模型
    """

    access_token: str = Field(description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: Optional[int] = Field(default=None, description="过期时间（秒）")
    refresh_token: Optional[str] = Field(default=None, description="刷新令牌")
    scope: Optional[str] = Field(default=None, description="令牌权限范围")


class APIKeyCreate(BaseModel):
    """
    API Key创建请求模型
    """

    client_name: str = Field(description="客户端名称")
    scopes: List[str] = Field(default=["tools:read"], description="权限范围")
    rate_limit_tier: str = Field(default="standard", description="限流级别")
    expires_days: Optional[int] = Field(default=None, description="过期天数（None表示永不过期）")

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v):
        """验证权限范围"""
        valid_scopes = ["tools:read", "tools:execute", "health:check", "admin"]

        for scope in v:
            if scope not in valid_scopes:
                raise ValueError(f"Invalid scope '{scope}'. Valid scopes: {valid_scopes}")

        return v


class APIKeyResponse(BaseModel):
    """
    API Key响应模型
    """

    api_key: str = Field(description="生成的API密钥")
    client: AuthClient = Field(description="客户端信息")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")


class UserProfile(BaseModel):
    """
    用户资料模型
    """

    user_id: str = Field(description="用户唯一标识符")
    email: Optional[str] = Field(default=None, description="用户邮箱")
    name: Optional[str] = Field(default=None, description="用户姓名")
    avatar_url: Optional[str] = Field(default=None, description="头像URL")
    created_at: Optional[str] = Field(default=None, description="账户创建时间")
    updated_at: Optional[str] = Field(default=None, description="账户更新时间")
    email_verified: bool = Field(default=False, description="邮箱验证状态")
    phone: Optional[str] = Field(default=None, description="电话号码")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="用户元数据")


class UserProfileResponse(BaseModel):
    """
    用户资料响应模型
    """

    user_profile: UserProfile = Field(description="用户资料信息")
    message: Optional[str] = Field(default=None, description="响应消息")


class UserSession(BaseModel):
    """
    用户会话模型（认证相关）
    """

    id: str = Field(description="会话ID")
    session_type: Optional[str] = Field(default=None, description="会话类型")
    status: str = Field(description="会话状态")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    last_activity: Optional[str] = Field(default=None, description="最后活动时间")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="会话元数据")
    auth_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="认证上下文")


class UserSessionListResponse(BaseModel):
    """
    用户会话列表响应模型
    """

    sessions: List[UserSession] = Field(default_factory=list, description="会话列表")
    total_count: int = Field(default=0, description="总数量")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")
    message: Optional[str] = Field(default=None, description="响应消息")
