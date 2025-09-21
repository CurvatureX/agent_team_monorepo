"""
Document Store Memory Implementation.

This implementation provides document storage and full-text search capabilities
using Supabase PostgreSQL with built-in full-text search features.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from supabase import Client, create_client

from .base import MemoryBase

logger = logging.getLogger(__name__)


class DocumentStoreMemory(MemoryBase):
    """
    Document Store Memory with full-text search capabilities.

    Features:
    - Document storage with metadata
    - PostgreSQL full-text search (tsvector)
    - Collection-based organization
    - Relevance scoring and ranking
    - Metadata filtering
    - Content indexing and search
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize document store memory.

        Args:
            config: Configuration dict with keys:
                - supabase_url: Supabase project URL
                - supabase_key: Supabase service key
                - collection_name: Document collection name (required)
                - search_fields: Fields to search (default: ['content', 'title'])
                - max_results: Maximum search results (default: 10)
                - full_text_search: Enable full-text search (default: True)
        """
        super().__init__(config)

        # Supabase configuration
        self.supabase_url = config.get("supabase_url")
        self.supabase_key = config.get("supabase_key")
        self.supabase: Optional[Client] = None

        # Document store configuration
        self.collection_name = config.get("collection_name")
        if not self.collection_name:
            raise ValueError("collection_name is required for DocumentStoreMemory")

        self.search_fields = config.get("search_fields", ["content", "title", "description"])
        self.max_results = config.get("max_results", 10)
        self.full_text_search = config.get("full_text_search", True)

        # Table names
        self.documents_table = "document_store"

    async def _setup(self) -> None:
        """Initialize Supabase client and ensure tables exist."""
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("supabase_url and supabase_key are required")

        try:
            self.supabase = create_client(self.supabase_url, self.supabase_key)

            # Test connection
            result = self.supabase.table(self.documents_table).select("id").limit(1).execute()
            logger.info(
                f"DocumentStoreMemory connected to Supabase for collection: {self.collection_name}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store a document in the collection.

        Args:
            data: Document data with keys:
                - content: Document content (required)
                - document_id: Unique document ID (optional, auto-generated)
                - title: Document title (optional)
                - description: Document description (optional)
                - metadata: Additional metadata (optional)
                - category: Document category (optional)
                - tags: List of tags (optional)

        Returns:
            Dict with store operation results
        """
        try:
            content = data.get("content")
            if not content:
                return {"stored": False, "error": "content is required"}

            document_id = data.get("document_id", str(uuid.uuid4()))
            title = data.get("title", "")
            description = data.get("description", "")
            metadata = data.get("metadata", {})
            category = data.get("category", "general")
            tags = data.get("tags", [])

            # Create search vector for full-text search
            search_content = f"{title} {description} {content} {' '.join(tags)}"

            document_data = {
                "id": document_id,
                "collection_name": self.collection_name,
                "title": title,
                "description": description,
                "content": content,
                "search_content": search_content,  # For tsvector indexing
                "metadata": json.dumps(metadata) if isinstance(metadata, dict) else metadata,
                "category": category,
                "tags": tags,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Check if document exists
            existing = (
                self.supabase.table(self.documents_table)
                .select("id")
                .eq("id", document_id)
                .eq("collection_name", self.collection_name)
                .execute()
            )

            if existing.data:
                # Update existing document
                result = (
                    self.supabase.table(self.documents_table)
                    .update({**document_data, "updated_at": datetime.utcnow().isoformat()})
                    .eq("id", document_id)
                    .eq("collection_name", self.collection_name)
                    .execute()
                )
                operation = "updated"
            else:
                # Insert new document
                result = self.supabase.table(self.documents_table).insert(document_data).execute()
                operation = "created"

            if result.data:
                return {
                    "stored": True,
                    "operation": operation,
                    "document_id": document_id,
                    "collection": self.collection_name,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {"stored": False, "error": "Failed to store document"}

        except Exception as e:
            logger.error(f"Error storing document: {e}")
            return {"stored": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve documents by ID or search criteria.

        Args:
            query: Query parameters:
                - document_id: Specific document ID (optional)
                - query: Search query string (optional)
                - filters: Metadata filters (optional)
                - category: Category filter (optional)
                - tags: Tag filters (optional)
                - max_results: Maximum results (optional)

        Returns:
            Dict with retrieved documents
        """
        try:
            document_id = query.get("document_id")
            search_query = query.get("query", "")
            filters = query.get("filters", {})
            category = query.get("category")
            tags = query.get("tags", [])
            max_results = query.get("max_results", self.max_results)

            # Build base query
            supabase_query = (
                self.supabase.table(self.documents_table)
                .select("*")
                .eq("collection_name", self.collection_name)
            )

            # Specific document ID
            if document_id:
                supabase_query = supabase_query.eq("id", document_id)

            # Category filter
            if category:
                supabase_query = supabase_query.eq("category", category)

            # Tag filters (contains any of the specified tags)
            if tags:
                for tag in tags:
                    supabase_query = supabase_query.contains("tags", [tag])

            # Full-text search
            if search_query and self.full_text_search:
                # Use PostgreSQL full-text search
                supabase_query = supabase_query.text_search("search_content", search_query)
            elif search_query:
                # Fallback to basic text search
                supabase_query = supabase_query.or_(
                    f"content.ilike.%{search_query}%,title.ilike.%{search_query}%,description.ilike.%{search_query}%"
                )

            # Apply limit
            supabase_query = supabase_query.limit(max_results)

            # Execute query
            result = supabase_query.execute()

            documents = []
            for doc in result.data:
                # Parse metadata if it's JSON string
                metadata = doc.get("metadata", {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}

                documents.append(
                    {
                        "document_id": doc["id"],
                        "title": doc.get("title", ""),
                        "description": doc.get("description", ""),
                        "content": doc["content"],
                        "metadata": metadata,
                        "category": doc.get("category", "general"),
                        "tags": doc.get("tags", []),
                        "created_at": doc.get("created_at"),
                        "updated_at": doc.get("updated_at"),
                        "relevance_score": 1.0,  # PostgreSQL full-text search doesn't return scores easily
                    }
                )

            return {
                "documents": documents,
                "total_count": len(documents),
                "query": search_query,
                "collection": self.collection_name,
            }

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return {"documents": [], "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get document context for LLM consumption.

        Args:
            query: Query parameters (same as retrieve)

        Returns:
            Dict with formatted context for LLM
        """
        try:
            # Get documents
            result = await self.retrieve(query)

            if "error" in result:
                return {"documents": [], "context_text": "", "error": result["error"]}

            documents = result["documents"]

            # Format context for LLM
            context_parts = []
            relevance_scores = []

            for doc in documents:
                # Create formatted document entry
                doc_text = f"**{doc['title']}**\n" if doc["title"] else ""
                if doc["description"]:
                    doc_text += f"*{doc['description']}*\n"
                doc_text += f"{doc['content']}\n"

                if doc["tags"]:
                    doc_text += f"Tags: {', '.join(doc['tags'])}\n"

                context_parts.append(doc_text.strip())
                relevance_scores.append(doc.get("relevance_score", 1.0))

            # Join all documents
            context_text = "\n\n---\n\n".join(context_parts)

            # Calculate average relevance
            avg_relevance = (
                sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
            )

            # Estimate tokens (rough approximation)
            estimated_tokens = len(context_text) // 4

            return {
                "documents": documents,
                "context_text": context_text,
                "total_count": len(documents),
                "relevance_scores": relevance_scores,
                "average_relevance": avg_relevance,
                "estimated_tokens": estimated_tokens,
                "metadata": {
                    "collection": self.collection_name,
                    "search_query": query.get("query", ""),
                    "total_documents": len(documents),
                },
            }

        except Exception as e:
            logger.error(f"Error getting document context: {e}")
            return {"documents": [], "context_text": "", "error": str(e)}

    async def delete(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete documents from the collection.

        Args:
            query: Delete parameters:
                - document_id: Specific document ID (optional)
                - category: Delete all in category (optional)
                - confirm_delete_all: Required for collection-wide deletion

        Returns:
            Dict with deletion results
        """
        try:
            document_id = query.get("document_id")
            category = query.get("category")
            confirm_delete_all = query.get("confirm_delete_all", False)

            if document_id:
                # Delete specific document
                result = (
                    self.supabase.table(self.documents_table)
                    .delete()
                    .eq("id", document_id)
                    .eq("collection_name", self.collection_name)
                    .execute()
                )
                return {
                    "deleted": True,
                    "document_id": document_id,
                    "count": len(result.data) if result.data else 0,
                }

            elif category:
                # Delete by category
                result = (
                    self.supabase.table(self.documents_table)
                    .delete()
                    .eq("collection_name", self.collection_name)
                    .eq("category", category)
                    .execute()
                )
                return {
                    "deleted": True,
                    "category": category,
                    "count": len(result.data) if result.data else 0,
                }

            elif confirm_delete_all:
                # Delete entire collection
                result = (
                    self.supabase.table(self.documents_table)
                    .delete()
                    .eq("collection_name", self.collection_name)
                    .execute()
                )
                return {
                    "deleted": True,
                    "collection": self.collection_name,
                    "count": len(result.data) if result.data else 0,
                }

            else:
                return {"deleted": False, "error": "No deletion criteria specified"}

        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return {"deleted": False, "error": str(e)}

    async def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about the document collection."""
        try:
            target_collection = collection_name or self.collection_name

            # Get total count
            count_result = (
                self.supabase.table(self.documents_table)
                .select("id", count="exact")
                .eq("collection_name", target_collection)
                .execute()
            )
            total_documents = count_result.count if hasattr(count_result, "count") else 0

            # Get category breakdown
            categories_result = (
                self.supabase.table(self.documents_table)
                .select("category")
                .eq("collection_name", target_collection)
                .execute()
            )

            categories = {}
            for doc in categories_result.data:
                cat = doc.get("category", "general")
                categories[cat] = categories.get(cat, 0) + 1

            # Get recent activity
            recent_result = (
                self.supabase.table(self.documents_table)
                .select("created_at")
                .eq("collection_name", target_collection)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            latest_document = None
            if recent_result.data:
                latest_document = recent_result.data[0].get("created_at")

            return {
                "collection": target_collection,
                "total_documents": total_documents,
                "categories": categories,
                "latest_document": latest_document,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of document store connections."""
        try:
            # Test Supabase connection
            test_result = self.supabase.table(self.documents_table).select("id").limit(1).execute()

            stats = await self.get_collection_stats()

            return {
                "status": "healthy",
                "supabase_connected": True,
                "collection": self.collection_name,
                "total_documents": stats.get("total_documents", 0),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"DocumentStore health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
