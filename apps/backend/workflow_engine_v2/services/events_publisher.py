"""Event publisher for workflow_engine_v2.

Builds and publishes ExecutionUpdateEvent for engine lifecycle transitions.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

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
    NodeExecution,
)

from .events import get_event_bus


def _now_ms() -> int:
    return int(time.time() * 1000)


class EventPublisher:
    def __init__(self) -> None:
        self._bus = get_event_bus()

    def publish(self, event: ExecutionUpdateEvent) -> None:
        self._bus.publish(event)

    def _build(
        self, execution_id: str, event_type: ExecutionEventType, data: ExecutionUpdateData
    ) -> ExecutionUpdateEvent:
        return ExecutionUpdateEvent(
            event_type=event_type,
            execution_id=execution_id,
            timestamp=_now_ms(),
            data=data,
        )

    def execution_started(self, we: Execution) -> None:
        self.publish(
            self._build(
                we.execution_id,
                ExecutionEventType.EXECUTION_STARTED,
                ExecutionUpdateData(execution_status=we.status),
            )
        )

    def execution_completed(self, we: Execution) -> None:
        self.publish(
            self._build(
                we.execution_id,
                ExecutionEventType.EXECUTION_COMPLETED,
                ExecutionUpdateData(execution_status=we.status),
            )
        )

    def execution_failed(self, we: Execution) -> None:
        self.publish(
            self._build(
                we.execution_id,
                ExecutionEventType.EXECUTION_FAILED,
                ExecutionUpdateData(execution_status=ExecutionStatus.ERROR),
            )
        )

    def execution_paused(self, we: Execution) -> None:
        self.publish(
            self._build(
                we.execution_id,
                ExecutionEventType.EXECUTION_PAUSED,
                ExecutionUpdateData(execution_status=we.status),
            )
        )

    def execution_resumed(self, we: Execution) -> None:
        self.publish(
            self._build(
                we.execution_id,
                ExecutionEventType.EXECUTION_RESUMED,
                ExecutionUpdateData(execution_status=we.status),
            )
        )

    def node_started(self, we: Execution, node_id: str, ne: NodeExecution) -> None:
        self.publish(
            self._build(
                we.execution_id,
                ExecutionEventType.NODE_STARTED,
                ExecutionUpdateData(node_id=node_id, node_execution=ne),
            )
        )

    def node_completed(self, we: Execution, node_id: str, ne: NodeExecution) -> None:
        self.publish(
            self._build(
                we.execution_id,
                ExecutionEventType.NODE_COMPLETED,
                ExecutionUpdateData(node_id=node_id, node_execution=ne),
            )
        )

    def node_failed(self, we: Execution, node_id: str, ne: NodeExecution) -> None:
        self.publish(
            self._build(
                we.execution_id,
                ExecutionEventType.NODE_FAILED,
                ExecutionUpdateData(node_id=node_id, node_execution=ne),
            )
        )

    def user_input_required(self, we: Execution, node_id: str, ne: NodeExecution) -> None:
        self.publish(
            self._build(
                we.execution_id,
                ExecutionEventType.USER_INPUT_REQUIRED,
                ExecutionUpdateData(node_id=node_id, node_execution=ne),
            )
        )

    def node_output_update(
        self, we: Execution, node_id: str, ne: NodeExecution, partial: Optional[dict] = None
    ) -> None:
        data = ExecutionUpdateData(node_id=node_id, node_execution=ne)
        if partial is not None:
            data.partial_output = partial
        self.publish(self._build(we.execution_id, ExecutionEventType.NODE_OUTPUT_UPDATE, data))


_publisher = EventPublisher()


def get_event_publisher() -> EventPublisher:
    return _publisher


__all__ = ["EventPublisher", "get_event_publisher"]
