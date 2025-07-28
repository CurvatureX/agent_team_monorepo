"""
Global Exception Handling for API Gateway
全局异常处理，遵循FastAPI最佳实践
"""

import traceback
from typing import Union, Dict, Any
from datetime import datetime, timezone

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# 自定义异常类
# =============================================================================


class APIGatewayException(Exception):
    """API Gateway基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Dict[str, Any] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(APIGatewayException):
    """认证错误"""

    def __init__(self, message: str = "Authentication failed", details: Dict[str, Any] = None):
        super().__init__(
            message=message, error_code="AUTHENTICATION_FAILED", status_code=401, details=details
        )


class AuthorizationError(APIGatewayException):
    """授权错误"""

    def __init__(self, message: str = "Insufficient permissions", details: Dict[str, Any] = None):
        super().__init__(
            message=message, error_code="AUTHORIZATION_FAILED", status_code=403, details=details
        )


class ValidationError(APIGatewayException):
    """验证错误"""

    def __init__(self, message: str = "Validation failed", details: Dict[str, Any] = None):
        super().__init__(
            message=message, error_code="VALIDATION_ERROR", status_code=400, details=details
        )


class NotFoundError(APIGatewayException):
    """资源未找到错误"""

    def __init__(self, resource: str = "Resource", details: Dict[str, Any] = None):
        super().__init__(
            message=f"{resource} not found",
            error_code="NOT_FOUND",
            status_code=404,
            details=details,
        )


class ConflictError(APIGatewayException):
    """冲突错误"""

    def __init__(self, message: str = "Resource conflict", details: Dict[str, Any] = None):
        super().__init__(message=message, error_code="CONFLICT", status_code=409, details=details)


class RateLimitError(APIGatewayException):
    """限流错误"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = None,
        details: Dict[str, Any] = None,
    ):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message=message, error_code="RATE_LIMIT_EXCEEDED", status_code=429, details=details
        )


class ServiceUnavailableError(APIGatewayException):
    """服务不可用错误"""

    def __init__(self, service: str = "Service", details: Dict[str, Any] = None):
        super().__init__(
            message=f"{service} is temporarily unavailable",
            error_code="SERVICE_UNAVAILABLE",
            status_code=503,
            details=details,
        )


class ExternalServiceError(APIGatewayException):
    """外部服务错误"""

    def __init__(self, service: str, message: str = None, details: Dict[str, Any] = None):
        message = message or f"External service '{service}' error"
        super().__init__(
            message=message, error_code="EXTERNAL_SERVICE_ERROR", status_code=502, details=details
        )


class TimeoutError(APIGatewayException):
    """超时错误"""

    def __init__(self, operation: str = "Operation", details: Dict[str, Any] = None):
        super().__init__(
            message=f"{operation} timed out", error_code="TIMEOUT", status_code=408, details=details
        )


# =============================================================================
# 异常处理函数
# =============================================================================


def create_error_response(
    request: Request,
    error_code: str,
    message: str,
    status_code: int = 500,
    details: Dict[str, Any] = None,
) -> JSONResponse:
    """
    创建标准化的错误响应

    Args:
        request: FastAPI请求对象
        error_code: 错误代码
        message: 错误消息
        status_code: HTTP状态码
        details: 错误详情

    Returns:
        JSON响应
    """
    error_response = {
        "success": False,
        "error_code": error_code,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
        "method": request.method,
    }

    # 添加请求ID（如果存在）
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        error_response["request_id"] = request_id

    # 添加详细信息
    if details:
        error_response["details"] = details

    # 在调试模式下添加更多信息
    try:
        from app.core.config import get_settings

        settings = get_settings()
        if settings.DEBUG:
            error_response["debug"] = {
                "user_agent": request.headers.get("User-Agent"),
                "client_ip": request.headers.get("X-Forwarded-For")
                or request.headers.get("X-Real-IP")
                or str(request.client.host)
                if request.client
                else "unknown",
            }
    except Exception:
        pass  # 忽略配置获取错误

    return JSONResponse(status_code=status_code, content=error_response)


# =============================================================================
# 异常处理器
# =============================================================================


async def api_gateway_exception_handler(request: Request, exc: APIGatewayException) -> JSONResponse:
    """处理自定义API Gateway异常"""
    logger.error(
        f"API Gateway Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details,
        },
    )

    return create_error_response(
        request=request,
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理FastAPI HTTP异常"""
    error_code = f"HTTP_{exc.status_code}"

    # 特殊处理某些状态码
    if exc.status_code == 401:
        error_code = "AUTHENTICATION_REQUIRED"
    elif exc.status_code == 403:
        error_code = "AUTHORIZATION_FAILED"
    elif exc.status_code == 404:
        error_code = "NOT_FOUND"
    elif exc.status_code == 422:
        error_code = "VALIDATION_ERROR"

    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={"status_code": exc.status_code, "path": request.url.path, "method": request.method},
    )

    # 处理详细信息
    details = None
    if isinstance(exc.detail, dict):
        details = exc.detail
        message = details.get("message", f"HTTP {exc.status_code} error")
    else:
        message = str(exc.detail)

    return create_error_response(
        request=request,
        error_code=error_code,
        message=message,
        status_code=exc.status_code,
        details=details,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """处理请求验证异常"""
    logger.warning(
        f"Validation Error: {exc.errors()}",
        extra={"path": request.url.path, "method": request.method, "errors": exc.errors()},
    )

    # 格式化验证错误
    error_details = []
    for error in exc.errors():
        error_detail = {
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        if "input" in error:
            error_detail["input"] = error["input"]
        error_details.append(error_detail)

    return create_error_response(
        request=request,
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=422,
        details={"validation_errors": error_details},
    )


async def starlette_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """处理Starlette HTTP异常"""
    logger.warning(
        f"Starlette HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={"status_code": exc.status_code, "path": request.url.path, "method": request.method},
    )

    return create_error_response(
        request=request,
        error_code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        status_code=exc.status_code,
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的一般异常"""
    error_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    logger.error(
        f"Unhandled Exception [{error_id}]: {str(exc)}",
        extra={
            "error_id": error_id,
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        },
    )

    # 在生产环境中隐藏内部错误详情
    try:
        from app.core.config import get_settings

        settings = get_settings()
        debug = settings.DEBUG
    except Exception:
        debug = False

    if debug:
        details = {
            "exception_type": type(exc).__name__,
            "error_id": error_id,
            "traceback": traceback.format_exc().split("\n"),
        }
        message = f"Internal server error: {str(exc)}"
    else:
        details = {"error_id": error_id}
        message = "Internal server error occurred"

    return create_error_response(
        request=request,
        error_code="INTERNAL_SERVER_ERROR",
        message=message,
        status_code=500,
        details=details,
    )


# =============================================================================
# 异常处理器注册函数
# =============================================================================


def register_exception_handlers(app):
    """
    注册所有异常处理器到FastAPI应用

    Args:
        app: FastAPI应用实例
    """
    # 自定义异常
    app.add_exception_handler(APIGatewayException, api_gateway_exception_handler)

    # FastAPI异常
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Starlette异常
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)

    # 通用异常（必须放在最后）
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("✅ Exception handlers registered successfully")
