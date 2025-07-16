"""
Enhanced logging configuration for workflow engine.

This module provides structured logging, audit integration, and monitoring
support with performance metrics and security event tracking.
"""

import logging
import logging.config
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger
import structlog

from .config import get_settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if available
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "execution_id"):
            log_data["execution_id"] = record.execution_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data, ensure_ascii=False)


class PerformanceLogger:
    """Logger for performance metrics and monitoring."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"performance.{name}")
        self.name = name
    
    def log_execution_time(
        self, 
        operation: str, 
        duration_ms: float, 
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log operation execution time."""
        extra = {
            "operation": operation,
            "duration_ms": int(duration_ms),
            "component": self.name
        }
        
        if user_id:
            extra["user_id"] = user_id
        if metadata:
            extra.update(metadata)
        
        # Log with different levels based on performance
        if duration_ms > 10000:  # > 10 seconds
            self.logger.warning(f"Slow operation: {operation}", extra=extra)
        elif duration_ms > 5000:  # > 5 seconds
            self.logger.info(f"Operation completed: {operation}", extra=extra)
        else:
            self.logger.debug(f"Operation completed: {operation}", extra=extra)
    
    def log_api_call(
        self,
        provider: str,
        method: str,
        url: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Log API call performance."""
        extra = {
            "provider": provider,
            "method": method,
            "url": url,
            "status_code": status_code,
            "duration_ms": int(duration_ms),
            "component": self.name
        }
        
        if user_id:
            extra["user_id"] = user_id
        if error:
            extra["error"] = error
        
        message = f"API call to {provider}: {method} {url}"
        
        if status_code >= 500:
            self.logger.error(message, extra=extra)
        elif status_code >= 400:
            self.logger.warning(message, extra=extra)
        else:
            self.logger.info(message, extra=extra)
    
    def log_resource_usage(
        self,
        cpu_percent: float,
        memory_mb: float,
        concurrent_operations: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log resource usage metrics."""
        extra = {
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "concurrent_operations": concurrent_operations,
            "component": self.name
        }
        
        if metadata:
            extra.update(metadata)
        
        self.logger.info("Resource usage", extra=extra)


class SecurityLogger:
    """Logger for security events and audit trails."""
    
    def __init__(self):
        self.logger = logging.getLogger("security")
    
    def log_authentication_attempt(
        self,
        user_id: Optional[str],
        success: bool,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authentication attempts."""
        extra = {
            "event_type": "authentication",
            "user_id": user_id,
            "success": success,
            "source_ip": source_ip,
            "user_agent": user_agent
        }
        
        if details:
            extra.update(details)
        
        if success:
            self.logger.info("Authentication successful", extra=extra)
        else:
            self.logger.warning("Authentication failed", extra=extra)
    
    def log_authorization_check(
        self,
        user_id: str,
        resource: str,
        action: str,
        granted: bool,
        reason: Optional[str] = None
    ):
        """Log authorization checks."""
        extra = {
            "event_type": "authorization",
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "granted": granted,
            "reason": reason
        }
        
        if granted:
            self.logger.debug("Access granted", extra=extra)
        else:
            self.logger.warning("Access denied", extra=extra)
    
    def log_suspicious_activity(
        self,
        user_id: Optional[str],
        activity_type: str,
        details: Dict[str, Any],
        source_ip: Optional[str] = None,
        severity: str = "medium"
    ):
        """Log suspicious activities."""
        extra = {
            "event_type": "suspicious_activity",
            "user_id": user_id,
            "activity_type": activity_type,
            "source_ip": source_ip,
            "severity": severity,
            **details
        }
        
        if severity == "critical":
            self.logger.critical("Critical suspicious activity detected", extra=extra)
        elif severity == "high":
            self.logger.error("High priority suspicious activity", extra=extra)
        else:
            self.logger.warning("Suspicious activity detected", extra=extra)


def configure_logging():
    """Configure logging for the application."""
    settings = get_settings()
    
    # Basic configuration
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "json": {
                "()": jsonlogger.JsonFormatter,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "structured",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "structured",
                "filename": "logs/application.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf8"
            },
            "audit_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "structured",
                "filename": "logs/audit.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 50,  # Keep more audit logs
                "encoding": "utf8"
            },
            "security_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "structured",
                "filename": "logs/security.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 30,
                "encoding": "utf8"
            },
            "performance_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "structured",
                "filename": "logs/performance.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 20,
                "encoding": "utf8"
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": log_level,
                "handlers": ["console", "file"]
            },
            "audit": {
                "level": "INFO",
                "handlers": ["audit_file", "console"],
                "propagate": False
            },
            "security": {
                "level": "INFO",
                "handlers": ["security_file", "console"],
                "propagate": False
            },
            "performance": {
                "level": "INFO",
                "handlers": ["performance_file"],
                "propagate": False
            },
            "workflow_engine": {
                "level": log_level,
                "handlers": ["console", "file"]
            },
            "sqlalchemy.engine": {
                "level": "WARNING",  # Reduce SQL query noise
                "handlers": ["file"]
            },
            "httpx": {
                "level": "WARNING",  # Reduce HTTP client noise
                "handlers": ["file"]
            },
            "grpc": {
                "level": "WARNING",  # Reduce gRPC noise
                "handlers": ["file"]
            }
        }
    }
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return logging.getLogger(name)


def get_performance_logger(component: str) -> PerformanceLogger:
    """Get a performance logger for a specific component."""
    return PerformanceLogger(component)


def get_security_logger() -> SecurityLogger:
    """Get the security logger instance."""
    return SecurityLogger()


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)
    
    @property
    def performance_logger(self) -> PerformanceLogger:
        """Get performance logger for this class."""
        return PerformanceLogger(self.__class__.__name__)
    
    def log_with_context(
        self, 
        level: int, 
        message: str, 
        **context
    ):
        """Log message with additional context."""
        extra = {}
        
        # Add common context
        if hasattr(self, 'user_id'):
            extra['user_id'] = self.user_id
        if hasattr(self, 'request_id'):
            extra['request_id'] = self.request_id
        if hasattr(self, 'execution_id'):
            extra['execution_id'] = self.execution_id
        
        # Add provided context
        extra.update(context)
        
        self.logger.log(level, message, extra=extra)


class ContextFilter(logging.Filter):
    """Filter to add context information to log records."""
    
    def __init__(self, context: Dict[str, Any]):
        super().__init__()
        self.context = context
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


def add_logging_context(logger: logging.Logger, **context):
    """Add context to a logger."""
    filter_obj = ContextFilter(context)
    logger.addFilter(filter_obj)
    return logger


# Performance monitoring decorator
def log_performance(component: str, operation: str = None):
    """Decorator to log performance metrics."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            perf_logger = PerformanceLogger(component)
            start_time = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                op_name = operation or func.__name__
                perf_logger.log_execution_time(op_name, duration)
                
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                op_name = operation or func.__name__
                
                perf_logger.log_execution_time(
                    op_name, 
                    duration, 
                    metadata={"error": str(e), "success": False}
                )
                raise
        
        # For async functions
        async def async_wrapper(*args, **kwargs):
            perf_logger = PerformanceLogger(component)
            start_time = datetime.now()
            
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                op_name = operation or func.__name__
                perf_logger.log_execution_time(op_name, duration)
                
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                op_name = operation or func.__name__
                
                perf_logger.log_execution_time(
                    op_name, 
                    duration, 
                    metadata={"error": str(e), "success": False}
                )
                raise
        
        if hasattr(func, '__await__'):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


# Initialize logging when module is imported
configure_logging() 