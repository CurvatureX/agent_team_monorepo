"""
API适配器模块
提供统一的外部API调用接口
"""

from .base import (
    APIAdapter,
    APIError,
    AuthenticationError,
    RateLimitError,
    TemporaryError,
    PermanentError,
    RetryConfig,
    OAuth2Config,
    APIAdapterRegistry
)

# 导入所有适配器以触发注册装饰器
from . import github
from . import slack
from . import google_calendar
from . import http_tool

__all__ = [
    "APIAdapter",
    "APIError",
    "AuthenticationError", 
    "RateLimitError",
    "TemporaryError",
    "PermanentError",
    "RetryConfig",
    "OAuth2Config",
    "APIAdapterRegistry"
]