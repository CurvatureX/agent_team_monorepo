"""
Persistent Vector Database Memory implementation for workflow_engine_v2.

Uses Supabase embeddings table with pgvector for persistent vector storage and semantic search.
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from .persistent_base import PersistentMemoryBase


class PersistentVectorDatabaseMemory(PersistentMemoryBase):
    """Persistent vector database memory using Supabase embeddings table with pgvector."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.embedding_model = config.get("embedding_model", "text-embedding-ada-002")
        self.similarity_threshold = config.get("similarity_threshold", 0.3)
        self.max_results = config.get("max_results", 10)
        self.namespace = config.get("namespace", "default")

        # OpenAI API key for generating embeddings
        self._openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self._openai_api_key:
            self.logger.warning(
                "OPENAI_API_KEY not found - vector operations will require pre-computed embeddings"
            )

    async def _setup_persistent_storage(self) -> None:
        """Setup the persistent vector database storage."""
        # Verify pgvector extension is available (informational)
        try:
            # Test vector similarity function availability
            test_result = await self._execute_rpc("vector_similarity_test", {})
            if not test_result["success"]:
                self.logger.warning("pgvector extension may not be properly configured")
        except Exception as e:
            self.logger.warning(f"Could not verify pgvector configuration: {e}")

        self.logger.info(
            f"Persistent Vector Database initialized: model={self.embedding_model}, "
            f"threshold={self.similarity_threshold}, user_id={self.user_id}, memory_node_id={self.memory_node_id}"
        )

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store text with vector embeddings in the database."""
        try:
            content = data.get("content") or data.get("text", "")
            if not content:
                return {"success": False, "error": "Content or text is required for vector storage"}

            document_type = data.get("document_type", "text")
            metadata = data.get("metadata", {})

            # Generate or use provided embedding
            embedding = data.get("embedding")
            if not embedding:
                embedding_result = await self._generate_embedding(content)
                if not embedding_result["success"]:
                    return embedding_result
                embedding = embedding_result["embedding"]

            # Create content hash for deduplication
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            # Prepare embedding data for storage
            embedding_data = self._prepare_storage_data(
                {
                    "content": content,
                    "embedding": embedding,
                    "content_hash": content_hash,
                    "metadata": {
                        "document_type": document_type,
                        "namespace": self.namespace,
                        "embedding_model": self.embedding_model,
                        **metadata,
                    },
                }
            )

            # Use upsert to handle duplicates
            result = await self._execute_query(
                table="embeddings", operation="upsert", data=embedding_data
            )

            if result["success"]:
                self.logger.debug(f"Stored vector embedding: {content[:50]}...")

                return {
                    "success": True,
                    "content_hash": content_hash,
                    "embedding_dimensions": len(embedding) if embedding else 0,
                    "document_type": document_type,
                    "storage": "persistent_database",
                }
            else:
                return {"success": False, "error": result["error"]}

        except Exception as e:
            self.logger.error(f"Error storing vector embedding: {e}")
            return {"success": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Perform semantic search using vector similarity."""
        try:
            query_text = query.get("query") or query.get("text", "")
            if not query_text:
                return {"success": False, "error": "Query text is required for vector search"}

            limit = query.get("limit", self.max_results)
            similarity_threshold = query.get("similarity_threshold", self.similarity_threshold)
            document_type_filter = query.get("document_type")
            namespace_filter = query.get("namespace", self.namespace)

            # Generate query embedding
            query_embedding_result = await self._generate_embedding(query_text)
            if not query_embedding_result["success"]:
                return query_embedding_result

            query_embedding = query_embedding_result["embedding"]

            # Build metadata filters
            metadata_filters = {"namespace": namespace_filter}
            if document_type_filter:
                metadata_filters["document_type"] = document_type_filter

            # Perform vector similarity search using RPC function
            search_params = {
                "query_embedding": query_embedding,
                "user_id": self.user_id,
                "memory_node_id": self.memory_node_id,
                "similarity_threshold": similarity_threshold,
                "result_limit": limit,
                "metadata_filters": metadata_filters,
            }

            # Use the search_documents RPC function created in our migration
            result = await self._execute_rpc("search_embeddings_semantic", search_params)

            if result["success"]:
                # Format results for compatibility
                search_results = []
                for row in result["data"]:
                    search_result = {
                        "content": row.get("content", ""),
                        "similarity": row.get("similarity", 0.0),
                        "metadata": row.get("metadata", {}),
                        "created_at": row.get("created_at", ""),
                        "content_hash": row.get("content_hash", ""),
                    }
                    search_results.append(search_result)

                return {
                    "success": True,
                    "results": search_results,
                    "query_text": query_text,
                    "similarity_threshold": similarity_threshold,
                    "result_count": len(search_results),
                    "storage": "persistent_database",
                }
            else:
                # Fallback to manual similarity search if RPC not available
                return await self._manual_similarity_search(
                    query_embedding, query_text, limit, similarity_threshold, metadata_filters
                )

        except Exception as e:
            self.logger.error(f"Error performing vector search: {e}")
            return {"success": False, "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted context from vector search results."""
        try:
            # Perform vector search
            search_result = await self.retrieve(query)

            if not search_result["success"]:
                return search_result

            results = search_result["results"]
            if not results:
                return {
                    "success": True,
                    "context": "No relevant context found in vector database.",
                    "result_count": 0,
                    "query_text": query.get("query", ""),
                    "storage": "persistent_database",
                }

            # Format context for LLM
            max_tokens = query.get("max_tokens", 2000)
            format_style = query.get("format", "detailed")  # detailed, compact, list

            if format_style == "detailed":
                context = self._format_detailed_context(results, max_tokens)
            elif format_style == "compact":
                context = self._format_compact_context(results, max_tokens)
            else:  # list
                context = self._format_list_context(results, max_tokens)

            return {
                "success": True,
                "context": context,
                "result_count": len(results),
                "query_text": query.get("query", ""),
                "format": format_style,
                "storage": "persistent_database",
            }

        except Exception as e:
            self.logger.error(f"Error getting vector context: {e}")
            return {"success": False, "error": str(e)}

    def _format_detailed_context(self, results: List[Dict[str, Any]], max_tokens: int) -> str:
        """Format results as detailed context with similarity scores."""
        lines = ["Relevant Information from Vector Database:"]
        total_chars = len(lines[0]) + 10

        for i, result in enumerate(results, 1):
            similarity = result.get("similarity", 0.0)
            content = result.get("content", "")
            doc_type = result.get("metadata", {}).get("document_type", "text")

            formatted = f"\n{i}. [{doc_type.title()}] (similarity: {similarity:.3f})\n   {content}"

            # Check token limit (rough approximation: 4 chars per token)
            if total_chars + len(formatted) > max_tokens * 4:
                lines.append(
                    f"\n... ({len(results) - i + 1} more results truncated due to token limit)"
                )
                break

            lines.append(formatted)
            total_chars += len(formatted)

        return "".join(lines)

    def _format_compact_context(self, results: List[Dict[str, Any]], max_tokens: int) -> str:
        """Format results as compact context."""
        lines = ["Context: "]
        total_chars = len(lines[0])

        for result in results:
            content = result.get("content", "")
            # Truncate long content
            if len(content) > 200:
                content = content[:197] + "..."

            formatted = f"{content} | "

            if total_chars + len(formatted) > max_tokens * 4:
                break

            lines.append(formatted)
            total_chars += len(formatted)

        context = "".join(lines)
        return context.rstrip(" | ")  # Remove trailing separator

    def _format_list_context(self, results: List[Dict[str, Any]], max_tokens: int) -> str:
        """Format results as a simple list."""
        lines = ["Related information:"]
        total_chars = len(lines[0]) + 5

        for result in results:
            content = result.get("content", "")
            if len(content) > 150:
                content = content[:147] + "..."

            formatted = f"\n• {content}"

            if total_chars + len(formatted) > max_tokens * 4:
                break

            lines.append(formatted)
            total_chars += len(formatted)

        return "".join(lines)

    async def _generate_embedding(self, text: str) -> Dict[str, Any]:
        """Generate embedding using OpenAI API."""
        if not self._openai_api_key:
            return {
                "success": False,
                "error": "OpenAI API key not configured - cannot generate embeddings",
            }

        try:
            # Lazy import to avoid dependency issues if not needed
            import openai

            # Use the updated OpenAI client
            client = openai.OpenAI(api_key=self._openai_api_key)

            response = client.embeddings.create(
                model=self.embedding_model, input=text.replace("\n", " ")  # Clean up text
            )

            embedding = response.data[0].embedding

            return {
                "success": True,
                "embedding": embedding,
                "model": self.embedding_model,
                "dimensions": len(embedding),
            }

        except ImportError:
            return {
                "success": False,
                "error": "OpenAI library not available - install with: pip install openai",
            }
        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            return {"success": False, "error": f"Embedding generation failed: {str(e)}"}

    async def _manual_similarity_search(
        self,
        query_embedding: List[float],
        query_text: str,
        limit: int,
        similarity_threshold: float,
        metadata_filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fallback manual similarity search using SQL."""
        try:
            # Build metadata filter conditions
            metadata_conditions = []
            for key, value in metadata_filters.items():
                metadata_conditions.append(f"metadata ->> '{key}' = '{value}'")

            metadata_where = (
                " AND " + " AND ".join(metadata_conditions) if metadata_conditions else ""
            )

            # Use raw SQL for vector similarity (requires pgvector)
            sql_query = f"""
                SELECT
                    content,
                    metadata,
                    created_at,
                    content_hash,
                    1 - (embedding <=> %s) as similarity
                FROM embeddings
                WHERE user_id = %s
                  AND metadata ->> 'memory_node_id' = %s
                  {metadata_where}
                  AND 1 - (embedding <=> %s) > %s
                ORDER BY embedding <=> %s
                LIMIT %s
            """

            # Execute raw SQL query
            # Note: This requires a custom RPC function in Supabase
            result = await self._execute_rpc(
                "execute_vector_similarity_sql",
                {
                    "sql_query": sql_query,
                    "query_embedding": query_embedding,
                    "user_id": self.user_id,
                    "memory_node_id": self.memory_node_id,
                    "similarity_threshold": similarity_threshold,
                    "limit": limit,
                },
            )

            if result["success"]:
                search_results = []
                for row in result["data"]:
                    search_result = {
                        "content": row.get("content", ""),
                        "similarity": row.get("similarity", 0.0),
                        "metadata": row.get("metadata", {}),
                        "created_at": row.get("created_at", ""),
                        "content_hash": row.get("content_hash", ""),
                    }
                    search_results.append(search_result)

                return {
                    "success": True,
                    "results": search_results,
                    "query_text": query_text,
                    "similarity_threshold": similarity_threshold,
                    "result_count": len(search_results),
                    "storage": "persistent_database",
                    "method": "manual_sql",
                }
            else:
                return {
                    "success": False,
                    "error": f"Manual similarity search failed: {result['error']}",
                }

        except Exception as e:
            self.logger.error(f"Manual similarity search error: {e}")
            return {"success": False, "error": f"Manual similarity search failed: {str(e)}"}

    async def clear_namespace(self, namespace: str = None) -> Dict[str, Any]:
        """Clear all vectors in a specific namespace."""
        try:
            target_namespace = namespace or self.namespace

            # Delete vectors in the specified namespace
            result = await self._execute_query(
                table="embeddings",
                operation="delete",
                filters={**self._build_base_filters(), "metadata->>namespace": target_namespace},
            )

            if result["success"]:
                self.logger.info(
                    f"Cleared {result['count']} vectors from namespace '{target_namespace}'"
                )
                return {
                    "success": True,
                    "cleared_count": result["count"],
                    "namespace": target_namespace,
                    "storage": "persistent_database",
                }
            else:
                return {"success": False, "error": result["error"]}

        except Exception as e:
            self.logger.error(f"Error clearing namespace {namespace}: {e}")
            return {"success": False, "error": str(e)}

    async def get_statistics(self) -> Dict[str, Any]:
        """Get vector database statistics."""
        try:
            # Get vector count by namespace and document type
            result = await self._execute_query(
                table="embeddings",
                operation="select",
                filters=self._build_base_filters(),
                select_columns="""
                    COUNT(*) as total_vectors,
                    metadata ->> 'namespace' as namespace,
                    metadata ->> 'document_type' as document_type,
                    MIN(created_at) as oldest_vector,
                    MAX(created_at) as newest_vector
                """,
            )

            if result["success"]:
                stats = {
                    "total_vectors": 0,
                    "by_namespace": {},
                    "by_document_type": {},
                    "oldest_vector": None,
                    "newest_vector": None,
                    "embedding_model": self.embedding_model,
                    "default_similarity_threshold": self.similarity_threshold,
                }

                for row in result["data"]:
                    namespace = row.get("namespace", "default")
                    doc_type = row.get("document_type", "text")
                    count = row.get("total_vectors", 0)

                    stats["total_vectors"] += count
                    stats["by_namespace"][namespace] = (
                        stats["by_namespace"].get(namespace, 0) + count
                    )
                    stats["by_document_type"][doc_type] = (
                        stats["by_document_type"].get(doc_type, 0) + count
                    )

                    if row.get("oldest_vector"):
                        if (
                            not stats["oldest_vector"]
                            or row["oldest_vector"] < stats["oldest_vector"]
                        ):
                            stats["oldest_vector"] = row["oldest_vector"]

                    if row.get("newest_vector"):
                        if (
                            not stats["newest_vector"]
                            or row["newest_vector"] > stats["newest_vector"]
                        ):
                            stats["newest_vector"] = row["newest_vector"]

                return {"success": True, "statistics": stats, "storage": "persistent_database"}
            else:
                return {"success": False, "error": result["error"]}

        except Exception as e:
            self.logger.error(f"Error getting vector statistics: {e}")
            return {"success": False, "error": str(e)}


__all__ = ["PersistentVectorDatabaseMemory"]
