"""
Dependencies for FastAPI
"""

from fastapi import Request
from typing import Optional
from core.logging_config import get_logger

logger = get_logger(__name__)


async def get_request_id(request: Request) -> str:
    """获取请求ID"""
    return getattr(request.state, 'request_id', 'unknown')


async def get_user_context(request: Request) -> Optional[dict]:
    """
    获取用户上下文
    在实际应用中，这里应该从认证中间件获取用户信息
    """
    # 暂时返回默认用户
    return {
        "user_id": "fastapi_user",
        "session_id": getattr(request.state, 'session_id', None)
    }


async def log_request_info(request: Request):
    """记录请求信息"""
    logger.info(
        "FastAPI request",
        method=request.method,
        url=str(request.url),
        client=request.client.host if request.client else None
    )