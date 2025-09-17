"""
Vector Database Memory Implementation.

This implements vector storage and semantic search using Supabase with pgvector:
- Store text embeddings for semantic similarity search
- Support multiple embedding models (OpenAI, etc.)
- Efficient similarity search with configurable thresholds
- Metadata filtering and collection management
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import openai
from supabase import Client, create_client

from .base import MemoryBase

logger = logging.getLogger(__name__)


class VectorDatabaseMemory(MemoryBase):
    """
    Vector Database Memory with Supabase pgvector backend.

    Features:
    - Semantic similarity search using embeddings
    - Multiple embedding model support
    - Collection-based organization
    - Metadata filtering
    - Configurable similarity thresholds
    - Automatic embedding generation
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize vector database memory.

        Args:
            config: Configuration dict with keys:
                - supabase_url: Supabase project URL
                - supabase_key: Supabase service key
                - openai_api_key: OpenAI API key for embeddings
                - embedding_model: Model to use (default: 'text-embedding-3-small')
                - similarity_threshold: Default similarity threshold (default: 0.7)
                - max_results: Default max results (default: 5)
                - auto_embed: Automatically generate embeddings (default: True)
                - embedding_dimensions: Embedding vector dimensions (default: 1536)
        """
        super().__init__(config)

        # Configuration
        self.embedding_model = config.get("embedding_model", "text-embedding-3-small")
        self.similarity_threshold = config.get("similarity_threshold", 0.7)
        self.max_results = config.get("max_results", 5)
        self.auto_embed = config.get("auto_embed", True)
        self.embedding_dimensions = config.get("embedding_dimensions", 1536)

        # Clients
        self.supabase_client: Optional[Client] = None
        self.openai_client: Optional[openai.OpenAI] = None

    async def _setup(self) -> None:
        """Setup Supabase and OpenAI clients."""
        try:
            # Setup Supabase
            supabase_url = self.config["supabase_url"]
            supabase_key = self.config["supabase_key"]
            self.supabase_client = create_client(supabase_url, supabase_key)

            # Setup OpenAI
            openai_api_key = self.config["openai_api_key"]
            self.openai_client = openai.OpenAI(api_key=openai_api_key)

            logger.info("VectorDatabaseMemory initialized successfully")

        except Exception as e:
            logger.error(f"Failed to setup VectorDatabaseMemory: {str(e)}")
            raise

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store text with embeddings in vector database.

        Args:
            data: Data dict with keys:
                - text: Text content to store
                - collection_name: Collection/namespace for the embedding
                - metadata: Additional metadata (optional)
                - user_id: User identifier (optional)
                - vector: Pre-computed embedding vector (optional)
                - embedding_id: Custom ID for the embedding (optional)

        Returns:
            Dict with storage confirmation
        """
        await self.initialize()

        try:
            text_content = data["text"]
            collection_name = data["collection_name"]
            metadata = data.get("metadata", {})
            user_id = data.get("user_id")
            pre_computed_vector = data.get("vector")
            embedding_id = data.get("embedding_id")

            # Generate embedding if not provided and auto_embed is enabled
            if pre_computed_vector is None and self.auto_embed:
                embedding_vector = await self._generate_embedding(text_content)
            elif pre_computed_vector is not None:
                embedding_vector = pre_computed_vector
            else:
                raise ValueError("No embedding vector provided and auto_embed is disabled")

            # Validate embedding dimensions
            if len(embedding_vector) != self.embedding_dimensions:
                raise ValueError(
                    f"Embedding dimensions mismatch: expected {self.embedding_dimensions}, got {len(embedding_vector)}"
                )

            # Prepare data for storage
            embedding_data = {
                "collection_name": collection_name,
                "text_content": text_content,
                "embedding": embedding_vector,
                "metadata": metadata,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Add custom ID if provided
            if embedding_id:
                embedding_data["id"] = embedding_id

            # Store in Supabase
            result = (
                self.supabase_client.table("vector_embeddings").insert(embedding_data).execute()
            )

            if not result.data:
                raise Exception("Failed to store embedding in Supabase")

            stored_item = result.data[0]

            logger.debug(f"Stored embedding {stored_item['id']} in collection {collection_name}")

            return {
                "stored": True,
                "embedding_id": stored_item["id"],
                "collection_name": collection_name,
                "text_length": len(text_content),
                "embedding_dimensions": len(embedding_vector),
                "stored_at": stored_item["created_at"],
            }

        except Exception as e:
            logger.error(f"Failed to store vector embedding: {str(e)}")
            raise

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve embeddings by ID or collection.

        Args:
            query: Query dict with keys:
                - embedding_id: Specific embedding ID (optional)
                - collection_name: Collection to search in (optional)
                - limit: Maximum number of results (optional)
                - metadata_filter: Filter by metadata (optional)

        Returns:
            Dict with embeddings
        """
        await self.initialize()

        try:
            embedding_id = query.get("embedding_id")
            collection_name = query.get("collection_name")
            limit = query.get("limit", 50)
            metadata_filter = query.get("metadata_filter", {})

            # Build query
            supabase_query = self.supabase_client.table("vector_embeddings").select("*")

            if embedding_id:
                supabase_query = supabase_query.eq("id", embedding_id)
            elif collection_name:
                supabase_query = supabase_query.eq("collection_name", collection_name)

            # Apply metadata filters
            for key, value in metadata_filter.items():
                supabase_query = supabase_query.eq(f"metadata->{key}", value)

            # Apply limit and execute
            result = supabase_query.limit(limit).execute()
            embeddings = result.data if result.data else []

            return {
                "embeddings": embeddings,
                "total_count": len(embeddings),
                "retrieved_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to retrieve embeddings: {str(e)}")
            raise

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get relevant context through semantic similarity search.

        Args:
            query: Query dict with keys:
                - text: Text to find similar content for (optional)
                - query: Same as text (alternative key)
                - vector: Pre-computed query vector (optional)
                - collection_name: Collection to search in
                - similarity_threshold: Minimum similarity score (optional)
                - max_results: Maximum results to return (optional)
                - filters: Metadata filters (optional)

        Returns:
            Dict with relevant context for LLM consumption
        """
        await self.initialize()

        try:
            query_text = query.get("text") or query.get("query")
            query_vector = query.get("vector")
            collection_name = query["collection_name"]
            similarity_threshold = query.get("similarity_threshold", self.similarity_threshold)
            max_results = query.get("max_results", self.max_results)
            filters = query.get("filters", {})

            # Generate query embedding if not provided
            if query_vector is None and query_text:
                query_vector = await self._generate_embedding(query_text)
            elif query_vector is None:
                raise ValueError("Either text or vector must be provided for similarity search")

            # Perform similarity search
            similar_items = await self._similarity_search(
                query_vector=query_vector,
                collection_name=collection_name,
                similarity_threshold=similarity_threshold,
                max_results=max_results,
                filters=filters,
            )

            # Format results for LLM context
            results = []
            similarities = []
            context_texts = []
            metadata_summary = {}

            for item, similarity in similar_items:
                results.append(
                    {
                        "id": item["id"],
                        "text": item["text_content"],
                        "metadata": item.get("metadata", {}),
                        "similarity": similarity,
                        "created_at": item.get("created_at"),
                    }
                )

                similarities.append(similarity)
                context_texts.append(item["text_content"])

                # Aggregate metadata for summary
                item_metadata = item.get("metadata", {})
                for key, value in item_metadata.items():
                    if key not in metadata_summary:
                        metadata_summary[key] = set()
                    metadata_summary[key].add(str(value))

            # Convert sets to lists for JSON serialization
            metadata_summary = {k: list(v) for k, v in metadata_summary.items()}

            # Create consolidated context text
            context_text = "\n---\n".join(context_texts)

            return {
                "results": results,
                "similarities": similarities,
                "context_text": context_text,
                "metadata_summary": metadata_summary,
                "total_results": len(results),
                "avg_similarity": sum(similarities) / len(similarities) if similarities else 0.0,
                "collection_name": collection_name,
                "search_performed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get vector context: {str(e)}")
            raise

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()

            def _get_embedding():
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model, input=text
                )
                return response.data[0].embedding

            embedding = await loop.run_in_executor(None, _get_embedding)
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise

    async def _similarity_search(
        self,
        query_vector: List[float],
        collection_name: str,
        similarity_threshold: float,
        max_results: int,
        filters: Dict[str, Any],
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Perform similarity search using Supabase function."""
        try:
            # Use the custom similarity search function
            result = self.supabase_client.rpc(
                "search_similar_vectors",
                {
                    "query_embedding": query_vector,
                    "collection_name_param": collection_name,
                    "similarity_threshold": similarity_threshold,
                    "max_results": max_results,
                },
            ).execute()

            if not result.data:
                return []

            # Apply additional metadata filters if specified
            filtered_results = []
            for item in result.data:
                # Check metadata filters
                item_metadata = item.get("metadata", {})
                matches_filters = True

                for filter_key, filter_value in filters.items():
                    if filter_key not in item_metadata or item_metadata[filter_key] != filter_value:
                        matches_filters = False
                        break

                if matches_filters:
                    filtered_results.append((item, item["similarity"]))

            # Sort by similarity score (descending)
            filtered_results.sort(key=lambda x: x[1], reverse=True)

            return filtered_results[:max_results]

        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            # Fallback to basic search without similarity function
            return await self._fallback_similarity_search(
                query_vector, collection_name, max_results
            )

    async def _fallback_similarity_search(
        self, query_vector: List[float], collection_name: str, max_results: int
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Fallback similarity search using basic vector operations."""
        try:
            # Get all embeddings from collection
            result = (
                self.supabase_client.table("vector_embeddings")
                .select("*")
                .eq("collection_name", collection_name)
                .execute()
            )

            if not result.data:
                return []

            # Calculate similarities manually
            query_array = np.array(query_vector)
            similarities = []

            for item in result.data:
                item_vector = np.array(item["embedding"])

                # Calculate cosine similarity
                dot_product = np.dot(query_array, item_vector)
                norm_query = np.linalg.norm(query_array)
                norm_item = np.linalg.norm(item_vector)

                if norm_query > 0 and norm_item > 0:
                    similarity = dot_product / (norm_query * norm_item)
                    similarities.append((item, float(similarity)))

            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:max_results]

        except Exception as e:
            logger.error(f"Fallback similarity search failed: {str(e)}")
            return []

    async def update_embedding(self, embedding_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing embedding."""
        await self.initialize()

        try:
            update_data = {"updated_at": datetime.utcnow().isoformat()}

            # Update text and regenerate embedding if provided
            if "text" in data:
                update_data["text_content"] = data["text"]
                if self.auto_embed:
                    update_data["embedding"] = await self._generate_embedding(data["text"])

            # Update vector if provided
            if "vector" in data:
                update_data["embedding"] = data["vector"]

            # Update metadata if provided
            if "metadata" in data:
                update_data["metadata"] = data["metadata"]

            # Perform update
            result = (
                self.supabase_client.table("vector_embeddings")
                .update(update_data)
                .eq("id", embedding_id)
                .execute()
            )

            if not result.data:
                raise Exception(f"No embedding found with ID {embedding_id}")

            updated_item = result.data[0]

            return {
                "updated": True,
                "embedding_id": embedding_id,
                "updated_at": updated_item["updated_at"],
            }

        except Exception as e:
            logger.error(f"Failed to update embedding: {str(e)}")
            raise

    async def delete_embedding(self, embedding_id: str) -> Dict[str, Any]:
        """Delete an embedding by ID."""
        await self.initialize()

        try:
            result = (
                self.supabase_client.table("vector_embeddings")
                .delete()
                .eq("id", embedding_id)
                .execute()
            )

            if not result.data:
                raise Exception(f"No embedding found with ID {embedding_id}")

            return {
                "deleted": True,
                "embedding_id": embedding_id,
                "deleted_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to delete embedding: {str(e)}")
            raise

    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics for a vector collection."""
        await self.initialize()

        try:
            # Get collection data
            result = (
                self.supabase_client.table("vector_embeddings")
                .select("id, metadata, created_at")
                .eq("collection_name", collection_name)
                .execute()
            )

            if not result.data:
                return {
                    "collection_name": collection_name,
                    "total_embeddings": 0,
                    "created_at": None,
                    "last_updated": None,
                }

            embeddings = result.data

            # Calculate statistics
            total_embeddings = len(embeddings)

            # Get date range
            created_dates = [item["created_at"] for item in embeddings if item.get("created_at")]
            created_dates.sort()

            # Analyze metadata
            metadata_keys = set()
            for item in embeddings:
                metadata = item.get("metadata", {})
                metadata_keys.update(metadata.keys())

            return {
                "collection_name": collection_name,
                "total_embeddings": total_embeddings,
                "earliest_embedding": created_dates[0] if created_dates else None,
                "latest_embedding": created_dates[-1] if created_dates else None,
                "metadata_keys": list(metadata_keys),
                "analyzed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            raise

    async def cleanup_old_embeddings(
        self, collection_name: str, retention_days: int = 90
    ) -> Dict[str, Any]:
        """Clean up old embeddings from a collection."""
        await self.initialize()

        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=retention_days)).isoformat()

            # Delete old embeddings
            result = (
                self.supabase_client.table("vector_embeddings")
                .delete()
                .eq("collection_name", collection_name)
                .lt("created_at", cutoff_date)
                .execute()
            )

            deleted_count = len(result.data) if result.data else 0

            logger.info(
                f"Cleaned up {deleted_count} old embeddings from collection {collection_name}"
            )

            return {
                "collection_name": collection_name,
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date,
                "cleanup_completed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to cleanup old embeddings: {str(e)}")
            raise
