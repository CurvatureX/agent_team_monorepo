"""
Memory Orchestrator for Unified Memory Access.

This orchestrator provides a unified interface to all memory types,
enabling complex memory operations and intelligent context composition.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from .base import MemoryBase

# Import all memory implementations
from .conversation_buffer import ConversationBufferMemory
from .conversation_summary import ConversationSummaryMemory
from .document_store import DocumentStoreMemory
from .entity_memory import EntityMemory
from .episodic_memory import EpisodicMemory
from .graph_memory import GraphMemory
from .key_value_store import KeyValueStoreMemory
from .knowledge_base import KnowledgeBaseMemory
from .vector_database import VectorDatabaseMemory
from .working_memory import WorkingMemory

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Available memory types."""

    CONVERSATION_BUFFER = "conversation_buffer"
    CONVERSATION_SUMMARY = "conversation_summary"
    VECTOR_DATABASE = "vector_database"
    WORKING_MEMORY = "working_memory"
    KEY_VALUE_STORE = "key_value_store"
    ENTITY_MEMORY = "entity_memory"
    EPISODIC_MEMORY = "episodic_memory"
    KNOWLEDGE_BASE = "knowledge_base"
    GRAPH_MEMORY = "graph_memory"
    DOCUMENT_STORE = "document_store"


@dataclass
class ContextPriority:
    """Priority settings for different context types."""

    recent_conversation: float = 0.4
    summary: float = 0.2
    entities: float = 0.15
    vector_search: float = 0.15
    working_memory: float = 0.1


@dataclass
class ContextRequest:
    """Request for LLM context composition."""

    query: str
    session_id: str
    user_id: Optional[str] = None
    priority: Optional[ContextPriority] = None
    max_total_tokens: int = 4000
    include_reasoning_chain: bool = True
    vector_collections: Optional[List[str]] = None
    entity_types: Optional[List[str]] = None


