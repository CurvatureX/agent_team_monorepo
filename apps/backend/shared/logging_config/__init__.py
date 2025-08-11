"""
Unified Logging System for All Backend Services
统一的日志系统，支持 CloudWatch 和本地开发
"""

from .config import setup_logging, get_logger
from .formatters import SimpleCloudWatchFormatter, StructuredCloudWatchFormatter

__all__ = [
    "setup_logging",
    "get_logger",
    "SimpleCloudWatchFormatter",
    "StructuredCloudWatchFormatter",
]