"""
Audit logging system for workflow engine.

This module provides comprehensive audit logging for security events,
credential operations, API calls, and system activities with structured
logging and monitoring support.
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from .config import get_settings
from ..models.database import Base, get_db


class AuditEventType(Enum):
    """Types of audit events."""
    
    # Authentication and Authorization
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    
    # Credential Operations
    CREDENTIAL_CREATED = "credential_created"
    CREDENTIAL_UPDATED = "credential_updated"
    CREDENTIAL_DELETED = "credential_deleted"
    CREDENTIAL_ACCESSED = "credential_accessed"
    OAUTH2_TOKEN_REFRESH = "oauth2_token_refresh"
    
    # API Operations
    API_CALL_SUCCESS = "api_call_success"
    API_CALL_FAILURE = "api_call_failure"
    API_RATE_LIMIT = "api_rate_limit"
    API_TIMEOUT = "api_timeout"
    
    # Workflow Operations
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_UPDATED = "workflow_updated"
    WORKFLOW_DELETED = "workflow_deleted"
    WORKFLOW_EXECUTED = "workflow_executed"
    
    # Tool Operations
    TOOL_EXECUTED = "tool_executed"
    TOOL_FAILED = "tool_failed"
    
    # System Events
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    CONFIGURATION_CHANGED = "configuration_changed"
    ERROR_OCCURRED = "error_occurred"
    
    # Security Events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_VIOLATION = "security_violation"
    ACCESS_DENIED = "access_denied"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Structured audit event data."""
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}
        if self.metadata is None:
            self.metadata = {}


class AuditLog(Base):
    """Database model for audit logs."""
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    user_id = Column(String(255), index=True)
    resource_type = Column(String(100), index=True)
    resource_id = Column(String(255), index=True)
    action = Column(String(100), index=True)
    source_ip = Column(String(45))  # IPv6 max length
    user_agent = Column(Text)
    details = Column(JSONB)
    audit_metadata = Column(JSONB)  # 避免与 SQLAlchemy 保留字段 metadata 冲突
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    session_id = Column(String(255), index=True)
    correlation_id = Column(String(255), index=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, timestamp={self.timestamp})>"


class AuditLogger:
    """Main audit logging service."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger("audit")
        self._configure_logger()
        
        # Async queue for batch processing
        self._audit_queue = asyncio.Queue()
        self._processing_task = None
        self._shutdown_event = asyncio.Event()
    
    def _configure_logger(self):
        """Configure the audit logger with structured format."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    async def start(self):
        """Start the audit logger service."""
        if self._processing_task is None:
            self._processing_task = asyncio.create_task(self._process_audit_queue())
            await self.log_event(AuditEvent(
                event_type=AuditEventType.SERVICE_STARTED,
                severity=AuditSeverity.LOW,
                action="audit_logger_started",
                details={"component": "audit_logger"}
            ))
    
    async def stop(self):
        """Stop the audit logger service."""
        self._shutdown_event.set()
        if self._processing_task:
            await self._processing_task
            self._processing_task = None
        
        await self.log_event(AuditEvent(
            event_type=AuditEventType.SERVICE_STOPPED,
            severity=AuditSeverity.LOW,
            action="audit_logger_stopped",
            details={"component": "audit_logger"}
        ))
    
    async def log_event(self, event: AuditEvent, immediate: bool = False):
        """Log an audit event."""
        try:
            if immediate:
                await self._write_to_database(event)
                await self._write_to_log(event)
            else:
                await self._audit_queue.put(event)
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
    
    async def _process_audit_queue(self):
        """Process audit events from the queue."""
        batch = []
        batch_size = 10
        batch_timeout = 5.0  # seconds
        
        while not self._shutdown_event.is_set():
            try:
                # Collect events for batch processing
                timeout = batch_timeout if not batch else 0.1
                
                try:
                    event = await asyncio.wait_for(
                        self._audit_queue.get(), 
                        timeout=timeout
                    )
                    batch.append(event)
                except asyncio.TimeoutError:
                    pass
                
                # Process batch when full or timeout
                if len(batch) >= batch_size or (batch and timeout == 0.1):
                    await self._process_batch(batch)
                    batch = []
                    
            except Exception as e:
                self.logger.error(f"Error processing audit queue: {e}")
                await asyncio.sleep(1)
    
    async def _process_batch(self, events: list[AuditEvent]):
        """Process a batch of audit events."""
        try:
            # Write to database
            for event in events:
                await self._write_to_database(event)
                await self._write_to_log(event)
        except Exception as e:
            self.logger.error(f"Failed to process audit batch: {e}")
    
    async def _write_to_database(self, event: AuditEvent):
        """Write audit event to database."""
        try:
            db = next(get_db())
            try:
                audit_log = AuditLog(
                    event_type=event.event_type.value,
                    severity=event.severity.value,
                    user_id=event.user_id,
                    resource_type=event.resource_type,
                    resource_id=event.resource_id,
                    action=event.action,
                    source_ip=event.source_ip,
                    user_agent=event.user_agent,
                    details=event.details,
                    audit_metadata=event.metadata,
                    timestamp=event.timestamp
                )
                db.add(audit_log)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            self.logger.error(f"Failed to write audit event to database: {e}")
    
    async def _write_to_log(self, event: AuditEvent):
        """Write audit event to log file."""
        log_data = {
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "user_id": event.user_id,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "action": event.action,
            "source_ip": event.source_ip,
            "user_agent": event.user_agent,
            "details": event.details,
            "metadata": event.metadata,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None
        }
        
        # Log with appropriate level based on severity
        if event.severity == AuditSeverity.CRITICAL:
            self.logger.critical(json.dumps(log_data))
        elif event.severity == AuditSeverity.HIGH:
            self.logger.error(json.dumps(log_data))
        elif event.severity == AuditSeverity.MEDIUM:
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))
    
    async def log_credential_operation(
        self,
        operation: str,
        user_id: str,
        provider: str,
        success: bool = True,
        details: Dict[str, Any] = None
    ):
        """Log credential-related operations."""
        event_type = {
            "create": AuditEventType.CREDENTIAL_CREATED,
            "update": AuditEventType.CREDENTIAL_UPDATED,
            "delete": AuditEventType.CREDENTIAL_DELETED,
            "access": AuditEventType.CREDENTIAL_ACCESSED
        }.get(operation, AuditEventType.CREDENTIAL_ACCESSED)
        
        severity = AuditSeverity.MEDIUM if success else AuditSeverity.HIGH
        
        event_details = {
            "provider": provider,
            "operation": operation,
            "success": success
        }
        if details:
            event_details.update(details)
        
        await self.log_event(AuditEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            resource_type="credential",
            resource_id=f"{user_id}:{provider}",
            action=operation,
            details=event_details
        ))
    
    async def log_api_call(
        self,
        provider: str,
        operation: str,
        user_id: str,
        success: bool = True,
        response_time: Optional[float] = None,
        error_message: Optional[str] = None,
        details: Dict[str, Any] = None
    ):
        """Log API calls to external services."""
        event_type = AuditEventType.API_CALL_SUCCESS if success else AuditEventType.API_CALL_FAILURE
        severity = AuditSeverity.LOW if success else AuditSeverity.MEDIUM
        
        event_details = {
            "provider": provider,
            "operation": operation,
            "success": success,
            "response_time_ms": int(response_time * 1000) if response_time else None
        }
        
        if error_message:
            event_details["error_message"] = error_message
        
        if details:
            event_details.update(details)
        
        await self.log_event(AuditEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            resource_type="api_call",
            resource_id=f"{provider}:{operation}",
            action=operation,
            details=event_details
        ))
    
    async def log_security_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        details: Dict[str, Any] = None,
        severity: AuditSeverity = AuditSeverity.HIGH
    ):
        """Log security-related events."""
        await self.log_event(AuditEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            source_ip=source_ip,
            resource_type="security",
            action=event_type.value,
            details=details or {}
        ))
    
    async def log_tool_execution(
        self,
        tool_type: str,
        provider: str,
        user_id: str,
        execution_time: float,
        success: bool = True,
        error_message: Optional[str] = None,
        details: Dict[str, Any] = None
    ):
        """Log tool node execution."""
        event_type = AuditEventType.TOOL_EXECUTED if success else AuditEventType.TOOL_FAILED
        severity = AuditSeverity.LOW if success else AuditSeverity.MEDIUM
        
        event_details = {
            "tool_type": tool_type,
            "provider": provider,
            "execution_time_ms": int(execution_time * 1000),
            "success": success
        }
        
        if error_message:
            event_details["error_message"] = error_message
        
        if details:
            event_details.update(details)
        
        await self.log_event(AuditEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            resource_type="tool_execution",
            resource_id=f"{tool_type}:{provider}",
            action="execute",
            details=event_details
        ))


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


