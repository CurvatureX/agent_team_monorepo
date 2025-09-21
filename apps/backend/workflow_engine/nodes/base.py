"""
Base classes for node executors.

Migrated and simplified from the old complex structure.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# Import logging service
try:
    from services.execution_log_service import (
        ExecutionLogEntry,
        LogEventType,
        get_execution_log_service,
    )

    LOGGING_SERVICE_AVAILABLE = True
except ImportError:
    LOGGING_SERVICE_AVAILABLE = False

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Execution status for nodes."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class NodeExecutionContext:
    """Context for node execution."""

    workflow_id: str
    execution_id: str
    node_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_data: Dict[str, Any] = field(default_factory=dict)
    static_data: Dict[str, Any] = field(default_factory=dict)
    credentials: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get node parameter value."""
        return self.parameters.get(key, default)

    def get_credential(self, key: str, default: Any = None) -> Any:
        """Get credential value."""
        return self.credentials.get(key, default)


@dataclass
class NodeExecutionResult:
    """Result of node execution."""

    status: ExecutionStatus
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    logs: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "status": self.status.value,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "execution_time": self.execution_time,
            "logs": self.logs or [],
            "metadata": self.metadata or {},
        }


class BaseNodeExecutor(ABC):
    """Base class for all node executors."""

    def __init__(self, node_type: str, subtype: Optional[str] = None):
        """Initialize node executor."""
        self.node_type = node_type
        self.subtype = subtype
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # Debug logging service initialization
        logger.error(f"🔧 DEBUG: LOGGING_SERVICE_AVAILABLE = {LOGGING_SERVICE_AVAILABLE}")
        if LOGGING_SERVICE_AVAILABLE:
            try:
                self.log_service = get_execution_log_service()
                logger.error(f"🔧 DEBUG: Log service initialized successfully: {self.log_service}")
            except Exception as e:
                logger.error(f"🔧 DEBUG: Failed to initialize log service: {e}")
                self.log_service = None
        else:
            logger.error(f"🔧 DEBUG: Logging service not available - import failed")
            self.log_service = None

    @abstractmethod
    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute the node."""
        pass

    def validate_parameters(self, context: NodeExecutionContext) -> tuple[bool, str]:
        """Validate node parameters. Returns (is_valid, error_message)."""
        # Basic validation - can be overridden by subclasses
        return True, ""

    def get_parameter_with_spec(
        self, context: NodeExecutionContext, param_name: str, default: Any = None
    ) -> Any:
        """Get parameter with spec-based type conversion and validation."""
        # Simplified version - in full implementation this would use node specs
        return context.get_parameter(param_name, default)

    def log_execution(self, context: NodeExecutionContext, message: str, level: str = "INFO"):
        """Log execution message."""
        log_message = f"[{context.workflow_id}:{context.execution_id}:{context.node_id}] {message}"

        if level == "ERROR":
            self.logger.error(log_message)
        elif level == "WARNING":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

    async def execute_with_logging(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute node with comprehensive logging."""
        logger.error(f"🔧 DEBUG: execute_with_logging called for {context.node_id}")
        logger.error(f"🔧 DEBUG: self.log_service = {self.log_service}")
        logger.error(f"🔧 DEBUG: LOGGING_SERVICE_AVAILABLE = {LOGGING_SERVICE_AVAILABLE}")

        start_time = datetime.now()
        self.log_execution(context, f"Starting execution of {self.node_type} node")

        # Add step started log to database
        if self.log_service and LOGGING_SERVICE_AVAILABLE:
            step_start_entry = ExecutionLogEntry(
                execution_id=context.execution_id,
                event_type=LogEventType.STEP_STARTED,
                timestamp=start_time.isoformat(),
                message=f"Started {self.node_type} node execution",
                level="INFO",
                data={
                    "node_id": context.node_id,
                    "node_type": self.node_type,
                    "node_name": context.parameters.get("name", context.node_id),
                    "user_friendly_message": f"🔧 Starting {self.node_type} execution",
                    "display_priority": 6,
                    "is_milestone": False,
                },
            )
            try:
                logger.info(f"📝 Adding log entry for {context.node_id}: {step_start_entry.message}")
                await self.log_service.add_log_entry(step_start_entry)
                logger.info(f"✅ Log entry added successfully for {context.node_id}")
            except Exception as e:
                logger.error(f"❌ Failed to add log entry for {context.node_id}: {e}")

        try:
            # Validate parameters
            is_valid, validation_error = self.validate_parameters(context)
            if not is_valid:
                error_message = validation_error or "Parameter validation failed"

                # Log validation error
                if self.log_service and LOGGING_SERVICE_AVAILABLE:
                    error_entry = ExecutionLogEntry(
                        execution_id=context.execution_id,
                        event_type=LogEventType.STEP_ERROR,
                        timestamp=datetime.now().isoformat(),
                        message=error_message,
                        level="ERROR",
                        data={
                            "node_id": context.node_id,
                            "node_type": self.node_type,
                            "user_friendly_message": f"❌ {error_message}",
                            "display_priority": 8,
                            "is_milestone": False,
                        },
                    )
                    await self.log_service.add_log_entry(error_entry)

                return NodeExecutionResult(
                    status=ExecutionStatus.ERROR, error_message=error_message
                )

            # Execute the node
            result = await self.execute(context)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time

            # Log completion
            completion_message = (
                f"Completed execution in {execution_time:.2f}s with status: {result.status.value}"
            )
            self.log_execution(context, completion_message)

            # Add step completed log to database
            if self.log_service and LOGGING_SERVICE_AVAILABLE:
                if result.status == ExecutionStatus.SUCCESS:
                    completion_entry = ExecutionLogEntry(
                        execution_id=context.execution_id,
                        event_type=LogEventType.STEP_COMPLETED,
                        timestamp=datetime.now().isoformat(),
                        message=completion_message,
                        level="INFO",
                        data={
                            "node_id": context.node_id,
                            "node_type": self.node_type,
                            "node_name": context.parameters.get("name", context.node_id),
                            "status": "SUCCESS",
                            "duration_seconds": int(execution_time),
                            "user_friendly_message": f"✅ {self.node_type} completed successfully",
                            "display_priority": 7,
                            "is_milestone": False,
                        },
                    )
                    await self.log_service.add_log_entry(completion_entry)
                else:
                    error_entry = ExecutionLogEntry(
                        execution_id=context.execution_id,
                        event_type=LogEventType.STEP_ERROR,
                        timestamp=datetime.now().isoformat(),
                        message=result.error_message or "Node execution failed",
                        level="ERROR",
                        data={
                            "node_id": context.node_id,
                            "node_type": self.node_type,
                            "node_name": context.parameters.get("name", context.node_id),
                            "status": "ERROR",
                            "duration_seconds": int(execution_time),
                            "user_friendly_message": f"❌ {self.node_type} execution failed",
                            "display_priority": 8,
                            "is_milestone": False,
                        },
                    )
                    await self.log_service.add_log_entry(error_entry)

            return result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_message = f"Execution failed: {str(e)}"

            self.log_execution(context, error_message, "ERROR")

            # Log exception to database
            if self.log_service and LOGGING_SERVICE_AVAILABLE:
                exception_entry = ExecutionLogEntry(
                    execution_id=context.execution_id,
                    event_type=LogEventType.STEP_ERROR,
                    timestamp=datetime.now().isoformat(),
                    message=error_message,
                    level="ERROR",
                    data={
                        "node_id": context.node_id,
                        "node_type": self.node_type,
                        "node_name": context.parameters.get("name", context.node_id),
                        "exception": str(e),
                        "exception_type": type(e).__name__,
                        "duration_seconds": int(execution_time),
                        "user_friendly_message": f"❌ {self.node_type} execution failed: {str(e)}",
                        "display_priority": 9,
                        "is_milestone": False,
                    },
                )
                await self.log_service.add_log_entry(exception_entry)

            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error_message,
                error_details={"exception": str(e), "type": type(e).__name__},
                execution_time=execution_time,
            )
