"""
Base class for memory implementations.

Provides common interface and utilities for all memory types.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class MemoryBase(ABC):
    """Base class for all memory implementations."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize memory with configuration."""
        self.config = config
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the memory backend."""
        if not self._initialized:
            await self._setup()
            self._initialized = True

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
            logger.error(f"Memory health check failed: {str(e)}")
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
