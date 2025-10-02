"""
workflow_engine_v2

Lightweight, spec-driven execution engine aligned with the new workflow models (v2).

This package intentionally avoids touching the legacy engine under
`apps/backend/workflow_engine/` and provides a fresh, composable core
for graph execution and spec validation.
"""

from .core.engine import ExecutionEngine

__all__ = ["ExecutionEngine"]
