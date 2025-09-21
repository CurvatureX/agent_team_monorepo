"""
Incremental Conversation Summary Memory Implementation.

This provides conversation summarization that:
- Creates/updates summary every time a new message is added
- Uses previous summary + recent 5 rounds of conversation to create updated summary
- Maintains comprehensive context for LLM while keeping summaries manageable
- Updates existing summary records with each new conversation activity
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from shared.models.node_enums import GoogleGeminiModel, MemorySubtype

from .base import MemoryBase
from .conversation_buffer import ConversationBufferMemory

logger = logging.getLogger(__name__)


class ConversationSummaryMemory(MemoryBase):
    """
    Incremental Conversation Summary Memory.

    Features:
    - Creates/updates summary every time new messages are added
    - Combines previous summary with recent 5 rounds of conversation
    - Maintains comprehensive LLM context while keeping summaries manageable
    - Updates existing summary records with incremental changes
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize incremental conversation summary memory.

        Args:
            config: Configuration dict with keys:
                - redis_url: Redis connection URL
                - supabase_url: Supabase project URL
                - supabase_key: Supabase service key
                - google_api_key: Google AI API key for summarization
        """
        super().__init__(config)

        # Simple configuration - only what we need
        self.google_api_key = config.get("google_api_key")
        self.summarization_model = GoogleGeminiModel.GEMINI_2_5_FLASH.value

        # Components
        self.buffer_memory: Optional[ConversationBufferMemory] = None
        self.supabase_client: Optional[Client] = None
        self.model = None

    async def _setup(self) -> None:
        """Setup simple memory components."""
        try:
            # Configure buffer memory
            self.buffer_memory = ConversationBufferMemory(self.config)
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

            logger.info("ConversationSummaryMemory initialized successfully")

        except Exception as e:
            logger.error(f"Failed to setup ConversationSummaryMemory: {str(e)}")
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
            # Store in buffer memory
            buffer_result = await self.buffer_memory.store(data)

            result = {
                "stored": buffer_result["stored"],
                "message_index": buffer_result.get("message_index"),
                "session_id": data["session_id"],
                "timestamp": buffer_result.get("timestamp"),
                "summary_generated": False,
            }

            # Check if we should trigger summary (after 5 rounds)
            if buffer_result["stored"] and self.model:
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
            logger.error(f"Failed to store message in summary memory: {str(e)}")
            raise

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve conversation data from both buffer and summary.

        Args:
            query: Query dict with keys:
                - session_id: Session identifier

        Returns:
            Dict with both buffer messages and summary
        """
        await self.initialize()

        try:
            session_id = query["session_id"]

            result = {"session_id": session_id, "retrieved_at": datetime.utcnow().isoformat()}

            # Get buffer messages
            buffer_data = await self.buffer_memory.retrieve({"session_id": session_id})
            result["messages"] = buffer_data.get("messages", [])

            # Get summary
            if self.supabase_client:
                summary_data = await self._get_latest_summary(session_id)
                result["summary"] = summary_data.get("summary", "") if summary_data else ""

            return result

        except Exception as e:
            logger.error(f"Failed to retrieve conversation data: {str(e)}")
            raise

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get conversation context for LLM consumption."""
        await self.initialize()

        try:
            session_id = query["session_id"]

            # Get both buffer and summary data
            data = await self.retrieve({"session_id": session_id})

            # Format for LLM context - limit to last 10 messages for better performance
            all_messages = data.get("messages", [])
            recent_messages = all_messages[-10:] if len(all_messages) > 10 else all_messages
            messages = [{"role": msg["role"], "content": msg["content"]} for msg in recent_messages]
            summary = data.get("summary", "")

            return {
                "messages": messages,
                "summary": summary,
                "memory_type": MemorySubtype.CONVERSATION_SUMMARY.value,
                "session_id": session_id,
            }

        except Exception as e:
            logger.error(f"Failed to get conversation context: {str(e)}")
            raise

    async def _check_and_generate_summary(
        self, session_id: str, user_id: Optional[str]
    ) -> Dict[str, Any]:
        """Generate/update summary every time using previous summary + recent 5 rounds."""
        try:
            # Get all messages for this session
            buffer_data = await self.buffer_memory.retrieve({"session_id": session_id})
            messages = buffer_data.get("messages", [])

            if not messages:
                return {"summary_generated": False, "reason": "No messages to summarize"}

            # Count conversation rounds (user + assistant pairs)
            conversation_rounds = self._count_conversation_rounds(messages)

            # Need at least 1 round to create a summary
            if conversation_rounds < 1:
                return {
                    "summary_generated": False,
                    "reason": "Need at least 1 conversation round",
                }

            # Get previous summary if it exists
            existing_summary = await self._get_latest_summary(session_id)
            previous_summary_text = existing_summary.get("summary", "") if existing_summary else ""

            # Get recent 5 rounds of conversation (10 messages max: 5 user + 5 assistant)
            recent_messages = self._get_recent_conversation_rounds(messages, 5)

            # Generate updated summary using previous summary + recent messages
            summary_text = await self._generate_incremental_summary(
                previous_summary_text, recent_messages
            )

            # Store or update summary
            summary_id = await self._store_or_update_summary(
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "summary": summary_text,
                    "message_count": len(messages),
                }
            )

            logger.info(
                f"Generated incremental summary for session {session_id} with {len(recent_messages)} recent messages"
            )

            return {
                "summary_generated": True,
                "summary_id": summary_id,
                "session_id": session_id,
                "message_count": len(messages),
                "recent_messages_processed": len(recent_messages),
            }

        except Exception as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            return {"summary_generated": False, "error": str(e)}

    def _count_conversation_rounds(self, messages: List[Dict[str, Any]]) -> int:
        """Count conversation rounds (user + assistant pairs)."""
        # Count unique user messages (each represents a conversation round)
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        return len(user_messages)

    def _get_recent_conversation_rounds(
        self, messages: List[Dict[str, Any]], num_rounds: int = 5
    ) -> List[Dict[str, Any]]:
        """Get the most recent N conversation rounds (user + assistant pairs)."""
        if not messages:
            return []

        # Find the last N user messages and their corresponding assistant responses
        user_messages = [(i, msg) for i, msg in enumerate(messages) if msg.get("role") == "user"]

        if not user_messages:
            return []

        # Get the last num_rounds user messages
        recent_user_msgs = (
            user_messages[-num_rounds:] if len(user_messages) >= num_rounds else user_messages
        )

        # Collect messages from the first recent user message onwards
        if recent_user_msgs:
            start_index = recent_user_msgs[0][0]  # Index of first recent user message
            return messages[start_index:]

        return messages

    async def _generate_incremental_summary(
        self, previous_summary: str, recent_messages: List[Dict[str, Any]]
    ) -> str:
        """Generate updated summary by combining previous summary with recent messages."""
        try:
            # Format recent messages for summarization
            recent_conversation_text = "\n".join(
                [f"{msg['role'].upper()}: {msg['content']}" for msg in recent_messages]
            )

            # Create incremental summary prompt
            if previous_summary:
                prompt = f"""You are updating a conversation summary by incorporating new messages. The summary will be used as context for a Large Language Model (LLM).

