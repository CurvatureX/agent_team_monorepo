"""
Memory Orchestrator for workflow_engine_v2.

Coordinates between different memory types and provides unified access.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from .base import MemoryBase
from .conversation_buffer import ConversationBufferMemory
from .conversation_summary import ConversationSummaryMemory
from .entity_memory import EntityMemory
from .key_value_store import KeyValueStoreMemory
from .vector_database import VectorDatabaseMemory
from .working_memory import WorkingMemory


class MemoryOrchestrator(MemoryBase):
    """Orchestrator that coordinates multiple memory types."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.memory_instances = {}
        self.enabled_memories = config.get(
            "enabled_memories", ["key_value_store", "conversation_buffer", "working_memory"]
        )

        # Memory type mappings
        self.memory_classes = {
            "key_value_store": KeyValueStoreMemory,
            "conversation_buffer": ConversationBufferMemory,
            "conversation_summary": ConversationSummaryMemory,
            "entity_memory": EntityMemory,
            "vector_database": VectorDatabaseMemory,
            "working_memory": WorkingMemory,
        }

    async def _setup(self) -> None:
        """Setup all enabled memory instances."""
        for memory_type in self.enabled_memories:
            if memory_type in self.memory_classes:
                memory_config = self.config.get(memory_type, {})
                memory_class = self.memory_classes[memory_type]
                memory_instance = memory_class(memory_config)
                await memory_instance.initialize()
                self.memory_instances[memory_type] = memory_instance
                self.logger.info(f"Initialized {memory_type} memory")

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store data in appropriate memory types."""
        try:
            memory_type = data.get("memory_type", "auto")
            results = {}

            if memory_type == "auto":
                # Auto-route based on data type
                memory_targets = self._determine_memory_targets(data)
            elif memory_type == "all":
                # Store in all enabled memories
                memory_targets = list(self.memory_instances.keys())
            else:
                # Store in specific memory type
                memory_targets = [memory_type] if memory_type in self.memory_instances else []

            for target in memory_targets:
                if target in self.memory_instances:
                    try:
                        result = await self.memory_instances[target].store(data)
                        results[target] = result
                    except Exception as e:
                        self.logger.error(f"Error storing in {target}: {e}")
                        results[target] = {"success": False, "error": str(e)}

            overall_success = any(r.get("success", False) for r in results.values())

            return {
                "success": overall_success,
                "results": results,
                "stored_in": [k for k, v in results.items() if v.get("success")],
            }

        except Exception as e:
            self.logger.error(f"Error in memory orchestrator store: {e}")
            return {"success": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve data from specified memory types."""
        try:
            memory_types = query.get("memory_types", ["auto"])
            results = {}

            if "auto" in memory_types:
                # Auto-determine best memory for query
                memory_types = self._determine_retrieval_targets(query)

            for memory_type in memory_types:
                if memory_type in self.memory_instances:
                    try:
                        result = await self.memory_instances[memory_type].retrieve(query)
                        if result.get("success"):
                            results[memory_type] = result
                    except Exception as e:
                        self.logger.error(f"Error retrieving from {memory_type}: {e}")

            return {"success": bool(results), "results": results}

        except Exception as e:
            self.logger.error(f"Error in memory orchestrator retrieve: {e}")
            return {"success": False, "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get unified context from multiple memory types."""
        try:
            memory_types = query.get("memory_types", self.enabled_memories)
            context_parts = []
            all_results = {}

            for memory_type in memory_types:
                if memory_type in self.memory_instances:
                    try:
                        result = await self.memory_instances[memory_type].get_context(query)
                        if result.get("success") and result.get("context"):
                            context_parts.append(f"--- {memory_type.replace('_', ' ').title()} ---")
                            context_parts.append(result["context"])
                            all_results[memory_type] = result
                    except Exception as e:
                        self.logger.error(f"Error getting context from {memory_type}: {e}")

            unified_context = (
                "\n\n".join(context_parts)
                if context_parts
                else "No context available from any memory type."
            )

            return {
                "success": bool(context_parts),
                "context": unified_context,
                "memory_results": all_results,
                "memory_count": len(context_parts)
                // 2,  # Each memory adds 2 parts (header + content)
            }

        except Exception as e:
            self.logger.error(f"Error getting unified context: {e}")
            return {"success": False, "error": str(e)}

    def _determine_memory_targets(self, data: Dict[str, Any]) -> List[str]:
        """Determine which memory types should store this data."""
        targets = []

        # Key-value data
        if "key" in data and "value" in data:
            targets.append("key_value_store")

        # Conversation data
        if "message" in data or "role" in data:
            targets.extend(["conversation_buffer", "conversation_summary"])

        # Entity data
        if "entity_name" in data or "entity_info" in data:
            targets.append("entity_memory")

        # Semantic search data
        if "content" in data and len(data.get("content", "")) > 50:
            targets.append("vector_database")

        # Working data (temporary)
        if data.get("temporary") or "ttl" in data:
            targets.append("working_memory")

        # Default fallback
        if not targets:
            targets.append("key_value_store")

        # Only return targets that are enabled
        return [t for t in targets if t in self.memory_instances]

    def _determine_retrieval_targets(self, query: Dict[str, Any]) -> List[str]:
        """Determine which memory types to query for retrieval."""
        targets = []

        # Specific key lookup
        if "key" in query:
            targets.extend(["key_value_store", "working_memory"])

        # Conversation queries
        if "role" in query or "since_timestamp" in query:
            targets.extend(["conversation_buffer", "conversation_summary"])

        # Entity queries
        if "entity_name" in query:
            targets.append("entity_memory")

        # Semantic search
        if "query" in query and isinstance(query["query"], str):
            targets.append("vector_database")

        # Default to all if no specific target
        if not targets:
            targets = list(self.memory_instances.keys())

        return [t for t in targets if t in self.memory_instances]

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics from all memory instances."""
        stats = {"orchestrator": {"enabled_memories": self.enabled_memories}}

        for memory_type, instance in self.memory_instances.items():
            try:
                if hasattr(instance, "get_statistics"):
                    memory_stats = await instance.get_statistics()
                    stats[memory_type] = memory_stats.get("statistics", {})
                else:
                    health = await instance.health_check()
                    stats[memory_type] = {"status": health.get("status", "unknown")}
            except Exception as e:
                stats[memory_type] = {"error": str(e)}

        return stats

    async def clear_all_memories(self) -> Dict[str, Any]:
        """Clear all memory instances."""
        results = {}

        for memory_type, instance in self.memory_instances.items():
            try:
                if hasattr(instance, "clear") or hasattr(instance, "clear_all"):
                    clear_method = getattr(instance, "clear_all", getattr(instance, "clear", None))
                    if clear_method:
                        result = await clear_method()
                        results[memory_type] = result
                    else:
                        results[memory_type] = {
                            "success": False,
                            "error": "No clear method available",
                        }
                else:
                    results[memory_type] = {"success": False, "error": "Clear not supported"}
            except Exception as e:
                results[memory_type] = {"success": False, "error": str(e)}

        return {"results": results}


__all__ = ["MemoryOrchestrator"]
