# 通用基础模型
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field


class BaseModel(PydanticBaseModel):
    """
    基础模型类
    为所有数据模型提供通用字段和配置
    """

    model_config = ConfigDict(
        # 允许从ORM对象转换为Pydantic模型
        from_attributes=True,
        # 在序列化时排除None值
        exclude_none=True,
        # 使用枚举值而不是枚举名称
        use_enum_values=True,
        # 验证赋值
        validate_assignment=True,
    )


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


class BaseResponse(BaseModel):
    """
    基础响应模型（向后兼容版本）
    """

    success: bool = True
    message: str = ""

    model_config = ConfigDict(json_schema_extra={"example": {"success": True, "message": "操作成功"}})


class ErrorModel(ResponseModel):
    """
    错误响应模型
    """

    success: bool = Field(default=False, description="请求失败")
    error_code: Optional[str] = Field(default=None, description="错误代码")
    error_type: Optional[str] = Field(default=None, description="错误类型")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")


class ErrorResponse(BaseResponse):
    """Error response model（向后兼容版本）"""

    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "message": "操作失败",
                "error_code": "VALIDATION_ERROR",
                "details": {"field": "name", "issue": "名称不能为空"},
            }
        }
    )


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


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
    request_id: Optional[str] = Field(default=None, description="请求ID")
    processing_time_ms: Optional[float] = Field(default=None, description="处理时间（毫秒）")
    environment: Optional[str] = Field(default=None, description="环境")
    debug: Optional[bool] = Field(default=None, description="调试模式")


class HealthResponse(BaseModel):
    """健康响应模型（向后兼容版本）"""

    status: HealthStatus
    version: str = "1.0.0"
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": 1640995200,
                "details": {"database": "connected", "redis": "connected"},
            }
        }
    )


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


# 🎯 简化配置：移除复杂的服务发现模型
# 现在使用静态环境变量配置：WORKFLOW_AGENT_URL 和 WORKFLOW_ENGINE_URL


class ServiceStatus(str, Enum):
    """服务状态枚举"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNREACHABLE = "unreachable"


class ServiceHealthCheck(BaseModel):
    """服务健康检查响应模型"""

    status: ServiceStatus
    status_code: Optional[int] = None
    url: str
    error: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "status_code": 200,
                "url": "http://internal-alb-dns/agent",
                "error": None,
            }
        }
    )
