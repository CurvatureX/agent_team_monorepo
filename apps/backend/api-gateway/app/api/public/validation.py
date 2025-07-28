"""
Validation Status API endpoints for monitoring security validation
验证状态API端点，用于监控安全验证
"""

from datetime import datetime
from typing import Any, Dict

from app.models.base import ResponseModel
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


@router.get("/validation/health")
async def get_validation_health():
    """
    Health check for validation service
    验证服务健康检查
    """
    try:
        stats = validation_service.get_validation_stats()

        # Determine health based on error rate
        error_rate = stats.get("error_rate", 0)
        threat_detection_rate = stats.get("threat_detection_rate", 0)

        is_healthy = error_rate < 10.0  # Less than 10% error rate is considered healthy
        status = "healthy" if is_healthy else "degraded"

        return {
            "status": status,
            "healthy": is_healthy,
            "error_rate_percent": error_rate,
            "threat_detection_rate_percent": threat_detection_rate,
            "requests_processed": stats.get("requests_validated", 0),
            "threats_blocked": stats.get("threats_detected", 0),
            "validation_errors": stats.get("validation_errors", 0),
            "features_active": {
                "request_validation": True,
                "response_validation": True,
                "security_scanning": True,
                "input_sanitization": True,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "status": "error",
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.post("/validation/test")
async def test_validation_service(test_data: Dict[str, Any]):
    """
    Test endpoint for validation service (public for testing)
    验证服务测试端点（公开用于测试）
    """
    try:
        # Test input validation
        validation_result = validation_service.input_validator.validate_request_data(
            test_data, security_check=True
        )

        return {
            "test_result": {
                "is_valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "sanitized": validation_result.sanitized,
                "original_data": test_data,
                "processed_data": validation_result.data,
            },
            "security_checks": {
                "xss_scan": "completed",
                "sql_injection_scan": "completed",
                "command_injection_scan": "completed",
                "path_traversal_scan": "completed",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "test_result": {"is_valid": False, "error": str(e)},
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.post("/validation/reset-stats")
async def reset_validation_stats():
    """
    Reset validation statistics (for testing/monitoring)
    重置验证统计信息（用于测试/监控）
    """
    try:
        old_stats = validation_service.get_validation_stats()
        validation_service.reset_stats()
        new_stats = validation_service.get_validation_stats()

        return {
            "success": True,
            "message": "Validation statistics reset successfully",
            "previous_stats": old_stats,
            "current_stats": new_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.utcnow().isoformat()}
