"""Engine-specific exceptions for workflow_engine_v2 (core)."""

from __future__ import annotations


class EngineError(Exception):
    pass


class SpecNotFoundError(EngineError):
    pass


class GraphError(EngineError):
    pass


class CycleError(GraphError):
    pass


class ExecutionFailure(EngineError):
    pass


__all__ = [
    "EngineError",
    "SpecNotFoundError",
    "GraphError",
    "CycleError",
    "ExecutionFailure",
]
