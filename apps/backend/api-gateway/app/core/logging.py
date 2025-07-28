"""
Logging Configuration for API Gateway
统一的日志配置管理，支持多种格式和级别
"""

import logging
import logging.config
import sys
from typing import Dict, Any
from pathlib import Path

from app.core.config import get_settings


def setup_logging() -> None:
    """
    设置应用程序日志配置
    根据配置文件中的设置选择不同的日志格式和级别
    """
    settings = get_settings()

    # 基础日志配置
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # 根据格式选择配置
    if settings.LOG_FORMAT == "json":
        config = get_json_logging_config(log_level)
    elif settings.LOG_FORMAT == "simple":
        config = get_simple_logging_config(log_level)
    else:
        config = get_standard_logging_config(log_level)

    # 应用配置
    logging.config.dictConfig(config)

    # 配置第三方库日志级别
    configure_third_party_loggers()

    # 记录日志配置信息
    logger = logging.getLogger(__name__)
    logger.info(f"📝 Logging configured: level={settings.LOG_LEVEL}, format={settings.LOG_FORMAT}")


def get_standard_logging_config(log_level: int) -> Dict[str, Any]:
    """标准日志格式配置"""
    settings = get_settings()
    
    loggers_handlers = ["console"]
    handlers_config = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "standard",
            "stream": sys.stdout,
        }
    }

    if settings.is_production():
        loggers_handlers.append("file")
        handlers_config["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "standard",
            "filename": "logs/api_gateway.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d:%(funcName)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": handlers_config,
        "loggers": {
            "app": {"level": log_level, "handlers": loggers_handlers, "propagate": False},
            "uvicorn.access": {"level": "INFO", "handlers": ["console"], "propagate": False},
        },
        "root": {"level": log_level, "handlers": ["console"]},
    }


def get_json_logging_config(log_level: int) -> Dict[str, Any]:
    """JSON格式日志配置（适合生产环境）"""
    settings = get_settings()
    
    loggers_handlers = ["console"]
    handlers_config = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "json",
            "stream": sys.stdout,
        }
    }

    if settings.is_production():
        loggers_handlers.append("file")
        handlers_config["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "json",
            "filename": "logs/api_gateway.json",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "encoding": "utf-8",
        }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d %(funcName)s",
            }
        },
        "handlers": handlers_config,
        "loggers": {
            "app": {"level": log_level, "handlers": loggers_handlers, "propagate": False}
        },
        "root": {"level": log_level, "handlers": ["console"]},
    }


def get_simple_logging_config(log_level: int) -> Dict[str, Any]:
    """简单格式日志配置（适合开发调试）"""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"simple": {"format": "[%(levelname)s] %(message)s"}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "simple",
                "stream": sys.stdout,
            }
        },
        "loggers": {"app": {"level": log_level, "handlers": ["console"], "propagate": False}},
        "root": {"level": log_level, "handlers": ["console"]},
    }


def configure_third_party_loggers() -> None:
    """配置第三方库的日志级别"""
    settings = get_settings()

    # 第三方库日志配置
    third_party_loggers = {
        "httpx": "WARNING",
        "httpcore": "WARNING",
        "supabase": "INFO",
        "redis": "WARNING",
        "grpc": "WARNING",
        "asyncio": "WARNING",
        "urllib3": "WARNING",
        "requests": "WARNING",
    }

    # 在调试模式下显示更多信息
    if settings.DEBUG:
        third_party_loggers.update({"supabase": "DEBUG", "redis": "INFO"})

    for logger_name, level in third_party_loggers.items():
        logging.getLogger(logger_name).setLevel(getattr(logging, level))


def ensure_log_directory() -> None:
    """确保日志目录存在"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)


# 在模块导入时设置日志目录
ensure_log_directory()
