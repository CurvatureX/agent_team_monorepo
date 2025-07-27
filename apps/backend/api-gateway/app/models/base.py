"""
Base Models for API Gateway
基础数据模型定义
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List
from pydantic import BaseModel as PydanticBaseModel, Field


class BaseModel(PydanticBaseModel):
    """
    基础模型类
    为所有数据模型提供通用字段和配置
    """

    class Config:
        # 允许使用orm_mode进行ORM对象转换
        from_attributes = True
        # 在序列化时排除None值
        exclude_none = True
        # 使用枚举值而不是枚举名称
        use_enum_values = True
        # 验证赋值
        validate_assignment = True


class TimestampedModel(BaseModel):
    """
    带时间戳的基础模型
    包含创建时间和更新时间字段
    """

    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="创建时间"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="更新时间"
    )


class IDModel(BaseModel):
    """
    带ID的基础模型
    包含唯一标识符字段
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="唯一标识符")


class EntityModel(IDModel, TimestampedModel):
    """
    实体模型基类
    结合ID和时间戳功能
    """

    pass


class ResponseModel(BaseModel):
    """
    API响应基础模型
    """

    success: bool = Field(default=True, description="请求是否成功")
    message: Optional[str] = Field(default=None, description="响应消息")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="响应时间戳"
    )


class ErrorModel(ResponseModel):
    """
    错误响应模型
    """

    success: bool = Field(default=False, description="请求失败")
    error_code: Optional[str] = Field(default=None, description="错误代码")
    error_type: Optional[str] = Field(default=None, description="错误类型")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")


class PaginationModel(BaseModel):
    """
    分页模型
    """

    page: int = Field(default=1, ge=1, description="页码（从1开始）")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数（1-100）")
    total_count: Optional[int] = Field(default=None, description="总条数")
    total_pages: Optional[int] = Field(default=None, description="总页数")


class PaginatedResponseModel(ResponseModel):
    """
    分页响应模型
    """

    pagination: PaginationModel = Field(description="分页信息")
    data: List[Any] = Field(default_factory=list, description="数据列表")


class HealthCheckModel(BaseModel):
    """
    健康检查模型
    """

    service: str = Field(description="服务名称")
    version: str = Field(description="服务版本")
    status: str = Field(description="服务状态 (healthy, degraded, unhealthy)")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="检查时间"
    )
    checks: Optional[Dict[str, Any]] = Field(default=None, description="详细检查结果")
    message: Optional[str] = Field(default=None, description="状态消息")
