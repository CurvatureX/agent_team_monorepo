"""
Key-Value Store Memory implementation for workflow_engine_v2.

Provides simple key-value storage with optional persistence.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.supabase import create_supabase_client

from .base import MemoryBase


class KeyValueStoreMemory(MemoryBase):
    """Key-Value Store memory implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.store = {}  # In-memory fallback
        self.supabase = None
        self.use_persistence = config.get("use_persistence", False)
        self.namespace = config.get("namespace", "default")

    async def _setup(self) -> None:
        """Setup the key-value store."""
        if self.use_persistence:
            try:
                self.supabase = create_supabase_client()
                if self.supabase:
                    self.logger.info("Key-Value Store: Using Supabase for persistence")
                else:
                    self.logger.warning(
                        "Key-Value Store: Supabase not available, using in-memory only"
                    )
                    self.use_persistence = False
            except Exception as e:
                self.logger.warning(f"Key-Value Store: Failed to setup persistence: {e}")
                self.use_persistence = False

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store key-value pairs."""
        try:
            key = data.get("key")
            value = data.get("value")

            if not key:
                return {"success": False, "error": "Missing 'key' in data"}

            # Create storage entry
            entry = {
                "value": value,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": data.get("metadata", {}),
            }

            # Store in memory
            storage_key = self._create_storage_key(self.namespace, key)
            self.store[storage_key] = entry

            # Store in database if persistence enabled
            if self.use_persistence and self.supabase:
                try:
                    record = {
                        "namespace": self.namespace,
                        "key": key,
                        "value": self._serialize_data(value),
                        "metadata": entry["metadata"],
                        "created_at": entry["timestamp"],
                    }

                    # Upsert the record
                    result = self.supabase.table("memory_key_value").upsert(record).execute()

                    if not result.data:
                        self.logger.warning(f"Failed to persist key-value: {key}")

                except Exception as e:
                    self.logger.error(f"Error persisting key-value {key}: {e}")

            self.logger.debug(f"Stored key-value: {key}")
            return {
                "success": True,
                "key": key,
                "stored_at": entry["timestamp"],
            }

        except Exception as e:
            self.logger.error(f"Error storing key-value: {e}")
            return {"success": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve value by key."""
        try:
            key = query.get("key")

            if not key:
                return {"success": False, "error": "Missing 'key' in query"}

            storage_key = self._create_storage_key(self.namespace, key)

            # Try in-memory store first
            if storage_key in self.store:
                entry = self.store[storage_key]
                return {
                    "success": True,
                    "key": key,
                    "value": entry["value"],
                    "timestamp": entry["timestamp"],
                    "metadata": entry["metadata"],
                }

            # Try database if persistence enabled
            if self.use_persistence and self.supabase:
                try:
                    result = (
                        self.supabase.table("memory_key_value")
                        .select("*")
                        .eq("namespace", self.namespace)
                        .eq("key", key)
                        .order("created_at", desc=True)
                        .limit(1)
                        .execute()
                    )

                    if result.data:
                        record = result.data[0]
                        value = self._deserialize_data(record["value"])

                        # Cache in memory
                        entry = {
                            "value": value,
                            "timestamp": record["created_at"],
                            "metadata": record.get("metadata", {}),
                        }
                        self.store[storage_key] = entry

                        return {
                            "success": True,
                            "key": key,
                            "value": value,
                            "timestamp": record["created_at"],
                            "metadata": record.get("metadata", {}),
                        }

                except Exception as e:
                    self.logger.error(f"Error retrieving from database: {e}")

            return {"success": False, "error": f"Key not found: {key}"}

        except Exception as e:
            self.logger.error(f"Error retrieving key-value: {e}")
            return {"success": False, "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted context for LLM."""
        try:
            key = query.get("key")
            pattern = query.get("pattern")  # For pattern matching
            limit = query.get("limit", 10)

            context_items = []

            if key:
                # Get specific key
                result = await self.retrieve({"key": key})
                if result.get("success"):
                    context_items.append(
                        {
                            "key": key,
                            "value": result["value"],
                            "timestamp": result["timestamp"],
                        }
                    )
            elif pattern:
                # Pattern matching (simple contains)
                for storage_key, entry in self.store.items():
                    if self.namespace in storage_key:
                        actual_key = storage_key.split(":", 1)[1]
                        if pattern.lower() in actual_key.lower():
                            context_items.append(
                                {
                                    "key": actual_key,
                                    "value": entry["value"],
                                    "timestamp": entry["timestamp"],
                                }
                            )

                            if len(context_items) >= limit:
                                break
            else:
                # Get all keys in namespace
                for storage_key, entry in self.store.items():
                    if self.namespace in storage_key:
                        actual_key = storage_key.split(":", 1)[1]
                        context_items.append(
                            {
                                "key": actual_key,
                                "value": entry["value"],
                                "timestamp": entry["timestamp"],
                            }
                        )

                        if len(context_items) >= limit:
                            break

            # Format for LLM
            if not context_items:
                formatted_context = "No stored values found."
            else:
                context_lines = []
                for item in context_items:
                    context_lines.append(f"{item['key']}: {item['value']}")

                formatted_context = "Stored Values:\n" + "\n".join(context_lines)

            return {
                "success": True,
                "context": formatted_context,
                "raw_items": context_items,
                "count": len(context_items),
            }

        except Exception as e:
            self.logger.error(f"Error getting context: {e}")
            return {"success": False, "error": str(e)}

    async def delete(self, key: str) -> Dict[str, Any]:
        """Delete a key-value pair."""
        try:
            storage_key = self._create_storage_key(self.namespace, key)

            # Remove from memory
            existed_in_memory = storage_key in self.store
            if existed_in_memory:
                del self.store[storage_key]

            # Remove from database if persistence enabled
            deleted_from_db = False
            if self.use_persistence and self.supabase:
                try:
                    result = (
                        self.supabase.table("memory_key_value")
                        .delete()
                        .eq("namespace", self.namespace)
                        .eq("key", key)
                        .execute()
                    )

                    deleted_from_db = bool(result.data)

                except Exception as e:
                    self.logger.error(f"Error deleting from database: {e}")

            success = existed_in_memory or deleted_from_db
            return {
                "success": success,
                "key": key,
                "deleted_from_memory": existed_in_memory,
                "deleted_from_db": deleted_from_db,
            }

        except Exception as e:
            self.logger.error(f"Error deleting key-value: {e}")
            return {"success": False, "error": str(e)}

    async def list_keys(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        """List all keys in the namespace."""
        try:
            keys = []

            # Get keys from memory
            for storage_key in self.store.keys():
                if self.namespace in storage_key:
                    actual_key = storage_key.split(":", 1)[1]
                    if not pattern or pattern.lower() in actual_key.lower():
                        keys.append(actual_key)

            # Get additional keys from database if persistence enabled
            if self.use_persistence and self.supabase:
                try:
                    query = (
                        self.supabase.table("memory_key_value")
                        .select("key")
                        .eq("namespace", self.namespace)
                    )

                    if pattern:
                        query = query.ilike("key", f"%{pattern}%")

                    result = query.execute()

                    for record in result.data:
                        key = record["key"]
                        if key not in keys:
                            keys.append(key)

                except Exception as e:
                    self.logger.error(f"Error listing keys from database: {e}")

            return {
                "success": True,
                "keys": sorted(keys),
                "count": len(keys),
                "namespace": self.namespace,
            }

        except Exception as e:
            self.logger.error(f"Error listing keys: {e}")
            return {"success": False, "error": str(e)}

    async def clear_namespace(self) -> Dict[str, Any]:
        """Clear all keys in the current namespace."""
        try:
            # Clear from memory
            keys_to_remove = [k for k in self.store.keys() if self.namespace in k]
            for key in keys_to_remove:
                del self.store[key]

            memory_count = len(keys_to_remove)

            # Clear from database if persistence enabled
            db_count = 0
            if self.use_persistence and self.supabase:
                try:
                    result = (
                        self.supabase.table("memory_key_value")
                        .delete()
                        .eq("namespace", self.namespace)
                        .execute()
                    )

                    db_count = len(result.data) if result.data else 0

                except Exception as e:
                    self.logger.error(f"Error clearing namespace from database: {e}")

            self.logger.info(
                f"Cleared namespace {self.namespace}: {memory_count} from memory, {db_count} from database"
            )

            return {
                "success": True,
                "namespace": self.namespace,
                "cleared_from_memory": memory_count,
                "cleared_from_db": db_count,
            }

        except Exception as e:
            self.logger.error(f"Error clearing namespace: {e}")
            return {"success": False, "error": str(e)}


__all__ = ["KeyValueStoreMemory"]
