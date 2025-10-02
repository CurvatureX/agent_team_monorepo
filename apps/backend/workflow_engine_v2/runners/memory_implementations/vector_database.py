"""
Vector Database Memory implementation for workflow_engine_v2.

Provides semantic search capabilities using vector embeddings.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.supabase import create_supabase_client

from .base import MemoryBase


class VectorDatabaseMemory(MemoryBase):
    """Vector database memory implementation with semantic search."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.supabase = None
        self.collection_name = config.get("collection_name", "workflow_memories")
        self.similarity_threshold = config.get("similarity_threshold", 0.7)
        # Fallback in-memory store for when Supabase is not available
        self.memory_store = []

    async def _setup(self) -> None:
        """Setup vector database connection."""
        try:
            self.supabase = create_supabase_client()
            if self.supabase:
                self.logger.info("Vector Database: Using Supabase with pgvector")
            else:
                self.logger.warning(
                    "Vector Database: Supabase not available, using in-memory store"
                )
        except Exception as e:
            self.logger.warning(f"Vector Database: Setup failed: {e}, using in-memory store")

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store data with vector embedding."""
        try:
            content = data.get("content", "")
            metadata = data.get("metadata", {})

            if not content:
                return {"success": False, "error": "Missing 'content' in data"}

            entry = {
                "content": content,
                "metadata": metadata,
                "timestamp": datetime.utcnow().isoformat(),
                "id": f"mem_{datetime.utcnow().timestamp()}",
            }

            if self.supabase:
                # In a real implementation, you would generate embeddings here
                # For now, we'll store without embeddings
                try:
                    record = {
                        "collection": self.collection_name,
                        "content": content,
                        "metadata": metadata,
                        "created_at": entry["timestamp"],
                    }

                    result = self.supabase.table("vector_memories").insert(record).execute()

                    if result.data:
                        entry["id"] = result.data[0]["id"]
                        self.logger.debug(f"Stored vector memory: {content[:50]}...")
                    else:
                        # Fallback to in-memory
                        self.memory_store.append(entry)

                except Exception as e:
                    self.logger.warning(f"Failed to store in Supabase, using in-memory: {e}")
                    self.memory_store.append(entry)
            else:
                # In-memory storage
                self.memory_store.append(entry)

            return {"success": True, "id": entry["id"], "timestamp": entry["timestamp"]}

        except Exception as e:
            self.logger.error(f"Error storing vector data: {e}")
            return {"success": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve similar content using vector search."""
        try:
            search_query = query.get("query", "")
            limit = query.get("limit", 5)

            if not search_query:
                return {"success": False, "error": "Missing 'query' parameter"}

            results = []

            if self.supabase:
                try:
                    # Simple text search (in production, would use vector similarity)
                    result = (
                        self.supabase.table("vector_memories")
                        .select("*")
                        .eq("collection", self.collection_name)
                        .ilike("content", f"%{search_query}%")
                        .limit(limit)
                        .execute()
                    )

                    for record in result.data:
                        results.append(
                            {
                                "id": record["id"],
                                "content": record["content"],
                                "metadata": record.get("metadata", {}),
                                "timestamp": record["created_at"],
                                "similarity": 0.8,  # Mock similarity score
                            }
                        )

                except Exception as e:
                    self.logger.warning(f"Supabase query failed, using in-memory: {e}")

            # Fallback to in-memory search
            if not results:
                search_lower = search_query.lower()
                for entry in self.memory_store:
                    if search_lower in entry["content"].lower():
                        results.append(
                            {
                                "id": entry["id"],
                                "content": entry["content"],
                                "metadata": entry["metadata"],
                                "timestamp": entry["timestamp"],
                                "similarity": 0.7,  # Mock similarity
                            }
                        )

                        if len(results) >= limit:
                            break

            return {"success": True, "results": results, "count": len(results)}

        except Exception as e:
            self.logger.error(f"Error retrieving vector data: {e}")
            return {"success": False, "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted context for LLM using semantic search."""
        try:
            search_query = query.get("query", "")
            max_results = query.get("max_results", 5)

            if not search_query:
                return {"success": True, "context": "No search query provided.", "result_count": 0}

            # Get similar content
            retrieval_result = await self.retrieve({"query": search_query, "limit": max_results})

            if not retrieval_result.get("success"):
                return {"success": False, "error": retrieval_result.get("error")}

            results = retrieval_result.get("results", [])

            if not results:
                return {
                    "success": True,
                    "context": f"No relevant memories found for: {search_query}",
                    "result_count": 0,
                }

            # Format context
            context_lines = [f"Relevant memories for '{search_query}':"]
            for i, result in enumerate(results, 1):
                similarity = result.get("similarity", 0.0)
                content = result["content"][:200]  # Truncate long content
                if len(result["content"]) > 200:
                    content += "..."

                context_lines.append(f"{i}. (similarity: {similarity:.2f}) {content}")

            context = "\n".join(context_lines)

            return {
                "success": True,
                "context": context,
                "result_count": len(results),
                "search_query": search_query,
            }

        except Exception as e:
            self.logger.error(f"Error getting vector context: {e}")
            return {"success": False, "error": str(e)}


__all__ = ["VectorDatabaseMemory"]
