"""In-memory execution state store for workflow_engine_v2 (core)."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import Execution
from shared.models.workflow_new import Workflow
from workflow_engine_v2.core.graph import WorkflowGraph


@dataclass
class ExecutionContext:
    workflow: Workflow
    graph: WorkflowGraph
    execution: Execution
    pending_inputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    memory_store: Dict[str, Any] = field(default_factory=dict)
    node_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    node_outputs_by_name: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class ExecutionStore:
    def __init__(self) -> None:
        self._store: Dict[str, ExecutionContext] = {}

    def put(self, ctx: ExecutionContext) -> None:
        self._store[ctx.execution.execution_id] = ctx

    def get(self, execution_id: str) -> ExecutionContext:
        return self._store[execution_id]

    def remove(self, execution_id: str) -> None:
        self._store.pop(execution_id, None)


__all__ = ["ExecutionContext", "ExecutionStore"]
