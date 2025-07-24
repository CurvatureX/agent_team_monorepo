"""
Node Knowledge client for MCP service
"""

import time
from typing import Any, Dict, List, Optional

import structlog
from supabase import Client, create_client

from core.config import settings
from core.mcp_exceptions import MCPDatabaseError, MCPParameterError
from models.mcp_models import NodeKnowledgeResponse, NodeKnowledgeResult

logger = structlog.get_logger()


class NodeKnowledgeClient:
    """Client for interacting with node knowledge database"""

    def __init__(self):
        self.supabase: Optional[Client] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Supabase client"""
        try:
            if not settings.NODE_KNOWLEDGE_SUPABASE_URL or not settings.NODE_KNOWLEDGE_SUPABASE_KEY:
                logger.warning("Node knowledge Supabase credentials not configured")
                return

            self.supabase = create_client(
                settings.NODE_KNOWLEDGE_SUPABASE_URL, settings.NODE_KNOWLEDGE_SUPABASE_KEY
            )
            logger.info("Node knowledge client initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize node knowledge client", error=str(e))
            raise MCPDatabaseError(
                message=f"Failed to initialize database client: {str(e)}",
                user_message="Database connection failed",
            )

    async def retrieve_node_knowledge(
        self, node_names: List[str], include_metadata: bool = False
    ) -> NodeKnowledgeResponse:
        """
        Retrieve knowledge for specified nodes

        Args:
            node_names: List of node names to retrieve knowledge for
            include_metadata: Whether to include metadata in response

        Returns:
            NodeKnowledgeResponse with results
        """
        start_time = time.time()

        if not node_names:
            raise MCPParameterError(
                message="node_names parameter is required and cannot be empty",
                user_message="node_names is required",
            )

        if not self.supabase:
            raise MCPDatabaseError(
                message="Supabase client not initialized",
                user_message="Database service unavailable",
            )

        logger.info(
            "Retrieving node knowledge", node_names=node_names, include_metadata=include_metadata
        )

        results = []

        for node_name in node_names:
            try:
                node_result = await self._query_supabase(node_name, include_metadata)
                results.append(node_result)

            except Exception as e:
                logger.error(
                    "Failed to retrieve knowledge for node", node_name=node_name, error=str(e)
                )
                # Add empty result for failed nodes
                results.append(
                    NodeKnowledgeResult(
                        node_name=node_name,
                        knowledge="",
                        metadata={} if include_metadata else {},
                        similarity_score=None,
                    )
                )

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Node knowledge retrieval completed",
            total_nodes=len(results),
            processing_time_ms=processing_time_ms,
        )

        return NodeKnowledgeResponse(
            success=True,
            results=results,
            total_nodes=len(results),
            processing_time_ms=processing_time_ms,
        )

    async def _query_supabase(self, node_name: str, include_metadata: bool) -> NodeKnowledgeResult:
        """
        Query Supabase for a specific node's knowledge

        Args:
            node_name: Name of the node to query
            include_metadata: Whether to include metadata

        Returns:
            NodeKnowledgeResult for the node
        """
        max_retries = 2
        retry_count = 0

        while retry_count <= max_retries:
            try:
                # Query the node_knowledge_vectors table for exact title match
                query = (
                    self.supabase.table("node_knowledge_vectors")
                    .select("id, node_type, node_subtype, title, description, content, metadata")
                    .eq("title", node_name)
                )

                response = query.execute()

                if response.data:
                    # Use the first matching result
                    data = response.data[0]

                    return NodeKnowledgeResult(
                        node_name=node_name,
                        knowledge=data.get("content", ""),
                        metadata=data.get("metadata", {}) if include_metadata else {},
                        similarity_score=1.0,  # Exact match
                    )
                else:
                    # Try fuzzy search using vector similarity
                    return await self._vector_search(node_name, include_metadata)

            except Exception as e:
                logger.error(
                    f"Supabase query failed (attempt {retry_count + 1})",
                    node_name=node_name,
                    error=str(e),
                )

                if retry_count < max_retries:
                    retry_count += 1
                    await self._wait_for_retry(retry_count)
                    continue
                else:
                    raise MCPDatabaseError(
                        message=f"Failed to query database for node '{node_name}': {str(e)}",
                        user_message="Database query failed",
                    )

    async def _vector_search(self, node_name: str, include_metadata: bool) -> NodeKnowledgeResult:
        """
        Perform vector similarity search for node knowledge

        Args:
            node_name: Name of the node to search for
            include_metadata: Whether to include metadata

        Returns:
            NodeKnowledgeResult for the node
        """
        try:
            # For now, return empty result as we don't have embedding generation here
            # This would need OpenAI integration similar to the existing query route
            logger.info(
                "Vector search not implemented, returning empty result", node_name=node_name
            )

            return NodeKnowledgeResult(
                node_name=node_name,
                knowledge=f"Knowledge for node '{node_name}' not found",
                metadata={} if include_metadata else {},
                similarity_score=0.0,
            )

        except Exception as e:
            logger.error("Vector search failed", node_name=node_name, error=str(e))
            raise MCPDatabaseError(
                message=f"Vector search failed for node '{node_name}': {str(e)}",
                user_message="Search operation failed",
            )

    async def _wait_for_retry(self, retry_count: int):
        """Wait before retrying with exponential backoff"""
        import asyncio

        wait_time = min(1.0 * (2 ** (retry_count - 1)), 5.0)  # Max 5 seconds
        await asyncio.sleep(wait_time)

    def health_check(self) -> Dict[str, Any]:
        """Check the health of the node knowledge service"""
        try:
            if not self.supabase:
                return {"healthy": False, "error": "Supabase client not initialized"}

            # Simple query to check connection
            response = self.supabase.table("node_knowledge_vectors").select("id").limit(1).execute()

            return {"healthy": True, "total_records": len(response.data) if response.data else 0}

        except Exception as e:
            logger.error("Node knowledge health check failed", error=str(e))
            return {"healthy": False, "error": str(e)}
