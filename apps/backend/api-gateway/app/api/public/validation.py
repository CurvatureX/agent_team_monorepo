"""
Validation Status API endpoints for monitoring security validation
验证状态API端点，用于监控安全验证
"""

from datetime import datetime
from typing import Any, Dict

from shared.models import ResponseModel
from app.services.auth_service import get_auth_cache_stats
from app.services.validation import (
    EnhancedValidationService,
    get_validation_service,
    validation_service,
)
from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/validation/stats")
async def get_validation_stats(
    service: EnhancedValidationService = Depends(get_validation_service),
):
    """
    Get validation service statistics and health
    获取验证服务统计信息和健康状态
    """
    try:
        # Get validation stats
        validation_stats = service.get_validation_stats()

        # Get auth cache stats
        auth_stats = await get_auth_cache_stats()

        return {
            "validation_service": {
                "status": "healthy",
                "statistics": validation_stats,
                "security_features": {
                    "xss_protection": True,
                    "sql_injection_detection": True,
                    "command_injection_detection": True,
                    "path_traversal_detection": True,
                    "html_sanitization": True,
                    "input_size_limits": True,
                    "response_validation": True,
                    "sensitive_data_detection": True,
                },
            },
            "authentication_cache": auth_stats,
            "system_info": {
                "validation_enabled": True,
                "security_checks_enabled": True,
                "max_request_size_mb": 10.0,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    except Exception as e:
        return {
            "validation_service": {"status": "error", "error": str(e)},
            "timestamp": datetime.utcnow().isoformat(),
        }
