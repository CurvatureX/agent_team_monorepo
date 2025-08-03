"""
External API Integration Models
外部API集成相关的数据模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import Field, field_validator

from .base import BaseModel, TimestampedModel


class ExternalAPIProvider(str, Enum):
    """外部API提供商枚举"""
    GOOGLE_CALENDAR = "google_calendar"
    GITHUB = "github"
    SLACK = "slack"
    HTTP_TOOL = "http_tool"


class OAuth2AuthorizeRequest(BaseModel):
    """OAuth2授权请求模型"""
    
    provider: ExternalAPIProvider = Field(description="API提供商")
    scopes: List[str] = Field(default_factory=list, description="请求的权限范围")
    redirect_url: Optional[str] = Field(default=None, description="授权后重定向URL")
    
    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v, info):
        """验证权限范围"""
        if not v:  # 允许空列表，使用默认权限
            return v
        
        # 基础验证：确保所有scope都是字符串
        if not all(isinstance(scope, str) for scope in v):
            raise ValueError("All scopes must be strings")
        
        return v


class OAuth2AuthUrlResponse(BaseModel):
    """OAuth2授权URL响应模型"""
    
    auth_url: str = Field(description="授权URL")
    state: str = Field(description="状态参数，用于防止CSRF攻击")
    expires_at: datetime = Field(description="授权URL过期时间")
    provider: str = Field(description="API提供商")


class OAuth2CallbackRequest(BaseModel):
    """OAuth2回调请求模型"""
    
    code: str = Field(description="授权码")
    state: str = Field(description="状态参数")
    provider: ExternalAPIProvider = Field(description="API提供商")


class OAuth2TokenResponse(BaseModel):
    """OAuth2令牌响应模型"""
    
    access_token: str = Field(description="访问令牌")
    refresh_token: Optional[str] = Field(default=None, description="刷新令牌")
    expires_at: Optional[datetime] = Field(default=None, description="令牌过期时间")
    scope: List[str] = Field(default_factory=list, description="授权的权限范围")
    provider: str = Field(description="API提供商")
    token_type: str = Field(default="Bearer", description="令牌类型")


class CredentialInfo(TimestampedModel):
    """凭证信息模型"""
    
    provider: str = Field(description="API提供商")
    is_valid: bool = Field(description="凭证是否有效")
    scope: List[str] = Field(default_factory=list, description="授权的权限范围")
    last_used_at: Optional[datetime] = Field(default=None, description="最后使用时间")
    expires_at: Optional[datetime] = Field(default=None, description="凭证过期时间")


class CredentialListResponse(BaseModel):
    """凭证列表响应模型"""
    
    credentials: List[CredentialInfo] = Field(default_factory=list, description="凭证列表")
    total_count: int = Field(default=0, description="总数量")


class TestAPICallRequest(BaseModel):
    """测试API调用请求模型"""
    
    provider: ExternalAPIProvider = Field(description="API提供商")
    operation: str = Field(description="操作名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="操作参数")
    timeout_seconds: int = Field(default=30, description="超时时间（秒）")


class TestAPICallResponse(BaseModel):
    """测试API调用响应模型"""
    
    success: bool = Field(description="调用是否成功")
    provider: str = Field(description="API提供商")
    operation: str = Field(description="操作名称")
    execution_time_ms: float = Field(description="执行时间（毫秒）")
    result: Optional[Dict[str, Any]] = Field(default=None, description="调用结果")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="详细错误信息")


class ExternalAPICallLog(TimestampedModel):
    """外部API调用日志模型"""
    
    user_id: str = Field(description="用户ID")
    provider: str = Field(description="API提供商")
    operation: str = Field(description="操作名称")
    success: bool = Field(description="调用是否成功")
    execution_time_ms: float = Field(description="执行时间（毫秒）")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    request_parameters: Optional[Dict[str, Any]] = Field(default=None, description="请求参数")
    response_data: Optional[Dict[str, Any]] = Field(default=None, description="响应数据")


class ExternalAPIStatus(BaseModel):
    """外部API状态模型"""
    
    provider: str = Field(description="API提供商")
    available: bool = Field(description="是否可用")
    operations: List[str] = Field(default_factory=list, description="支持的操作列表")
    last_check: datetime = Field(description="最后检查时间")
    response_time_ms: Optional[float] = Field(default=None, description="响应时间（毫秒）")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class ExternalAPIStatusResponse(BaseModel):
    """外部API状态响应模型"""
    
    providers: List[ExternalAPIStatus] = Field(default_factory=list, description="提供商状态列表")
    total_available: int = Field(default=0, description="可用提供商数量")
    last_updated: datetime = Field(description="最后更新时间")


class StatusResponse(BaseModel):
    """通用状态响应模型"""
    
    success: bool = Field(description="操作是否成功")
    message: str = Field(description="状态消息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="详细信息")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    
    error: str = Field(description="错误类型")
    message: str = Field(description="错误消息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")
    provider: Optional[str] = Field(default=None, description="相关的API提供商")
    operation: Optional[str] = Field(default=None, description="相关的操作")


class ExternalAPIMetrics(BaseModel):
    """外部API指标模型"""
    
    provider: str = Field(description="API提供商")
    total_calls: int = Field(default=0, description="总调用次数")
    successful_calls: int = Field(default=0, description="成功调用次数")
    failed_calls: int = Field(default=0, description="失败调用次数")
    average_response_time_ms: float = Field(default=0.0, description="平均响应时间（毫秒）")
    last_24h_calls: int = Field(default=0, description="最近24小时调用次数")
    success_rate: float = Field(default=0.0, description="成功率")


class ExternalAPIMetricsResponse(BaseModel):
    """外部API指标响应模型"""
    
    metrics: List[ExternalAPIMetrics] = Field(default_factory=list, description="指标列表")
    time_range: str = Field(description="时间范围")
    generated_at: datetime = Field(description="生成时间")