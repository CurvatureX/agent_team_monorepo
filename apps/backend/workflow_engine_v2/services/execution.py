"""Execution service (v2) to run workflows using the v2 engine."""

from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import TriggerInfo
from shared.models.execution_new import Execution
from shared.models.workflow_new import Workflow
from workflow_engine_v2.core.engine import ExecutionEngine
from workflow_engine_v2.services.file_repository import FileExecutionRepository
from workflow_engine_v2.services.supabase_repository_v2 import SupabaseExecutionRepository


class ExecutionServiceV2:
    def __init__(self, use_file_repo: bool = False, use_supabase_repo: bool = False) -> None:
        repo = None
        if use_supabase_repo:
            repo = SupabaseExecutionRepository()
        elif use_file_repo:
            repo = FileExecutionRepository()
        self._engine = ExecutionEngine(repository=repo)

    def execute(
        self,
        wf: Workflow,
        *,
        trigger_type: str = "manual",
        trigger_data: Optional[Dict[str, Any]] = None,
    ) -> Execution:
        trig = TriggerInfo(
            trigger_type=trigger_type,
            trigger_data=trigger_data or {},
            timestamp=int(time.time() * 1000),
        )
        return self._engine.run(wf, trig)

    def resume_hil(self, execution_id: str, node_id: str, input_data: Any) -> Execution:
        return self._engine.resume_with_user_input(execution_id, node_id, input_data)

    def resume_due_timers(self) -> None:
        return self._engine.resume_due_timers()

    # Control operations
    def pause(self, execution_id: str) -> Execution:
        return self._engine.pause(execution_id)

    def cancel(self, execution_id: str) -> Execution:
        return self._engine.cancel(execution_id)

    def retry_node(self, execution_id: str, node_id: str) -> Execution:
        return self._engine.retry_node(execution_id, node_id)

    # Repository accessors (in-memory by default)
    def get_execution(self, execution_id: str) -> Optional[Execution]:
        # Access internal repository via engine (exposed for convenience)
        try:
            repo = self._engine._repo  # type: ignore[attr-defined]
            return repo.get(execution_id)
        except Exception:
            return None

    def list_executions(self, limit: int = 50, offset: int = 0) -> list[Execution]:
        try:
            repo = self._engine._repo  # type: ignore[attr-defined]
            return repo.list(limit=limit, offset=offset)
        except Exception:
            return []

    # Execute by workflow id via WorkflowServiceV2
    def execute_by_id(
        self,
        workflow_service,
        workflow_id: str,
        *,
        trigger_type: str = "manual",
        trigger_data: dict | None = None,
    ) -> Execution:
        wf = workflow_service.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")
        return self.execute(wf, trigger_type=trigger_type, trigger_data=trigger_data)

    # Event streaming hook
    def register_websocket_forwarder(self, send_callable) -> None:
        from .websocket_forwarder import WebSocketForwarder

        WebSocketForwarder(send_callable).start()


__all__ = ["ExecutionServiceV2"]
