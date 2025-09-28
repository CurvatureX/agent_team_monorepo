"""
Persistent Working Memory implementation for workflow_engine_v2.

Uses Supabase memory_data table for persistent key-value storage with TTL support.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from .persistent_base import PersistentMemoryBase


class PersistentWorkingMemory(PersistentMemoryBase):
    """Persistent working memory using Supabase memory_data table with TTL support."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.default_ttl = config.get("default_ttl", 3600)  # Default 1 hour
        self.max_ttl = config.get("max_ttl", 86400 * 7)  # Max 1 week
        self.auto_cleanup = config.get("auto_cleanup", True)

    async def _setup_persistent_storage(self) -> None:
        """Setup the persistent working memory storage."""
        # Clean up expired entries on initialization
        if self.auto_cleanup:
            await self._cleanup_expired_entries()

        self.logger.info(
            f"Persistent Working Memory initialized: default_ttl={self.default_ttl}s, "
            f"user_id={self.user_id}, memory_node_id={self.memory_node_id}"
        )

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store key-value data in persistent working memory."""
        try:
            key = data.get("key")
            value = data.get("value")

            if key is None:
                return {"success": False, "error": "Key is required for working memory storage"}

            # Handle TTL
            ttl_seconds = data.get("ttl_seconds", self.default_ttl)
            if ttl_seconds > self.max_ttl:
                ttl_seconds = self.max_ttl

            expires_at = None
            if ttl_seconds > 0:
                expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()

            # Prepare storage data
            memory_data = self._prepare_storage_data(
                {
                    "key": str(key),
                    "value": self._serialize_for_storage(value),
                    "expires_at": expires_at,
                    "metadata": {
                        "ttl_seconds": ttl_seconds,
                        "data_type": type(value).__name__,
                        **data.get("metadata", {}),
                    },
                }
            )

            # Use upsert to handle key conflicts
            result = await self._execute_query(
                table="memory_data", operation="upsert", data=memory_data
            )

            if result["success"]:
                self.logger.debug(f"Stored working memory key '{key}' with TTL {ttl_seconds}s")

                return {
                    "success": True,
                    "key": key,
                    "expires_at": expires_at,
                    "ttl_seconds": ttl_seconds,
                    "storage": "persistent_database",
                }
            else:
                return {"success": False, "error": result["error"]}

        except Exception as e:
            self.logger.error(f"Error storing working memory data: {e}")
            return {"success": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve working memory data, automatically cleaning expired entries."""
        try:
            # Clean expired entries if auto_cleanup is enabled
            if self.auto_cleanup:
                await self._cleanup_expired_entries()

            key = query.get("key")

            if key is not None:
                # Retrieve specific key
                result = await self._execute_query(
                    table="memory_data",
                    operation="select",
                    filters={**self._build_base_filters(), "key": str(key)},
                    select_columns="key,value,expires_at,metadata,created_at",
                )

                if result["success"] and result["data"]:
                    item = result["data"][0]

                    # Check if expired
                    if self._is_expired(item):
                        # Delete expired item
                        await self._delete_key(str(key))
                        return {"success": False, "error": "Key expired", "key": key}

                    value = self._deserialize_from_storage(item["value"])

                    return {
                        "success": True,
                        "key": key,
                        "value": value,
                        "expires_at": item.get("expires_at"),
                        "metadata": item.get("metadata", {}),
                        "created_at": item.get("created_at"),
                        "storage": "persistent_database",
                    }
                else:
                    return {"success": False, "error": "Key not found", "key": key}
            else:
                # Retrieve all keys for this memory node
                result = await self._execute_query(
                    table="memory_data",
                    operation="select",
                    filters=self._build_base_filters(),
                    select_columns="key,value,expires_at,metadata,created_at",
                )

                if not result["success"]:
                    return {"success": False, "error": result["error"], "data": {}}

                # Filter out expired items and build data dictionary
                data_dict = {}
                expired_keys = []

                for item in result["data"]:
                    item_key = item["key"]

                    if self._is_expired(item):
                        expired_keys.append(item_key)
                        continue

                    value = self._deserialize_from_storage(item["value"])
                    data_dict[item_key] = {
                        "value": value,
                        "expires_at": item.get("expires_at"),
                        "metadata": item.get("metadata", {}),
                        "created_at": item.get("created_at"),
                    }

                # Clean up expired keys
                for expired_key in expired_keys:
                    await self._delete_key(expired_key)

                return {
                    "success": True,
                    "data": data_dict,
                    "total_keys": len(data_dict),
                    "expired_keys_cleaned": len(expired_keys),
                    "storage": "persistent_database",
                }

        except Exception as e:
            self.logger.error(f"Error retrieving working memory data: {e}")
            return {"success": False, "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted context from working memory data."""
        try:
            # Retrieve all data
            data_result = await self.retrieve({})

            if not data_result["success"]:
                return data_result

            data_dict = data_result["data"]

            if not data_dict:
                return {
                    "success": True,
                    "context": "No working memory data available.",
                    "key_count": 0,
                    "storage": "persistent_database",
                }

            # Format context based on query parameters
            format_style = query.get("format", "structured")  # structured, compact, list
            include_metadata = query.get("include_metadata", False)
            max_keys = query.get("max_keys", 50)

            # Limit keys if needed
            keys_to_include = list(data_dict.keys())[:max_keys]

            if format_style == "structured":
                context = self._format_structured_context(
                    data_dict, keys_to_include, include_metadata
                )
            elif format_style == "compact":
                context = self._format_compact_context(data_dict, keys_to_include)
            else:  # list
                context = self._format_list_context(data_dict, keys_to_include)

            return {
                "success": True,
                "context": context,
                "key_count": len(keys_to_include),
                "total_keys": len(data_dict),
                "format": format_style,
                "storage": "persistent_database",
            }

        except Exception as e:
            self.logger.error(f"Error getting working memory context: {e}")
            return {"success": False, "error": str(e)}

    def _format_structured_context(
        self, data_dict: Dict[str, Any], keys: List[str], include_metadata: bool
    ) -> str:
        """Format working memory data as structured context."""
        lines = ["Working Memory State:"]

        for key in keys:
            item = data_dict[key]
            value = item["value"]
            expires_at = item.get("expires_at")

            # Format value for display
            if isinstance(value, str):
                display_value = value[:100] + "..." if len(value) > 100 else value
            else:
                display_value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)

            line = f"\n  {key}: {display_value}"

            if expires_at:
                line += f" (expires: {expires_at[:19]})"

            if include_metadata:
                metadata = item.get("metadata", {})
                if metadata:
                    line += f" [meta: {metadata}]"

            lines.append(line)

        return "".join(lines)

    def _format_compact_context(self, data_dict: Dict[str, Any], keys: List[str]) -> str:
        """Format working memory data as compact context."""
        pairs = []
        for key in keys:
            value = data_dict[key]["value"]
            if isinstance(value, str):
                display_value = value[:50] + "..." if len(value) > 50 else value
            else:
                display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)

            pairs.append(f"{key}={display_value}")

        return f"Working Memory: {' | '.join(pairs)}"

    def _format_list_context(self, data_dict: Dict[str, Any], keys: List[str]) -> str:
        """Format working memory data as a simple list."""
        lines = ["Working memory keys:"]
        for key in keys:
            lines.append(f"\n• {key}")

        return "".join(lines)

    async def update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update working memory entry (same as store with upsert)."""
        return await self.store(data)

    async def delete(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Delete working memory entries."""
        try:
            key = query.get("key")

            if key is not None:
                # Delete specific key
                result = await self._delete_key(str(key))
                return result
            else:
                # Delete all keys for this memory node
                result = await self._execute_query(
                    table="memory_data", operation="delete", filters=self._build_base_filters()
                )

                if result["success"]:
                    return {
                        "success": True,
                        "deleted_count": result["count"],
                        "storage": "persistent_database",
                    }
                else:
                    return {"success": False, "error": result["error"]}

        except Exception as e:
            self.logger.error(f"Error deleting working memory data: {e}")
            return {"success": False, "error": str(e)}

    async def clear(self) -> Dict[str, Any]:
        """Clear all working memory data."""
        return await self.delete({})

    async def get_statistics(self) -> Dict[str, Any]:
        """Get working memory statistics."""
        try:
            # Get basic statistics
            result = await self._execute_query(
                table="memory_data",
                operation="select",
                filters=self._build_base_filters(),
                select_columns="""
                    COUNT(*) as total_keys,
                    MIN(created_at) as oldest_entry,
                    MAX(created_at) as newest_entry,
                    COUNT(*) FILTER (WHERE expires_at IS NOT NULL AND expires_at > NOW()) as keys_with_ttl,
                    COUNT(*) FILTER (WHERE expires_at IS NOT NULL AND expires_at <= NOW()) as expired_keys
                """,
            )

            if result["success"] and result["data"]:
                stats = result["data"][0]
                return {
                    "success": True,
                    "statistics": {
                        "total_keys": stats.get("total_keys", 0),
                        "keys_with_ttl": stats.get("keys_with_ttl", 0),
                        "expired_keys": stats.get("expired_keys", 0),
                        "oldest_entry": stats.get("oldest_entry"),
                        "newest_entry": stats.get("newest_entry"),
                        "default_ttl": self.default_ttl,
                        "max_ttl": self.max_ttl,
                    },
                    "storage": "persistent_database",
                }
            else:
                return {
                    "success": True,
                    "statistics": {
                        "total_keys": 0,
                        "keys_with_ttl": 0,
                        "expired_keys": 0,
                        "oldest_entry": None,
                        "newest_entry": None,
                        "default_ttl": self.default_ttl,
                        "max_ttl": self.max_ttl,
                    },
                    "storage": "persistent_database",
                }

        except Exception as e:
            self.logger.error(f"Error getting working memory statistics: {e}")
            return {"success": False, "error": str(e)}

    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """Check if a memory item has expired."""
        expires_at = item.get("expires_at")
        if not expires_at:
            return False  # No expiration set

        try:
            expiry_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            return datetime.utcnow() > expiry_time
        except (ValueError, AttributeError):
            return False  # Invalid expiry format, assume not expired

    async def _delete_key(self, key: str) -> Dict[str, Any]:
        """Delete a specific key from working memory."""
        result = await self._execute_query(
            table="memory_data",
            operation="delete",
            filters={**self._build_base_filters(), "key": key},
        )

        if result["success"]:
            return {
                "success": True,
                "key": key,
                "deleted": result["count"] > 0,
                "storage": "persistent_database",
            }
        else:
            return {"success": False, "error": result["error"], "key": key}

    async def _cleanup_expired_entries(self) -> int:
        """Clean up expired entries and return count of cleaned entries."""
        return await self._cleanup_expired_data("memory_data")

    async def extend_ttl(self, key: str, additional_seconds: int) -> Dict[str, Any]:
        """Extend the TTL of a specific key."""
        try:
            # First, get the current entry
            retrieve_result = await self.retrieve({"key": key})
            if not retrieve_result["success"]:
                return retrieve_result

            current_expires_at = retrieve_result.get("expires_at")
            if not current_expires_at:
                # No TTL set, set one from now
                new_expires_at = (
                    datetime.utcnow() + timedelta(seconds=additional_seconds)
                ).isoformat()
            else:
                # Extend existing TTL
                current_expiry = datetime.fromisoformat(current_expires_at.replace("Z", "+00:00"))
                new_expires_at = (
                    current_expiry + timedelta(seconds=additional_seconds)
                ).isoformat()

                # Respect max TTL
                max_allowed_expiry = datetime.utcnow() + timedelta(seconds=self.max_ttl)
                if (
                    datetime.fromisoformat(new_expires_at.replace("Z", "+00:00"))
                    > max_allowed_expiry
                ):
                    new_expires_at = max_allowed_expiry.isoformat()

            # Update the expires_at field
            result = await self._execute_query(
                table="memory_data",
                operation="update",
                data={"expires_at": new_expires_at},
                filters={**self._build_base_filters(), "key": key},
            )

            if result["success"]:
                return {
                    "success": True,
                    "key": key,
                    "new_expires_at": new_expires_at,
                    "extended_by_seconds": additional_seconds,
                    "storage": "persistent_database",
                }
            else:
                return {"success": False, "error": result["error"]}

        except Exception as e:
            self.logger.error(f"Error extending TTL for key {key}: {e}")
            return {"success": False, "error": str(e)}


__all__ = ["PersistentWorkingMemory"]
