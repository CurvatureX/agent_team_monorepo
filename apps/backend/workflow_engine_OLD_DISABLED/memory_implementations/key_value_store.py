"""
Key-Value Store Memory Implementation.

This implements key-value storage with Redis + PostgreSQL backup:
- Fast Redis storage for frequently accessed data
- PostgreSQL persistence for durability
- Automatic synchronization between stores
- TTL management and compression support
"""

import asyncio
import json
import logging
import zlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis
from supabase import Client, create_client

from .base import MemoryBase

logger = logging.getLogger(__name__)


class KeyValueStoreMemory(MemoryBase):
    """
    Key-Value Store Memory with Redis + PostgreSQL backend.

    Features:
    - Fast Redis cache for active data
    - PostgreSQL backup for persistence
    - Automatic JSON serialization
    - Optional compression for large values
    - TTL support with automatic cleanup
    - Namespace isolation
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize key-value store memory.

        Args:
            config: Configuration dict with keys:
                - redis_url: Redis connection URL
                - supabase_url: Supabase project URL
                - supabase_key: Supabase service key
                - namespace: Default namespace (default: 'default')
                - serialize_json: Auto serialize/deserialize JSON (default: True)
                - compression: Enable compression for large values (default: False)
                - compression_threshold: Size threshold for compression in bytes (default: 1024)
                - sync_to_postgres: Enable PostgreSQL backup (default: True)
        """
        super().__init__(config)

        # Configuration
        self.default_namespace = config.get("namespace", "default")
        self.serialize_json = config.get("serialize_json", True)
        self.compression = config.get("compression", False)
        self.compression_threshold = config.get("compression_threshold", 1024)
        self.sync_to_postgres = config.get("sync_to_postgres", True)

        # Clients
        self.redis_client: Optional[redis.Redis] = None
        self.supabase_client: Optional[Client] = None

    async def _setup(self) -> None:
        """Setup Redis and Supabase connections."""
        try:
            # Setup Redis
            redis_url = self.config.get("redis_url", "redis://localhost:6379")
            self.redis_client = redis.from_url(
                redis_url, decode_responses=False
            )  # Binary mode for compression

            await self.redis_client.ping()
            logger.info("Redis connection established for KeyValueStoreMemory")

            # Setup Supabase if sync enabled
            if self.sync_to_postgres:
                supabase_url = self.config["supabase_url"]
                supabase_key = self.config["supabase_key"]
                self.supabase_client = create_client(supabase_url, supabase_key)

                logger.info("Supabase connection established for KeyValueStoreMemory")

        except Exception as e:
            logger.error(f"Failed to setup KeyValueStoreMemory: {str(e)}")
            raise

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store key-value data.

        Args:
            data: Data dict with keys:
                - key: Storage key
                - value: Value to store
                - operation: 'set', 'update', 'increment' (default: 'set')
                - namespace: Namespace (optional)
                - ttl_seconds: Time-to-live in seconds (optional)
                - metadata: Additional metadata (optional)

        Returns:
            Dict with storage confirmation
        """
        await self.initialize()

        try:
            key = data["key"]
            value = data["value"]
            operation = data.get("operation", "set")
            namespace = data.get("namespace", self.default_namespace)
            ttl_seconds = data.get("ttl_seconds")
            metadata = data.get("metadata", {})

            # Create namespaced key
            full_key = f"kv:{namespace}:{key}"

            # Handle different operations
            if operation == "set":
                result_value = await self._set_value(full_key, value, ttl_seconds, metadata)
            elif operation == "update":
                result_value = await self._update_value(full_key, value, ttl_seconds, metadata)
            elif operation == "increment":
                result_value = await self._increment_value(full_key, value, ttl_seconds, metadata)
            else:
                raise ValueError(f"Unknown operation: {operation}")

            # Sync to PostgreSQL if enabled
            if self.sync_to_postgres:
                await self._sync_to_postgres(namespace, key, result_value, metadata, ttl_seconds)

            logger.debug(f"Stored key-value {key} in namespace {namespace}")

            return {
                "stored": True,
                "key": key,
                "namespace": namespace,
                "operation": operation,
                "value": result_value,
                "ttl_seconds": ttl_seconds,
                "stored_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to store key-value data: {str(e)}")
            raise

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve key-value data.

        Args:
            query: Query dict with keys:
                - key: Storage key
                - namespace: Namespace (optional)
                - default_value: Default value if key not found (optional)

        Returns:
            Dict with retrieved data
        """
        await self.initialize()

        try:
            key = query["key"]
            namespace = query.get("namespace", self.default_namespace)
            default_value = query.get("default_value")

            full_key = f"kv:{namespace}:{key}"

            # Try Redis first
            value = await self._get_from_redis(full_key)

            # If not in Redis and PostgreSQL sync is enabled, try PostgreSQL
            if value is None and self.sync_to_postgres:
                value = await self._get_from_postgres(namespace, key)

                # If found in PostgreSQL, restore to Redis
                if value is not None:
                    await self._set_value(full_key, value, None, {})

            # Use default value if not found
            if value is None:
                value = default_value
                found = False
            else:
                found = True

            return {
                "found": found,
                "key": key,
                "namespace": namespace,
                "value": value,
                "retrieved_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to retrieve key-value data: {str(e)}")
            raise

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get key-value context for LLM consumption.

        Args:
            query: Query dict with keys:
                - keys: List of keys to retrieve (optional)
                - namespace: Namespace (optional)
                - pattern: Key pattern for bulk retrieval (optional)
                - max_items: Maximum items to return (optional, default: 50)

        Returns:
            Dict with formatted context for LLM
        """
        await self.initialize()

        try:
            keys = query.get("keys", [])
            namespace = query.get("namespace", self.default_namespace)
            pattern = query.get("pattern")
            max_items = query.get("max_items", 50)

            context_data = {}

            if keys:
                # Retrieve specific keys
                for key in keys[:max_items]:
                    result = await self.retrieve({"key": key, "namespace": namespace})
                    if result["found"]:
                        context_data[key] = result["value"]

            elif pattern:
                # Retrieve by pattern
                full_pattern = f"kv:{namespace}:{pattern}"
                matching_keys = await self.redis_client.keys(full_pattern)

                for full_key in matching_keys[:max_items]:
                    key = full_key.decode("utf-8").split(":", 2)[-1]
                    value = await self._get_from_redis(full_key)
                    if value is not None:
                        context_data[key] = value

            else:
                # Retrieve all keys in namespace
                full_pattern = f"kv:{namespace}:*"
                matching_keys = await self.redis_client.keys(full_pattern)

                for full_key in matching_keys[:max_items]:
                    key = full_key.decode("utf-8").split(":", 2)[-1]
                    value = await self._get_from_redis(full_key)
                    if value is not None:
                        context_data[key] = value

            return {
                "context_data": context_data,
                "namespace": namespace,
                "total_items": len(context_data),
                "context_generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get key-value context: {str(e)}")
            raise

    async def _set_value(
        self, full_key: str, value: Any, ttl_seconds: Optional[int], metadata: Dict[str, Any]
    ) -> Any:
        """Set a value in Redis."""
        # Prepare data
        data = {"value": value, "metadata": metadata, "stored_at": datetime.utcnow().isoformat()}

        # Serialize and optionally compress
        serialized_data = await self._serialize_and_compress(data)

        # Store in Redis
        if ttl_seconds:
            await self.redis_client.setex(full_key, ttl_seconds, serialized_data)
        else:
            await self.redis_client.set(full_key, serialized_data)

        return value

    async def _update_value(
        self, full_key: str, value: Any, ttl_seconds: Optional[int], metadata: Dict[str, Any]
    ) -> Any:
        """Update an existing value or create if not exists."""
        existing_data = await self._get_from_redis(full_key, include_metadata=True)

        if existing_data and isinstance(existing_data, dict) and "value" in existing_data:
            # Update existing
            if isinstance(existing_data["value"], dict) and isinstance(value, dict):
                # Merge dictionaries
                updated_value = {**existing_data["value"], **value}
            else:
                # Replace value
                updated_value = value
        else:
            # Create new
            updated_value = value

        return await self._set_value(full_key, updated_value, ttl_seconds, metadata)

    async def _increment_value(
        self,
        full_key: str,
        increment: Union[int, float],
        ttl_seconds: Optional[int],
        metadata: Dict[str, Any],
    ) -> Union[int, float]:
        """Increment a numeric value."""
        # Try atomic increment first
        try:
            if isinstance(increment, int):
                result = await self.redis_client.incrby(full_key, increment)
                return result
            else:
                result = await self.redis_client.incrbyfloat(full_key, increment)
                return result
        except:
            # Fallback to manual increment
            existing_data = await self._get_from_redis(full_key)
            current_value = 0

            if existing_data is not None:
                if isinstance(existing_data, (int, float)):
                    current_value = existing_data
                elif isinstance(existing_data, dict) and "value" in existing_data:
                    current_value = (
                        existing_data["value"]
                        if isinstance(existing_data["value"], (int, float))
                        else 0
                    )

            new_value = current_value + increment
            await self._set_value(full_key, new_value, ttl_seconds, metadata)
            return new_value

    async def _get_from_redis(self, full_key: str, include_metadata: bool = False) -> Any:
        """Get value from Redis."""
        try:
            raw_data = await self.redis_client.get(full_key)
            if raw_data is None:
                return None

            # Decompress and deserialize
            data = await self._decompress_and_deserialize(raw_data)

            if include_metadata:
                return data
            else:
                # Extract just the value
                if isinstance(data, dict) and "value" in data:
                    return data["value"]
                else:
                    return data

        except Exception as e:
            logger.warning(f"Failed to get from Redis {full_key}: {str(e)}")
            return None

    async def _serialize_and_compress(self, data: Any) -> bytes:
        """Serialize data and optionally compress."""
        if self.serialize_json:
            serialized = json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")
        else:
            serialized = str(data).encode("utf-8")

        # Compress if enabled and data is large enough
        if self.compression and len(serialized) > self.compression_threshold:
            compressed = zlib.compress(serialized)
            # Prefix with compression marker
            return b"COMPRESSED:" + compressed

        return serialized

    async def _decompress_and_deserialize(self, data: bytes) -> Any:
        """Decompress and deserialize data."""
        # Check for compression marker
        if data.startswith(b"COMPRESSED:"):
            data = zlib.decompress(data[11:])  # Remove 'COMPRESSED:' prefix

        # Deserialize
        try:
            text_data = data.decode("utf-8")
            if self.serialize_json:
                return json.loads(text_data)
            else:
                return text_data
        except:
            # Fallback to string
            return data.decode("utf-8", errors="ignore")

    async def _sync_to_postgres(
        self,
        namespace: str,
        key: str,
        value: Any,
        metadata: Dict[str, Any],
        ttl_seconds: Optional[int],
    ) -> None:
        """Sync data to PostgreSQL."""
        if not self.supabase_client:
            return

        try:
            # Calculate expiration time
            expires_at = None
            if ttl_seconds:
                expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()

            # Prepare data for PostgreSQL
            # Note: We need to create the kv_memory table in the database migrations
            pg_data = {
                "key": f"{namespace}:{key}",
                "value": value,
                "metadata": metadata,
                "expires_at": expires_at,
            }

            # Upsert to PostgreSQL
            result = (
                self.supabase_client.table("kv_memory").upsert(pg_data, on_conflict="key").execute()
            )

        except Exception as e:
            logger.warning(f"Failed to sync to PostgreSQL: {str(e)}")

    async def _get_from_postgres(self, namespace: str, key: str) -> Any:
        """Get value from PostgreSQL."""
        if not self.supabase_client:
            return None

        try:
            full_key = f"{namespace}:{key}"
            result = (
                self.supabase_client.table("kv_memory")
                .select("value, expires_at")
                .eq("key", full_key)
                .single()
                .execute()
            )

            if not result.data:
                return None

            # Check expiration
            expires_at = result.data.get("expires_at")
            if expires_at:
                expiry_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.utcnow().replace(tzinfo=expiry_time.tzinfo) > expiry_time:
                    # Expired, delete from PostgreSQL
                    self.supabase_client.table("kv_memory").delete().eq("key", full_key).execute()
                    return None

            return result.data["value"]

        except Exception as e:
            logger.warning(f"Failed to get from PostgreSQL: {str(e)}")
            return None

    async def delete_key(self, key: str, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Delete a key from both Redis and PostgreSQL."""
        await self.initialize()

        try:
            namespace = namespace or self.default_namespace
            full_key = f"kv:{namespace}:{key}"

            # Delete from Redis
            deleted_from_redis = await self.redis_client.delete(full_key)

            # Delete from PostgreSQL if sync enabled
            deleted_from_postgres = 0
            if self.sync_to_postgres and self.supabase_client:
                result = (
                    self.supabase_client.table("kv_memory")
                    .delete()
                    .eq("key", f"{namespace}:{key}")
                    .execute()
                )
                deleted_from_postgres = len(result.data) if result.data else 0

            return {
                "deleted": True,
                "key": key,
                "namespace": namespace,
                "deleted_from_redis": bool(deleted_from_redis),
                "deleted_from_postgres": bool(deleted_from_postgres),
                "deleted_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to delete key: {str(e)}")
            raise

    async def list_keys(
        self, namespace: Optional[str] = None, pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """List all keys in a namespace."""
        await self.initialize()

        try:
            namespace = namespace or self.default_namespace

            if pattern:
                search_pattern = f"kv:{namespace}:{pattern}"
            else:
                search_pattern = f"kv:{namespace}:*"

            redis_keys = await self.redis_client.keys(search_pattern)

            # Extract actual keys (remove namespace prefix)
            actual_keys = []
            for key in redis_keys:
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                actual_key = key_str.split(":", 2)[-1]
                actual_keys.append(actual_key)

            return {
                "keys": sorted(actual_keys),
                "total_count": len(actual_keys),
                "namespace": namespace,
                "pattern": pattern,
                "listed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to list keys: {str(e)}")
            raise
