"""
Authentication Models
认证相关的数据模型
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from .common import BaseModel


class AuthUser(BaseModel):
    """
    认证用户模型
    """

    id: str = Field(description="用户ID")
    email: Optional[str] = Field(default=None, description="用户邮箱")
    user_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="用户元数据")
    app_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="应用元数据")
    role: Optional[str] = Field(default=None, description="用户角色")
    aud: Optional[str] = Field(default=None, description="JWT audience")
    iss: Optional[str] = Field(default=None, description="JWT issuer")
    sub: Optional[str] = Field(default=None, description="JWT subject")
    exp: Optional[int] = Field(default=None, description="JWT expiration")
    iat: Optional[int] = Field(default=None, description="JWT issued at")


class AuthClient(BaseModel):
    """
    API客户端认证模型
    """

    client_id: str = Field(description="客户端ID")
    client_name: Optional[str] = Field(default=None, description="客户端名称")
    scopes: List[str] = Field(default_factory=list, description="客户端权限范围")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="客户端元数据")


class AuthResult(BaseModel):
    """
    认证结果模型
    """

    authenticated: bool = Field(description="是否认证成功")
    user: Optional[AuthUser] = Field(default=None, description="认证用户信息")
    client: Optional[AuthClient] = Field(default=None, description="认证客户端信息")
    token_type: Optional[str] = Field(default=None, description="令牌类型 (jwt, api_key)")
    error: Optional[str] = Field(default=None, description="认证错误信息")
