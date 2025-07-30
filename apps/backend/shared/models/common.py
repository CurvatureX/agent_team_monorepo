# 通用基础模型
import time
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base model for all responses"""

    success: bool = True
    message: str = ""

    class Config:
        json_schema_extra = {"example": {"success": True, "message": "操作成功"}}


class ErrorResponse(BaseResponse):
    """Error response model"""

    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "操作失败",
                "error_code": "VALIDATION_ERROR",
                "details": {"field": "name", "issue": "名称不能为空"},
            }
        }


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthResponse(BaseModel):
    status: HealthStatus
    version: str = "1.0.0"
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    details: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": 1640995200,
                "details": {"database": "connected", "redis": "connected"},
            }
        }


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

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "status_code": 200,
                "url": "http://internal-alb-dns/agent",
                "error": None,
            }
        }
