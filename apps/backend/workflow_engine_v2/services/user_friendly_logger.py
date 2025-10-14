"""
Simplified Async User-Friendly Logger (V2)

Clean, lock-free async logging system:
- asyncio.Queue for non-blocking log collection
- Async batch writes to Supabase every 1 second
- Redis pub/sub for real-time streaming (optional)
- No SQLite, no threads, no locks, no deadlocks
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.execution_new import Execution
from shared.models.workflow import Node

logger = logging.getLogger(__name__)


def _serialize_for_json(obj: Any) -> Any:
    """
    Recursively serialize objects to JSON-compatible types.
    Converts datetime objects to ISO format strings.
    """
    if isinstance(obj, datetime):
        return obj.isoformat() + "Z" if obj.tzinfo is None else obj.isoformat()
    elif isinstance(obj, dict):
        return {key: _serialize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_for_json(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        # Handle custom objects by converting to dict
        return _serialize_for_json(obj.__dict__)
    else:
        return obj


class LogCategory(str, Enum):
    """Categories for log entries"""

    BUSINESS = "business"
    TECHNICAL = "technical"
    MILESTONE = "milestone"
    PROGRESS = "progress"


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
    created_at: str  # ISO format
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
    display_priority: int = 5
    is_milestone: bool = False
    data: Optional[Dict[str, Any]] = None

    def to_supabase_row(self) -> Dict[str, Any]:
        """Convert to Supabase table row format"""
        level_value = self.level.value
        if level_value == "WARN":
            level_value = "WARNING"

        # Serialize data field to ensure JSON compatibility
        serialized_data = _serialize_for_json(self.data) if self.data else {}

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
            "data": serialized_data,
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


class AsyncUserFriendlyLogger:
    """Simplified async user-friendly logger (V2)"""

    def __init__(self):
        self._progress_tracker = NodeProgressTracker()
        self._log_queue: Optional[asyncio.Queue] = None
        self._writer_task: Optional[asyncio.Task] = None
        self._redis = None
        self._supabase = None
        self._shutdown = False

        # Initialize clients
        self._init_redis()
        self._init_supabase()

    def _init_redis(self):
        """Initialize Redis client for real-time streaming (optional)"""
        try:
            import redis

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/2")
            if redis_url:
                self._redis = redis.from_url(redis_url, decode_responses=True)
                logger.info(f"✅ Redis initialized for log streaming: {redis_url}")
        except Exception as e:
            logger.warning(f"⚠️ Redis not available for log streaming: {e}")

    def _init_supabase(self):
        """Initialize async Supabase client"""
        try:
            from supabase import create_client

            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_ANON_KEY")

            if url and key:
                self._supabase = create_client(url, key)
                logger.info("✅ Supabase client initialized for async logging")
            else:
                logger.warning("⚠️ Supabase credentials not found - logs will be buffered only")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")

    async def start(self):
        """Start the async log writer"""
        if self._writer_task is not None:
            logger.warning("Async log writer already running")
            return

        self._log_queue = asyncio.Queue(maxsize=1000)
        self._shutdown = False
        self._writer_task = asyncio.create_task(self._background_writer())
        logger.info("✅ Async log writer started")

    async def stop(self, timeout: float = 5.0):
        """Stop the async log writer and drain remaining logs"""
        if self._writer_task is None:
            return

        logger.info("🛑 Stopping async log writer...")
        self._shutdown = True

        try:
            await asyncio.wait_for(self._writer_task, timeout=timeout)
            logger.info("✅ Async log writer stopped cleanly")
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Log writer did not finish within {timeout}s, canceling...")
            self._writer_task.cancel()
            try:
                await self._writer_task
            except asyncio.CancelledError:
                pass

    def flush_sync(self, timeout: float = 2.0):
        """Synchronously flush all pending logs to database (for use in sync code)"""
        if self._log_queue is None or self._log_queue.empty():
            return

        logger.info(f"🔄 Flushing {self._log_queue.qsize()} pending logs...")

        # Collect all queued logs
        batch = []
        while not self._log_queue.empty():
            try:
                entry = self._log_queue.get_nowait()
                batch.append(entry.to_supabase_row())
            except Exception:
                break

        # Write batch synchronously
        if batch and self._supabase:
            try:
                self._supabase.table("workflow_execution_logs").insert(batch).execute()
                logger.info(f"✅ Flushed {len(batch)} logs to database")
            except Exception as e:
                logger.error(f"❌ Failed to flush logs: {e}")

    def log_entry(self, entry: UserFriendlyLogEntry):
        """Add log entry to queue (thread-safe, non-blocking)"""
        if self._log_queue is None:
            logger.warning("Log queue not initialized, dropping log entry")
            return

        # Publish to Redis for real-time streaming (best-effort)
        if self._redis:
            try:
                channel = f"execution_logs:{entry.execution_id}"
                log_data = {
                    "timestamp": entry.created_at,
                    "node_name": entry.node_name,
                    "event_type": entry.event_type.value,
                    "message": entry.user_friendly_message,
                    "level": entry.level.value.lower(),
                    "data": _serialize_for_json(entry.data) if entry.data else {},
                }
                self._redis.publish(channel, json.dumps(log_data))
            except Exception as e:
                logger.debug(f"Failed to publish log to Redis: {e}")

        # Add to async queue
        try:
            self._log_queue.put_nowait(entry)
        except asyncio.QueueFull:
            # Drop oldest log if queue full
            try:
                self._log_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._log_queue.put_nowait(entry)

    async def _background_writer(self):
        """Background task that batches writes to Supabase"""
        batch = []
        batch_size = 100
        flush_interval = 1.0  # 1 second

        logger.info("📝 Background log writer started (batch_size=100, interval=1s)")

        while not self._shutdown or not self._log_queue.empty():
            try:
                # Collect logs for up to 1 second
                entry = await asyncio.wait_for(self._log_queue.get(), timeout=flush_interval)
                batch.append(entry.to_supabase_row())

                # Drain queue up to batch limit
                while len(batch) < batch_size:
                    try:
                        entry = self._log_queue.get_nowait()
                        batch.append(entry.to_supabase_row())
                    except asyncio.QueueEmpty:
                        break

                # Write batch to Supabase (async, non-blocking)
                if batch and self._supabase:
                    await self._write_batch(batch)
                    batch = []

            except asyncio.TimeoutError:
                # Flush partial batch every second
                if batch and self._supabase:
                    await self._write_batch(batch)
                    batch = []
            except Exception as e:
                logger.error(f"Log writer error: {e}")
                batch = []  # Clear batch on error

        # Final flush on shutdown
        if batch and self._supabase:
            await self._write_batch(batch)

        logger.info("📝 Background log writer stopped")

    async def _write_batch(self, batch: list):
        """Write batch of logs to Supabase (async)"""
        try:
            # Use thread pool for sync Supabase call
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._supabase.table("workflow_execution_logs").insert(batch).execute(),
            )
            logger.debug(f"✅ Wrote {len(batch)} logs to Supabase")
        except Exception as e:
            logger.error(f"❌ Failed to write {len(batch)} logs to Supabase: {e}")

    # Logging methods (same interface as old logger)

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

        user_message = f"Started workflow: {workflow_name or 'Unnamed'}"
        if total_nodes > 0:
            user_message += f" ({total_nodes} steps)"

        log_entry = UserFriendlyLogEntry(
            execution_id=execution.execution_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.INFO,
            event_type=EventType.WORKFLOW_STARTED,
            message=user_message,
            user_friendly_message=user_message,
            step_number=0,
            total_steps=total_nodes,
            display_priority=0,
            is_milestone=False,
            data={
                "workflow_name": workflow_name,
                "total_nodes": total_nodes,
                "trigger_info": trigger_info,
            },
        )

        self.log_entry(log_entry)

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
            user_message = f"Workflow completed ({completed}/{total} steps)"
            if duration_ms:
                user_message += f" in {duration_ms/1000:.1f}s"
            event_type = EventType.WORKFLOW_COMPLETED
        else:
            user_message = f"Workflow failed ({completed} completed, {failed} failed)"
            event_type = EventType.WORKFLOW_FAILED

        log_entry = UserFriendlyLogEntry(
            execution_id=execution.execution_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.INFO if success else LogLevel.ERROR,
            event_type=event_type,
            message=user_message,
            user_friendly_message=user_message,
            display_priority=0,
            is_milestone=False,
            data={
                "completed_nodes": completed,
                "failed_nodes": failed,
                "total_nodes": total,
                "duration_ms": duration_ms,
                "success": success,
                **(summary or {}),
            },
        )

        self.log_entry(log_entry)

    def log_node_start(
        self, execution_id: str, node: Node, input_summary: Optional[Dict[str, Any]] = None
    ):
        """Log node execution start"""
        step_number = self._progress_tracker.start_node(execution_id, node)
        progress = self._progress_tracker.get_execution_progress(execution_id)
        total_steps = progress.get("total_nodes", 0)

        # Build user-friendly message (no inline JSON)
        user_message = f"Started: {node.name}"

        # Store input params in data field for structured access
        data_field = {
            "node_type": node.type.value if hasattr(node.type, "value") else str(node.type),
            "node_subtype": node.subtype,
        }

        # Add input_params if available
        if input_summary and isinstance(input_summary, dict) and input_summary:
            data_field["input_params"] = input_summary

        log_entry = UserFriendlyLogEntry(
            execution_id=execution_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.INFO,
            event_type=EventType.STEP_STARTED,
            message=user_message,
            user_friendly_message=user_message,
            node_id=node.id,
            node_name=node.name,
            node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
            step_number=step_number,
            total_steps=total_steps,
            display_priority=0,
            data=data_field,
        )

        self.log_entry(log_entry)

    def log_node_complete(
        self,
        execution_id: str,
        node_id: str,
        success: bool = True,
        duration_ms: Optional[float] = None,
        output_summary: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        """Log node execution completion"""
        self._progress_tracker.complete_node(node_id, success, error_message)
        node_info = self._progress_tracker.get_node_info(node_id)

        if not node_info:
            logger.warning(
                f"⚠️ log_node_complete called for node {node_id} but node info not found"
            )
            return

        step_number = node_info.get("step_number", 0)
        progress = self._progress_tracker.get_execution_progress(execution_id)
        total_steps = progress.get("total_nodes", 0)

        # Prepare data field for structured access
        data_field = {
            "success": success,
            "duration_ms": duration_ms,
            "node_subtype": node_info.get("node_subtype"),
        }

        if success:
            user_message = f"Completed: {node_info['node_name']}"

            # Store output params in data field if available
            if output_summary and isinstance(output_summary, dict):
                # Extract output_params from the summary
                output_params = output_summary.get("output_params", {})
                if output_params and isinstance(output_params, dict):
                    data_field["output_params"] = output_params

            event_type = EventType.STEP_COMPLETED
            level = LogLevel.INFO
        else:
            user_message = f"Failed: {node_info['node_name']}"

            # Store error message in data field
            if error_message:
                data_field["error_message"] = error_message

            event_type = EventType.STEP_FAILED
            level = LogLevel.ERROR

        log_entry = UserFriendlyLogEntry(
            execution_id=execution_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            level=level,
            event_type=event_type,
            message=user_message,
            user_friendly_message=user_message,
            node_id=node_id,
            node_name=node_info["node_name"],
            node_type=node_info["node_type"],
            step_number=step_number,
            total_steps=total_steps,
            display_priority=0,
            data=data_field,
        )

        self.log_entry(log_entry)

    def log_tool_usage(
        self,
        execution_id: str,
        node_id: str,
        node_name: str,
        tool_name: str,
        tool_input: Optional[Dict[str, Any]] = None,
        tool_output: Optional[Any] = None,
    ):
        """Log AI agent tool usage"""
        user_message = f"Tool: {node_name} used {tool_name}"

        log_entry = UserFriendlyLogEntry(
            execution_id=execution_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.INFO,
            event_type=EventType.DATA_PROCESSING,
            message=user_message,
            user_friendly_message=user_message,
            node_id=node_id,
            node_name=node_name,
            display_priority=0,
            data={
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_output": tool_output,
            },
        )

        self.log_entry(log_entry)


# Global instance
_async_logger: Optional[AsyncUserFriendlyLogger] = None


def get_async_user_friendly_logger() -> AsyncUserFriendlyLogger:
    """Get the global async user-friendly logger instance"""
    global _async_logger
    if _async_logger is None:
        _async_logger = AsyncUserFriendlyLogger()
    return _async_logger


__all__ = [
    "AsyncUserFriendlyLogger",
    "UserFriendlyLogEntry",
    "LogCategory",
    "EventType",
    "LogLevel",
    "NodeProgressTracker",
    "get_async_user_friendly_logger",
]
