"""
Comprehensive Workflow Execution Logger

This module provides detailed logging for workflow execution progress,
including node-level tracking with input/output parameters, timing information,
and multiple output formatters for different use cases.

Key Features:
- Node execution progress tracking
- Input/output parameter logging
- Performance metrics
- Multiple output formats (console, JSON, structured)
- Real-time streaming capabilities
- Error context and debugging information
"""

from __future__ import annotations

import json
import logging
import sys
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Union

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import ExecutionStatus, LogLevel, NodeExecutionStatus
from shared.models.execution_new import Execution
from shared.models.workflow_new import Node


class ExecutionLogLevel(str, Enum):
    """Enhanced logging levels for workflow execution"""

    TRACE = "TRACE"  # Detailed internal operations
    DEBUG = "DEBUG"  # Debugging information
    INFO = "INFO"  # General information
    PROGRESS = "PROGRESS"  # Execution progress updates
    WARNING = "WARNING"  # Non-critical issues
    ERROR = "ERROR"  # Error conditions
    CRITICAL = "CRITICAL"  # Critical failures


class NodeExecutionPhase(str, Enum):
    """Phases of node execution for detailed tracking"""

    QUEUED = "QUEUED"  # Node is queued for execution
    STARTING = "STARTING"  # Node execution is starting
    VALIDATING_INPUTS = "VALIDATING_INPUTS"  # Validating input parameters
    PROCESSING = "PROCESSING"  # Main processing logic
    WAITING_HUMAN = "WAITING_HUMAN"  # Waiting for human input (HIL)
    COMPLETING = "COMPLETING"  # Finalizing execution
    COMPLETED = "COMPLETED"  # Successfully completed
    FAILED = "FAILED"  # Failed with error
    TIMEOUT = "TIMEOUT"  # Execution timed out


@dataclass
class NodeExecutionContext:
    """Context information for node execution"""

    node_id: str
    node_name: str
    node_type: str
    node_subtype: str
    execution_id: str
    workflow_id: str
    phase: NodeExecutionPhase
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    input_parameters: Optional[Dict[str, Any]] = None
    output_parameters: Optional[Dict[str, Any]] = None
    configuration: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate execution duration in milliseconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None

    @property
    def is_completed(self) -> bool:
        """Check if node execution is completed"""
        return self.phase in [
            NodeExecutionPhase.COMPLETED,
            NodeExecutionPhase.FAILED,
            NodeExecutionPhase.TIMEOUT,
        ]


@dataclass
class ExecutionLogEntry:
    """Enhanced log entry for workflow execution"""

    timestamp: float
    level: ExecutionLogLevel
    message: str
    execution_id: str
    node_context: Optional[NodeExecutionContext] = None
    workflow_context: Optional[Dict[str, Any]] = None
    structured_data: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None

    @property
    def iso_timestamp(self) -> str:
        """Get ISO formatted timestamp"""
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            "timestamp": self.timestamp,
            "iso_timestamp": self.iso_timestamp,
            "level": self.level.value,
            "message": self.message,
            "execution_id": self.execution_id,
        }

        if self.node_context:
            result["node_context"] = asdict(self.node_context)

        if self.workflow_context:
            result["workflow_context"] = self.workflow_context

        if self.structured_data:
            result["structured_data"] = self.structured_data

        if self.trace_id:
            result["trace_id"] = self.trace_id

        return result


