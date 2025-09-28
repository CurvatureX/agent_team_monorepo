"""
Base class for memory implementations in workflow_engine_v2.

Provides common interface and utilities for all memory types.
"""

from __future__ import annotations

import json
import logging
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

logger = logging.getLogger(__name__)


class MemoryBase(ABC):
    """Base class for all memory implementations in workflow_engine_v2."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize memory with configuration."""
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the memory backend."""
        if not self._initialized:
            await self._setup()
            self._initialized = True
            self.logger.info(f"Memory backend {self.__class__.__name__} initialized")

    @abstractmethod
    async def _setup(self) -> None:
        """Setup the memory backend (abstract method)."""
        pass

    @abstractmethod
    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store data in memory (abstract method)."""
        pass

    @abstractmethod
    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve data from memory (abstract method)."""
        pass

    @abstractmethod
    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted context for LLM (abstract method)."""
        pass

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the memory backend."""
        try:
            await self.initialize()
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            self.logger.error(f"Memory health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _serialize_data(self, data: Any) -> str:
        """Serialize data to JSON string."""
        if isinstance(data, str):
            return data
        return json.dumps(data, default=str, ensure_ascii=False)

    def _deserialize_data(self, data: str) -> Any:
        """Deserialize JSON string to data."""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data

    def _get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback."""
        return self.config.get(key, default)

    def _create_storage_key(self, namespace: str, identifier: str) -> str:
        """Create a standardized storage key."""
        return f"{namespace}:{identifier}"

    def _extract_timestamp(self, data: Dict[str, Any]) -> datetime:
        """Extract timestamp from data, with fallback to current time."""
        timestamp_str = data.get("timestamp")
        if timestamp_str:
            try:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        return datetime.utcnow()

    def _format_context_for_llm(
        self, context_data: List[Dict[str, Any]], max_tokens: int = 2000
    ) -> str:
        """Format context data for LLM consumption with token limit."""
        if not context_data:
            return "No relevant context found."

        formatted_parts = []
        total_chars = 0

        for item in context_data:
            # Format each context item
            if "message" in item:
                formatted = f"- {item['message']}"
            elif "content" in item:
                formatted = f"- {item['content']}"
            elif "text" in item:
                formatted = f"- {item['text']}"
            else:
                formatted = f"- {self._serialize_data(item)}"

            # Add timestamp if available
            if "timestamp" in item:
                formatted += f" ({item['timestamp']})"

            # Check token limit (rough approximation: 4 chars per token)
            if total_chars + len(formatted) > max_tokens * 4:
                break

            formatted_parts.append(formatted)
            total_chars += len(formatted)

        return "\n".join(formatted_parts)


__all__ = ["MemoryBase"]
