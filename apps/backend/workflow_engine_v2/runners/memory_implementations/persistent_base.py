"""
Persistent Memory Base Class for workflow_engine_v2.

Provides database-backed persistent storage using Supabase for all memory implementations.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from abc import abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from supabase import Client, create_client

from .base import MemoryBase

logger = logging.getLogger(__name__)


class PersistentMemoryBase(MemoryBase):
    """Base class for persistent memory implementations using Supabase."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize persistent memory with configuration."""
        super().__init__(config)

        # Extract user context from configuration
        self.user_id = config.get("user_id")
        self.memory_node_id = config.get("memory_node_id", config.get("node_id", "default"))

        if not self.user_id:
            raise ValueError("user_id is required for persistent memory operations")

        # Initialize Supabase client
        self.supabase: Optional[Client] = None
        self._supabase_url = os.getenv("SUPABASE_URL")
        self._supabase_key = os.getenv("SUPABASE_SECRET_KEY")

        if not self._supabase_url or not self._supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SECRET_KEY environment variables are required"
            )

    async def _setup(self) -> None:
        """Setup Supabase connection and initialize the persistent storage."""
        try:
            # Initialize Supabase client
            self.supabase = create_client(self._supabase_url, self._supabase_key)

            # Test connection with a simple query
            test_query = self.supabase.table("memory_nodes").select("id").limit(1).execute()

            self.logger.info(f"Supabase connection established for {self.__class__.__name__}")

            # Allow subclasses to perform additional setup
            await self._setup_persistent_storage()

        except Exception as e:
            self.logger.error(f"Failed to setup persistent memory: {str(e)}")
            raise

    @abstractmethod
    async def _setup_persistent_storage(self) -> None:
        """Setup persistent storage backend (implemented by subclasses)."""
        pass

    async def _execute_query(
        self,
        table: str,
        operation: str,
        data: Dict[str, Any] = None,
        filters: Dict[str, Any] = None,
        select_columns: str = "*",
    ) -> Dict[str, Any]:
        """Execute database operation with error handling and logging."""
        if not self.supabase:
            await self._setup()

        try:
            query = self.supabase.table(table)

            if operation == "insert":
                result = query.insert(data).execute()
            elif operation == "select":
                query = query.select(select_columns)
                if filters:
                    for key, value in filters.items():
                        if "->" in key or "->>" in key:
                            # Handle JSONB queries
                            query = query.filter(key, "eq", value)
                        else:
                            query = query.eq(key, value)
                result = query.execute()
            elif operation == "update":
                if filters:
                    for key, value in filters.items():
                        if "->" in key or "->>" in key:
                            query = query.filter(key, "eq", value)
                        else:
                            query = query.eq(key, value)
                result = query.update(data).execute()
            elif operation == "delete":
                # Apply filters before delete - process all filters first
                if filters:
                    # Separate comparison filters from equality filters
                    # Process equality filters first with .eq() which maintains query builder
                    for key, value in filters.items():
                        if not isinstance(value, str):
                            # Non-string values are always equality
                            query = query.eq(key, value)
                        elif not any(value.startswith(op) for op in ["lt.", "gt.", "lte.", "gte."]):
                            # String values without comparison operators are equality
                            if "->" in key or "->>" in key:
                                # JSONB queries use filter
                                query = query.filter(key, "eq", value)
                            else:
                                query = query.eq(key, value)

                    # Then process comparison filters with .filter() method
                    for key, value in filters.items():
                        if isinstance(value, str):
                            if value.startswith("lt."):
                                query = query.filter(key, "lt", value[3:])
                            elif value.startswith("gt."):
                                query = query.filter(key, "gt", value[3:])
                            elif value.startswith("lte."):
                                query = query.filter(key, "lte", value[4:])
                            elif value.startswith("gte."):
                                query = query.filter(key, "gte", value[4:])

                result = query.delete().execute()
            elif operation == "upsert":
                result = query.upsert(data, on_conflict="user_id,memory_node_id,data_key").execute()
            else:
                raise ValueError(f"Unsupported operation: {operation}")

            self.logger.debug(
                f"Database {operation} on {table}: {len(result.data) if result.data else 0} rows affected"
            )

            return {
                "success": True,
                "data": result.data,
                "count": result.count
                if hasattr(result, "count")
                else len(result.data)
                if result.data
                else 0,
            }

        except Exception as e:
            self.logger.error(f"Database operation failed: {operation} on {table} - {str(e)}")
            return {"success": False, "error": str(e), "data": None, "count": 0}

    async def _execute_rpc(
        self, function_name: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute Supabase RPC function with error handling."""
        if not self.supabase:
            await self._setup()

        try:
            result = self.supabase.rpc(function_name, params or {}).execute()

            return {
                "success": True,
                "data": result.data,
                "count": len(result.data) if result.data else 0,
            }

        except Exception as e:
            self.logger.error(f"RPC function {function_name} failed: {str(e)}")
            return {"success": False, "error": str(e), "data": None, "count": 0}

    def _prepare_storage_data(
        self, data: Dict[str, Any], additional_fields: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Prepare data for database storage with standard fields."""
        storage_data = {
            "user_id": self.user_id,
            "memory_node_id": self.memory_node_id,
            "created_at": datetime.utcnow().isoformat(),
            **data,
        }

        if additional_fields:
            storage_data.update(additional_fields)

        return storage_data

    def _build_base_filters(self, additional_filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build base filters for user and memory node isolation."""
        filters = {"user_id": self.user_id, "memory_node_id": self.memory_node_id}

        if additional_filters:
            filters.update(additional_filters)

        return filters

    async def _cleanup_expired_data(self, table: str) -> int:
        """Clean up expired data from the specified table."""
        try:
            if not self.supabase:
                await self._setup()

            current_time = datetime.utcnow().isoformat()

            # First, query to find expired entries
            query = self.supabase.table(table).select("id")
            query = query.eq("user_id", self.user_id)
            query = query.eq("memory_node_id", self.memory_node_id)
            query = query.filter("expires_at", "lt", current_time)

            expired_result = query.execute()

            if not expired_result.data:
                return 0

            # Extract IDs of expired entries
            expired_ids = [row["id"] for row in expired_result.data]

            # Delete expired entries by ID
            delete_query = self.supabase.table(table).delete()
            delete_query = delete_query.in_("id", expired_ids)
            result = delete_query.execute()

            cleaned_count = len(expired_ids)

            if cleaned_count > 0:
                self.logger.info(f"Cleaned {cleaned_count} expired entries from {table}")

            return cleaned_count

        except Exception as e:
            self.logger.warning(f"Failed to cleanup expired data from {table}: {str(e)}")
            return 0

    def _serialize_for_storage(self, data: Any) -> Any:
        """Serialize data for database storage (JSON-compatible)."""
        if isinstance(data, (dict, list)):
            return data  # PostgreSQL JSONB handles these directly
        elif isinstance(data, str):
            return data
        elif isinstance(data, (int, float, bool)):
            return data
        elif data is None:
            return None
        else:
            # Convert complex objects to JSON string
            return json.dumps(data, default=str, ensure_ascii=False)

    def _deserialize_from_storage(self, data: Any) -> Any:
        """Deserialize data from database storage."""
        if isinstance(data, str):
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return data
        return data

    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check for persistent storage."""
        try:
            base_health = await super().health_check()

            if base_health["status"] != "healthy":
                return base_health

            # Test database connectivity
            test_result = await self._execute_query(
                table="memory_nodes",
                operation="select",
                filters={"user_id": self.user_id},
                select_columns="id",
            )

            if test_result["success"]:
                return {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "storage_type": "persistent_supabase",
                    "user_id": self.user_id,
                    "memory_node_id": self.memory_node_id,
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"Database connectivity failed: {test_result['error']}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "storage_type": "persistent_supabase",
                }

        except Exception as e:
            self.logger.error(f"Persistent memory health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "storage_type": "persistent_supabase",
            }

    async def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage statistics for this memory instance."""
        try:
            # This is a placeholder - subclasses should implement specific statistics
            return {
                "success": True,
                "storage_type": "persistent_supabase",
                "user_id": self.user_id,
                "memory_node_id": self.memory_node_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Failed to get storage statistics: {str(e)}")
            return {"success": False, "error": str(e)}


__all__ = ["PersistentMemoryBase"]