TASK: Update the existing summary by incorporating the new conversation messages while maintaining all important context.

REQUIREMENTS:
1. Merge the previous summary with the new messages seamlessly
2. Maintain chronological flow and context continuity
3. Preserve all important information from both the previous summary and new messages
4. Keep the updated summary comprehensive but concise (up to 2000 words)
5. Ensure an LLM can understand the full conversation context from this summary
6. Include specific details and decisions from both old and new content

EXISTING SUMMARY:
{previous_summary}

NEW MESSAGES TO INCORPORATE:
{recent_conversation_text}

UPDATED COMPREHENSIVE SUMMARY FOR LLM CONTEXT:"""
            else:
                # No previous summary, create initial summary
                prompt = f"""You are creating the first conversation summary that will be used as context for a Large Language Model (LLM).

TASK: Create a comprehensive conversation summary (up to 2000 words) that captures all important information from these initial messages.

REQUIREMENTS:
1. Write a detailed summary that an LLM can use to understand the conversation context
2. Include key topics, user requests, decisions made, and important details
3. Maintain chronological flow and logical connections
4. Use clear, structured language that an LLM can easily parse
5. Include specific details, not just high-level summaries

CONVERSATION MESSAGES:
{recent_conversation_text}

COMPREHENSIVE SUMMARY FOR LLM CONTEXT:"""

            # Call Gemini
            response = await self._call_gemini_async(prompt)

            return response.strip()

        except Exception as e:
            logger.error(f"Failed to generate incremental summary: {str(e)}")
            # Fallback: combine previous summary with basic recent message info
            if previous_summary and recent_messages:
                return f"{previous_summary}\n\nRecent activity: {len(recent_messages)} new messages added to the conversation."
            elif recent_messages:
                return f"Conversation with {len(recent_messages)} messages. Latest: {recent_messages[-1].get('content', '')[:100]}..."
            return previous_summary or "Empty conversation"

    async def _call_gemini_async(self, prompt: str) -> str:
        """Call Gemini API asynchronously."""

        def _call_gemini_sync():
            response = self.model.generate_content(prompt)
            return response.text

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call_gemini_sync)

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

    async def _store_or_update_summary(self, summary_data: Dict[str, Any]) -> str:
        """Store or update summary in Supabase."""
        if not self.supabase_client:
            return ""

        try:
            session_id = summary_data["session_id"]
            user_id = summary_data.get("user_id")

            # Check if summary already exists for this session and user
            existing_result = (
                self.supabase_client.table("conversation_summaries")
                .select("id")
                .eq("session_id", session_id)
            )

            # Add user_id filter if provided
            if user_id:
                existing_result = existing_result.eq("user_id", user_id)

            existing_result = existing_result.limit(1).execute()

            # Prepare summary record
            summary_record = {
                "session_id": session_id,
                "user_id": user_id,
                "summary": summary_data["summary"],
                "message_count": summary_data.get("message_count", 0),
                "summary_type": "simple",
                "model_used": self.summarization_model,
                "updated_at": datetime.utcnow().isoformat(),
            }

            if existing_result.data:
                # Update existing summary record
                result = (
                    self.supabase_client.table("conversation_summaries")
                    .update(summary_record)
                    .eq("id", existing_result.data[0]["id"])
                    .execute()
                )
                summary_id = existing_result.data[0]["id"]
            else:
                # Create new summary record
                summary_record["created_at"] = datetime.utcnow().isoformat()
                result = (
                    self.supabase_client.table("conversation_summaries")
                    .insert(summary_record)
                    .execute()
                )
                summary_id = result.data[0]["id"] if result.data else ""

            return summary_id

        except Exception as e:
            logger.error(f"Failed to store/update summary: {str(e)}")
            raise
