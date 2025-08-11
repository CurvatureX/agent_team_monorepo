"""
Enhanced logging utility using shared logging configuration
Compatible with the unified logging system
"""

import sys
from typing import Optional
import logging

# Import from shared logging configuration
from shared.logging_config import get_logger as shared_get_logger, setup_logging as shared_setup_logging


def setup_logger(name: str = "api-gateway", level: Optional[str] = None) -> logging.Logger:
    """
    Setup logger using shared configuration
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR). If None, uses config setting
        
    Returns:
        Configured logger instance
    """
    # Use shared setup_logging if this is the main logger
    if name == "api-gateway":
        return shared_setup_logging(
            service_name=name,
            log_level=level or "INFO"
        )
    
    # For other loggers, just get from shared
    return shared_get_logger(name)


# Global logger instance
_logger: Optional[logging.Logger] = None


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get or create a logger instance using shared configuration
    
    Args:
        name: Logger name, defaults to calling module name or global logger
        
    Returns:
        Configured logger instance
    """
    if name is not None:
        # Return named logger using shared configuration
        return shared_get_logger(name)
    
    # Backward compatibility: return global logger
    global _logger
    if _logger is None:
        _logger = shared_get_logger("api-gateway")
    return _logger


def log_info(message: str) -> None:
    """Log info message"""
    logger = get_logger()
    if logger.isEnabledFor(logging.INFO):
        # Get caller's frame info
        frame = logging.currentframe()
        if frame and frame.f_back:
            caller_frame = frame.f_back
            # Create a LogRecord with caller's location
            record = logging.LogRecord(
                name=logger.name,
                level=logging.INFO,
                pathname=caller_frame.f_code.co_filename,
                lineno=caller_frame.f_lineno,
                msg=message,
                args=(),
                exc_info=None,
                func=caller_frame.f_code.co_name,
            )
            logger.handle(record)


def log_warning(message: str) -> None:
    """Log warning message"""
    logger = get_logger()
    if logger.isEnabledFor(logging.WARNING):
        # Get caller's frame info
        frame = logging.currentframe()
        if frame and frame.f_back:
            caller_frame = frame.f_back
            # Create a LogRecord with caller's location
            record = logging.LogRecord(
                name=logger.name,
                level=logging.WARNING,
                pathname=caller_frame.f_code.co_filename,
                lineno=caller_frame.f_lineno,
                msg=message,
                args=(),
                exc_info=None,
                func=caller_frame.f_code.co_name,
            )
            logger.handle(record)


def log_error(message: str) -> None:
    """Log error message"""
    logger = get_logger()
    if logger.isEnabledFor(logging.ERROR):
        # Get caller's frame info
        frame = logging.currentframe()
        if frame and frame.f_back:
            caller_frame = frame.f_back
            # Create a LogRecord with caller's location
            record = logging.LogRecord(
                name=logger.name,
                level=logging.ERROR,
                pathname=caller_frame.f_code.co_filename,
                lineno=caller_frame.f_lineno,
                msg=message,
                args=(),
                exc_info=None,
                func=caller_frame.f_code.co_name,
            )
            logger.handle(record)


def log_debug(message: str) -> None:
    """Log debug message"""
    logger = get_logger()
    if logger.isEnabledFor(logging.DEBUG):
        # Get caller's frame info
        frame = logging.currentframe()
        if frame and frame.f_back:
            caller_frame = frame.f_back
            # Create a LogRecord with caller's location
            record = logging.LogRecord(
                name=logger.name,
                level=logging.DEBUG,
                pathname=caller_frame.f_code.co_filename,
                lineno=caller_frame.f_lineno,
                msg=message,
                args=(),
                exc_info=None,
                func=caller_frame.f_code.co_name,
            )
            logger.handle(record)


def log_exception(message: str, exc_info: bool = True) -> None:
    """Log exception with traceback"""
    logger = get_logger()
    if logger.isEnabledFor(logging.ERROR):
        # Get caller's frame info
        frame = logging.currentframe()
        if frame and frame.f_back:
            caller_frame = frame.f_back
            # Get exception info if requested
            exception_info = sys.exc_info() if exc_info else None
            # Create a LogRecord with caller's location
            record = logging.LogRecord(
                name=logger.name,
                level=logging.ERROR,
                pathname=caller_frame.f_code.co_filename,
                lineno=caller_frame.f_lineno,
                msg=message,
                args=(),
                exc_info=exception_info,
                func=caller_frame.f_code.co_name,
            )
            logger.handle(record)