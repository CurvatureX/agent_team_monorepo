"""
Enhanced Logging Service for Workflow Engine V2

This service integrates comprehensive execution logging with the existing workflow engine,
providing detailed progress tracking, parameter logging, and multiple output formats.
It extends the existing LoggingService with enhanced capabilities while maintaining
backward compatibility.

Features:
- Detailed node execution tracking
- Input/output parameter logging
- Real-time progress monitoring
- Multiple output formats
- Performance metrics
- Error context tracking
- Integration with existing event system
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Union

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import (
    Execution,
    ExecutionEventType,
    ExecutionStatus,
    ExecutionUpdateData,
    ExecutionUpdateEvent,
    LogEntry,
    LogLevel,
    NodeExecution,
    NodeExecutionStatus,
    TriggerInfo,
)
from shared.models.workflow import Node
from workflow_engine_v2.services.events import get_event_bus
from workflow_engine_v2.services.execution_logger import (
    ExecutionLogger,
    ExecutionLogLevel,
    NodeExecutionContext,
    NodeExecutionPhase,
    get_execution_logger,
)
from workflow_engine_v2.services.log_formatters import LogFormatterFactory, OutputFormat
from workflow_engine_v2.services.logging import LoggingService, get_logging_service


class NodeExecutionTracker:
    """Tracks detailed execution progress for individual nodes"""

    def __init__(self, execution_logger: ExecutionLogger, logging_service: LoggingService):
        self._execution_logger = execution_logger
        self._logging_service = logging_service
        self._active_contexts: Dict[str, NodeExecutionContext] = {}
        self._lock = Lock()

    @asynccontextmanager
    async def track_node_execution(
        self,
        node: Node,
        execution: Execution,
        input_parameters: Optional[Dict[str, Any]] = None,
        configuration: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Context manager for tracking complete node execution lifecycle"""

        # Generate trace ID if not provided
        if not trace_id:
            trace_id = str(uuid.uuid4())

        # Start tracking
        context = self._start_tracking(
            node=node,
            execution=execution,
            input_parameters=input_parameters,
            configuration=configuration,
            trace_id=trace_id,
        )

        try:
            yield context
            # Successful completion
            self._complete_tracking(
                context=context,
                execution=execution,
                phase=NodeExecutionPhase.COMPLETED,
                trace_id=trace_id,
            )
        except Exception as e:
            # Error handling
            self._complete_tracking(
                context=context,
                execution=execution,
                phase=NodeExecutionPhase.FAILED,
                error=e,
                trace_id=trace_id,
            )
            raise

    def _start_tracking(
        self,
        node: Node,
        execution: Execution,
        input_parameters: Optional[Dict[str, Any]] = None,
        configuration: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> NodeExecutionContext:
        """Start tracking node execution"""

        with self._lock:
            # Log to execution logger
            context = self._execution_logger.log_node_start(
                node=node,
                execution_id=execution.execution_id,
                workflow_id=execution.workflow_id,
                input_parameters=input_parameters,
                configuration=configuration,
                trace_id=trace_id,
            )

            # Log to traditional logging service
            message = f"Node '{node.name}' execution started"
            if input_parameters:
                param_summary = self._create_parameter_summary(input_parameters)
                message += f" with inputs: {param_summary}"

            self._logging_service.log(
                execution=execution, level=LogLevel.INFO, message=message, node_id=node.id
            )

            self._active_contexts[node.id] = context
            return context

    def _complete_tracking(
        self,
        context: NodeExecutionContext,
        execution: Execution,
        phase: NodeExecutionPhase,
        output_parameters: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
        trace_id: Optional[str] = None,
    ):
        """Complete node execution tracking"""

        with self._lock:
            # Prepare completion data
            error_details = None
            performance_metrics = {
                "execution_time_ms": context.duration_ms or 0,
                "memory_usage": self._get_memory_usage(),
                "timestamp": time.time(),
            }

            if error:
                error_details = {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "error_context": getattr(error, "__dict__", {}),
                }
                self._execution_logger.log_node_error(
                    node_id=context.node_id, error=error, trace_id=trace_id
                )

            # Complete execution tracking
            self._execution_logger.log_node_complete(
                node_id=context.node_id,
                phase=phase,
                output_parameters=output_parameters,
                error_details=error_details,
                performance_metrics=performance_metrics,
                trace_id=trace_id,
            )

            # Log to traditional service
            status = "completed" if phase == NodeExecutionPhase.COMPLETED else "failed"
            message = f"Node '{context.node_name}' execution {status}"

            if context.duration_ms:
                message += f" (took {context.duration_ms:.1f}ms)"

            if output_parameters:
                param_summary = self._create_parameter_summary(output_parameters)
                message += f" with outputs: {param_summary}"

            log_level = LogLevel.INFO if phase == NodeExecutionPhase.COMPLETED else LogLevel.ERROR
            self._logging_service.log(
                execution=execution, level=log_level, message=message, node_id=context.node_id
            )

            # Remove from active contexts
            self._active_contexts.pop(context.node_id, None)

    def update_node_phase(
        self,
        node_id: str,
        phase: NodeExecutionPhase,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Update the execution phase of a node"""

        self._execution_logger.log_node_phase_change(
            node_id=node_id, phase=phase, details=details, trace_id=trace_id
        )

        # Log phase change to traditional service if significant
        if phase in [NodeExecutionPhase.WAITING_HUMAN, NodeExecutionPhase.PROCESSING]:
            context = self._active_contexts.get(node_id)
            if context:
                # Create a dummy execution object for legacy compatibility
                dummy_execution = type(
                    "MockExecution",
                    (),
                    {"execution_id": context.execution_id, "workflow_id": context.workflow_id},
                )()

                phase_messages = {
                    NodeExecutionPhase.WAITING_HUMAN: "waiting for human input",
                    NodeExecutionPhase.PROCESSING: "processing request",
                }

                message = (
                    f"Node '{context.node_name}' {phase_messages.get(phase, phase.value.lower())}"
                )
                self._logging_service.log(
                    execution=dummy_execution, level=LogLevel.INFO, message=message, node_id=node_id
                )

    def _create_parameter_summary(self, parameters: Dict[str, Any], max_length: int = 200) -> str:
        """Create a concise summary of parameters"""
        if not parameters:
            return "{}"

        # Create a summary that shows parameter names and types/values
        summary_parts = []
        for key, value in parameters.items():
            if isinstance(value, (dict, list)):
                summary_parts.append(f"{key}:{type(value).__name__}({len(value)})")
            elif isinstance(value, str) and len(value) > 50:
                summary_parts.append(f"{key}:str({len(value)})")
            else:
                summary_parts.append(f"{key}:{repr(value)}")

        summary = "{" + ", ".join(summary_parts) + "}"

        if len(summary) > max_length:
            return summary[: max_length - 3] + "...}"
        return summary

    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage metrics"""
        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            return {"error": str(e)}


class EnhancedLoggingService:
    """Enhanced logging service that integrates comprehensive execution tracking"""

    def __init__(self):
        self._traditional_service = get_logging_service()
        self._execution_logger = get_execution_logger()
        self._event_bus = get_event_bus()
        self._node_tracker = NodeExecutionTracker(self._execution_logger, self._traditional_service)
        self._formatter_factory = LogFormatterFactory()

    # Workflow-level logging methods

    def log_workflow_start(
        self,
        execution: Execution,
        trigger: TriggerInfo,
        workflow_context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Log the start of workflow execution with enhanced details"""

        # Traditional logging
        self._traditional_service.log(
            execution=execution,
            level=LogLevel.INFO,
            message=f"Workflow execution started - Trigger: {trigger.trigger_type}",
        )

        # Enhanced logging
        enhanced_context = {
            "trigger": {
                "type": trigger.trigger_type,
                "source": getattr(trigger, "source", None),
                "timestamp": getattr(trigger, "timestamp", None),
            }
        }
        if workflow_context:
            enhanced_context.update(workflow_context)

        self._execution_logger.log_execution_start(
            execution=execution, workflow_context=enhanced_context, trace_id=trace_id
        )

    def log_workflow_complete(
        self,
        execution: Execution,
        final_status: ExecutionStatus,
        summary: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Log workflow completion with comprehensive summary"""

        # Traditional logging
        status_message = f"Workflow execution {final_status.value.lower()}"
        log_level = LogLevel.INFO if final_status == ExecutionStatus.COMPLETED else LogLevel.ERROR

        self._traditional_service.log(execution=execution, level=log_level, message=status_message)

        # Enhanced logging with summary
        execution_summary = self._execution_logger.get_execution_summary(execution.execution_id)
        if summary:
            execution_summary.update(summary)

        self._execution_logger.log_execution_complete(
            execution=execution,
            final_status=final_status,
            summary=execution_summary,
            trace_id=trace_id,
        )

    # Node-level logging methods

    @asynccontextmanager
    async def track_node_execution(
        self,
        node: Node,
        execution: Execution,
        input_parameters: Optional[Dict[str, Any]] = None,
        configuration: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Track complete node execution with detailed logging"""
        async with self._node_tracker.track_node_execution(
            node=node,
            execution=execution,
            input_parameters=input_parameters,
            configuration=configuration,
            trace_id=trace_id,
        ) as context:
            yield context

    def update_node_phase(
        self,
        node_id: str,
        phase: NodeExecutionPhase,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Update node execution phase"""
        self._node_tracker.update_node_phase(node_id, phase, details, trace_id)

    def log_node_output(
        self,
        node_id: str,
        execution_id: str,
        output_parameters: Dict[str, Any],
        trace_id: Optional[str] = None,
    ):
        """Log node output parameters"""
        self._execution_logger.log_custom(
            level=ExecutionLogLevel.DEBUG,
            message=f"Node output generated: {len(output_parameters)} parameters",
            execution_id=execution_id,
            node_id=node_id,
            structured_data={"output_parameters": output_parameters},
            trace_id=trace_id,
        )

    # Query and formatting methods

    def get_execution_logs(
        self,
        execution_id: str,
        format_type: OutputFormat = OutputFormat.JSON,
        node_id: Optional[str] = None,
        level_filter: Optional[ExecutionLogLevel] = None,
        limit: Optional[int] = None,
    ) -> str:
        """Get formatted execution logs"""

        # Get logs from execution logger
        logs = self._execution_logger.get_logs(
            execution_id=execution_id, node_id=node_id, level_filter=level_filter, limit=limit
        )

        # Format using appropriate formatter
        formatter = self._formatter_factory.create(format_type)
        return formatter.format_entries(logs)

    def get_execution_summary(
        self, execution_id: str, format_type: OutputFormat = OutputFormat.JSON
    ) -> str:
        """Get formatted execution summary"""

        summary = self._execution_logger.get_execution_summary(execution_id)
        formatter = self._formatter_factory.create(format_type)
        return formatter.format_summary(summary)

    def get_node_execution_details(
        self, execution_id: str, node_id: str, format_type: OutputFormat = OutputFormat.JSON
    ) -> str:
        """Get detailed information about a specific node execution"""

        logs = self._execution_logger.get_logs(execution_id=execution_id, node_id=node_id)

        # Get node context
        node_contexts = self._execution_logger._progress_tracker.get_all_contexts()
        node_context = None
        for ctx in node_contexts.values():
            if ctx.node_id == node_id and ctx.execution_id == execution_id:
                node_context = ctx
                break

        # Create detailed summary
        details = {
            "node_id": node_id,
            "execution_id": execution_id,
            "log_count": len(logs),
            "context": node_context.__dict__ if node_context else None,
            "logs": [log.to_dict() for log in logs],
        }

        formatter = self._formatter_factory.create(format_type)
        if format_type == OutputFormat.JSON or format_type == OutputFormat.JSON_PRETTY:
            import json

            return json.dumps(
                details, indent=2 if format_type == OutputFormat.JSON_PRETTY else None, default=str
            )
        else:
            return formatter.format_entries(logs)

    def stream_execution_progress(
        self, execution_id: str, format_type: OutputFormat = OutputFormat.CONSOLE
    ):
        """Stream real-time execution progress (generator)"""
        # This would integrate with the event bus for real-time streaming
        # Implementation would depend on the specific streaming requirements
        pass

    # Utility methods

    def get_available_formats(self) -> List[str]:
        """Get list of available output formats"""
        return [fmt.value for fmt in self._formatter_factory.get_available_formats()]

    def export_execution_logs(
        self,
        execution_id: str,
        file_path: str,
        format_type: OutputFormat = OutputFormat.JSON_PRETTY,
    ):
        """Export execution logs to file"""

        logs_content = self.get_execution_logs(execution_id, format_type)
        summary_content = self.get_execution_summary(execution_id, format_type)

        # Combine logs and summary
        if format_type == OutputFormat.MARKDOWN:
            content = f"{summary_content}\n\n---\n\n{logs_content}"
        elif format_type in [OutputFormat.JSON, OutputFormat.JSON_PRETTY]:
            import json

            combined = {"summary": json.loads(summary_content), "logs": json.loads(logs_content)}
            content = json.dumps(
                combined, indent=2 if format_type == OutputFormat.JSON_PRETTY else None, default=str
            )
        else:
            content = f"{summary_content}\n\n{logs_content}"

        # Write to file
        Path(file_path).write_text(content, encoding="utf-8")

    # Integration with existing logging service

    def log_custom(
        self,
        execution: Execution,
        level: LogLevel,
        message: str,
        node_id: Optional[str] = None,
        structured_data: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Log a custom message with enhanced tracking"""

        # Traditional logging
        self._traditional_service.log(
            execution=execution, level=level, message=message, node_id=node_id
        )

        # Enhanced logging
        enhanced_level = self._map_log_level(level)
        self._execution_logger.log_custom(
            level=enhanced_level,
            message=message,
            execution_id=execution.execution_id,
            node_id=node_id,
            structured_data=structured_data,
            trace_id=trace_id,
        )

    def _map_log_level(self, level: LogLevel) -> ExecutionLogLevel:
        """Map traditional log level to enhanced log level"""
        mapping = {
            LogLevel.DEBUG: ExecutionLogLevel.DEBUG,
            LogLevel.INFO: ExecutionLogLevel.INFO,
            LogLevel.WARN: ExecutionLogLevel.WARNING,
            LogLevel.ERROR: ExecutionLogLevel.ERROR,
            LogLevel.CRITICAL: ExecutionLogLevel.CRITICAL,
        }
        return mapping.get(level, ExecutionLogLevel.INFO)


# Global instance
_enhanced_logging_service = EnhancedLoggingService()


def get_enhanced_logging_service() -> EnhancedLoggingService:
    """Get the global enhanced logging service instance"""
    return _enhanced_logging_service


__all__ = ["NodeExecutionTracker", "EnhancedLoggingService", "get_enhanced_logging_service"]
