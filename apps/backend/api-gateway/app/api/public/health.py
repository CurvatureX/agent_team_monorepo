"""
Public API endpoints - No authentication required
包括健康检查、系统信息等公开端点
"""

import time
from datetime import datetime, timezone

from app.core.config import Settings, get_settings
from app.core.events import health_check
from app.dependencies import CommonDeps
from app.models import HealthCheckModel
from shared.logging_config import get_logger
from fastapi import APIRouter, Depends, Request

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthCheckModel)
async def health_check_endpoint(request: Request, settings: Settings = Depends(get_settings)):
    """Health check endpoint - 公开健康检查接口"""
    start_time = time.time()

    logger.info("🏥 Public health check requested")

    try:
        # 使用核心健康检查
        health_info = await health_check()

        # 添加请求信息
        health_info["timestamp"] = datetime.now(timezone.utc)
        health_info["request_id"] = getattr(request.state, "request_id", None)
        health_info["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)

        return HealthCheckModel(**health_info)

    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return HealthCheckModel(
            service="API Gateway",
            version=settings.VERSION,
            status="unhealthy",
            timestamp=datetime.now(timezone.utc),
            message=f"Health check failed: {str(e)}",
        )
