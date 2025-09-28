"""Engine logging service that appends logs and publishes update events.

Follows v1 design principles:
- Redis-backed caching (DB 1) with in-memory fallback
- Optional Supabase persistence for user-friendly logs
- EventBus publishing for live SSE streaming
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import (
    Execution,
    ExecutionEventType,
    ExecutionUpdateData,
    ExecutionUpdateEvent,
    LogEntry,
    LogLevel,
)

from .events import get_event_bus


def _now_ms() -> int:
    import time as _t

    return int(_t.time() * 1000)


class LoggingService:
    def __init__(self) -> None:
        self._bus = get_event_bus()
        self._store: Dict[str, List[LogEntry]] = {}

        # Redis (db=1) optional
        self._redis = None
        try:
            import redis  # type: ignore

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            if "redis://" in redis_url:
                base = redis_url.split("/")[0] + "//" + redis_url.split("//")[1].split("/")[0]
                redis_url = base + "/1"
            self._redis = redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
        except Exception:
            self._redis = None

        # Supabase (optional)
        self._supabase = None
        try:
            from supabase import create_client  # type: ignore

            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
            if url and key:
                self._supabase = create_client(url, key)
        except Exception:
            self._supabase = None

        # Batch writer
        self._batch_buffer: deque = deque()
        self._buffer_lock = Lock()
        self._batch_writer_task = None
        self._shutdown = False

    def log(
        self, execution: Execution, level: LogLevel, message: str, node_id: Optional[str] = None
    ) -> None:
        # Friendly dict
        event_type = self._infer_event_type(message, node_id)
        ts_str = datetime.utcfromtimestamp(_now_ms() / 1000).isoformat()
        friendly = {
            "execution_id": execution.execution_id,
            "event_type": event_type,
            "timestamp": ts_str,
            "message": str(message),
            "level": str(level.name if hasattr(level, "name") else level),
            "data": {"node_id": node_id} if node_id else {},
        }

        # Memory store (bounded)
        arr = self._store.setdefault(execution.execution_id, [])
        if len(arr) >= 5000:
            del arr[:1000]
        arr.append(LogEntry(timestamp=_now_ms(), level=level, message=message, node_id=node_id))

        # Redis append
        try:
            if self._redis is not None:
                key = f"workflow_logs:{execution.execution_id}"
                self._redis.rpush(key, self._safe_json_dumps(friendly))
                self._redis.ltrim(key, -5000, -1)
        except Exception:
            pass

        # Publish for SSE
        event = ExecutionUpdateEvent(
            event_type=ExecutionEventType.NODE_OUTPUT_UPDATE
            if node_id
            else ExecutionEventType.EXECUTION_STARTED,
            execution_id=execution.execution_id,
            timestamp=_now_ms(),
            data=ExecutionUpdateData(node_id=node_id, partial_output={"log": friendly}),
        )
        self._bus.publish(event)

        # Batch for DB
        try:
            if self._is_user_friendly_log(friendly):
                self._add_to_batch_buffer(friendly)
        except Exception:
            pass

    def get_logs(self, execution_id: str) -> List[Dict]:
        # Try Redis first
        logs = self._get_logs_from_redis(execution_id)
        if logs:
            return logs
        # Memory fallback
        result: List[Dict] = []
        for e in self._store.get(execution_id, []):
            ts_str = datetime.utcfromtimestamp((e.timestamp or _now_ms()) / 1000).isoformat()
            result.append(
                {
                    "execution_id": execution_id,
                    "event_type": self._infer_event_type(e.message, e.node_id),
                    "timestamp": ts_str,
                    "message": e.message,
                    "level": str(e.level.name if hasattr(e.level, "name") else e.level),
                    "data": {"node_id": e.node_id} if e.node_id else {},
                }
            )
        if not result:
            result = self._get_logs_from_database(execution_id)
        return result

    def _infer_event_type(self, message: str, node_id: Optional[str]) -> str:
        msg = (message or "").lower()
        if "execution started" in msg:
            return "workflow_started"
        if "execution completed" in msg or "completed successfully" in msg:
            return "workflow_completed"
        if "node" in msg and "started" in msg:
            return "step_started"
        if "node" in msg and "completed" in msg:
            return "step_completed"
        if "failed" in msg or "error" in msg:
            return "step_error"
        return "workflow_progress"

    # ---------- Redis ----------
    def _get_logs_from_redis(self, execution_id: str) -> List[Dict]:
        try:
            if self._redis is None:
                return []
            key = f"workflow_logs:{execution_id}"
            raw = self._redis.lrange(key, 0, -1) or []
            out: List[Dict] = []
            for r in raw:
                try:
                    out.append(json.loads(r))
                except Exception:
                    continue
            return out
        except Exception:
            return []

    # ---------- DB ----------
    def _add_to_batch_buffer(self, friendly_log: Dict[str, Any]) -> None:
        try:
            with self._buffer_lock:
                self._batch_buffer.append(friendly_log)
            if len(self._batch_buffer) >= 50:
                asyncio.create_task(self._flush_batch_buffer())
        except Exception:
            pass

    async def _flush_batch_buffer(self) -> None:
        if self._supabase is None:
            return
        entries: List[Dict[str, Any]] = []
        with self._buffer_lock:
            if not self._batch_buffer:
                return
            size = min(len(self._batch_buffer), 100)
            for _ in range(size):
                if self._batch_buffer:
                    entries.append(self._batch_buffer.popleft())
        if not entries:
            return
        try:
            rows = [self._friendly_to_db_row(e) for e in entries]
            self._supabase.table("workflow_execution_logs").insert(rows).execute()
        except Exception:
            pass

    def _friendly_to_db_row(self, e: Dict[str, Any]) -> Dict[str, Any]:
        row = {
            "execution_id": e.get("execution_id"),
            "log_category": "business",
            "event_type": e.get("event_type"),
            "level": (e.get("level") or "INFO").upper(),
            "message": e.get("message"),
            "data": e.get("data") or {},
        }
        return row

    def _get_logs_from_database(self, execution_id: str) -> List[Dict]:
        if self._supabase is None:
            return []
        try:
            resp = (
                self._supabase.table("workflow_execution_logs")
                .select("*")
                .eq("execution_id", execution_id)
                .order("created_at", desc=False)
                .execute()
            )
            out: List[Dict] = []
            for row in resp.data or []:
                out.append(
                    {
                        "execution_id": row.get("execution_id"),
                        "event_type": row.get("event_type"),
                        "timestamp": row.get("created_at"),
                        "message": row.get("message"),
                        "level": row.get("level"),
                        "data": row.get("data") or {},
                    }
                )
            return out
        except Exception:
            return []

    def _is_user_friendly_log(self, e: Dict[str, Any]) -> bool:
        d = e.get("data") or {}
        if d.get("user_friendly_message"):
            return True
        if e.get("event_type") in {
            "workflow_started",
            "workflow_completed",
            "step_completed",
            "step_error",
        }:
            return True
        if (d.get("display_priority") or 5) >= 7:
            return True
        return False

    def _safe_json_dumps(self, data: Any) -> str:
        try:
            from ...workflow_engine.utils.unicode_utils import safe_json_dumps  # type: ignore

            return safe_json_dumps(data)
        except Exception:
            return json.dumps(data, ensure_ascii=True)

    def ensure_started(self) -> None:
        if self._batch_writer_task is not None:
            return
        try:
            loop = asyncio.get_running_loop()

            async def runner():
                while not self._shutdown:
                    try:
                        await asyncio.sleep(1.0)
                        await self._flush_batch_buffer()
                    except Exception:
                        await asyncio.sleep(1.0)

            self._batch_writer_task = loop.create_task(runner())
        except RuntimeError:
            pass


_svc = LoggingService()


def get_logging_service() -> LoggingService:
    return _svc


__all__ = ["LoggingService", "get_logging_service"]
