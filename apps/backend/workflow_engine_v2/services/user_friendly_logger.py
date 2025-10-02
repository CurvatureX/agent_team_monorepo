"""
User-Friendly Workflow Execution Logger for V2 Engine

This logger creates user-friendly log entries that are exposed through the API Gateway's
/api/v1/app/executions/{execution_id}/logs endpoint. It focuses on meaningful progress
updates that users care about, with detailed node execution tracking.

Key Features:
- User-friendly messages with clear progress indicators
- Input/output parameter summaries
- Milestone and step tracking
- Performance metrics
- Direct integration with Supabase logs table
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Union

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.execution_new import Execution

# Use absolute imports
from shared.models.workflow_new import Node

logger = logging.getLogger(__name__)


class LogCategory(str, Enum):
    """Categories for log entries"""

    BUSINESS = "business"  # User-facing business logic logs
    TECHNICAL = "technical"  # Technical details for debugging
    MILESTONE = "milestone"  # Important workflow milestones
    PROGRESS = "progress"  # Step-by-step progress updates


class EventType(str, Enum):
    """Event types for log entries"""

    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_ERROR = "step_error"
    WORKFLOW_PROGRESS = "workflow_progress"
    HUMAN_INTERACTION = "human_interaction"
    DATA_PROCESSING = "data_processing"


class LogLevel(str, Enum):
    """Log severity levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class UserFriendlyLogEntry:
    """User-friendly log entry for API consumption"""

    execution_id: str
    created_at: str  # ISO format - matches database column
    level: LogLevel
    event_type: EventType
    message: str
    user_friendly_message: str

    # Optional fields
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    node_type: Optional[str] = None
    step_number: Optional[int] = None
    total_steps: Optional[int] = None
    display_priority: int = 5  # 1-10, higher = more important
    is_milestone: bool = False

    # Structured data
    data: Optional[Dict[str, Any]] = None

    def to_supabase_row(self) -> Dict[str, Any]:
        """Convert to Supabase table row format using direct enum values."""
        level_value = self.level.value
        if level_value == "WARN":
            level_value = "WARNING"

        return {
            "execution_id": self.execution_id,
            "created_at": self.created_at,
            "log_category": LogCategory.BUSINESS.value,
            "level": level_value,
            "event_type": self.event_type.value,
            "message": self.message,
            "user_friendly_message": self.user_friendly_message,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "step_number": self.step_number,
            "total_steps": self.total_steps,
            "display_priority": self.display_priority,
            "is_milestone": self.is_milestone,
            "data": self.data or {},
        }


