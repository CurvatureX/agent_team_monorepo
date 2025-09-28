"""Simple in-memory event bus for engine updates.

Publishes ExecutionUpdateEvent from models.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import ExecutionUpdateEvent

Subscriber = Callable[[ExecutionUpdateEvent], None]


@dataclass
class EventBus:
    subscribers: List[Subscriber]

    def __init__(self) -> None:
        self.subscribers = []

    def subscribe(self, fn: Subscriber) -> None:
        self.subscribers.append(fn)

    def publish(self, event: ExecutionUpdateEvent) -> None:
        for fn in list(self.subscribers):
            try:
                fn(event)
            except Exception:
                # Ignore subscriber errors for bus robustness
                pass


_bus = EventBus()


def get_event_bus() -> EventBus:
    return _bus


__all__ = ["EventBus", "get_event_bus"]
