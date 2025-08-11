"""
Unified Logging Configuration for All Backend Services
统一的日志配置，支持 CloudWatch 和本地开发
"""

import os
import logging
import sys
from typing import Optional, Dict, Any
from .formatters import SimpleCloudWatchFormatter, StructuredCloudWatchFormatter


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    log_format: Optional[str] = None,
    **kwargs
) -> logging.Logger:
    """
    Setup unified logging for a service
    
    Args:
        service_name: Name of the service (e.g., "api-gateway", "workflow-agent")
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Format type ("simple", "json", "standard")
        **kwargs: Additional configuration options
        
    Returns:
        Configured logger instance
    """
    
    # Get log format from environment or parameter
    if log_format is None:
        log_format = os.getenv("LOG_FORMAT", "simple")
    
    # Get log level from environment or parameter
    log_level = os.getenv("LOG_LEVEL", log_level).upper()
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Set root logger level
    root_logger.setLevel(getattr(logging, log_level))
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    
    # Select formatter based on format type
    if log_format == "json":
        formatter = StructuredCloudWatchFormatter()
    elif log_format == "simple":
        formatter = SimpleCloudWatchFormatter()
    else:
        # Standard Python logging format
        formatter = logging.Formatter(
            fmt="%(levelname)s:     %(asctime)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure third-party library log levels to reduce noise
    _configure_third_party_loggers()
    
    # Get service-specific logger
    logger = logging.getLogger(service_name)
    logger.info(f"Logging configured for {service_name} with level={log_level}, format={log_format}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name (usually module name)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def _configure_third_party_loggers():
    """Configure log levels for third-party libraries to reduce noise"""
    
    # Reduce noise from common libraries
    noisy_loggers = [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "httpx",
        "httpcore",
        "opentelemetry",
        "opentelemetry.instrumentation",
        "opentelemetry.sdk",
        "grpc",
        "urllib3",
        "requests",
        "asyncio",
        "watchfiles",
        "supabase",
        "gotrue",
        "postgrest",
        "realtime",
        "storage3",
        "supafunc",
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Special handling for uvicorn access logs
    # Only show errors and above for access logs
    logging.getLogger("uvicorn.access").setLevel(logging.ERROR)


def add_tracking_id_to_log(record: logging.LogRecord, tracking_id: str):
    """
    Add tracking_id to a log record
    
    This is typically called by middleware to inject the tracking_id
    
    Args:
        record: The log record to modify
        tracking_id: The tracking ID to add
    """
    record.tracking_id = tracking_id  # type: ignore


def configure_for_cloudwatch(logger: logging.Logger):
    """
    Additional configuration specific to CloudWatch
    
    Args:
        logger: Logger to configure
    """
    # CloudWatch automatically captures stdout, so we ensure we're using stdout
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.stream = sys.stdout
    
    # Ensure logs are flushed immediately for CloudWatch
    for handler in logger.handlers:
        handler.flush()


def get_log_config() -> Dict[str, Any]:
    """
    Get current logging configuration as a dictionary
    
    Returns:
        Dictionary with current logging configuration
    """
    return {
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "log_format": os.getenv("LOG_FORMAT", "simple"),
        "handlers": len(logging.getLogger().handlers),
        "third_party_level": "WARNING",
    }