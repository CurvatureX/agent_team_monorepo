"""
Enhanced logging utility using Python standard library
Compatible with the new core.logging system
"""

import logging
import sys
from typing import Optional


def setup_logger(name: str = "api-gateway", level: Optional[str] = None) -> logging.Logger:
    """
    Setup logger with consistent formatting

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR). If None, uses config setting

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Get level and format from config if not provided
    if level is None:
        try:
            from app.core.config import get_settings

            settings = get_settings()
            level = settings.LOG_LEVEL
            log_format = settings.LOG_FORMAT
        except ImportError:
            try:
                # Fallback to old config location
                from app.config import settings

                level = settings.LOG_LEVEL
                log_format = settings.LOG_FORMAT
            except ImportError:
                level = "INFO"
                log_format = "standard"
    else:
        log_format = "standard"

    # Set level
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Create formatter based on format preference
    if log_format == "json":
        # JSON format for structured logging
        formatter = logging.Formatter(
            fmt='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "file": "%(filename)s", "line": %(lineno)d, "function": "%(funcName)s", "message": "%(message)s"}',
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    elif log_format == "simple":
        # Simple format for development
        formatter = logging.Formatter(fmt="%(levelname)s - %(message)s")
    else:
        # Standard format with file, line, and function info
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d:%(funcName)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    return logger


# Global logger instance
_logger: Optional[logging.Logger] = None


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get or create a logger instance

    Args:
        name: Logger name, defaults to calling module name or global logger

    Returns:
        Configured logger instance
    """
    if name is not None:
        # Return named logger (compatible with new core system)
        return logging.getLogger(name)

    # Backward compatibility: return global logger
    global _logger
    if _logger is None:
        _logger = setup_logger()
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
