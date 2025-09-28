"""Timer service for WAIT/DELAY/TIMEOUT flow support.

Provides a simple in-memory schedule and an API to check due tasks.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import List, Optional, Tuple


def _now_ms() -> int:
    import time as _t

    return int(_t.time() * 1000)


@dataclass(order=True)
class _Timer:
    at_ms: int
    execution_id: str
    node_id: str
    reason: str
    port: str


class TimerService:
    def __init__(self) -> None:
        self._pq: List[_Timer] = []

    def schedule(
        self,
        execution_id: str,
        node_id: str,
        delay_ms: int,
        *,
        reason: str = "delay",
        port: str = "main",
    ) -> int:
        at = _now_ms() + max(0, delay_ms)
        heapq.heappush(
            self._pq,
            _Timer(at_ms=at, execution_id=execution_id, node_id=node_id, reason=reason, port=port),
        )
        return at

    def due(self) -> List[Tuple[str, str, str, str]]:
        now = _now_ms()
        out: List[Tuple[str, str, str, str]] = []
        while self._pq and self._pq[0].at_ms <= now:
            t = heapq.heappop(self._pq)
            out.append((t.execution_id, t.node_id, t.reason, t.port))
        return out


_svc = TimerService()


def get_timer_service() -> TimerService:
    return _svc


__all__ = ["TimerService", "get_timer_service"]
