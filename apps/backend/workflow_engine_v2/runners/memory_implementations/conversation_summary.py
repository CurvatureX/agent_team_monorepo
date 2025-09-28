"""
Conversation Summary Memory implementation for workflow_engine_v2.

Maintains conversation summaries using AI to compress long conversations.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from .base import MemoryBase


class ConversationSummaryMemory(MemoryBase):
    """Conversation summary memory implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.summary_threshold = config.get("summary_threshold", 20)  # Messages before summarizing
        self.summaries = []
        self.recent_messages = []

    async def _setup(self) -> None:
        """Setup the conversation summary memory."""
        self.logger.info(f"Conversation Summary: threshold={self.summary_threshold} messages")

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a conversation message and potentially create summary."""
        try:
            message = data.get("message", "")
            role = data.get("role", "user")
            timestamp = data.get("timestamp", datetime.utcnow().isoformat())

            if not message:
                return {"success": False, "error": "Missing 'message' in data"}

            # Add to recent messages
            self.recent_messages.append(
                {
                    "role": role,
                    "message": message,
                    "timestamp": timestamp,
                }
            )

            # Check if we need to summarize
            if len(self.recent_messages) >= self.summary_threshold:
                await self._create_summary()

            return {
                "success": True,
                "recent_count": len(self.recent_messages),
                "summary_count": len(self.summaries),
            }

        except Exception as e:
            self.logger.error(f"Error storing conversation message: {e}")
            return {"success": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve conversation history with summaries."""
        try:
            return {
                "success": True,
                "summaries": self.summaries,
                "recent_messages": self.recent_messages,
                "total_summaries": len(self.summaries),
                "recent_count": len(self.recent_messages),
            }

        except Exception as e:
            self.logger.error(f"Error retrieving conversation: {e}")
            return {"success": False, "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted context for LLM."""
        try:
            context_parts = []

            # Add summaries
            if self.summaries:
                context_parts.append("Previous conversation summaries:")
                for i, summary in enumerate(self.summaries, 1):
                    context_parts.append(f"{i}. {summary['content']}")

            # Add recent messages
            if self.recent_messages:
                context_parts.append("\nRecent messages:")
                for msg in self.recent_messages[-10:]:  # Last 10 messages
                    context_parts.append(f"{msg['role']}: {msg['message']}")

            context = (
                "\n".join(context_parts) if context_parts else "No conversation history available."
            )

            return {
                "success": True,
                "context": context,
                "summary_count": len(self.summaries),
                "recent_count": len(self.recent_messages),
            }

        except Exception as e:
            self.logger.error(f"Error getting context: {e}")
            return {"success": False, "error": str(e)}

    async def _create_summary(self) -> None:
        """Create a summary of recent messages."""
        try:
            if not self.recent_messages:
                return

            # Simple heuristic summary (in production, would use AI)
            user_messages = [msg for msg in self.recent_messages if msg["role"] == "user"]
            assistant_messages = [msg for msg in self.recent_messages if msg["role"] == "assistant"]

            summary_content = (
                f"Summary of {len(self.recent_messages)} messages: "
                f"{len(user_messages)} from user, {len(assistant_messages)} responses. "
                f"Topics discussed: {self._extract_topics()}"
            )

            self.summaries.append(
                {
                    "content": summary_content,
                    "message_count": len(self.recent_messages),
                    "created_at": datetime.utcnow().isoformat(),
                    "time_range": {
                        "start": self.recent_messages[0]["timestamp"],
                        "end": self.recent_messages[-1]["timestamp"],
                    },
                }
            )

            # Clear recent messages
            self.recent_messages = []

            self.logger.info(f"Created conversation summary: {len(self.summaries)} total summaries")

        except Exception as e:
            self.logger.error(f"Error creating summary: {e}")

    def _extract_topics(self) -> str:
        """Extract main topics from recent messages (simple implementation)."""
        try:
            all_text = " ".join([msg["message"] for msg in self.recent_messages])
            words = all_text.lower().split()

            # Simple word frequency analysis
            word_count = {}
            for word in words:
                if len(word) > 3:  # Only meaningful words
                    word_count[word] = word_count.get(word, 0) + 1

            # Get top words
            top_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:3]
            return ", ".join([word for word, count in top_words])

        except Exception:
            return "general conversation"


__all__ = ["ConversationSummaryMemory"]
