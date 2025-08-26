"""
HTTP Exception Handlers for FastAPI
"""

import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTP异常"""
    logger.error(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail, "error_code": f"HTTP_{exc.status_code}"},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证异常"""
    logger.error("Validation error occurred", errors=exc.errors(), url=str(request.url))

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "请求数据验证失败",
            "error_code": "VALIDATION_ERROR",
            "details": exc.errors(),
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """处理通用异常"""
    logger.error(
        "Unexpected error occurred",
        error=str(exc),
        error_type=type(exc).__name__,
        url=str(request.url),
    )

    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "内部服务器错误", "error_code": "INTERNAL_ERROR"},
    )