class MemoryOrchestrator:
    """
    Unified orchestrator for all memory types.

    Features:
    - Intelligent context composition
    - Parallel memory queries
    - Token-aware optimization
    - Configurable memory priorities
    - Automatic memory type selection
    - Cross-memory relationship detection
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize memory orchestrator.

        Args:
            config: Configuration dict with memory-specific configs and:
                - enabled_memories: List of memory types to enable
                - default_context_priority: Default priority settings
                - parallel_queries: Enable parallel memory queries (default: True)
                - cross_memory_links: Enable cross-memory relationships (default: True)
        """
        self.config = config
        self.enabled_memories = config.get(
            "enabled_memories",
            [
                MemoryType.CONVERSATION_SUMMARY,
                MemoryType.VECTOR_DATABASE,
                MemoryType.WORKING_MEMORY,
                MemoryType.KEY_VALUE_STORE,
                MemoryType.ENTITY_MEMORY,
            ],
        )

        self.default_priority = ContextPriority(**config.get("default_context_priority", {}))
        self.parallel_queries = config.get("parallel_queries", True)
        self.cross_memory_links = config.get("cross_memory_links", True)

        # Memory instances
        self.memories: Dict[MemoryType, MemoryBase] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all enabled memory types."""
        if self._initialized:
            return

        try:
            # Memory type mappings
            memory_classes: Dict[MemoryType, Type[MemoryBase]] = {
                MemoryType.CONVERSATION_BUFFER: ConversationBufferMemory,
                MemoryType.CONVERSATION_SUMMARY: ConversationSummaryMemory,
                MemoryType.VECTOR_DATABASE: VectorDatabaseMemory,
                MemoryType.WORKING_MEMORY: WorkingMemory,
                MemoryType.KEY_VALUE_STORE: KeyValueStoreMemory,
                MemoryType.ENTITY_MEMORY: EntityMemory,
                MemoryType.EPISODIC_MEMORY: EpisodicMemory,
                MemoryType.KNOWLEDGE_BASE: KnowledgeBaseMemory,
                MemoryType.GRAPH_MEMORY: GraphMemory,
                MemoryType.DOCUMENT_STORE: DocumentStoreMemory,
            }

            # Initialize enabled memories
            init_tasks = []
            for memory_type in self.enabled_memories:
                if memory_type in memory_classes:
                    memory_config = self.config.get(memory_type.value, self.config)
                    memory_instance = memory_classes[memory_type](memory_config)
                    self.memories[memory_type] = memory_instance
                    init_tasks.append(memory_instance.initialize())

            # Initialize all memories in parallel
            await asyncio.gather(*init_tasks, return_exceptions=True)

            self._initialized = True
            logger.info(f"MemoryOrchestrator initialized with {len(self.memories)} memory types")

        except Exception as e:
            logger.error(f"Failed to initialize MemoryOrchestrator: {str(e)}")
            raise

    async def get_comprehensive_context(self, request: ContextRequest) -> Dict[str, Any]:
        """
        Get comprehensive context from all relevant memory types.

        Args:
            request: Context request with query and parameters

        Returns:
            Dict with comprehensive context for LLM consumption
        """
        await self.initialize()

        try:
            priority = request.priority or self.default_priority

            # Gather contexts from all relevant memory types
            if self.parallel_queries:
                contexts = await self._gather_contexts_parallel(request)
            else:
                contexts = await self._gather_contexts_sequential(request)

            # Compose unified context
            unified_context = await self._compose_unified_context(contexts, request, priority)

            logger.debug(f"Generated comprehensive context with {len(contexts)} memory sources")

            return unified_context

        except Exception as e:
            logger.error(f"Failed to get comprehensive context: {str(e)}")
            raise

    async def _gather_contexts_parallel(
        self, request: ContextRequest
    ) -> Dict[MemoryType, Dict[str, Any]]:
        """Gather contexts from all memory types in parallel."""
        contexts = {}
        tasks = []
        memory_types = []

        # Create tasks for each memory type
        for memory_type, memory in self.memories.items():
            task = self._get_memory_context(memory_type, memory, request)
            tasks.append(task)
            memory_types.append(memory_type)

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for memory_type, result in zip(memory_types, results):
            if isinstance(result, Exception):
                logger.warning(f"Memory {memory_type.value} failed: {str(result)}")
                contexts[memory_type] = {}
            else:
                contexts[memory_type] = result

        return contexts

    async def _gather_contexts_sequential(
        self, request: ContextRequest
    ) -> Dict[MemoryType, Dict[str, Any]]:
        """Gather contexts from all memory types sequentially."""
        contexts = {}

        for memory_type, memory in self.memories.items():
            try:
                context = await self._get_memory_context(memory_type, memory, request)
                contexts[memory_type] = context
            except Exception as e:
                logger.warning(f"Memory {memory_type.value} failed: {str(e)}")
                contexts[memory_type] = {}

        return contexts

    async def _get_memory_context(
        self, memory_type: MemoryType, memory: MemoryBase, request: ContextRequest
    ) -> Dict[str, Any]:
        """Get context from a specific memory type."""
        base_query = {"session_id": request.session_id, "user_id": request.user_id}

        if memory_type == MemoryType.CONVERSATION_SUMMARY:
            query = {**base_query, "context_strategy": "balanced", "prioritize_recency": True}
        elif memory_type == MemoryType.VECTOR_DATABASE:
            query = {
                "query": request.query,
                "collection_name": request.vector_collections[0]
                if request.vector_collections
                else "default",
                "max_results": 3,
                "similarity_threshold": 0.7,
            }
        elif memory_type == MemoryType.WORKING_MEMORY:
            query = {
                "namespace": request.session_id,
                "max_items": 10,
                "min_importance": 0.5,
                "include_reasoning_chain": request.include_reasoning_chain,
            }
        elif memory_type == MemoryType.KEY_VALUE_STORE:
            query = {"namespace": request.user_id or "default", "max_items": 20}
        elif memory_type == MemoryType.ENTITY_MEMORY:
            query = {
                **base_query,
                "content": request.query,
                "max_entities": 10,
                "include_relationships": True,
            }
        else:
            query = base_query

        return await memory.get_context(query)

    async def _compose_unified_context(
        self,
        contexts: Dict[MemoryType, Dict[str, Any]],
        request: ContextRequest,
        priority: ContextPriority,
    ) -> Dict[str, Any]:
        """Compose unified context from all memory sources."""

        # Initialize unified context
        unified_context = {
            "query": request.query,
            "session_id": request.session_id,
            "user_id": request.user_id,
            "context_sources": list(contexts.keys()),
            "composed_at": datetime.utcnow().isoformat(),
        }

        # Extract and prioritize different types of context
        conversation_context = self._extract_conversation_context(
            contexts, priority.recent_conversation
        )
        summary_context = self._extract_summary_context(contexts, priority.summary)
        entity_context = self._extract_entity_context(contexts, priority.entities)
        vector_context = self._extract_vector_context(contexts, priority.vector_search)
        working_context = self._extract_working_context(contexts, priority.working_memory)
        user_context = self._extract_user_context(contexts)

        # Combine contexts with token awareness
        combined_context = await self._optimize_context_tokens(
            {
                "conversation": conversation_context,
                "summary": summary_context,
                "entities": entity_context,
                "relevant_knowledge": vector_context,
                "reasoning_state": working_context,
                "user_preferences": user_context,
            },
            request.max_total_tokens,
        )

        unified_context.update(combined_context)

        # Add cross-memory insights if enabled
        if self.cross_memory_links:
            unified_context["cross_memory_insights"] = self._generate_cross_memory_insights(
                contexts
            )

        # Generate context summary
        unified_context["context_summary"] = self._generate_context_summary(unified_context)

        return unified_context

    def _extract_conversation_context(
        self, contexts: Dict[MemoryType, Dict[str, Any]], weight: float
    ) -> Dict[str, Any]:
        """Extract conversation context."""
        context = {"weight": weight}

        # Prefer hybrid conversation, fallback to buffer
        if MemoryType.CONVERSATION_SUMMARY in contexts:
            hybrid_ctx = contexts[MemoryType.CONVERSATION_SUMMARY]
            context.update(
                {
                    "recent_messages": hybrid_ctx.get("messages", []),
                    "summary": hybrid_ctx.get("summary", ""),
                    "method": "hybrid",
                    "total_tokens": hybrid_ctx.get("total_tokens", 0),
                }
            )
        elif MemoryType.CONVERSATION_BUFFER in contexts:
            buffer_ctx = contexts[MemoryType.CONVERSATION_BUFFER]
            context.update(
                {
                    "recent_messages": buffer_ctx.get("messages", []),
                    "method": "buffer_only",
                    "total_tokens": buffer_ctx.get("total_tokens", 0),
                }
            )

        return context

    def _extract_summary_context(
        self, contexts: Dict[MemoryType, Dict[str, Any]], weight: float
    ) -> Dict[str, Any]:
        """Extract summary context."""
        context = {"weight": weight}

        if MemoryType.CONVERSATION_SUMMARY in contexts:
            summary_ctx = contexts[MemoryType.CONVERSATION_SUMMARY]
            context.update(
                {
                    "summary": summary_ctx.get("summary", ""),
                    "key_points": summary_ctx.get("key_points", []),
                    "has_summary": summary_ctx.get("metadata", {}).get("has_summary", False),
                }
            )

        return context

    def _extract_entity_context(
        self, contexts: Dict[MemoryType, Dict[str, Any]], weight: float
    ) -> Dict[str, Any]:
        """Extract entity context."""
        context = {"weight": weight}

        if MemoryType.ENTITY_MEMORY in contexts:
            entity_ctx = contexts[MemoryType.ENTITY_MEMORY]
            context.update(
                {
                    "entities": entity_ctx.get("entities", []),
                    "relationships": entity_ctx.get("relationships", []),
                    "entity_summary": entity_ctx.get("entity_summary", ""),
                    "total_entities": entity_ctx.get("total_entities", 0),
                }
            )

        return context

    def _extract_vector_context(
        self, contexts: Dict[MemoryType, Dict[str, Any]], weight: float
    ) -> Dict[str, Any]:
        """Extract vector search context."""
        context = {"weight": weight}

        if MemoryType.VECTOR_DATABASE in contexts:
            vector_ctx = contexts[MemoryType.VECTOR_DATABASE]
            context.update(
                {
                    "relevant_documents": vector_ctx.get("results", []),
                    "context_text": vector_ctx.get("context_text", ""),
                    "avg_similarity": vector_ctx.get("avg_similarity", 0.0),
                    "total_results": vector_ctx.get("total_results", 0),
                }
            )

        return context

    def _extract_working_context(
        self, contexts: Dict[MemoryType, Dict[str, Any]], weight: float
    ) -> Dict[str, Any]:
        """Extract working memory context."""
        context = {"weight": weight}

        if MemoryType.WORKING_MEMORY in contexts:
            working_ctx = contexts[MemoryType.WORKING_MEMORY]
            context.update(
                {
                    "current_state": working_ctx.get("current_state", {}),
                    "reasoning_chain": working_ctx.get("reasoning_chain", []),
                    "active_items": working_ctx.get("active_items", 0),
                }
            )

        return context

    def _extract_user_context(self, contexts: Dict[MemoryType, Dict[str, Any]]) -> Dict[str, Any]:
        """Extract user preferences and settings."""
        context = {}

        if MemoryType.KEY_VALUE_STORE in contexts:
            kv_ctx = contexts[MemoryType.KEY_VALUE_STORE]
            context.update(
                {
                    "preferences": kv_ctx.get("context_data", {}).get("preferences", {}),
                    "session_data": kv_ctx.get("context_data", {}).get("conversation_context", {}),
                }
            )

        return context

    async def _optimize_context_tokens(
        self, contexts: Dict[str, Dict[str, Any]], max_tokens: int
    ) -> Dict[str, Any]:
        """Optimize context size to fit within token limits."""

        # Simple token estimation (1 token ≈ 4 characters)
        def estimate_tokens(text: str) -> int:
            return max(1, len(str(text)) // 4)

        # Calculate current token usage
        total_tokens = 0
        for context_type, context_data in contexts.items():
            context_str = json.dumps(context_data, default=str)
            total_tokens += estimate_tokens(context_str)

        # If under limit, return as is
        if total_tokens <= max_tokens:
            return contexts

        # Optimize by reducing content based on weights
        optimized_contexts = {}
        remaining_tokens = max_tokens

        # Sort by weight (highest first)
        sorted_contexts = sorted(
            contexts.items(), key=lambda x: x[1].get("weight", 0.1), reverse=True
        )

        for context_type, context_data in sorted_contexts:
            weight = context_data.get("weight", 0.1)
            allocated_tokens = int(remaining_tokens * weight)

            # Truncate context if necessary
            context_str = json.dumps(context_data, default=str)
            if estimate_tokens(context_str) > allocated_tokens:
                # Simple truncation strategy
                max_chars = allocated_tokens * 4
                truncated_str = context_str[:max_chars] + "..."
                try:
                    # Try to maintain JSON structure
                    optimized_context = json.loads(truncated_str.rsplit(",", 1)[0] + "}")
                except:
                    # Fallback to weight-based reduction
                    optimized_context = self._reduce_context_content(context_data, weight)
            else:
                optimized_context = context_data

            optimized_contexts[context_type] = optimized_context
            remaining_tokens -= estimate_tokens(json.dumps(optimized_context, default=str))

            if remaining_tokens <= 0:
                break

        return optimized_contexts

    def _reduce_context_content(
        self, context_data: Dict[str, Any], weight: float
    ) -> Dict[str, Any]:
        """Reduce context content based on weight."""
        reduced_context = context_data.copy()

        # Reduce lists and arrays
        for key, value in context_data.items():
            if isinstance(value, list):
                max_items = max(1, int(len(value) * weight))
                reduced_context[key] = value[:max_items]
            elif isinstance(value, str) and len(value) > 500:
                max_chars = max(100, int(len(value) * weight))
                reduced_context[key] = value[:max_chars] + "..."

        return reduced_context

    def _generate_cross_memory_insights(
        self, contexts: Dict[MemoryType, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate insights from cross-memory relationships."""
        insights = {
            "entity_conversation_overlap": [],
            "vector_entity_matches": [],
            "working_memory_entity_refs": [],
            "conversation_vector_relevance": 0.0,
        }

        # Find overlaps between different memory types
        entity_names = set()
        if MemoryType.ENTITY_MEMORY in contexts:
            entities = contexts[MemoryType.ENTITY_MEMORY].get("entities", [])
            entity_names = {entity.get("name", "").lower() for entity in entities}

        # Check conversation for entity mentions
        if MemoryType.CONVERSATION_SUMMARY in contexts and entity_names:
            messages = contexts[MemoryType.CONVERSATION_SUMMARY].get("messages", [])
            for msg in messages:
                content = msg.get("content", "").lower()
                for entity_name in entity_names:
                    if entity_name in content:
                        insights["entity_conversation_overlap"].append(
                            {
                                "entity": entity_name,
                                "message_role": msg.get("role"),
                                "mentioned_at": "recent",
                            }
                        )

        # Check vector results for entity matches
        if MemoryType.VECTOR_DATABASE in contexts and entity_names:
            vector_results = contexts[MemoryType.VECTOR_DATABASE].get("relevant_documents", [])
            for result in vector_results:
                text = result.get("text", "").lower()
                for entity_name in entity_names:
                    if entity_name in text:
                        insights["vector_entity_matches"].append(
                            {
                                "entity": entity_name,
                                "similarity": result.get("similarity", 0.0),
                                "document_id": result.get("id"),
                            }
                        )

        return insights

    def _generate_context_summary(self, unified_context: Dict[str, Any]) -> str:
        """Generate a summary of the unified context."""
        summary_parts = []

        # Conversation info
        conversation = unified_context.get("conversation", {})
        if conversation.get("recent_messages"):
            msg_count = len(conversation["recent_messages"])
            summary_parts.append(f"{msg_count} recent messages")

        if conversation.get("summary"):
            summary_parts.append("conversation summary available")

        # Entity info
        entities = unified_context.get("entities", {})
        entity_count = entities.get("total_entities", 0)
        if entity_count > 0:
            summary_parts.append(f"{entity_count} tracked entities")

        # Knowledge info
        knowledge = unified_context.get("relevant_knowledge", {})
        if knowledge.get("relevant_documents"):
            doc_count = len(knowledge["relevant_documents"])
            summary_parts.append(f"{doc_count} relevant documents")

        # Working memory info
        reasoning = unified_context.get("reasoning_state", {})
        if reasoning.get("active_items", 0) > 0:
            summary_parts.append(f"active reasoning state")

        if not summary_parts:
            return "No significant context available"

        return "Available context: " + ", ".join(summary_parts)

    async def store_conversation_turn(
        self,
        session_id: str,
        user_id: Optional[str],
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Store a conversation turn across relevant memory types."""
        await self.initialize()

        results = {}

        # Store in conversation memory (hybrid or buffer)
        conversation_data = {
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        if MemoryType.CONVERSATION_SUMMARY in self.memories:
            result = await self.memories[MemoryType.CONVERSATION_SUMMARY].store(conversation_data)
            results["conversation"] = result
        elif MemoryType.CONVERSATION_BUFFER in self.memories:
            result = await self.memories[MemoryType.CONVERSATION_BUFFER].store(conversation_data)
            results["conversation"] = result

        # Extract and store entities if enabled
        if MemoryType.ENTITY_MEMORY in self.memories and role == "user":
            try:
                entity_result = await self.memories[MemoryType.ENTITY_MEMORY].store(
                    {"content": content, "context": {"session_id": session_id}, "user_id": user_id}
                )
                results["entities"] = entity_result
            except Exception as e:
                logger.warning(f"Entity extraction failed: {str(e)}")

        return {
            "stored": True,
            "session_id": session_id,
            "role": role,
            "results": results,
            "stored_at": datetime.utcnow().isoformat(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all memory systems."""
        await self.initialize()

        health_results = {}
        overall_healthy = True

        for memory_type, memory in self.memories.items():
            try:
                health = await memory.health_check()
                health_results[memory_type.value] = health
                if health.get("status") != "healthy":
                    overall_healthy = False
            except Exception as e:
                health_results[memory_type.value] = {"status": "error", "error": str(e)}
                overall_healthy = False

        return {
            "overall_status": "healthy" if overall_healthy else "degraded",
            "memory_systems": health_results,
            "enabled_memories": [m.value for m in self.enabled_memories],
            "checked_at": datetime.utcnow().isoformat(),
        }
