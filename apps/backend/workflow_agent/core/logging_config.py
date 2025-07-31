"""
Centralized logging configuration using structlog.

Features:
- Simple console format: LEVEL - filename.py:line - message
- Hierarchical log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Automatic file and line number tracking
- Performance optimizations with caching
- Context preservation across async boundaries
"""

import logging
import structlog
from typing import Optional, Dict, Any
import os


def setup_logging(
    log_level: str = "INFO",
    service_name: str = "workflow_agent",
    environment: Optional[str] = None,
) -> None:
    """
    Configure structured logging for the application using structlog.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Name of the service for log identification
        environment: Environment name (development, staging, production)
    """
    # Set up stdlib logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
    )
    
    # Get environment from env var if not provided
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")
    
    # Custom renderer for simple console output with JSON content
    def console_renderer(_, __, event_dict):
        """Render logs in simple format: TIMESTAMP - LEVEL - filename.py:line - message with JSON content"""
        import json
        from datetime import datetime
        
        # Get timestamp - use ISO format with milliseconds
        timestamp = datetime.now().isoformat(timespec='milliseconds')
        
        level = event_dict.get("level", "INFO").upper()
        filename = event_dict.get("filename", "unknown")
        lineno = event_dict.get("lineno", 0)
        message = event_dict.get("event", "")
        
        # Remove metadata fields from the event dict for the JSON content
        content_dict = {k: v for k, v in event_dict.items() 
                       if k not in ["level", "filename", "lineno", "func_name", "event", "logger", "timestamp"]}
        
        # Format the log header with timestamp
        header = f"{timestamp} - {level} - {filename}:{lineno} - {message}"
        
        # If there's additional content, format it as indented JSON
        if content_dict:
            json_content = json.dumps(content_dict, indent=2, ensure_ascii=False, default=str)
            return f"{header}\n{json_content}"
        else:
            return header
    
    # Configure structlog processors
    processors = [
        # Filter by configured log level
        structlog.stdlib.filter_by_level,
        
        # Add contextual information
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        
        # Add call site information (file, line, function)
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
            additional_ignores=["logging", "__name__"],
        ),
        
        # Format positional arguments
        structlog.stdlib.PositionalArgumentsFormatter(),
        
        # Process exceptions
        structlog.processors.format_exc_info,
        
        # Ensure all strings are unicode
        structlog.processors.UnicodeDecoder(),
        
        # Use our custom console renderer
        console_renderer,
    ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(
    name: Optional[str] = None,
    **initial_context: Any
) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance with optional initial context.
    
    Args:
        name: Logger name (typically __name__)
        **initial_context: Initial key-value pairs to bind to logger
        
    Returns:
        Configured logger instance
        
    Example:
        logger = get_logger(__name__, module="workflow_agent", version="1.0.0")
        logger.info("Service started", port=8080)
    """
    logger = structlog.get_logger(name)
    
    if initial_context:
        logger = logger.bind(**initial_context)
    
    return logger


def configure_from_env() -> None:
    """
    Configure logging from environment variables.
    
    Environment variables:
    - LOG_LEVEL: Logging level (default: INFO)
    - SERVICE_NAME: Service identifier (default: workflow_agent)
    - ENVIRONMENT: Environment name (default: development)
    """
    log_level = os.getenv("LOG_LEVEL", "INFO")
    service_name = os.getenv("SERVICE_NAME", "workflow_agent")
    environment = os.getenv("ENVIRONMENT", "development")
    
    setup_logging(
        log_level=log_level,
        service_name=service_name,
        environment=environment,
    )


# Convenience class for log level constants
class LogLevel:
    """Standard log level constants."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Performance optimization: Pre-configured loggers for common modules
_module_loggers: Dict[str, structlog.stdlib.BoundLogger] = {}


def get_module_logger(module_name: str) -> structlog.stdlib.BoundLogger:
    """
    Get or create a cached logger for a module.
    
    This improves performance by caching logger instances.
    
    Args:
        module_name: Module name (typically __name__)
        
    Returns:
        Cached logger instance
    """
    if module_name not in _module_loggers:
        _module_loggers[module_name] = get_logger(module_name)
    return _module_loggers[module_name]