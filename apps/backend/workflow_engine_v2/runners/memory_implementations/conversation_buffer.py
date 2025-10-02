"""
Conversation Buffer Memory implementation for workflow_engine_v2.

Single conversation buffer memory with built-in auto-summary capability.
When auto_summarize is enabled and the buffer is nearly full (within 5
messages of max_messages), the node summarizes the oldest summarize_count
messages into the summary and frees space in the buffer.
"""

from __future__ import annotations

import sys
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from .base import MemoryBase


class ConversationBufferMemory(MemoryBase):
    """Conversation buffer memory with built-in auto-summarization capability."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.max_messages = config.get("max_messages", 50)
        self.auto_summarize = config.get("auto_summarize", True)
        self.summarize_count = config.get("summarize_count", 10)
        self.conversation_id = config.get("conversation_id", "default")

        # Use deque for efficient append/pop operations
        self.messages = deque(maxlen=self.max_messages)

        # Summary storage
        self.summary = ""
        self.summary_metadata = {}

    async def _setup(self) -> None:
        """Setup the conversation buffer."""
        self.logger.info(
            f"Conversation Buffer: max_messages={self.max_messages}, "
            f"auto_summarize={self.auto_summarize}, summarize_count={self.summarize_count}"
        )

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a conversation message and trigger auto-summarization if needed."""
        try:
            message = data.get("message", "")
            role = data.get("role", "user")  # user, assistant, system
            timestamp = data.get("timestamp", datetime.utcnow().isoformat())

            if not message:
                return {"success": False, "error": "Missing 'message' in data"}

            # Check if we need to auto-summarize before adding new message
            buffer_full = False
            if self.auto_summarize and len(self.messages) >= (self.max_messages - 5):
                await self._create_auto_summary()
                buffer_full = True

            # Create message entry
            entry = {
                "role": role,
                "content": message,  # Changed from 'message' to 'content' to match spec
                "timestamp": timestamp,
                "metadata": data.get("metadata", {}),
            }

            # Add to buffer
            self.messages.append(entry)

            self.logger.debug(f"Stored message ({role}): {message[:50]}...")
            return {
                "success": True,
                "messages": list(self.messages),
                "total_messages": len(self.messages),
                "buffer_full": buffer_full,
                "summary": self.summary,
                "summary_metadata": self.summary_metadata,
                "timestamp": timestamp,
            }

        except Exception as e:
            self.logger.error(f"Error storing conversation message: {e}")
            return {"success": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve conversation messages with summary."""
        try:
            limit = query.get("limit", len(self.messages))
            role_filter = query.get("role")  # Optional role filter
            since_timestamp = query.get("since_timestamp")

            messages = []
            for entry in list(self.messages)[-limit:]:
                # Apply role filter
                if role_filter and entry["role"] != role_filter:
                    continue

                # Apply timestamp filter
                if since_timestamp:
                    try:
                        entry_time = datetime.fromisoformat(
                            entry["timestamp"].replace("Z", "+00:00")
                        )
                        since_time = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
                        if entry_time < since_time:
                            continue
                    except ValueError:
                        pass  # Skip timestamp filtering if parsing fails

                messages.append(entry)

            return {
                "success": True,
                "messages": messages,
                "total_messages": len(self.messages),
                "buffer_full": len(self.messages) >= self.max_messages,
                "summary": self.summary,
                "summary_metadata": self.summary_metadata,
            }

        except Exception as e:
            self.logger.error(f"Error retrieving conversation messages: {e}")
            return {"success": False, "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted context for LLM, including summary if available."""
        try:
            max_messages = query.get("max_messages", 20)
            include_system = query.get("include_system", True)

            # Get recent messages
            recent_messages = list(self.messages)[-max_messages:]

            if not include_system:
                recent_messages = [msg for msg in recent_messages if msg["role"] != "system"]

            # Build context with summary if available
            context_parts = []
            if self.summary:
                context_parts.append(f"[Summary of earlier conversation]: {self.summary}")
                context_parts.append("")

            if recent_messages:
                context_parts.append("Recent messages:")
                for msg in recent_messages:
                    role = msg["role"]
                    content = msg.get("content", msg.get("message", ""))  # Support both formats
                    context_parts.append(f"{role}: {content}")
            else:
                context_parts.append("No recent messages.")

            context = "\n".join(context_parts)

            return {
                "success": True,
                "context": context,
                "messages": recent_messages,
                "message_count": len(recent_messages),
                "has_summary": bool(self.summary),
                "summary": self.summary,
            }

        except Exception as e:
            self.logger.error(f"Error getting conversation context: {e}")
            return {"success": False, "error": str(e)}

    async def _create_auto_summary(self) -> None:
        """
        Create a summary of the oldest messages and remove them from the buffer.
        This is called when the buffer is nearly full (within 5 messages of max_messages).
        """
        try:
            if len(self.messages) < self.summarize_count:
                return

            # Get the oldest messages to summarize
            messages_to_summarize = list(self.messages)[: self.summarize_count]

            # Create simple heuristic summary (in production, would use AI)
            user_messages = [msg for msg in messages_to_summarize if msg["role"] == "user"]
            assistant_messages = [
                msg for msg in messages_to_summarize if msg["role"] == "assistant"
            ]

            summary_content = (
                f"Summary of {len(messages_to_summarize)} earlier messages: "
                f"{len(user_messages)} from user, {len(assistant_messages)} responses. "
                f"Topics discussed: {self._extract_topics(messages_to_summarize)}"
            )

            # Update or append to existing summary
            if self.summary:
                self.summary = f"{self.summary}\n\n{summary_content}"
            else:
                self.summary = summary_content

            # Update summary metadata
            self.summary_metadata = {
                "message_count": len(messages_to_summarize),
                "created_at": datetime.utcnow().isoformat(),
                "time_range": {
                    "start": messages_to_summarize[0]["timestamp"],
                    "end": messages_to_summarize[-1]["timestamp"],
                },
            }

            # Remove the summarized messages from the buffer
            for _ in range(self.summarize_count):
                if self.messages:
                    self.messages.popleft()

            self.logger.info(
                f"Created auto-summary of {len(messages_to_summarize)} messages, "
                f"freed {self.summarize_count} slots in buffer"
            )

        except Exception as e:
            self.logger.error(f"Error creating auto-summary: {e}")

    def _extract_topics(self, messages: List[Dict[str, Any]]) -> str:
        """Extract main topics from messages (simple implementation)."""
        try:
            all_text = " ".join([msg.get("content", msg.get("message", "")) for msg in messages])
            words = all_text.lower().split()

            # Simple word frequency analysis
            word_count = {}
            for word in words:
                if len(word) > 3:  # Only meaningful words
                    word_count[word] = word_count.get(word, 0) + 1

            # Get top words
            top_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:3]
            return ", ".join([word for word, count in top_words]) if top_words else "general"

        except Exception:
            return "general conversation"

    async def clear(self) -> Dict[str, Any]:
        """Clear the conversation buffer and summary."""
        try:
            message_count = len(self.messages)
            self.messages.clear()
            self.summary = ""
            self.summary_metadata = {}

            self.logger.info(f"Cleared conversation buffer: {message_count} messages removed")
            return {
                "success": True,
                "cleared_messages": message_count,
                "conversation_id": self.conversation_id,
            }

        except Exception as e:
            self.logger.error(f"Error clearing conversation buffer: {e}")
            return {"success": False, "error": str(e)}

    async def get_statistics(self) -> Dict[str, Any]:
        """Get buffer statistics including summary info."""
        try:
            if not self.messages:
                return {
                    "success": True,
                    "statistics": {
                        "message_count": 0,
                        "by_role": {},
                        "oldest_message": None,
                        "newest_message": None,
                        "has_summary": bool(self.summary),
                        "summary_metadata": self.summary_metadata,
                    },
                }

            # Count by role
            role_counts = {}

            for entry in self.messages:
                role = entry["role"]
                role_counts[role] = role_counts.get(role, 0) + 1

            oldest = self.messages[0]["timestamp"] if self.messages else None
            newest = self.messages[-1]["timestamp"] if self.messages else None

            return {
                "success": True,
                "statistics": {
                    "message_count": len(self.messages),
                    "by_role": role_counts,
                    "oldest_message": oldest,
                    "newest_message": newest,
                    "buffer_utilization": len(self.messages) / self.max_messages,
                    "has_summary": bool(self.summary),
                    "summary_metadata": self.summary_metadata,
                },
            }

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"success": False, "error": str(e)}


__all__ = ["ConversationBufferMemory"]
