"""
Conversation Summary Memory Implementation.

This provides both short-term conversation buffer AND long-term summarization:
- Short-term buffer for recent context and nuance
- Long-term summary for background facts and history
- Intelligent context selection for LLM consumption
- All-in-one conversation memory solution
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from supabase import Client, create_client

from shared.models.node_enums import GoogleGeminiModel, MemorySubtype

from .base import MemoryBase
from .conversation_buffer import ConversationBufferMemory

logger = logging.getLogger(__name__)


class ConversationSummaryMemory(MemoryBase):
    """
    Conversation Summary Memory with integrated buffer and summarization.

    Features:
    - Short-term buffer for immediate context
    - Long-term summaries for historical context
    - Intelligent context composition for LLM
    - Automatic summary generation triggers
    - Optimal token usage for large conversations
    - Single memory for all conversation needs
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize conversation summary memory.

        Args:
            config: Configuration dict with keys:
                - redis_url: Redis connection URL
                - supabase_url: Supabase project URL
                - supabase_key: Supabase service key
                - google_api_key: Google AI API key for summarization
                - buffer_window_size: Size of short-term buffer (default: 10)
                - summary_context_weight: Weight given to summary vs buffer (default: 0.3)
                - max_total_tokens: Maximum tokens for combined context (default: 4000)
                - auto_summarize: Whether to automatically trigger summarization (default: True)
                - summarization_model: Gemini model to use (default: 'gemini-2.0-flash-exp')
                - summary_trigger: When to trigger summary ('message_count', 'token_count', 'time_interval')
                - trigger_threshold: Threshold for triggering (default: 10)
        """
        super().__init__(config)

        # Hybrid-specific configuration
        self.buffer_window_size = config.get("buffer_window_size", 10)
        self.summary_context_weight = config.get("summary_context_weight", 0.3)
        self.max_total_tokens = config.get("max_total_tokens", 4000)
        self.auto_summarize = config.get("auto_summarize", True)

        # Summarization configuration
        self.google_api_key = config.get("google_api_key")
        self.summarization_model = config.get(
            "summarization_model", GoogleGeminiModel.GEMINI_2_5_FLASH.value
        )
        self.summary_trigger = config.get("summary_trigger", "message_count")
        self.trigger_threshold = config.get("trigger_threshold", 10)

        # Component memories
        self.buffer_memory: Optional[ConversationBufferMemory] = None
        self.supabase_client: Optional[Client] = None
        self.model = None

    async def _setup(self) -> None:
        """Setup buffer memory and summarization components."""
        try:
            # Configure buffer memory
            buffer_config = self.config.copy()
            buffer_config["window_size"] = self.buffer_window_size
            self.buffer_memory = ConversationBufferMemory(buffer_config)
            await self.buffer_memory.initialize()

            # Setup Supabase for summary storage
            if self.config.get("supabase_url") and self.config.get("supabase_key"):
                supabase_url = self.config["supabase_url"]
                supabase_key = self.config["supabase_key"]
                self.supabase_client = create_client(supabase_url, supabase_key)

            # Setup Gemini for summarization
            if self.google_api_key:
                import google.generativeai as genai

                genai.configure(api_key=self.google_api_key)
                self.model = genai.GenerativeModel(self.summarization_model)

            logger.info("HybridConversationMemory initialized successfully")

        except Exception as e:
            logger.error(f"Failed to setup HybridConversationMemory: {str(e)}")
            raise

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store a conversation message and handle summarization.

        Args:
            data: Message data with keys:
                - session_id: Session identifier
                - user_id: User identifier (optional)
                - role: Message role ('user', 'assistant', 'system')
                - content: Message content
                - timestamp: Message timestamp (optional)
                - metadata: Additional metadata (optional)

        Returns:
            Dict with storage confirmation and summary status
        """
        await self.initialize()

        try:
            # Store in buffer memory (primary storage)
            buffer_result = await self.buffer_memory.store(data)

            result = {
                "stored": buffer_result["stored"],
                "message_index": buffer_result.get("message_index"),
                "session_id": data["session_id"],
                "timestamp": buffer_result.get("timestamp"),
                "summary_generated": False,
            }

            # Trigger summary generation if auto-summarize is enabled
            if self.auto_summarize and buffer_result["stored"] and self.model:
                try:
                    summary_result = await self._check_and_generate_summary(
                        data["session_id"], data.get("user_id")
                    )
                    result["summary_generated"] = summary_result.get("summary_generated", False)
                    if result["summary_generated"]:
                        result["summary_id"] = summary_result.get("summary_id")
                except Exception as e:
                    logger.warning(f"Summary generation failed: {str(e)}")

            return result

        except Exception as e:
            logger.error(f"Failed to store message in hybrid memory: {str(e)}")
            raise

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve conversation data from both buffer and summary.

        Args:
            query: Query dict with keys:
                - session_id: Session identifier
                - include_buffer: Include buffer messages (default: True)
                - include_summary: Include summary (default: True)
                - buffer_limit: Limit for buffer messages

        Returns:
            Dict with both buffer messages and summary
        """
        await self.initialize()

        try:
            session_id = query["session_id"]
            include_buffer = query.get("include_buffer", True)
            include_summary = query.get("include_summary", True)
            buffer_limit = query.get("buffer_limit", self.buffer_window_size)

            result = {"session_id": session_id, "retrieved_at": datetime.utcnow().isoformat()}

            # Retrieve buffer messages
            if include_buffer:
                buffer_data = await self.buffer_memory.retrieve(
                    {"session_id": session_id, "limit": buffer_limit, "include_metadata": True}
                )
                result.update(
                    {
                        "buffer_messages": buffer_data.get("messages", []),
                        "buffer_count": buffer_data.get("total_count", 0),
                    }
                )

            # Retrieve summary
            if include_summary and self.supabase_client:
                summary_data = await self._get_latest_summary(session_id)
                result.update({"summary": summary_data, "has_summary": summary_data is not None})

            return result

        except Exception as e:
            logger.error(f"Failed to retrieve hybrid conversation data: {str(e)}")
            raise

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get optimized conversation context for LLM consumption.

        This intelligently combines summary and buffer data to provide the best context
        within token limits.

        Args:
            query: Query dict with session_id and optional parameters:
                - prioritize_recency: Prioritize recent messages over summary (default: True)
                - context_strategy: 'balanced', 'summary_heavy', 'buffer_heavy' (default: 'balanced')

        Returns:
            Dict with optimized context for LLM
        """
        await self.initialize()

        try:
            session_id = query["session_id"]
            prioritize_recency = query.get("prioritize_recency", True)
            context_strategy = query.get("context_strategy", "balanced")

            # Get both buffer and summary data
            data = await self.retrieve(
                {"session_id": session_id, "include_buffer": True, "include_summary": True}
            )

            buffer_messages = data.get("buffer_messages", [])
            summary_data = data.get("summary")

            # Calculate token usage
            buffer_tokens = self._estimate_tokens_for_messages(buffer_messages)
            summary_tokens = self._estimate_tokens(
                summary_data.get("summary", "") if summary_data else ""
            )
            total_estimated_tokens = buffer_tokens + summary_tokens

            # Determine context composition strategy
            context = await self._compose_context(
                buffer_messages,
                summary_data,
                context_strategy,
                total_estimated_tokens,
                prioritize_recency,
            )

            # Add hybrid-specific metadata
            context["hybrid_info"] = {
                "buffer_messages_count": len(buffer_messages),
                "has_summary": summary_data is not None,
                "total_estimated_tokens": total_estimated_tokens,
                "context_strategy": context_strategy,
                "composition_method": context.get("_composition_method", "unknown"),
            }

            # Remove internal metadata
            context.pop("_composition_method", None)

            return context

        except Exception as e:
            logger.error(f"Failed to get hybrid conversation context: {str(e)}")
            raise

    async def _check_and_generate_summary(
        self, session_id: str, user_id: Optional[str]
    ) -> Dict[str, Any]:
        """Check if summary should be generated and create it if needed."""
        try:
            # Get recent messages for analysis
            buffer_data = await self.buffer_memory.retrieve(
                {"session_id": session_id, "limit": 1000, "include_metadata": True}
            )
            messages = buffer_data.get("messages", [])

            if not messages:
                return {"summary_generated": False, "reason": "No messages to summarize"}

            # Check if summary should be triggered
            should_summarize = await self._should_trigger_summary(session_id, messages)

            if not should_summarize:
                return {"summary_generated": False, "reason": "Summary trigger not met"}

            # Generate summary
            summary_data = await self._generate_summary(session_id, user_id, messages)

            # Store summary
            await self._store_summary(summary_data)

            logger.info(f"Generated summary for session {session_id} with {len(messages)} messages")

            return {
                "summary_generated": True,
                "summary_id": summary_data["id"],
                "session_id": session_id,
                "message_count": len(messages),
                "summary_length": len(summary_data["summary"]),
            }

        except Exception as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            return {"summary_generated": False, "error": str(e)}

    async def _should_trigger_summary(
        self, session_id: str, messages: List[Dict[str, Any]]
    ) -> bool:
        """Check if summary should be triggered based on configured criteria."""
        try:
            if self.summary_trigger == "message_count":
                return len(messages) >= self.trigger_threshold

            elif self.summary_trigger == "token_count":
                total_tokens = sum(msg.get("tokens_count", 0) for msg in messages)
                return total_tokens >= self.trigger_threshold

            elif self.summary_trigger == "time_interval":
                if not messages:
                    return False

                last_message_time = datetime.fromisoformat(
                    messages[-1]["timestamp"].replace("Z", "+00:00")
                )

                # Check if last summary was created before threshold
                latest_summary = await self._get_latest_summary(session_id)

                if not latest_summary:
                    return True  # No previous summary

                last_summary_time = datetime.fromisoformat(
                    latest_summary["created_at"].replace("Z", "+00:00")
                )

                time_diff = (last_message_time - last_summary_time).total_seconds() / 60
                return time_diff >= self.trigger_threshold  # threshold in minutes

            return False

        except Exception as e:
            logger.error(f"Failed to check summary trigger: {str(e)}")
            return False

    async def _generate_summary(
        self, session_id: str, user_id: Optional[str], messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate summary using Gemini."""
        try:
            # Get previous summary for progressive summarization
            previous_summary = await self._get_latest_summary(session_id)

            # Create conversation text
            conversation_text = self._format_messages_for_summary(messages)

            # Create prompt
            prompt = self._create_summary_prompt(conversation_text, previous_summary)

            # Generate summary using Gemini
            response = await self._call_gemini_async(prompt)

            # Parse response
            summary_result = self._parse_summary_response(response)

            # Prepare summary data
            summary_data = {
                "session_id": session_id,
                "user_id": user_id,
                "summary": summary_result.get("summary", ""),
                "key_points": summary_result.get("key_points", []),
                "entities": summary_result.get("entities", []),
                "topics": summary_result.get("topics", []),
                "summary_type": "progressive",
                "message_count": len(messages),
                "token_count": sum(msg.get("tokens_count", 0) for msg in messages),
                "model_used": self.summarization_model,
                "confidence_score": 0.8,  # Default confidence
                "previous_summary_id": previous_summary.get("id") if previous_summary else None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            return summary_data

        except Exception as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise

    def _format_messages_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for summary generation."""
        formatted_lines = []

        for msg in messages:
            role = msg["role"].upper()
            content = msg["content"]
            timestamp = msg.get("timestamp", "")

            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                    formatted_lines.append(f"[{time_str}] {role}: {content}")
                except:
                    formatted_lines.append(f"{role}: {content}")
            else:
                formatted_lines.append(f"{role}: {content}")

        return "\n".join(formatted_lines)

    def _create_summary_prompt(
        self, conversation_text: str, previous_summary: Optional[Dict[str, Any]]
    ) -> str:
        """Create prompt for summary generation."""
        base_instructions = """
You are a conversation summarization expert. Create a comprehensive summary for LLM context.

REQUIREMENTS:
1. Create a clear, concise summary capturing key information
2. Extract important entities (people, organizations, locations, products, concepts)
3. Identify main topics discussed
4. Highlight key points and decisions
5. Preserve important context for future reference

PROGRESSIVE SUMMARIZATION:
- Build upon previous summary if provided
- Focus on new information while maintaining historical context
- Update entities and topics with new mentions
"""

        prompt_parts = [base_instructions]

        if previous_summary:
            prompt_parts.append(
                f"""
PREVIOUS SUMMARY:
{previous_summary.get('summary', '')}

PREVIOUS ENTITIES: {', '.join(previous_summary.get('entities', []))}
PREVIOUS TOPICS: {', '.join(previous_summary.get('topics', []))}
"""
            )

        prompt_parts.extend(
            [
                f"\nCONVERSATION TO SUMMARIZE:\n{conversation_text}",
                """
Provide response in JSON format:
{
    "summary": "Comprehensive summary here",
    "key_points": ["Key point 1", "Key point 2", ...],
    "entities": ["Entity 1", "Entity 2", ...],
    "topics": ["Topic 1", "Topic 2", ...]
}
""",
            ]
        )

        return "\n".join(prompt_parts)

    async def _call_gemini_async(self, prompt: str) -> str:
        """Call Gemini API asynchronously."""

        def _call_gemini_sync():
            response = self.model.generate_content(prompt)
            return response.text

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call_gemini_sync)

    def _parse_summary_response(self, response: str) -> Dict[str, Any]:
        """Parse Gemini response."""
        try:
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {"summary": response.strip(), "key_points": [], "entities": [], "topics": []}
        except Exception as e:
            logger.warning(f"Failed to parse summary response: {str(e)}")
            return {"summary": response.strip(), "key_points": [], "entities": [], "topics": []}

    async def _store_summary(self, summary_data: Dict[str, Any]) -> None:
        """Store summary in Supabase."""
        if not self.supabase_client:
            return

        try:
            result = (
                self.supabase_client.table("conversation_summaries").insert(summary_data).execute()
            )
            if result.data:
                summary_data["id"] = result.data[0]["id"]
        except Exception as e:
            logger.error(f"Failed to store summary: {str(e)}")
            raise

    async def _get_latest_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest summary for a session."""
        if not self.supabase_client:
            return None

        try:
            result = (
                self.supabase_client.table("conversation_summaries")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            return result.data[0] if result.data else None

        except Exception as e:
            logger.warning(f"Failed to get latest summary: {str(e)}")
            return None

    async def _compose_context(
        self,
        buffer_messages: List[Dict[str, Any]],
        summary_data: Optional[Dict[str, Any]],
        strategy: str,
        total_tokens: int,
        prioritize_recency: bool,
    ) -> Dict[str, Any]:
        """Compose optimal context based on strategy."""

        # If no summary exists, return buffer context only
        if not summary_data:
            return {
                "messages": [
                    {"role": msg["role"], "content": msg["content"]} for msg in buffer_messages
                ],
                "summary": "",
                "key_points": [],
                "entities": [],
                "topics": [],
                "total_tokens": self._estimate_tokens_for_messages(buffer_messages),
                "memory_type": MemorySubtype.CONVERSATION_SUMMARY.value,
                "_composition_method": "buffer_only",
            }

        # If within token limit, return both
        if total_tokens <= self.max_total_tokens:
            return {
                "messages": [
                    {"role": msg["role"], "content": msg["content"]} for msg in buffer_messages
                ],
                "summary": summary_data.get("summary", ""),
                "key_points": summary_data.get("key_points", []),
                "entities": summary_data.get("entities", []),
                "topics": summary_data.get("topics", []),
                "total_tokens": total_tokens,
                "memory_type": MemorySubtype.CONVERSATION_SUMMARY.value,
                "_composition_method": "full_context",
            }

        # Need to optimize for token limits
        if strategy == "summary_heavy":
            return self._create_summary_heavy_context(buffer_messages, summary_data)
        elif strategy == "buffer_heavy":
            return self._create_buffer_heavy_context(buffer_messages, summary_data)
        else:  # balanced
            return self._create_balanced_context(buffer_messages, summary_data, prioritize_recency)

    def _create_summary_heavy_context(
        self, buffer_messages: List[Dict[str, Any]], summary_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create context prioritizing summary over buffer."""
        # Use summary + minimal recent messages
        recent_messages = buffer_messages[-3:] if len(buffer_messages) > 3 else buffer_messages

        return {
            "messages": [
                {"role": msg["role"], "content": msg["content"]} for msg in recent_messages
            ],
            "summary": summary_data.get("summary", ""),
            "key_points": summary_data.get("key_points", []),
            "entities": summary_data.get("entities", []),
            "topics": summary_data.get("topics", []),
            "total_tokens": self._estimate_tokens_for_messages(recent_messages)
            + self._estimate_tokens(summary_data.get("summary", "")),
            "memory_type": "CONVERSATION_SUMMARY",
            "_composition_method": "summary_heavy",
        }

    def _create_buffer_heavy_context(
        self, buffer_messages: List[Dict[str, Any]], summary_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create context prioritizing buffer over summary."""
        # Use full buffer + condensed summary
        condensed_summary = self._condense_summary(summary_data)

        return {
            "messages": [
                {"role": msg["role"], "content": msg["content"]} for msg in buffer_messages
            ],
            "summary": condensed_summary,
            "key_points": summary_data.get("key_points", [])[:3],
            "entities": summary_data.get("entities", [])[:5],
            "topics": summary_data.get("topics", [])[:3],
            "total_tokens": self._estimate_tokens_for_messages(buffer_messages)
            + self._estimate_tokens(condensed_summary),
            "memory_type": "CONVERSATION_SUMMARY",
            "_composition_method": "buffer_heavy",
        }

    def _create_balanced_context(
        self,
        buffer_messages: List[Dict[str, Any]],
        summary_data: Dict[str, Any],
        prioritize_recency: bool,
    ) -> Dict[str, Any]:
        """Create balanced context with optimal token distribution."""
        target_summary_tokens = int(self.max_total_tokens * self.summary_context_weight)
        target_buffer_tokens = self.max_total_tokens - target_summary_tokens

        # Adjust summary
        summary_text = summary_data.get("summary", "")
        if self._estimate_tokens(summary_text) > target_summary_tokens:
            summary_text = self._truncate_text(summary_text, target_summary_tokens)

        # Adjust buffer messages
        if prioritize_recency:
            adjusted_messages = []
            current_tokens = 0

            for msg in reversed(buffer_messages):
                msg_tokens = self._estimate_tokens(msg.get("content", ""))
                if current_tokens + msg_tokens <= target_buffer_tokens:
                    adjusted_messages.insert(0, msg)
                    current_tokens += msg_tokens
                else:
                    break
        else:
            adjusted_messages = buffer_messages

        return {
            "messages": [
                {"role": msg["role"], "content": msg["content"]} for msg in adjusted_messages
            ],
            "summary": summary_text,
            "key_points": summary_data.get("key_points", [])[:5],
            "entities": summary_data.get("entities", [])[:8],
            "topics": summary_data.get("topics", [])[:5],
            "total_tokens": self._estimate_tokens_for_messages(adjusted_messages)
            + self._estimate_tokens(summary_text),
            "memory_type": "CONVERSATION_SUMMARY",
            "_composition_method": "balanced",
        }

    def _condense_summary(self, summary_data: Dict[str, Any]) -> str:
        """Create condensed version of summary."""
        summary = summary_data.get("summary", "")
        key_points = summary_data.get("key_points", [])

        if not summary:
            return ""

        if len(summary) <= 300:
            return summary

        condensed_parts = []
        sentences = summary.split(". ")
        if sentences:
            condensed_parts.append(sentences[0] + ".")

        if key_points:
            condensed_parts.append("Key points: " + "; ".join(key_points[:3]))

        return " ".join(condensed_parts)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        return max(1, len(str(text)) // 4)

    def _estimate_tokens_for_messages(self, messages: List[Dict[str, Any]]) -> int:
        """Estimate total tokens for messages."""
        return sum(self._estimate_tokens(msg.get("content", "")) for msg in messages)

    def _truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to max tokens."""
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        last_space = truncated.rfind(" ")
        if last_space > max_chars * 0.8:
            return truncated[:last_space] + "..."
        else:
            return truncated + "..."

    async def force_summarize(
        self, session_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Force generation of a new summary."""
        await self.initialize()
        return await self._check_and_generate_summary(session_id, user_id)

    async def get_session_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics for a conversation session."""
        await self.initialize()

        try:
            # Get buffer stats
            buffer_stats = await self.buffer_memory.get_session_stats(session_id)

            # Get summary data
            summary_data = await self._get_latest_summary(session_id)

            analytics = {
                "session_id": session_id,
                "message_analytics": buffer_stats,
                "summary_analytics": {
                    "has_summary": summary_data is not None,
                    "latest_summary_date": summary_data.get("created_at") if summary_data else None,
                    "summary_length": len(summary_data.get("summary", "")) if summary_data else 0,
                    "entities_count": len(summary_data.get("entities", [])) if summary_data else 0,
                    "key_points_count": len(summary_data.get("key_points", []))
                    if summary_data
                    else 0,
                },
                "generated_at": datetime.utcnow().isoformat(),
            }

            return analytics

        except Exception as e:
            logger.error(f"Failed to get session analytics: {str(e)}")
            raise
