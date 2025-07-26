"""
Vector Store Client and RAG Service for Node Knowledge
Integrates with Supabase pgvector for intelligent node recommendation
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import structlog
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from supabase import Client, create_client
from supabase.client import ClientOptions

from .config import settings

logger = structlog.get_logger()


class NodeKnowledgeEntry:
    """Represents a node knowledge entry with metadata"""

    def __init__(
        self,
        id: str,
        node_type: str,
        node_subtype: Optional[str],
        title: str,
        description: str,
        content: str,
        similarity: float,
        metadata: Dict[str, Any],
    ):
        self.id = id
        self.node_type = node_type
        self.node_subtype = node_subtype
        self.title = title
        self.description = description
        self.content = content
        self.similarity = similarity
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "node_type": self.node_type,
            "node_subtype": self.node_subtype,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "similarity": self.similarity,
            "metadata": self.metadata,
        }


class SupabaseVectorStore:
    """
    Supabase vector store client for node knowledge retrieval
    """

    def __init__(self):
        self.supabase_client = self._create_supabase_client()
        self.embeddings = self._create_embeddings_client()

    def _create_supabase_client(self) -> Client:
        """Create Supabase client with proper configuration"""
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured")

        # Use service role key for full access to vector operations
        client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
            options=ClientOptions(schema="public", auto_refresh_token=False, persist_session=False),
        )

        logger.info("Supabase vector store client initialized")
        return client

    def _create_embeddings_client(self) -> Embeddings:
        """Create embeddings client"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be configured for embeddings")

        return OpenAIEmbeddings(model=settings.EMBEDDING_MODEL, api_key=settings.OPENAI_API_KEY)

    async def similarity_search(
        self,
        query: str,
        node_type_filter: Optional[str] = None,
        similarity_threshold: Optional[float] = None,
        max_results: Optional[int] = None,
    ) -> List[NodeKnowledgeEntry]:
        """
        Perform similarity search for node knowledge

        Args:
            query: Search query text
            node_type_filter: Optional filter by node type
            similarity_threshold: Minimum similarity score (0.0-1.0)
            max_results: Maximum number of results to return

        Returns:
            List of matching node knowledge entries
        """
        try:
            # Generate embedding for query
            query_embedding = await self.embeddings.aembed_query(query)

            # Use configured defaults if not provided
            threshold = similarity_threshold or settings.RAG_SIMILARITY_THRESHOLD
            max_count = max_results or settings.RAG_MAX_RESULTS

            # Call the PostgreSQL function for vector similarity search using asyncio.to_thread
            result = await asyncio.to_thread(
                lambda: self.supabase_client.rpc(
                    "match_node_knowledge",
                    {
                        "query_embedding": query_embedding,
                        "match_threshold": threshold,
                        "match_count": max_count,
                        "node_type_filter": node_type_filter,
                    },
                ).execute()
            )

            # Convert results to NodeKnowledgeEntry objects
            entries = []
            for row in result.data:
                entry = NodeKnowledgeEntry(
                    id=row["id"],
                    node_type=row["node_type"],
                    node_subtype=row["node_subtype"],
                    title=row["title"],
                    description=row["description"],
                    content=row["content"],
                    similarity=row["similarity"],
                    metadata=row["metadata"] or {},
                )
                entries.append(entry)

            logger.info(
                "Vector similarity search completed",
                query=query[:100],
                results_count=len(entries),
                threshold=threshold,
            )

            return entries

        except Exception as e:
            logger.error("Vector similarity search failed", error=str(e), query=query)
            return []

    async def search_by_capabilities(
        self,
        required_capabilities: List[str],
        complexity_preference: str = "medium",  # low, medium, high
    ) -> List[NodeKnowledgeEntry]:
        """
        Search for nodes based on required capabilities

        Args:
            required_capabilities: List of required capabilities
            complexity_preference: Preferred complexity level

        Returns:
            List of relevant node knowledge entries
        """
        # Create search query from capabilities
        query = f"capabilities: {', '.join(required_capabilities)}"
        if complexity_preference:
            query += f" complexity: {complexity_preference}"

        results = await self.similarity_search(query, max_results=10)

        # Filter and rank based on capability matching
        scored_results = []
        for result in results:
            capability_score = self._calculate_capability_score(
                result.metadata.get("capabilities", []), required_capabilities
            )
            complexity_score = self._calculate_complexity_score(
                result.metadata.get("complexity", "medium"), complexity_preference
            )

            # Combined score (capability match is more important)
            total_score = (capability_score * 0.7) + (complexity_score * 0.3)
            result.metadata["total_score"] = total_score
            scored_results.append(result)

        # Sort by total score (descending)
        scored_results.sort(key=lambda x: x.metadata.get("total_score", 0), reverse=True)

        return scored_results[: settings.RAG_MAX_RESULTS]

    async def search_by_node_type(
        self, node_types: List[str], context: str = ""
    ) -> List[NodeKnowledgeEntry]:
        """
        Search for specific node types with optional context

        Args:
            node_types: List of node types to search for
            context: Additional context for the search

        Returns:
            List of matching node knowledge entries
        """
        all_results = []

        for node_type in node_types:
            query = f"node type: {node_type}"
            if context:
                query += f" context: {context}"

            results = await self.similarity_search(
                query, node_type_filter=node_type, max_results=3  # Limit per node type
            )
            all_results.extend(results)

        # Remove duplicates and sort by similarity
        unique_results = {r.id: r for r in all_results}.values()
        sorted_results = sorted(unique_results, key=lambda x: x.similarity, reverse=True)

        return sorted_results[: settings.RAG_MAX_RESULTS]

    def _calculate_capability_score(
        self, node_capabilities: List[str], required_capabilities: List[str]
    ) -> float:
        """Calculate how well node capabilities match requirements"""
        if not required_capabilities:
            return 1.0

        if not node_capabilities:
            return 0.0

        matches = sum(1 for cap in required_capabilities if cap in node_capabilities)
        return matches / len(required_capabilities)

    def _calculate_complexity_score(self, node_complexity: str, preferred_complexity: str) -> float:
        """Calculate complexity preference score"""
        complexity_levels = {"low": 1, "medium": 2, "high": 3}

        node_level = complexity_levels.get(node_complexity, 2)
        preferred_level = complexity_levels.get(preferred_complexity, 2)

        # Closer complexity levels get higher scores
        difference = abs(node_level - preferred_level)
        return max(0, 1 - (difference * 0.3))


