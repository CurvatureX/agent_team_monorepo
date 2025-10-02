"""File-backed execution repository for v2 engine.

Stores Execution as JSON under a base directory.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import Execution

from .repository import ExecutionRepository


class FileExecutionRepository(ExecutionRepository):
    def __init__(self, base_dir: str = "apps/backend/workflow_engine_v2/data/executions") -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, execution_id: str) -> Path:
        return self._base / f"{execution_id}.json"

    def save(self, execution: Execution) -> None:
        p = self._path(execution.execution_id)
        data = json.dumps(execution.model_dump(), ensure_ascii=False)
        p.write_text(data, encoding="utf-8")

    def get(self, execution_id: str) -> Optional[Execution]:
        p = self._path(execution_id)
        if not p.exists():
            return None
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            return Execution(**raw)
        except Exception:
            return None

    def list(self, limit: int = 50, offset: int = 0) -> List[Execution]:
        executions: List[Execution] = []
        for f in sorted(self._base.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                executions.append(Execution(**raw))
            except Exception:
                continue
        return executions[offset : offset + limit]


__all__ = ["FileExecutionRepository"]
