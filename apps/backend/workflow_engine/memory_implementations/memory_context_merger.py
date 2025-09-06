"""
Memory Context Merger Utility.

This utility provides intelligent merging and optimization of multiple memory contexts
for LLM consumption, handling token limits and priority-based content selection.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MemoryPriority(Enum):
    """Memory context priority levels."""

    CRITICAL = 1.0  # Must include (conversation context)
    HIGH = 0.8  # Very important (recent entities, working memory)
    MEDIUM = 0.6  # Important (vector search results)
    LOW = 0.4  # Nice to have (episodic events)
    MINIMAL = 0.2  # Only if space available


@dataclass
class MemoryContext:
    """Structured memory context with metadata."""

    memory_type: str
    context: Dict[str, Any]
    priority: float = 0.5
    estimated_tokens: int = 0
    source_node_id: Optional[str] = None
    timestamp: Optional[str] = None


class MemoryContextMerger:
    """
    Intelligent memory context merger for LLM integration.

    Features:
    - Token-aware context optimization
    - Priority-based content selection
    - Multiple merge strategies
    - Context deduplication
    - Token estimation and management
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize memory context merger.

        Args:
            config: Configuration dict with keys:
                - max_total_tokens: Maximum tokens for merged context (default: 4000)
                - merge_strategy: Strategy for merging contexts (default: 'priority')
                - token_buffer: Safety buffer for token estimates (default: 0.1)
                - enable_deduplication: Remove duplicate content (default: True)
        """
        config = config or {}

        self.max_total_tokens = config.get("max_total_tokens", 4000)
        self.merge_strategy = config.get("merge_strategy", "priority")
        self.token_buffer = config.get("token_buffer", 0.1)  # 10% safety buffer
        self.enable_deduplication = config.get("enable_deduplication", True)

        # Strategy functions
        self.merge_strategies = {
            "priority": self._merge_by_priority,
            "balanced": self._merge_balanced,
            "conversation_first": self._merge_conversation_first,
            "semantic": self._merge_semantic,
        }

    def merge_contexts(
        self,
        memory_contexts: List[MemoryContext],
        user_message: str,
        merge_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Merge multiple memory contexts into optimized LLM input.

        Args:
            memory_contexts: List of memory contexts to merge
            user_message: Current user message/query
            merge_strategy: Override default merge strategy

        Returns:
            Dict with merged context ready for LLM consumption
        """
        try:
            if not memory_contexts:
                return {
                    "merged_context": "",
                    "user_message": user_message,
                    "memory_summary": {},
                    "total_estimated_tokens": self._estimate_tokens(user_message),
                    "contexts_included": 0,
                    "contexts_dropped": 0,
                }

            # Use specified strategy or default
            strategy = merge_strategy or self.merge_strategy
            merge_func = self.merge_strategies.get(strategy, self._merge_by_priority)

            # Apply deduplication if enabled
            if self.enable_deduplication:
                memory_contexts = self._deduplicate_contexts(memory_contexts)

            # Execute merge strategy
            result = merge_func(memory_contexts, user_message)

            return result

        except Exception as e:
            logger.error(f"Error merging memory contexts: {e}")
            return {
                "merged_context": "",
                "user_message": user_message,
                "memory_summary": {"error": str(e)},
                "total_estimated_tokens": self._estimate_tokens(user_message),
                "contexts_included": 0,
                "contexts_dropped": len(memory_contexts),
            }

    def _merge_by_priority(
        self, contexts: List[MemoryContext], user_message: str
    ) -> Dict[str, Any]:
        """Merge contexts by priority, fitting within token limits."""
        # Sort by priority (descending)
        sorted_contexts = sorted(contexts, key=lambda x: x.priority, reverse=True)

        # Calculate available tokens
        user_tokens = self._estimate_tokens(user_message)
        available_tokens = int(self.max_total_tokens * (1 - self.token_buffer)) - user_tokens

        # Select contexts within token limit
        selected_contexts = []
        used_tokens = 0

        for context in sorted_contexts:
            if used_tokens + context.estimated_tokens <= available_tokens:
                selected_contexts.append(context)
                used_tokens += context.estimated_tokens
            elif not selected_contexts:  # Always include at least one context if possible
                # Truncate the highest priority context to fit
                truncated_context = self._truncate_context(context, available_tokens)
                if truncated_context:
                    selected_contexts.append(truncated_context)
                    used_tokens += truncated_context.estimated_tokens
                break

        # Build merged context
        context_parts = []
        memory_summary = {}

        for context in selected_contexts:
            formatted_context = self._format_context(context)
            if formatted_context:
                context_parts.append(formatted_context)
                memory_summary[context.memory_type] = {
                    "priority": context.priority,
                    "tokens": context.estimated_tokens,
                    "included": True,
                }

        # Track dropped contexts
        for context in sorted_contexts:
            if context not in selected_contexts:
                memory_summary[context.memory_type] = {
                    "priority": context.priority,
                    "tokens": context.estimated_tokens,
                    "included": False,
                    "reason": "token_limit_exceeded",
                }

        merged_context = "\n\n".join(context_parts)
        total_tokens = user_tokens + used_tokens

        return {
            "merged_context": merged_context,
            "user_message": user_message,
            "memory_summary": memory_summary,
            "total_estimated_tokens": total_tokens,
            "contexts_included": len(selected_contexts),
            "contexts_dropped": len(contexts) - len(selected_contexts),
            "merge_strategy": "priority",
        }

    def _merge_balanced(self, contexts: List[MemoryContext], user_message: str) -> Dict[str, Any]:
        """Balanced merge ensuring representation from different memory types."""
        # Group contexts by type
        context_groups = {}
        for context in contexts:
            if context.memory_type not in context_groups:
                context_groups[context.memory_type] = []
            context_groups[context.memory_type].append(context)

        # Calculate token allocation per group
        user_tokens = self._estimate_tokens(user_message)
        available_tokens = int(self.max_total_tokens * (1 - self.token_buffer)) - user_tokens
        tokens_per_group = available_tokens // len(context_groups)

        selected_contexts = []
        used_tokens = 0

        # Select best context from each group within allocation
        for group_name, group_contexts in context_groups.items():
            # Sort by priority within group
            sorted_group = sorted(group_contexts, key=lambda x: x.priority, reverse=True)

            group_tokens = 0
            for context in sorted_group:
                if group_tokens + context.estimated_tokens <= tokens_per_group:
                    selected_contexts.append(context)
                    group_tokens += context.estimated_tokens
                    used_tokens += context.estimated_tokens
                elif group_tokens == 0:  # Include at least one from each group
                    truncated = self._truncate_context(context, tokens_per_group)
                    if truncated:
                        selected_contexts.append(truncated)
                        used_tokens += truncated.estimated_tokens
                    break

        # Use remaining tokens for highest priority contexts not yet included
        remaining_tokens = available_tokens - used_tokens
        remaining_contexts = [c for c in contexts if c not in selected_contexts]
        remaining_contexts.sort(key=lambda x: x.priority, reverse=True)

        for context in remaining_contexts:
            if context.estimated_tokens <= remaining_tokens:
                selected_contexts.append(context)
                remaining_tokens -= context.estimated_tokens

        return self._build_merge_result(selected_contexts, contexts, user_message, "balanced")

    def _merge_conversation_first(
        self, contexts: List[MemoryContext], user_message: str
    ) -> Dict[str, Any]:
        """Prioritize conversation memory, then add others by priority."""
        # Separate conversation contexts from others
        conversation_contexts = [c for c in contexts if "conversation" in c.memory_type.lower()]
        other_contexts = [c for c in contexts if "conversation" not in c.memory_type.lower()]

        user_tokens = self._estimate_tokens(user_message)
        available_tokens = int(self.max_total_tokens * (1 - self.token_buffer)) - user_tokens

        selected_contexts = []
        used_tokens = 0

        # First, include all conversation contexts
        for context in sorted(conversation_contexts, key=lambda x: x.priority, reverse=True):
            if used_tokens + context.estimated_tokens <= available_tokens:
                selected_contexts.append(context)
                used_tokens += context.estimated_tokens
            elif not selected_contexts:  # Always include at least one conversation context
                truncated = self._truncate_context(context, available_tokens)
                if truncated:
                    selected_contexts.append(truncated)
                    used_tokens += truncated.estimated_tokens
                break

        # Then add other contexts by priority
        remaining_tokens = available_tokens - used_tokens
        for context in sorted(other_contexts, key=lambda x: x.priority, reverse=True):
            if context.estimated_tokens <= remaining_tokens:
                selected_contexts.append(context)
                remaining_tokens -= context.estimated_tokens

        return self._build_merge_result(
            selected_contexts, contexts, user_message, "conversation_first"
        )

    def _merge_semantic(self, contexts: List[MemoryContext], user_message: str) -> Dict[str, Any]:
        """Merge based on semantic relevance to user message."""
        # Calculate relevance scores (simplified version)
        scored_contexts = []
        user_words = set(user_message.lower().split())

        for context in contexts:
            relevance_score = self._calculate_relevance(context, user_words)
            # Combine relevance with priority
            combined_score = (relevance_score * 0.6) + (context.priority * 0.4)
            scored_contexts.append((combined_score, context))

        # Sort by combined score
        scored_contexts.sort(key=lambda x: x[0], reverse=True)

        # Select contexts within token limit
        user_tokens = self._estimate_tokens(user_message)
        available_tokens = int(self.max_total_tokens * (1 - self.token_buffer)) - user_tokens

        selected_contexts = []
        used_tokens = 0

        for score, context in scored_contexts:
            if used_tokens + context.estimated_tokens <= available_tokens:
                selected_contexts.append(context)
                used_tokens += context.estimated_tokens

        return self._build_merge_result(selected_contexts, contexts, user_message, "semantic")

    def _calculate_relevance(self, context: MemoryContext, user_words: set) -> float:
        """Calculate relevance score between context and user message."""
        try:
            # Extract text from context for comparison
            context_text = ""
            if isinstance(context.context, dict):
                for key, value in context.context.items():
                    if isinstance(value, str):
                        context_text += f" {value}"
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                context_text += f" {item}"
                            elif isinstance(item, dict) and "content" in item:
                                context_text += f" {item['content']}"

            context_words = set(context_text.lower().split())

            if not context_words:
                return 0.0

            # Calculate word overlap
            overlap = len(user_words.intersection(context_words))
            relevance = overlap / (len(user_words) + len(context_words) - overlap)

            return min(relevance * 2, 1.0)  # Scale up and cap at 1.0

        except Exception:
            return 0.0

    def _deduplicate_contexts(self, contexts: List[MemoryContext]) -> List[MemoryContext]:
        """Remove duplicate or highly similar contexts."""
        if len(contexts) <= 1:
            return contexts

        deduplicated = []
        seen_signatures = set()

        for context in contexts:
            signature = self._get_context_signature(context)
            if signature not in seen_signatures:
                deduplicated.append(context)
                seen_signatures.add(signature)

        return deduplicated

    def _get_context_signature(self, context: MemoryContext) -> str:
        """Generate signature for context deduplication."""
        try:
            # Create a simple signature based on memory type and key content
            sig_parts = [context.memory_type]

            if isinstance(context.context, dict):
                # Add key strings from context
                for key, value in list(context.context.items())[:3]:  # First 3 keys
                    if isinstance(value, str):
                        sig_parts.append(value[:50])  # First 50 chars
                    elif isinstance(value, list) and value:
                        sig_parts.append(str(value[0])[:50])

            return hash("|".join(sig_parts)) % 10000  # Simple hash mod

        except Exception:
            return f"{context.memory_type}_{hash(str(context.context)) % 10000}"

    def _truncate_context(self, context: MemoryContext, max_tokens: int) -> Optional[MemoryContext]:
        """Truncate context to fit within token limit."""
        if context.estimated_tokens <= max_tokens:
            return context

        try:
            # Calculate truncation ratio
            ratio = max_tokens / context.estimated_tokens

            truncated_context = context.context.copy()

            # Truncate text fields
            for key, value in truncated_context.items():
                if isinstance(value, str):
                    target_length = int(len(value) * ratio)
                    truncated_context[key] = (
                        value[:target_length] + "..." if target_length < len(value) else value
                    )
                elif isinstance(value, list):
                    target_count = max(1, int(len(value) * ratio))
                    truncated_context[key] = value[:target_count]

            return MemoryContext(
                memory_type=context.memory_type,
                context=truncated_context,
                priority=context.priority,
                estimated_tokens=max_tokens,
                source_node_id=context.source_node_id,
                timestamp=context.timestamp,
            )

        except Exception as e:
            logger.error(f"Error truncating context: {e}")
            return None

    def _format_context(self, context: MemoryContext) -> str:
        """Format individual memory context for LLM consumption."""
        try:
            parts = [f"## {context.memory_type.replace('_', ' ').title()} Memory"]

            if isinstance(context.context, dict):
                for key, value in context.context.items():
                    if key in ["context_text", "summary", "content"]:
                        parts.append(f"{value}")
                    elif key == "messages" and isinstance(value, list):
                        parts.append("Recent conversation:")
                        for msg in value[-3:]:  # Last 3 messages
                            if isinstance(msg, dict):
                                role = msg.get("role", "unknown")
                                content = msg.get("content", "")
                                parts.append(f"- {role}: {content}")
                    elif key == "entities" and isinstance(value, list):
                        if value:
                            parts.append(
                                f"Relevant entities: {', '.join([e.get('name', str(e)) for e in value[:5]])}"
                            )
                    elif key == "results" and isinstance(value, list):
                        parts.append("Search results:")
                        for result in value[:3]:  # Top 3 results
                            if isinstance(result, dict) and "text" in result:
                                parts.append(f"- {result['text']}")

            return "\n".join(parts)

        except Exception as e:
            logger.error(f"Error formatting context: {e}")
            return f"## {context.memory_type} Memory\n[Context formatting error]"

    def _build_merge_result(
        self,
        selected_contexts: List[MemoryContext],
        all_contexts: List[MemoryContext],
        user_message: str,
        strategy: str,
    ) -> Dict[str, Any]:
        """Build standardized merge result."""
        context_parts = []
        memory_summary = {}
        used_tokens = 0

        for context in selected_contexts:
            formatted_context = self._format_context(context)
            if formatted_context:
                context_parts.append(formatted_context)
                used_tokens += context.estimated_tokens
                memory_summary[context.memory_type] = {
                    "priority": context.priority,
                    "tokens": context.estimated_tokens,
                    "included": True,
                }

        # Track dropped contexts
        for context in all_contexts:
            if context not in selected_contexts:
                memory_summary[context.memory_type] = {
                    "priority": context.priority,
                    "tokens": context.estimated_tokens,
                    "included": False,
                    "reason": "not_selected_by_strategy",
                }

        merged_context = "\n\n".join(context_parts)
        total_tokens = self._estimate_tokens(user_message) + used_tokens

        return {
            "merged_context": merged_context,
            "user_message": user_message,
            "memory_summary": memory_summary,
            "total_estimated_tokens": total_tokens,
            "contexts_included": len(selected_contexts),
            "contexts_dropped": len(all_contexts) - len(selected_contexts),
            "merge_strategy": strategy,
        }

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        if not text:
            return 0
        # Rough estimate: 1 token per 4 characters
        return len(str(text)) // 4

    def create_memory_context(
        self,
        memory_type: str,
        context_data: Dict[str, Any],
        priority: Optional[float] = None,
        source_node_id: Optional[str] = None,
    ) -> MemoryContext:
        """Helper to create MemoryContext from memory node output."""
        # Auto-detect priority based on memory type if not specified
        if priority is None:
            priority_map = {
                "conversation_summary": MemoryPriority.CRITICAL.value,
                "conversation_buffer": MemoryPriority.CRITICAL.value,
                "entity_memory": MemoryPriority.HIGH.value,
                "working_memory": MemoryPriority.HIGH.value,
                "vector_database": MemoryPriority.MEDIUM.value,
                "document_store": MemoryPriority.MEDIUM.value,
                "episodic_memory": MemoryPriority.LOW.value,
                "key_value_store": MemoryPriority.LOW.value,
            }
            priority = priority_map.get(memory_type.lower(), 0.5)

        # Estimate tokens from context data
        context_text = str(context_data)
        estimated_tokens = self._estimate_tokens(context_text)

        return MemoryContext(
            memory_type=memory_type,
            context=context_data,
            priority=priority,
            estimated_tokens=estimated_tokens,
            source_node_id=source_node_id,
        )
