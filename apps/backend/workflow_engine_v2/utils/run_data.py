"""Utilities for building execution run_data snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Dict, List

from shared.models.execution_new import Execution


def _sanitize_value(value: Any) -> Any:
    """Convert nested execution data into JSON-serializable primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        sanitized: Dict[str, Any] = {}
        for key, item in value.items():
            # Drop execution context references
            if key == "_ctx":
                continue
            sanitized[key] = _sanitize_value(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, Iterable):
        return [_sanitize_value(item) for item in value]
    return str(value)


def build_run_data_snapshot(execution: Execution) -> Dict[str, Any]:
    """Construct a serializable run_data snapshot from an execution instance."""
    node_results: Dict[str, Any] = {}

    for node_id, node_exec in execution.node_executions.items():
        status = (
            node_exec.status.value
            if hasattr(node_exec.status, "value")
            else str(node_exec.status)
        )

        logs: List[str] = []
        execution_logs = getattr(node_exec.execution_details, "logs", [])
        if execution_logs:
            for entry in execution_logs:
                if hasattr(entry, "message"):
                    logs.append(str(entry.message))
                elif isinstance(entry, str):
                    logs.append(entry)
                else:
                    logs.append(str(entry))

        details = (
            node_exec.execution_details.model_dump(mode="json")
            if node_exec.execution_details
            else {}
        )
        error = (
            node_exec.error.model_dump(mode="json")
            if node_exec.error and hasattr(node_exec.error, "model_dump")
            else None
        )

        node_results[node_id] = {
            "status": status,
            "start_time": node_exec.start_time,
            "end_time": node_exec.end_time,
            "duration_ms": node_exec.duration_ms,
            "input_data": _sanitize_value(node_exec.input_data),
            "output_data": _sanitize_value(node_exec.output_data),
            "logs": logs,
            "execution_details": details,
            "error": error,
            "retry_count": getattr(node_exec, "retry_count", 0),
        }

    snapshot: Dict[str, Any] = {
        "node_results": node_results,
        "execution_sequence": execution.execution_sequence,
    }

    if execution.current_node_id is not None:
        snapshot["current_node_id"] = execution.current_node_id
    if execution.next_nodes:
        snapshot["next_nodes"] = execution.next_nodes

    return snapshot
