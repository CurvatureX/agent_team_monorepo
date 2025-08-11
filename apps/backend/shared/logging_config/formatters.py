"""
Log Formatters for CloudWatch and Local Development
日志格式化器，支持简单文本和JSON格式
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict


class SimpleCloudWatchFormatter(logging.Formatter):
    """
    Simple text formatter optimized for CloudWatch and ECS console viewing
    格式示例: INFO:     2025-08-11 14:03:25 - api-gateway - [main.py:123] [Trace:abc123] - GET /health
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with file location and tracking_id"""
        # Get timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build basic components
        level = record.levelname
        name = record.name
        message = record.getMessage()
        file_location = f"{record.filename}:{record.lineno}"
        
        # Extract tracking_id if available
        # OpenTelemetry middleware adds it via extra={'tracking_id': 'xxx'}
        tracking_id = ""
        if hasattr(record, 'tracking_id') and record.tracking_id != 'unknown':
            tracking_id = f" [Trace:{record.tracking_id}]"
        
        # Format: LEVEL:     timestamp - service - [file:line] [Trace:id] - message
        formatted = f"{level}:     {timestamp} - {name} - [{file_location}]{tracking_id} - {message}"
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
            
        return formatted


class StructuredCloudWatchFormatter(logging.Formatter):
    """
    JSON formatter for CloudWatch Logs Insights queries
    Includes all context fields for advanced analysis
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with all context fields"""
        # Base log structure
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "file": f"{record.filename}:{record.lineno}",
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add tracking_id if available
        if hasattr(record, 'tracking_id'):
            log_obj["tracking_id"] = record.tracking_id
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add all extra fields (from logger.info(msg, extra={...}))
        # Skip internal LogRecord attributes
        skip_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'message', 'pathname', 'process', 'processName',
            'relativeCreated', 'thread', 'threadName', 'exc_info',
            'exc_text', 'stack_info', 'getMessage', 'tracking_id'
        }
        
        # Add extra fields
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in skip_attrs and not key.startswith('_'):
                extra_fields[key] = value
        
        if extra_fields:
            log_obj["extra"] = extra_fields
        
        return json.dumps(log_obj, ensure_ascii=False, default=str)