class ExecutionProgressTracker:
    """Tracks detailed progress of workflow execution"""

    def __init__(self):
        self._node_contexts: Dict[str, NodeExecutionContext] = {}
        self._lock = Lock()

    def start_node_execution(
        self,
        node: Node,
        execution_id: str,
        workflow_id: str,
        input_parameters: Optional[Dict[str, Any]] = None,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> NodeExecutionContext:
        """Start tracking a node execution"""
        with self._lock:
            context = NodeExecutionContext(
                node_id=node.id,
                node_name=node.name,
                node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
                node_subtype=node.subtype,
                execution_id=execution_id,
                workflow_id=workflow_id,
                phase=NodeExecutionPhase.STARTING,
                start_time=time.time(),
                input_parameters=self._sanitize_parameters(input_parameters),
                configuration=self._sanitize_parameters(configuration),
            )
            self._node_contexts[node.id] = context
            return context

    def update_node_phase(
        self, node_id: str, phase: NodeExecutionPhase
    ) -> Optional[NodeExecutionContext]:
        """Update the execution phase of a node"""
        with self._lock:
            if node_id in self._node_contexts:
                self._node_contexts[node_id].phase = phase
                return self._node_contexts[node_id]
        return None

    def complete_node_execution(
        self,
        node_id: str,
        phase: NodeExecutionPhase,
        output_parameters: Optional[Dict[str, Any]] = None,
        error_details: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
    ) -> Optional[NodeExecutionContext]:
        """Complete a node execution with results"""
        with self._lock:
            if node_id in self._node_contexts:
                context = self._node_contexts[node_id]
                context.phase = phase
                context.end_time = time.time()
                if output_parameters is not None:
                    context.output_parameters = self._sanitize_parameters(output_parameters)
                if error_details is not None:
                    context.error_details = error_details
                if performance_metrics is not None:
                    context.performance_metrics = performance_metrics
                return context
        return None

    def get_node_context(self, node_id: str) -> Optional[NodeExecutionContext]:
        """Get current context for a node"""
        with self._lock:
            return self._node_contexts.get(node_id)

    def get_all_contexts(self) -> Dict[str, NodeExecutionContext]:
        """Get all node contexts"""
        with self._lock:
            return self._node_contexts.copy()

    def _sanitize_parameters(self, params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Sanitize parameters to remove sensitive data and ensure serializability"""
        if params is None:
            return None

        sanitized = {}
        for key, value in params.items():
            # Remove sensitive keys
            if any(
                sensitive in key.lower()
                for sensitive in ["password", "secret", "token", "key", "credential"]
            ):
                sanitized[key] = "[REDACTED]"
            else:
                try:
                    # Ensure value is JSON serializable
                    json.dumps(value)
                    sanitized[key] = value
                except (TypeError, ValueError):
                    sanitized[key] = str(value)
        return sanitized


class ExecutionLogger:
    """Comprehensive workflow execution logger"""

    def __init__(self, max_entries: int = 10000):
        self._entries: deque = deque(maxlen=max_entries)
        self._progress_tracker = ExecutionProgressTracker()
        self._lock = Lock()

        # Initialize Python logger for integration
        self._python_logger = logging.getLogger("workflow_execution")

    def log_execution_start(
        self,
        execution: Execution,
        workflow_context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Log the start of workflow execution"""
        entry = ExecutionLogEntry(
            timestamp=time.time(),
            level=ExecutionLogLevel.PROGRESS,
            message=f"Workflow execution started: {execution.workflow_id}",
            execution_id=execution.execution_id,
            workflow_context=workflow_context,
            trace_id=trace_id,
        )
        self._add_entry(entry)

    def log_execution_complete(
        self,
        execution: Execution,
        final_status: ExecutionStatus,
        summary: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Log the completion of workflow execution"""
        level = (
            ExecutionLogLevel.PROGRESS
            if final_status == ExecutionStatus.COMPLETED
            else ExecutionLogLevel.ERROR
        )
        message = f"Workflow execution {final_status.value.lower()}: {execution.workflow_id}"

        entry = ExecutionLogEntry(
            timestamp=time.time(),
            level=level,
            message=message,
            execution_id=execution.execution_id,
            structured_data=summary,
            trace_id=trace_id,
        )
        self._add_entry(entry)

    def log_node_start(
        self,
        node: Node,
        execution_id: str,
        workflow_id: str,
        input_parameters: Optional[Dict[str, Any]] = None,
        configuration: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> NodeExecutionContext:
        """Log the start of node execution"""
        context = self._progress_tracker.start_node_execution(
            node=node,
            execution_id=execution_id,
            workflow_id=workflow_id,
            input_parameters=input_parameters,
            configuration=configuration,
        )

        entry = ExecutionLogEntry(
            timestamp=time.time(),
            level=ExecutionLogLevel.PROGRESS,
            message=f"Node execution started: {node.name} ({node.type}.{node.subtype})",
            execution_id=execution_id,
            node_context=context,
            trace_id=trace_id,
        )
        self._add_entry(entry)
        return context

    def log_node_phase_change(
        self,
        node_id: str,
        phase: NodeExecutionPhase,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Log a change in node execution phase"""
        context = self._progress_tracker.update_node_phase(node_id, phase)
        if not context:
            return

        entry = ExecutionLogEntry(
            timestamp=time.time(),
            level=ExecutionLogLevel.DEBUG,
            message=f"Node phase changed: {context.node_name} -> {phase.value}",
            execution_id=context.execution_id,
            node_context=context,
            structured_data=details,
            trace_id=trace_id,
        )
        self._add_entry(entry)

    def log_node_complete(
        self,
        node_id: str,
        phase: NodeExecutionPhase,
        output_parameters: Optional[Dict[str, Any]] = None,
        error_details: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Log the completion of node execution"""
        context = self._progress_tracker.complete_node_execution(
            node_id=node_id,
            phase=phase,
            output_parameters=output_parameters,
            error_details=error_details,
            performance_metrics=performance_metrics,
        )

        if not context:
            return

        level = (
            ExecutionLogLevel.PROGRESS
            if phase == NodeExecutionPhase.COMPLETED
            else ExecutionLogLevel.ERROR
        )
        message = f"Node execution {phase.value.lower()}: {context.node_name}"

        if context.duration_ms:
            message += f" (took {context.duration_ms:.1f}ms)"

        entry = ExecutionLogEntry(
            timestamp=time.time(),
            level=level,
            message=message,
            execution_id=context.execution_id,
            node_context=context,
            trace_id=trace_id,
        )
        self._add_entry(entry)

    def log_node_error(
        self,
        node_id: str,
        error: Exception,
        context_data: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Log a node execution error"""
        context = self._progress_tracker.get_node_context(node_id)
        if context:
            context.phase = NodeExecutionPhase.FAILED
            context.end_time = time.time()
            context.error_details = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context_data or {},
            }

        entry = ExecutionLogEntry(
            timestamp=time.time(),
            level=ExecutionLogLevel.ERROR,
            message=f"Node execution failed: {context.node_name if context else node_id} - {str(error)}",
            execution_id=context.execution_id if context else "",
            node_context=context,
            structured_data={"error_type": type(error).__name__, "error_message": str(error)},
            trace_id=trace_id,
        )
        self._add_entry(entry)

    def log_custom(
        self,
        level: ExecutionLogLevel,
        message: str,
        execution_id: str,
        node_id: Optional[str] = None,
        structured_data: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Log a custom message"""
        node_context = None
        if node_id:
            node_context = self._progress_tracker.get_node_context(node_id)

        entry = ExecutionLogEntry(
            timestamp=time.time(),
            level=level,
            message=message,
            execution_id=execution_id,
            node_context=node_context,
            structured_data=structured_data,
            trace_id=trace_id,
        )
        self._add_entry(entry)

    def get_logs(
        self,
        execution_id: Optional[str] = None,
        node_id: Optional[str] = None,
        level_filter: Optional[ExecutionLogLevel] = None,
        limit: Optional[int] = None,
    ) -> List[ExecutionLogEntry]:
        """Retrieve filtered logs"""
        with self._lock:
            logs = list(self._entries)

        # Apply filters
        if execution_id:
            logs = [log for log in logs if log.execution_id == execution_id]

        if node_id:
            logs = [log for log in logs if log.node_context and log.node_context.node_id == node_id]

        if level_filter:
            logs = [log for log in logs if log.level == level_filter]

        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply limit
        if limit:
            logs = logs[:limit]

        return logs

    def get_execution_summary(self, execution_id: str) -> Dict[str, Any]:
        """Get a summary of execution progress"""
        logs = self.get_logs(execution_id=execution_id)
        contexts = {
            ctx.node_id: ctx
            for ctx in self._progress_tracker.get_all_contexts().values()
            if ctx.execution_id == execution_id
        }

        # Calculate statistics
        total_nodes = len(contexts)
        completed_nodes = len(
            [ctx for ctx in contexts.values() if ctx.phase == NodeExecutionPhase.COMPLETED]
        )
        failed_nodes = len(
            [ctx for ctx in contexts.values() if ctx.phase == NodeExecutionPhase.FAILED]
        )
        in_progress_nodes = total_nodes - completed_nodes - failed_nodes

        # Calculate total duration
        durations = [ctx.duration_ms for ctx in contexts.values() if ctx.duration_ms]
        total_duration = sum(durations) if durations else 0

        return {
            "execution_id": execution_id,
            "total_logs": len(logs),
            "node_statistics": {
                "total_nodes": total_nodes,
                "completed_nodes": completed_nodes,
                "failed_nodes": failed_nodes,
                "in_progress_nodes": in_progress_nodes,
            },
            "performance": {
                "total_duration_ms": total_duration,
                "average_node_duration_ms": total_duration / len(durations) if durations else 0,
                "fastest_node_ms": min(durations) if durations else 0,
                "slowest_node_ms": max(durations) if durations else 0,
            },
            "timestamp": time.time(),
        }

    def _add_entry(self, entry: ExecutionLogEntry):
        """Add a log entry to the internal storage"""
        with self._lock:
            self._entries.append(entry)

        # Also log to Python logger for integration
        python_level = self._map_to_python_level(entry.level)
        extra = {
            "execution_id": entry.execution_id,
            "node_id": entry.node_context.node_id if entry.node_context else None,
            "trace_id": entry.trace_id,
        }
        self._python_logger.log(python_level, entry.message, extra=extra)

    def _map_to_python_level(self, level: ExecutionLogLevel) -> int:
        """Map custom log levels to Python logging levels"""
        mapping = {
            ExecutionLogLevel.TRACE: logging.DEBUG,
            ExecutionLogLevel.DEBUG: logging.DEBUG,
            ExecutionLogLevel.INFO: logging.INFO,
            ExecutionLogLevel.PROGRESS: logging.INFO,
            ExecutionLogLevel.WARNING: logging.WARNING,
            ExecutionLogLevel.ERROR: logging.ERROR,
            ExecutionLogLevel.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(level, logging.INFO)


# Global instance
_execution_logger = ExecutionLogger()


def get_execution_logger() -> ExecutionLogger:
    """Get the global execution logger instance"""
    return _execution_logger


__all__ = [
    "ExecutionLogLevel",
    "NodeExecutionPhase",
    "NodeExecutionContext",
    "ExecutionLogEntry",
    "ExecutionProgressTracker",
    "ExecutionLogger",
    "get_execution_logger",
]
