"""Memory service for v2 engine.

Provides per-execution key-value store and an in-memory vector store.
This is a pure-Python implementation suitable for local dev and tests.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


class KeyValueMemory:
    def __init__(self, backing: Dict[str, Any]):
        self._store = backing

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def set(self, key: str, value: Any) -> Any:
        self._store[key] = value
        return value

    def append(self, key: str, value: Any) -> List[Any]:
        cur = self._store.get(key) or []
        if not isinstance(cur, list):
            cur = [cur]
        cur.append(value)
        self._store[key] = cur
        return cur


class InMemoryVectorStore:
    def __init__(self):
        self._data: Dict[str, List[Tuple[List[float], Any]]] = {}

    def _embed(self, text: str) -> List[float]:
        # Simple character-hash embedding (deterministic)
        vec = [0.0] * 64
        for i, ch in enumerate(text):
            vec[i % 64] += (ord(ch) % 32) / 31.0
        # Normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def upsert(self, namespace: str, items: List[Dict[str, Any]]):
        arr = self._data.setdefault(namespace, [])
        for it in items:
            content = str(it.get("content", ""))
            embed = self._embed(content)
            arr.append((embed, it))

    def query(self, namespace: str, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        q = self._embed(query_text)
        arr = self._data.get(namespace, [])
        scored = []
        for emb, item in arr:
            score = sum(a * b for a, b in zip(q, emb))
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:top_k]]


__all__ = ["KeyValueMemory", "InMemoryVectorStore"]
