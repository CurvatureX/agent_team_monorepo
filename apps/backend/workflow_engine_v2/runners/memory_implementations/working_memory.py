"""
Working Memory implementation for workflow_engine_v2.

Maintains temporary working data during workflow execution.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from .base import MemoryBase


class WorkingMemory(MemoryBase):
    """Working memory implementation for temporary data."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.ttl_seconds = config.get("ttl_seconds", 3600)  # 1 hour default
        self.working_data = {}  # key -> {data, expires_at}

    async def _setup(self) -> None:
        """Setup working memory."""
        self.logger.info(f"Working Memory: TTL={self.ttl_seconds} seconds")

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store temporary working data."""
        try:
            key = data.get("key")
            value = data.get("value")
            ttl = data.get("ttl", self.ttl_seconds)

            if not key:
                return {"success": False, "error": "Missing 'key' in data"}

            expires_at = datetime.utcnow() + timedelta(seconds=ttl)

            self.working_data[key] = {
                "value": value,
                "stored_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat(),
                "metadata": data.get("metadata", {}),
            }

            # Clean up expired entries
            await self._cleanup_expired()

            return {"success": True, "key": key, "expires_at": expires_at.isoformat()}

        except Exception as e:
            self.logger.error(f"Error storing working data: {e}")
            return {"success": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve working data by key."""
        try:
            key = query.get("key")

            if not key:
                return {"success": False, "error": "Missing 'key' in query"}

            # Clean up expired first
            await self._cleanup_expired()

            if key not in self.working_data:
                return {"success": False, "error": f"Key '{key}' not found or expired"}

            entry = self.working_data[key]

            return {
                "success": True,
                "key": key,
                "value": entry["value"],
                "stored_at": entry["stored_at"],
                "expires_at": entry["expires_at"],
                "metadata": entry["metadata"],
            }

        except Exception as e:
            self.logger.error(f"Error retrieving working data: {e}")
            return {"success": False, "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted working memory context."""
        try:
            await self._cleanup_expired()

            if not self.working_data:
                return {"success": True, "context": "No working data available.", "entry_count": 0}

            pattern = query.get("pattern", "").lower()
            context_lines = ["Current working memory:"]

            for key, entry in self.working_data.items():
                if pattern and pattern not in key.lower():
                    continue

                value_preview = str(entry["value"])[:100]
                if len(str(entry["value"])) > 100:
                    value_preview += "..."

                context_lines.append(f"- {key}: {value_preview}")

            context = "\n".join(context_lines)

            return {"success": True, "context": context, "entry_count": len(self.working_data)}

        except Exception as e:
            self.logger.error(f"Error getting working memory context: {e}")
            return {"success": False, "error": str(e)}

    async def _cleanup_expired(self) -> None:
        """Clean up expired entries."""
        now = datetime.utcnow()
        expired_keys = []

        for key, entry in self.working_data.items():
            try:
                expires_at = datetime.fromisoformat(entry["expires_at"])
                if expires_at <= now:
                    expired_keys.append(key)
            except (ValueError, KeyError):
                # Invalid timestamp, consider expired
                expired_keys.append(key)

        for key in expired_keys:
            del self.working_data[key]

        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired working memory entries")

    async def clear_all(self) -> Dict[str, Any]:
        """Clear all working memory."""
        count = len(self.working_data)
        self.working_data.clear()
        return {"success": True, "cleared_count": count}


__all__ = ["WorkingMemory"]