class NodeProgressTracker:
    """Tracks progress through workflow execution"""

    def __init__(self):
        self._node_steps: Dict[str, Dict[str, Any]] = {}
        self._execution_context: Dict[str, Any] = {}
        self._step_counter = 0
        self._total_steps = 0

    def set_execution_context(self, execution_id: str, total_nodes: int, workflow_name: str = ""):
        """Set the overall execution context"""
        self._execution_context[execution_id] = {
            "total_nodes": total_nodes,
            "workflow_name": workflow_name,
            "completed_nodes": 0,
            "failed_nodes": 0,
        }
        self._total_steps = total_nodes
        self._step_counter = 0

    def start_node(self, execution_id: str, node: Node) -> int:
        """Mark a node as started and return its step number"""
        self._step_counter += 1
        step_number = self._step_counter

        self._node_steps[node.id] = {
            "execution_id": execution_id,
            "step_number": step_number,
            "node_name": node.name,
            "node_type": node.type.value if hasattr(node.type, "value") else str(node.type),
            "node_subtype": node.subtype,
            "start_time": time.time(),
            "status": "running",
        }

        return step_number

    def complete_node(self, node_id: str, success: bool = True, error_message: str = None):
        """Mark a node as completed"""
        if node_id in self._node_steps:
            self._node_steps[node_id]["status"] = "completed" if success else "failed"
            self._node_steps[node_id]["end_time"] = time.time()
            if error_message:
                self._node_steps[node_id]["error_message"] = error_message

            execution_id = self._node_steps[node_id]["execution_id"]
            if execution_id in self._execution_context:
                if success:
                    self._execution_context[execution_id]["completed_nodes"] += 1
                else:
                    self._execution_context[execution_id]["failed_nodes"] += 1

    def get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a node"""
        return self._node_steps.get(node_id)

    def get_execution_progress(self, execution_id: str) -> Dict[str, Any]:
        """Get overall execution progress"""
        return self._execution_context.get(execution_id, {})


class UserFriendlyLogger:
    """User-friendly logger for workflow execution"""

    def __init__(self):
        self._progress_tracker = NodeProgressTracker()
        self._supabase = None
        self._log_buffer: List[UserFriendlyLogEntry] = []
        self._buffer_lock = Lock()
        self._buffer_size_limit = 100

        # Initialize Supabase client
        self._init_supabase()

    def _init_supabase(self):
        """Initialize Supabase client for log storage"""
        try:
            import os

            from supabase import create_client

            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_ANON_KEY")

            if url and key:
                self._supabase = create_client(url, key)
                logger.info("✅ Supabase client initialized for user-friendly logging")
            else:
                logger.warning("⚠️ Supabase credentials not found - logs will be buffered only")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")

    def log_workflow_start(
        self,
        execution: Execution,
        workflow_name: str = "",
        total_nodes: int = 0,
        trigger_info: str = "",
    ):
        """Log workflow execution start"""
        self._progress_tracker.set_execution_context(
            execution.execution_id, total_nodes, workflow_name
        )

        user_message = f"🚀 Started workflow: {workflow_name or 'Unnamed'}"
        if trigger_info:
            user_message += f" (triggered by {trigger_info})"

        if total_nodes > 0:
            user_message += f" - {total_nodes} steps to execute"

        log_entry = UserFriendlyLogEntry(
            execution_id=execution.execution_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.INFO,
            event_type=EventType.WORKFLOW_STARTED,
            message=f"Workflow execution started: {execution.execution_id}",
            user_friendly_message=user_message,
            step_number=0,
            total_steps=total_nodes,
            display_priority=9,
            is_milestone=True,
            data={
                "workflow_name": workflow_name,
                "total_nodes": total_nodes,
                "trigger_info": trigger_info,
            },
        )

        self._add_log_entry(log_entry)

    def log_workflow_complete(
        self,
        execution: Execution,
        success: bool = True,
        duration_ms: Optional[float] = None,
        summary: Optional[Dict[str, Any]] = None,
    ):
        """Log workflow execution completion"""
        progress = self._progress_tracker.get_execution_progress(execution.execution_id)
        completed = progress.get("completed_nodes", 0)
        failed = progress.get("failed_nodes", 0)
        total = progress.get("total_nodes", 0)

        if success:
            user_message = f"✅ Workflow completed successfully! {completed}/{total} steps completed"
            if duration_ms:
                user_message += f" in {duration_ms/1000:.1f}s"
            event_type = EventType.WORKFLOW_COMPLETED
        else:
            user_message = f"❌ Workflow failed. {completed} steps completed, {failed} failed"
            event_type = EventType.WORKFLOW_FAILED

        log_entry = UserFriendlyLogEntry(
            execution_id=execution.execution_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.INFO if success else LogLevel.ERROR,
            event_type=event_type,
            message=f"Workflow execution {'completed' if success else 'failed'}: {execution.execution_id}",
            user_friendly_message=user_message,
            display_priority=10,
            is_milestone=True,
            data={
                "completed_nodes": completed,
                "failed_nodes": failed,
                "total_nodes": total,
                "duration_ms": duration_ms,
                "success": success,
                **(summary or {}),
            },
        )

        self._add_log_entry(log_entry)
        # Flush remaining logs
        asyncio.create_task(self._flush_logs())

    def log_node_start(self, execution_id: str, node: Node, input_summary: Optional[str] = None):
        """Log node execution start"""
        step_number = self._progress_tracker.start_node(execution_id, node)
        progress = self._progress_tracker.get_execution_progress(execution_id)
        total_steps = progress.get("total_nodes", 0)

        # Create user-friendly node type description
        node_description = self._get_node_description(node.type, node.subtype)

        user_message = f"⚡ Step {step_number}/{total_steps}: {node.name}"
        if node_description:
            user_message += f" ({node_description})"

        if input_summary:
            user_message += f" - Processing: {input_summary}"

        log_entry = UserFriendlyLogEntry(
            execution_id=execution_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.INFO,
            event_type=EventType.STEP_STARTED,
            message=f"Node execution started: {node.name}",
            user_friendly_message=user_message,
            node_id=node.id,
            node_name=node.name,
            node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
            step_number=step_number,
            total_steps=total_steps,
            display_priority=6,
            data={"node_subtype": node.subtype, "input_summary": input_summary},
        )

        self._add_log_entry(log_entry)

    def log_node_complete(
        self,
        execution_id: str,
        node_id: str,
        success: bool = True,
        duration_ms: Optional[float] = None,
        output_summary: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Log node execution completion"""
        self._progress_tracker.complete_node(node_id, success, error_message)
        node_info = self._progress_tracker.get_node_info(node_id)

        if not node_info:
            return

        step_number = node_info.get("step_number", 0)
        progress = self._progress_tracker.get_execution_progress(execution_id)
        total_steps = progress.get("total_nodes", 0)

        if success:
            user_message = f"✅ Step {step_number}/{total_steps}: {node_info['node_name']} completed"
            if duration_ms:
                user_message += f" ({duration_ms:.0f}ms)"
            if output_summary:
                user_message += f" - Result: {output_summary}"
            event_type = EventType.STEP_COMPLETED
            level = LogLevel.INFO
        else:
            user_message = f"❌ Step {step_number}/{total_steps}: {node_info['node_name']} failed"
            if error_message:
                user_message += f" - Error: {error_message}"
            event_type = EventType.STEP_FAILED
            level = LogLevel.ERROR

        log_entry = UserFriendlyLogEntry(
            execution_id=execution_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            level=level,
            event_type=event_type,
            message=f"Node execution {'completed' if success else 'failed'}: {node_info['node_name']}",
            user_friendly_message=user_message,
            node_id=node_id,
            node_name=node_info["node_name"],
            node_type=node_info["node_type"],
            step_number=step_number,
            total_steps=total_steps,
            display_priority=7 if success else 8,
            data={
                "success": success,
                "duration_ms": duration_ms,
                "output_summary": output_summary,
                "error_message": error_message,
                "node_subtype": node_info.get("node_subtype"),
            },
        )

        self._add_log_entry(log_entry)

    def log_node_phase(
        self, execution_id: str, node_id: str, phase: str, details: Optional[str] = None
    ):
        """Log node execution phase (for detailed tracking)"""
        node_info = self._progress_tracker.get_node_info(node_id)
        if not node_info:
            return

        phase_messages = {
            "VALIDATING_INPUTS": "Validating inputs",
            "PROCESSING": "Processing request",
            "WAITING_HUMAN": "Waiting for human input",
            "COMPLETING": "Finalizing results",
        }

        phase_description = phase_messages.get(phase, phase.lower().replace("_", " "))
        user_message = f"🔄 {node_info['node_name']}: {phase_description}"
        if details:
            user_message += f" - {details}"

        log_entry = UserFriendlyLogEntry(
            execution_id=execution_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.DEBUG,
            event_type=EventType.WORKFLOW_PROGRESS,
            message=f"Node phase change: {node_info['node_name']} -> {phase}",
            user_friendly_message=user_message,
            node_id=node_id,
            node_name=node_info["node_name"],
            node_type=node_info["node_type"],
            step_number=node_info.get("step_number"),
            display_priority=3,
            data={"phase": phase, "details": details},
        )

        self._add_log_entry(log_entry)

    def log_human_interaction(
        self,
        execution_id: str,
        node_id: str,
        interaction_type: str,
        message: str,
        timeout_minutes: Optional[int] = None,
    ):
        """Log human interaction requests"""
        node_info = self._progress_tracker.get_node_info(node_id)
        node_name = node_info["node_name"] if node_info else "Human Input"

        user_message = f"👤 {node_name}: {message}"
        if timeout_minutes:
            user_message += f" (timeout: {timeout_minutes}min)"

        log_entry = UserFriendlyLogEntry(
            execution_id=execution_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.INFO,
            event_type=EventType.HUMAN_INTERACTION,
            message=f"Human interaction required: {interaction_type}",
            user_friendly_message=user_message,
            node_id=node_id,
            node_name=node_name,
            display_priority=8,
            data={"interaction_type": interaction_type, "timeout_minutes": timeout_minutes},
        )

        self._add_log_entry(log_entry)

    def log_custom_milestone(
        self,
        execution_id: str,
        message: str,
        user_message: str,
        level: LogLevel = LogLevel.INFO,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Log a custom milestone"""
        log_entry = UserFriendlyLogEntry(
            execution_id=execution_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            level=level,
            event_type=EventType.WORKFLOW_PROGRESS,
            message=message,
            user_friendly_message=user_message,
            display_priority=7,
            is_milestone=True,
            data=data,
        )

        self._add_log_entry(log_entry)

    def _get_node_description(self, node_type: Any, node_subtype: str) -> str:
        """Get user-friendly description of node type"""
        node_type_str = node_type.value if hasattr(node_type, "value") else str(node_type)

        descriptions = {
            ("TRIGGER", "MANUAL"): "Manual trigger",
            ("TRIGGER", "WEBHOOK"): "Webhook trigger",
            ("TRIGGER", "CRON"): "Scheduled trigger",
            ("TRIGGER", "SLACK"): "Slack trigger",
            ("TRIGGER", "EMAIL"): "Email trigger",
            ("AI_AGENT", "OPENAI_CHATGPT"): "ChatGPT AI",
            ("AI_AGENT", "ANTHROPIC_CLAUDE"): "Claude AI",
            ("AI_AGENT", "OPENAI"): "OpenAI",
            ("ACTION", "HTTP_REQUEST"): "HTTP request",
            ("ACTION", "EMAIL_SEND"): "Send email",
            ("ACTION", "FILE_OPERATION"): "File operation",
            ("EXTERNAL_ACTION", "SLACK"): "Slack action",
            ("EXTERNAL_ACTION", "NOTION"): "Notion action",
            ("EXTERNAL_ACTION", "GITHUB"): "GitHub action",
            ("EXTERNAL_ACTION", "AIRTABLE"): "Airtable action",
            ("FLOW", "IF"): "Conditional logic",
            # ("FLOW", "SWITCH"): "Switch logic",  # SWITCH removed
            ("FLOW", "LOOP"): "Loop logic",
            ("HUMAN_IN_THE_LOOP", "SLACK_INTERACTION"): "Slack approval",
            ("HUMAN_IN_THE_LOOP", "EMAIL_INTERACTION"): "Email approval",
            ("TOOL", "NOTION_MCP_TOOL"): "Notion tool execution",
            ("MEMORY", "VECTOR_STORE"): "Vector memory",
        }

        return descriptions.get(
            (node_type_str, node_subtype), f"{node_subtype} {node_type_str.lower()}"
        )

    def _add_log_entry(self, entry: UserFriendlyLogEntry):
        """Add log entry to buffer and flush if needed"""
        with self._buffer_lock:
            self._log_buffer.append(entry)

            # Flush if buffer is getting full
            if len(self._log_buffer) >= self._buffer_size_limit:
                asyncio.create_task(self._flush_logs())

    async def _flush_logs(self):
        """Flush log buffer to Supabase"""
        if not self._supabase:
            return

        # Get logs to flush
        logs_to_flush = []
        with self._buffer_lock:
            if self._log_buffer:
                logs_to_flush = self._log_buffer.copy()
                self._log_buffer.clear()

        if not logs_to_flush:
            return

        try:
            # Convert to Supabase format
            rows = [entry.to_supabase_row() for entry in logs_to_flush]

            # Insert into workflow_execution_logs table
            result = self._supabase.table("workflow_execution_logs").insert(rows).execute()
            logger.info(f"✅ Flushed {len(logs_to_flush)} log entries to Supabase")

        except Exception as e:
            logger.error(f"❌ Failed to flush logs to Supabase: {e}")
            # Put logs back in buffer for retry
            with self._buffer_lock:
                self._log_buffer.extend(logs_to_flush)


# Global instance
_user_friendly_logger = UserFriendlyLogger()


def get_user_friendly_logger() -> UserFriendlyLogger:
    """Get the global user-friendly logger instance"""
    return _user_friendly_logger


__all__ = [
    "UserFriendlyLogger",
    "UserFriendlyLogEntry",
    "LogCategory",
    "EventType",
    "LogLevel",
    "NodeProgressTracker",
    "get_user_friendly_logger",
]