@asynccontextmanager
async def audit_context(
    user_id: Optional[str] = None,
    source_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    correlation_id: Optional[str] = None
):
    """Context manager for audit logging with automatic resource tracking."""
    audit_logger = get_audit_logger()
    
    # Store context in task-local storage (simplified)
    context_data = {
        "user_id": user_id,
        "source_ip": source_ip,
        "user_agent": user_agent,
        "correlation_id": correlation_id or str(uuid.uuid4())
    }
    
    try:
        yield audit_logger
    except Exception as e:
        # Log any unhandled exceptions
        await audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.ERROR_OCCURRED,
            severity=AuditSeverity.HIGH,
            user_id=user_id,
            source_ip=source_ip,
            action="unhandled_exception",
            details={
                "exception_type": type(e).__name__,
                "exception_message": str(e),
                "correlation_id": correlation_id
            }
        ))
        raise


class AuditDecorator:
    """Decorator for automatic audit logging of function calls."""
    
    def __init__(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.LOW,
        resource_type: Optional[str] = None,
        action: Optional[str] = None
    ):
        self.event_type = event_type
        self.severity = severity
        self.resource_type = resource_type
        self.action = action
    
    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            audit_logger = get_audit_logger()
            start_time = datetime.utcnow()
            
            try:
                result = await func(*args, **kwargs)
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                await audit_logger.log_event(AuditEvent(
                    event_type=self.event_type,
                    severity=self.severity,
                    resource_type=self.resource_type,
                    action=self.action or func.__name__,
                    details={
                        "function": func.__name__,
                        "execution_time_ms": int(execution_time * 1000),
                        "success": True
                    }
                ))
                
                return result
                
            except Exception as e:
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                await audit_logger.log_event(AuditEvent(
                    event_type=AuditEventType.ERROR_OCCURRED,
                    severity=AuditSeverity.HIGH,
                    resource_type=self.resource_type,
                    action=self.action or func.__name__,
                    details={
                        "function": func.__name__,
                        "execution_time_ms": int(execution_time * 1000),
                        "success": False,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                ))
                
                raise
        
        return wrapper


def audit_log(
    event_type: AuditEventType,
    severity: AuditSeverity = AuditSeverity.LOW,
    resource_type: Optional[str] = None,
    action: Optional[str] = None
):
    """Decorator for audit logging."""
    return AuditDecorator(event_type, severity, resource_type, action) 