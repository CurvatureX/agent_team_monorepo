"""
Working Memory Implementation.

This implements temporary memory for active reasoning and multi-step problem solving:
- Fast Redis-based storage for temporary data
- Automatic TTL management
- Capacity limits with configurable eviction policies
- Namespace isolation for different workflows
- Support for importance-based eviction
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import redis.asyncio as redis

from .base import MemoryBase

logger = logging.getLogger(__name__)


class WorkingMemory(MemoryBase):
    """
    Working Memory with Redis backend for temporary data storage.

    Features:
    - Fast in-memory storage for active reasoning
    - Automatic TTL management
    - Capacity limits with eviction policies
    - Namespace isolation
    - Importance-based prioritization
    - Support for structured data and reasoning chains
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize working memory.

        Args:
            config: Configuration dict with keys:
                - redis_url: Redis connection URL
                - ttl_seconds: Default TTL for items (default: 3600)
                - capacity_limit: Max items per namespace (default: 100)
                - eviction_policy: 'lru', 'fifo', 'importance' (default: 'lru')
                - namespace: Default namespace (default: 'default')
                - enable_reasoning_chain: Track reasoning steps (default: True)
        """
        super().__init__(config)

        # Configuration
        self.ttl_seconds = config.get("ttl_seconds", 3600)
        self.capacity_limit = config.get("capacity_limit", 100)
        self.eviction_policy = config.get("eviction_policy", "lru")
        self.default_namespace = config.get("namespace", "default")
        self.enable_reasoning_chain = config.get("enable_reasoning_chain", True)

        # Redis client
        self.redis_client: Optional[redis.Redis] = None

    async def _setup(self) -> None:
        """Setup Redis connection."""
        try:
            redis_url = self.config.get("redis_url", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)

            # Test connection
            await self.redis_client.ping()

            logger.info("WorkingMemory initialized successfully")

        except Exception as e:
            logger.error(f"Failed to setup WorkingMemory: {str(e)}")
            raise

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store data in working memory.

        Args:
            data: Data dict with keys:
                - operation: 'store', 'update', 'append' (default: 'store')
                - key: Storage key
                - value: Data to store
                - namespace: Namespace (optional, uses default)
                - importance: Importance score 0.0-1.0 (optional, default: 0.5)
                - ttl_seconds: Custom TTL (optional, uses default)
                - reasoning_step: Description of reasoning step (optional)

        Returns:
            Dict with storage confirmation
        """
        await self.initialize()

        try:
            operation = data.get("operation", "store")
            key = data["key"]
            value = data["value"]
            namespace = data.get("namespace", self.default_namespace)
            importance = data.get("importance", 0.5)
            ttl_seconds = data.get("ttl_seconds", self.ttl_seconds)
            reasoning_step = data.get("reasoning_step")

            # Validate importance score
            importance = max(0.0, min(1.0, importance))

            # Create full key with namespace
            full_key = f"wm:{namespace}:{key}"

            # Handle different operations
            if operation == "store":
                result = await self._store_item(full_key, value, importance, ttl_seconds)
            elif operation == "update":
                result = await self._update_item(full_key, value, importance, ttl_seconds)
            elif operation == "append":
                result = await self._append_item(full_key, value, importance, ttl_seconds)
            else:
                raise ValueError(f"Unknown operation: {operation}")

            # Track reasoning step if enabled
            if reasoning_step and self.enable_reasoning_chain:
                await self._add_reasoning_step(namespace, reasoning_step, key, operation)

            # Maintain capacity limits
            await self._maintain_capacity(namespace)

            logger.debug(f"Stored item {key} in namespace {namespace} with importance {importance}")

            return {
                "stored": True,
                "operation": operation,
                "key": key,
                "namespace": namespace,
                "importance": importance,
                "ttl_seconds": ttl_seconds,
                "stored_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to store working memory item: {str(e)}")
            raise

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve data from working memory.

        Args:
            query: Query dict with keys:
                - key: Storage key (optional)
                - namespace: Namespace (optional, uses default)
                - pattern: Key pattern for bulk retrieval (optional)
                - include_metadata: Include item metadata (optional, default: True)

        Returns:
            Dict with retrieved data
        """
        await self.initialize()

        try:
            key = query.get("key")
            namespace = query.get("namespace", self.default_namespace)
            pattern = query.get("pattern")
            include_metadata = query.get("include_metadata", True)

            if key:
                # Retrieve single item
                full_key = f"wm:{namespace}:{key}"
                item_data = await self._get_item(full_key, include_metadata)

                if item_data is None:
                    return {"found": False, "key": key, "namespace": namespace}

                return {
                    "found": True,
                    "key": key,
                    "namespace": namespace,
                    "value": item_data["value"],
                    "metadata": item_data.get("metadata", {}) if include_metadata else {},
                    "retrieved_at": datetime.utcnow().isoformat(),
                }

            elif pattern:
                # Retrieve multiple items by pattern
                search_pattern = f"wm:{namespace}:{pattern}"
                items = await self._get_items_by_pattern(search_pattern, include_metadata)

                return {
                    "items": items,
                    "total_count": len(items),
                    "namespace": namespace,
                    "pattern": pattern,
                    "retrieved_at": datetime.utcnow().isoformat(),
                }

            else:
                # Retrieve all items in namespace
                all_items = await self._get_all_items(namespace, include_metadata)

                return {
                    "items": all_items,
                    "total_count": len(all_items),
                    "namespace": namespace,
                    "retrieved_at": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to retrieve working memory data: {str(e)}")
            raise

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get formatted working memory context for LLM consumption.

        Args:
            query: Query dict with keys:
                - namespace: Namespace to get context from
                - max_items: Maximum items to include (optional, default: 20)
                - min_importance: Minimum importance score (optional, default: 0.0)
                - include_reasoning_chain: Include reasoning steps (optional, default: True)

        Returns:
            Dict with formatted context for LLM
        """
        await self.initialize()

        try:
            namespace = query.get("namespace", self.default_namespace)
            max_items = query.get("max_items", 20)
            min_importance = query.get("min_importance", 0.0)
            include_reasoning_chain = query.get("include_reasoning_chain", True)

            # Get all items in namespace
            all_items = await self._get_all_items(namespace, include_metadata=True)

            # Filter by importance
            filtered_items = [
                item
                for item in all_items
                if item.get("metadata", {}).get("importance", 0.0) >= min_importance
            ]

            # Sort by importance (descending) and recency
            filtered_items.sort(
                key=lambda x: (
                    x.get("metadata", {}).get("importance", 0.0),
                    x.get("metadata", {}).get("stored_at", ""),
                ),
                reverse=True,
            )

            # Limit results
            recent_items = filtered_items[:max_items]

            # Format current state
            current_state = {}
            for item in recent_items:
                current_state[item["key"]] = {
                    "value": item["value"],
                    "importance": item.get("metadata", {}).get("importance", 0.0),
                    "stored_at": item.get("metadata", {}).get("stored_at"),
                }

            # Get reasoning chain if enabled
            reasoning_chain = []
            if include_reasoning_chain and self.enable_reasoning_chain:
                reasoning_chain = await self._get_reasoning_chain(namespace)

            # Calculate summary statistics
            total_items = len(all_items)
            avg_importance = sum(
                item.get("metadata", {}).get("importance", 0.0) for item in all_items
            ) / max(1, total_items)

            return {
                "current_state": current_state,
                "recent_items": [
                    {
                        "key": item["key"],
                        "value": item["value"],
                        "importance": item.get("metadata", {}).get("importance", 0.0),
                    }
                    for item in recent_items
                ],
                "reasoning_chain": reasoning_chain,
                "namespace": namespace,
                "total_items": total_items,
                "active_items": len(recent_items),
                "avg_importance": avg_importance,
                "context_generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get working memory context: {str(e)}")
            raise

    async def _store_item(
        self, full_key: str, value: Any, importance: float, ttl_seconds: int
    ) -> bool:
        """Store an item with metadata."""
        item_data = {
            "value": value,
            "metadata": {
                "importance": importance,
                "stored_at": datetime.utcnow().isoformat(),
                "access_count": 0,
                "last_accessed": datetime.utcnow().isoformat(),
            },
        }

        serialized_data = self._serialize_data(item_data)
        await self.redis_client.setex(full_key, ttl_seconds, serialized_data)
        return True

    async def _update_item(
        self, full_key: str, value: Any, importance: float, ttl_seconds: int
    ) -> bool:
        """Update an existing item or create if doesn't exist."""
        existing_data = await self._get_item(full_key, include_metadata=True)

        if existing_data:
            # Update existing item
            metadata = existing_data.get("metadata", {})
            metadata.update(
                {
                    "importance": importance,
                    "last_updated": datetime.utcnow().isoformat(),
                    "update_count": metadata.get("update_count", 0) + 1,
                }
            )
        else:
            # Create new item
            metadata = {
                "importance": importance,
                "stored_at": datetime.utcnow().isoformat(),
                "access_count": 0,
                "last_accessed": datetime.utcnow().isoformat(),
            }

        item_data = {"value": value, "metadata": metadata}

        serialized_data = self._serialize_data(item_data)
        await self.redis_client.setex(full_key, ttl_seconds, serialized_data)
        return True

    async def _append_item(
        self, full_key: str, value: Any, importance: float, ttl_seconds: int
    ) -> bool:
        """Append to an existing item (assumes item value is a list)."""
        existing_data = await self._get_item(full_key, include_metadata=True)

        if existing_data:
            existing_value = existing_data["value"]
            if isinstance(existing_value, list):
                new_value = existing_value + [value]
            else:
                new_value = [existing_value, value]

            metadata = existing_data.get("metadata", {})
            metadata.update(
                {
                    "importance": max(importance, metadata.get("importance", 0.0)),
                    "last_updated": datetime.utcnow().isoformat(),
                    "append_count": metadata.get("append_count", 0) + 1,
                }
            )
        else:
            new_value = [value]
            metadata = {
                "importance": importance,
                "stored_at": datetime.utcnow().isoformat(),
                "access_count": 0,
                "last_accessed": datetime.utcnow().isoformat(),
            }

        item_data = {"value": new_value, "metadata": metadata}

        serialized_data = self._serialize_data(item_data)
        await self.redis_client.setex(full_key, ttl_seconds, serialized_data)
        return True

    async def _get_item(
        self, full_key: str, include_metadata: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get a single item."""
        data = await self.redis_client.get(full_key)

        if data is None:
            return None

        try:
            item_data = self._deserialize_data(data)

            # Update access statistics
            if include_metadata and isinstance(item_data, dict) and "metadata" in item_data:
                metadata = item_data["metadata"]
                metadata["access_count"] = metadata.get("access_count", 0) + 1
                metadata["last_accessed"] = datetime.utcnow().isoformat()

                # Update in Redis
                updated_data = self._serialize_data(item_data)
                await self.redis_client.set(full_key, updated_data, keepttl=True)

            return item_data

        except Exception as e:
            logger.warning(f"Failed to deserialize item {full_key}: {str(e)}")
            return None

    async def _get_items_by_pattern(
        self, pattern: str, include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """Get multiple items by key pattern."""
        keys = await self.redis_client.keys(pattern)
        items = []

        for key in keys:
            item_data = await self._get_item(key, include_metadata)
            if item_data:
                # Extract actual key from full key
                actual_key = key.split(":", 2)[-1] if ":" in key else key
                items.append(
                    {
                        "key": actual_key,
                        "value": item_data.get("value"),
                        "metadata": item_data.get("metadata", {}) if include_metadata else {},
                    }
                )

        return items

    async def _get_all_items(
        self, namespace: str, include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all items in a namespace."""
        pattern = f"wm:{namespace}:*"
        return await self._get_items_by_pattern(pattern, include_metadata)

    async def _maintain_capacity(self, namespace: str) -> None:
        """Maintain capacity limits by evicting items if necessary."""
        pattern = f"wm:{namespace}:*"
        keys = await self.redis_client.keys(pattern)

        if len(keys) <= self.capacity_limit:
            return

        # Need to evict items
        items_to_evict = len(keys) - self.capacity_limit

        if self.eviction_policy == "importance":
            await self._evict_by_importance(keys, items_to_evict)
        elif self.eviction_policy == "fifo":
            await self._evict_by_fifo(keys, items_to_evict)
        else:  # lru
            await self._evict_by_lru(keys, items_to_evict)

    async def _evict_by_importance(self, keys: List[str], count: int) -> None:
        """Evict items with lowest importance scores."""
        items_with_importance = []

        for key in keys:
            item_data = await self._get_item(key, include_metadata=True)
            if item_data:
                importance = item_data.get("metadata", {}).get("importance", 0.0)
                items_with_importance.append((key, importance))

        # Sort by importance (ascending) and evict lowest
        items_with_importance.sort(key=lambda x: x[1])
        keys_to_evict = [item[0] for item in items_with_importance[:count]]

        if keys_to_evict:
            await self.redis_client.delete(*keys_to_evict)

    async def _evict_by_fifo(self, keys: List[str], count: int) -> None:
        """Evict oldest items first."""
        items_with_age = []

        for key in keys:
            item_data = await self._get_item(key, include_metadata=True)
            if item_data:
                stored_at = item_data.get("metadata", {}).get("stored_at", "")
                items_with_age.append((key, stored_at))

        # Sort by stored_at (ascending) and evict oldest
        items_with_age.sort(key=lambda x: x[1])
        keys_to_evict = [item[0] for item in items_with_age[:count]]

        if keys_to_evict:
            await self.redis_client.delete(*keys_to_evict)

    async def _evict_by_lru(self, keys: List[str], count: int) -> None:
        """Evict least recently used items."""
        items_with_access = []

        for key in keys:
            item_data = await self._get_item(key, include_metadata=True)
            if item_data:
                last_accessed = item_data.get("metadata", {}).get("last_accessed", "")
                items_with_access.append((key, last_accessed))

        # Sort by last_accessed (ascending) and evict least recent
        items_with_access.sort(key=lambda x: x[1])
        keys_to_evict = [item[0] for item in items_with_access[:count]]

        if keys_to_evict:
            await self.redis_client.delete(*keys_to_evict)

    async def _add_reasoning_step(
        self, namespace: str, step: str, key: str, operation: str
    ) -> None:
        """Add a reasoning step to the chain."""
        reasoning_key = f"wm:reasoning:{namespace}"

        step_data = {
            "step": step,
            "key": key,
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add to list (keep last 50 steps)
        await self.redis_client.lpush(reasoning_key, json.dumps(step_data))
        await self.redis_client.ltrim(reasoning_key, 0, 49)
        await self.redis_client.expire(reasoning_key, self.ttl_seconds)

    async def _get_reasoning_chain(self, namespace: str) -> List[Dict[str, Any]]:
        """Get the reasoning chain for a namespace."""
        reasoning_key = f"wm:reasoning:{namespace}"

        chain_data = await self.redis_client.lrange(reasoning_key, 0, -1)
        reasoning_chain = []

        for item in reversed(chain_data):  # Reverse to get chronological order
            try:
                step_data = json.loads(item)
                reasoning_chain.append(step_data)
            except json.JSONDecodeError:
                continue

        return reasoning_chain

    async def clear_namespace(self, namespace: str) -> Dict[str, Any]:
        """Clear all data in a namespace."""
        await self.initialize()

        try:
            # Clear working memory items
            pattern = f"wm:{namespace}:*"
            keys = await self.redis_client.keys(pattern)

            # Clear reasoning chain
            reasoning_key = f"wm:reasoning:{namespace}"
            keys.append(reasoning_key)

            deleted_count = 0
            if keys:
                deleted_count = await self.redis_client.delete(*keys)

            return {
                "cleared": True,
                "namespace": namespace,
                "deleted_count": deleted_count,
                "cleared_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to clear namespace: {str(e)}")
            raise

    async def get_namespace_stats(self, namespace: str) -> Dict[str, Any]:
        """Get statistics for a namespace."""
        await self.initialize()

        try:
            items = await self._get_all_items(namespace, include_metadata=True)

            if not items:
                return {
                    "namespace": namespace,
                    "total_items": 0,
                    "analyzed_at": datetime.utcnow().isoformat(),
                }

            # Calculate statistics
            total_items = len(items)
            importance_scores = [item.get("metadata", {}).get("importance", 0.0) for item in items]
            avg_importance = sum(importance_scores) / total_items

            # Access statistics
            access_counts = [item.get("metadata", {}).get("access_count", 0) for item in items]
            total_accesses = sum(access_counts)

            return {
                "namespace": namespace,
                "total_items": total_items,
                "avg_importance": avg_importance,
                "importance_distribution": {
                    "min": min(importance_scores),
                    "max": max(importance_scores),
                    "high_importance_items": len([s for s in importance_scores if s >= 0.7]),
                },
                "access_statistics": {
                    "total_accesses": total_accesses,
                    "avg_accesses_per_item": total_accesses / total_items,
                    "most_accessed": max(access_counts),
                    "least_accessed": min(access_counts),
                },
                "capacity_usage": {
                    "current_items": total_items,
                    "capacity_limit": self.capacity_limit,
                    "usage_percentage": (total_items / self.capacity_limit) * 100,
                },
                "analyzed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get namespace stats: {str(e)}")
            raise
