"""Tiny expression helper for flow nodes (core)."""

from __future__ import annotations

from typing import Any


def get_path(data: Any, path: str) -> Any:
    if not path:
        return data
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict):
            if part in cur:
                cur = cur[part]
            else:
                lowered = {k.lower(): k for k in cur.keys()}
                key = lowered.get(part.lower())
                if key is None:
                    return None
                cur = cur[key]
        elif isinstance(cur, list):
            if part.isdigit():
                idx = int(part)
                if 0 <= idx < len(cur):
                    cur = cur[idx]
                else:
                    return None
            else:
                return None
        else:
            return None
    return cur


__all__ = ["get_path"]