class NodeKnowledgeRAG:
    """
    RAG (Retrieval-Augmented Generation) service for node knowledge
    Provides intelligent node recommendations based on requirements
    """

    def __init__(self):
        self.vector_store = SupabaseVectorStore()
        self.cache = {}  # Simple in-memory cache

    async def get_capability_recommendations(
        self, required_capabilities: List[str], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get node recommendations for required capabilities

        Args:
            required_capabilities: List of required capabilities
            context: Additional context (complexity preference, etc.)

        Returns:
            Dictionary with recommendations and alternatives
        """
        context = context or {}
        complexity_pref = context.get("complexity_preference", "medium")

        # Search for capability matches
        results = await self.vector_store.search_by_capabilities(
            required_capabilities, complexity_pref
        )

        # Group by capability
        capability_map = {}
        for capability in required_capabilities:
            matches = [r for r in results if capability.lower() in r.content.lower()]
            capability_map[capability] = matches[:3]  # Top 3 per capability

        # Find alternatives for missing capabilities
        missing_capabilities = []
        for capability in required_capabilities:
            if not capability_map[capability]:
                missing_capabilities.append(capability)

        alternatives = []
        if missing_capabilities:
            alt_query = f"alternative solutions for: {', '.join(missing_capabilities)}"
            alt_results = await self.vector_store.similarity_search(
                alt_query, similarity_threshold=0.2  # Lower threshold for alternatives
            )
            alternatives = alt_results[:5]

        return {
            "capability_matches": capability_map,
            "missing_capabilities": missing_capabilities,
            "alternatives": [r.to_dict() for r in alternatives],
            "total_matches": len(results),
            "coverage_score": self._calculate_coverage_score(required_capabilities, capability_map),
        }

    async def get_node_type_suggestions(
        self, task_description: str, existing_nodes: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get node type suggestions based on task description

        Args:
            task_description: Description of the task/requirement
            existing_nodes: List of existing node types in workflow

        Returns:
            List of suggested node types with explanations
        """
        existing_nodes = existing_nodes or []

        # Search for relevant nodes
        results = await self.vector_store.similarity_search(task_description, max_results=8)

        # Filter out existing nodes and rank suggestions
        suggestions = []
        for result in results:
            if result.node_type not in existing_nodes:
                suggestion = {
                    "node_type": result.node_type,
                    "node_subtype": result.node_subtype,
                    "title": result.title,
                    "description": result.description,
                    "similarity": result.similarity,
                    "confidence": self._calculate_confidence(result.similarity),
                    "use_case": result.metadata.get("use_case", ""),
                    "complexity": result.metadata.get("complexity", "medium"),
                    "setup_time": result.metadata.get("setup_time", "unknown"),
                }
                suggestions.append(suggestion)

        return suggestions[:5]  # Top 5 suggestions

    async def get_integration_guidance(
        self, integration_type: str, requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get guidance for specific integrations (Slack, Notion, etc.)

        Args:
            integration_type: Type of integration (slack, notion, gmail, etc.)
            requirements: Specific requirements for the integration

        Returns:
            Integration guidance with examples and best practices
        """
        # Create search query
        query_parts = [f"{integration_type} integration"]

        if requirements.get("data_direction") == "input":
            query_parts.append("data input")
        elif requirements.get("data_direction") == "output":
            query_parts.append("data output")

        if requirements.get("authentication"):
            query_parts.append("authentication setup")

        query = " ".join(query_parts)

        # Search for integration-specific knowledge
        results = await self.vector_store.similarity_search(
            query, node_type_filter=f"EXTERNAL_{integration_type.upper()}", max_results=3
        )

        # Also search for general integration patterns
        pattern_results = await self.vector_store.similarity_search(
            f"integration patterns {integration_type}", max_results=2
        )

        return {
            "integration_type": integration_type,
            "specific_guidance": [r.to_dict() for r in results],
            "general_patterns": [r.to_dict() for r in pattern_results],
            "configuration_requirements": self._extract_config_requirements(results),
            "best_practices": self._extract_best_practices(results + pattern_results),
        }

    def _calculate_coverage_score(
        self, required_capabilities: List[str], capability_map: Dict[str, List[NodeKnowledgeEntry]]
    ) -> float:
        """Calculate how well the requirements are covered"""
        if not required_capabilities:
            return 1.0

        covered = sum(1 for cap in required_capabilities if capability_map.get(cap))
        return covered / len(required_capabilities)

    def _calculate_confidence(self, similarity: float) -> str:
        """Convert similarity score to confidence level"""
        if similarity >= 0.8:
            return "high"
        elif similarity >= 0.6:
            return "medium"
        elif similarity >= 0.4:
            return "low"
        else:
            return "very_low"

    def _extract_config_requirements(self, results: List[NodeKnowledgeEntry]) -> List[str]:
        """Extract configuration requirements from results"""
        requirements = []
        for result in results:
            config_reqs = result.metadata.get("configuration_requirements", [])
            requirements.extend(config_reqs)

        # Remove duplicates and return
        return list(set(requirements))

    def _extract_best_practices(self, results: List[NodeKnowledgeEntry]) -> List[str]:
        """Extract best practices from results"""
        practices = []
        for result in results:
            best_practices = result.metadata.get("best_practices", [])
            practices.extend(best_practices)

        # Remove duplicates and return top practices
        unique_practices = list(set(practices))
        return unique_practices[:5]


# Global RAG instance
_rag_instance = None


def get_node_knowledge_rag() -> NodeKnowledgeRAG:
    """Get global RAG instance (singleton pattern)"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = NodeKnowledgeRAG()
    return _rag_instance
