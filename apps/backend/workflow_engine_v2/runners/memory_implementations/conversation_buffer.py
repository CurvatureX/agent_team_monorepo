"""
Conversation Buffer Memory implementation for workflow_engine_v2.

Maintains a buffer of recent conversation messages with size limits.
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
    """Conversation buffer memory implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.max_messages = config.get("max_messages", 100)
        self.max_tokens = config.get("max_tokens", 4000)
        self.conversation_id = config.get("conversation_id", "default")

        # Use deque for efficient append/pop operations
        self.messages = deque(maxlen=self.max_messages)

    async def _setup(self) -> None:
        """Setup the conversation buffer."""
        self.logger.info(
            f"Conversation Buffer: max_messages={self.max_messages}, max_tokens={self.max_tokens}"
        )

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a conversation message."""
        try:
            message = data.get("message", "")
            role = data.get("role", "user")  # user, assistant, system
            timestamp = data.get("timestamp", datetime.utcnow().isoformat())

            if not message:
                return {"success": False, "error": "Missing 'message' in data"}

            # Create message entry
            entry = {
                "role": role,
                "message": message,
                "timestamp": timestamp,
                "metadata": data.get("metadata", {}),
                "token_count": len(message.split()) * 1.3,  # Rough token estimate
            }

            # Add to buffer (deque automatically handles max_messages limit)
            self.messages.append(entry)

            # Trim buffer if token limit exceeded
            await self._trim_to_token_limit()

            self.logger.debug(f"Stored message ({role}): {message[:50]}...")
            return {
                "success": True,
                "messages_count": len(self.messages),
                "timestamp": timestamp,
            }

        except Exception as e:
            self.logger.error(f"Error storing conversation message: {e}")
            return {"success": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve conversation messages."""
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
                "count": len(messages),
                "total_in_buffer": len(self.messages),
            }

        except Exception as e:
            self.logger.error(f"Error retrieving conversation messages: {e}")
            return {"success": False, "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted context for LLM."""
        try:
            max_messages = query.get("max_messages", 20)
            include_system = query.get("include_system", True)
            format_style = query.get("format", "conversation")  # conversation, summary, compact

            # Get recent messages
            recent_messages = list(self.messages)[-max_messages:]

            if not include_system:
                recent_messages = [msg for msg in recent_messages if msg["role"] != "system"]

            if not recent_messages:
                return {
                    "success": True,
                    "context": "No conversation history available.",
                    "message_count": 0,
                }

            # Format based on style
            if format_style == "conversation":
                context = self._format_as_conversation(recent_messages)
            elif format_style == "summary":
                context = self._format_as_summary(recent_messages)
            else:  # compact
                context = self._format_as_compact(recent_messages)

            return {
                "success": True,
                "context": context,
                "message_count": len(recent_messages),
                "format": format_style,
            }

        except Exception as e:
            self.logger.error(f"Error getting conversation context: {e}")
            return {"success": False, "error": str(e)}

    def _format_as_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages as a conversation."""
        lines = ["Recent Conversation:"]
        for msg in messages:
            role = msg["role"].title()
            message = msg["message"]
            timestamp = msg["timestamp"][:19]  # Remove microseconds
            lines.append(f"{role} ({timestamp}): {message}")

        return "\n".join(lines)

    def _format_as_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages as a summary."""
        if not messages:
            return "No conversation history."

        user_messages = [msg for msg in messages if msg["role"] == "user"]
        assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]

        summary_lines = [
            f"Conversation Summary:",
            f"- Total messages: {len(messages)}",
            f"- User messages: {len(user_messages)}",
            f"- Assistant responses: {len(assistant_messages)}",
        ]

        # Add recent key exchanges
        if len(messages) > 0:
            summary_lines.append("\nRecent exchange:")
            for msg in messages[-4:]:  # Last 4 messages
                role = msg["role"].title()
                preview = msg["message"][:100]
                if len(msg["message"]) > 100:
                    preview += "..."
                summary_lines.append(f"{role}: {preview}")

        return "\n".join(summary_lines)

    def _format_as_compact(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages in compact format."""
        if not messages:
            return "No conversation history."

        lines = []
        for msg in messages:
            role_short = msg["role"][0].upper()  # U, A, S for user, assistant, system
            message = msg["message"][:150]
            if len(msg["message"]) > 150:
                message += "..."
            lines.append(f"{role_short}: {message}")

        return " | ".join(lines)

    async def _trim_to_token_limit(self) -> None:
        """Trim buffer to stay within token limit."""
        if not self.max_tokens:
            return

        total_tokens = sum(entry.get("token_count", 0) for entry in self.messages)

        while total_tokens > self.max_tokens and len(self.messages) > 1:
            # Remove oldest message
            removed = self.messages.popleft()
            total_tokens -= removed.get("token_count", 0)
            self.logger.debug("Trimmed oldest message due to token limit")

    async def clear(self) -> Dict[str, Any]:
        """Clear the conversation buffer."""
        try:
            message_count = len(self.messages)
            self.messages.clear()

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
        """Get buffer statistics."""
        try:
            if not self.messages:
                return {
                    "success": True,
                    "statistics": {
                        "message_count": 0,
                        "total_tokens": 0,
                        "by_role": {},
                        "oldest_message": None,
                        "newest_message": None,
                    },
                }

            # Count by role
            role_counts = {}
            total_tokens = 0

            for entry in self.messages:
                role = entry["role"]
                role_counts[role] = role_counts.get(role, 0) + 1
                total_tokens += entry.get("token_count", 0)

            oldest = self.messages[0]["timestamp"] if self.messages else None
            newest = self.messages[-1]["timestamp"] if self.messages else None

            return {
                "success": True,
                "statistics": {
                    "message_count": len(self.messages),
                    "total_tokens": total_tokens,
                    "by_role": role_counts,
                    "oldest_message": oldest,
                    "newest_message": newest,
                    "buffer_utilization": len(self.messages) / self.max_messages,
                },
            }

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"success": False, "error": str(e)}


__all__ = ["ConversationBufferMemory"]
