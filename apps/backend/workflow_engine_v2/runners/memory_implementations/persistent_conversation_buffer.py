"""
Persistent Conversation Buffer Memory implementation for workflow_engine_v2.

Uses Supabase conversation_buffers table for persistent message storage.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from .persistent_base import PersistentMemoryBase


class PersistentConversationBufferMemory(PersistentMemoryBase):
    """Persistent conversation buffer memory using Supabase conversation_buffers table."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.max_messages = config.get("max_messages", 100)
        self.max_tokens = config.get("max_tokens", 4000)
        self.conversation_id = config.get("conversation_id", "default")

    async def _setup_persistent_storage(self) -> None:
        """Setup the persistent conversation buffer storage."""
        # Clean up any expired messages on initialization
        await self._cleanup_old_messages()

        self.logger.info(
            f"Persistent Conversation Buffer initialized: max_messages={self.max_messages}, "
            f"max_tokens={self.max_tokens}, user_id={self.user_id}, memory_node_id={self.memory_node_id}"
        )

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a conversation message in the database."""
        try:
            message = data.get("message", "")
            role = data.get("role", "user")  # user, assistant, system
            timestamp = data.get("timestamp", datetime.utcnow().isoformat())

            if not message:
                return {"success": False, "error": "Missing 'message' in data"}

            # Get next message order
            next_order = await self._get_next_message_order()

            # Prepare message data for storage
            message_data = self._prepare_storage_data(
                {
                    "message_order": next_order,
                    "role": role,
                    "content": message,
                    "metadata": {
                        "conversation_id": self.conversation_id,
                        "token_count": len(message.split()) * 1.3,  # Rough token estimate
                        **data.get("metadata", {}),
                    },
                }
            )

            # Store message in database
            result = await self._execute_query(
                table="conversation_buffers", operation="insert", data=message_data
            )

            if result["success"]:
                # Maintain message and token limits
                await self._cleanup_old_messages()

                self.logger.debug(f"Stored message ({role}): {message[:50]}...")

                # Get current message count
                stats = await self._get_buffer_statistics()

                return {
                    "success": True,
                    "message_order": next_order,
                    "messages_count": stats.get("message_count", 0),
                    "timestamp": timestamp,
                    "storage": "persistent_database",
                }
            else:
                return {"success": False, "error": result["error"]}

        except Exception as e:
            self.logger.error(f"Error storing conversation message: {e}")
            return {"success": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve conversation messages from the database."""
        try:
            limit = query.get("limit", self.max_messages)
            role_filter = query.get("role")
            since_timestamp = query.get("since_timestamp")

            # Build base filters
            filters = self._build_base_filters()

            # Add role filter if specified
            if role_filter:
                filters["role"] = role_filter

            # Execute query with ordering
            result = await self._execute_query(
                table="conversation_buffers",
                operation="select",
                filters=filters,
                select_columns="message_order,role,content,metadata,created_at",
            )

            if not result["success"]:
                return {"success": False, "error": result["error"], "messages": []}

            messages = result["data"]

            # Apply timestamp filter if provided
            if since_timestamp:
                try:
                    since_time = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
                    messages = [
                        msg
                        for msg in messages
                        if datetime.fromisoformat(msg["created_at"].replace("Z", "+00:00"))
                        >= since_time
                    ]
                except ValueError:
                    self.logger.warning(f"Invalid timestamp format: {since_timestamp}")

            # Sort by message order and apply limit
            messages = sorted(messages, key=lambda x: x["message_order"])
            if limit:
                messages = messages[-limit:]  # Get most recent messages

            # Format messages for compatibility with in-memory format
            formatted_messages = []
            for msg in messages:
                formatted_msg = {
                    "role": msg["role"],
                    "message": msg["content"],
                    "timestamp": msg["created_at"],
                    "message_order": msg["message_order"],
                    "metadata": msg.get("metadata", {}),
                    "token_count": msg.get("metadata", {}).get("token_count", 0),
                }
                formatted_messages.append(formatted_msg)

            # Get total count for statistics
            total_count = await self._get_total_message_count()

            return {
                "success": True,
                "messages": formatted_messages,
                "count": len(formatted_messages),
                "total_in_buffer": total_count,
                "storage": "persistent_database",
            }

        except Exception as e:
            self.logger.error(f"Error retrieving conversation messages: {e}")
            return {"success": False, "error": str(e), "messages": []}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted context for LLM from persistent storage."""
        try:
            max_messages = query.get("max_messages", 20)
            include_system = query.get("include_system", True)
            format_style = query.get("format", "conversation")  # conversation, summary, compact

            # Retrieve recent messages
            retrieve_query = {"limit": max_messages}
            if not include_system:
                # We'll filter system messages after retrieval for simplicity
                retrieve_query["limit"] = max_messages * 2  # Get extra to account for filtering

            messages_result = await self.retrieve(retrieve_query)

            if not messages_result["success"]:
                return {"success": False, "error": messages_result["error"]}

            messages = messages_result["messages"]

            # Filter system messages if not included
            if not include_system:
                messages = [msg for msg in messages if msg["role"] != "system"]
                messages = messages[-max_messages:]  # Apply limit after filtering

            if not messages:
                return {
                    "success": True,
                    "context": "No conversation history available.",
                    "message_count": 0,
                    "format": format_style,
                    "storage": "persistent_database",
                }

            # Format based on style
            if format_style == "conversation":
                context = self._format_as_conversation(messages)
            elif format_style == "summary":
                context = self._format_as_summary(messages)
            else:  # compact
                context = self._format_as_compact(messages)

            return {
                "success": True,
                "context": context,
                "message_count": len(messages),
                "format": format_style,
                "storage": "persistent_database",
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

    async def clear(self) -> Dict[str, Any]:
        """Clear the conversation buffer from database."""
        try:
            # Get current count before clearing
            total_count = await self._get_total_message_count()

            # Delete all messages for this user and memory node
            result = await self._execute_query(
                table="conversation_buffers", operation="delete", filters=self._build_base_filters()
            )

            if result["success"]:
                self.logger.info(
                    f"Cleared conversation buffer: {total_count} messages removed from database"
                )
                return {
                    "success": True,
                    "cleared_messages": total_count,
                    "conversation_id": self.conversation_id,
                    "storage": "persistent_database",
                }
            else:
                return {"success": False, "error": result["error"]}

        except Exception as e:
            self.logger.error(f"Error clearing conversation buffer: {e}")
            return {"success": False, "error": str(e)}

    async def get_statistics(self) -> Dict[str, Any]:
        """Get buffer statistics from database."""
        try:
            stats = await self._get_buffer_statistics()
            return {
                "success": True,
                "statistics": {
                    **stats,
                    "buffer_utilization": stats["message_count"] / self.max_messages
                    if self.max_messages > 0
                    else 0,
                    "storage": "persistent_database",
                },
            }

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"success": False, "error": str(e)}

    async def _get_next_message_order(self) -> int:
        """Get the next message order number."""
        try:
            result = await self._execute_query(
                table="conversation_buffers",
                operation="select",
                filters=self._build_base_filters(),
                select_columns="MAX(message_order) as max_order",
            )

            if result["success"] and result["data"] and result["data"][0]["max_order"] is not None:
                return result["data"][0]["max_order"] + 1
            return 0

        except Exception as e:
            self.logger.warning(f"Error getting next message order: {e}")
            return 0

    async def _get_total_message_count(self) -> int:
        """Get total message count for this buffer."""
        try:
            result = await self._execute_query(
                table="conversation_buffers",
                operation="select",
                filters=self._build_base_filters(),
                select_columns="COUNT(*) as count",
            )

            if result["success"] and result["data"]:
                return result["data"][0]["count"]
            return 0

        except Exception as e:
            self.logger.warning(f"Error getting message count: {e}")
            return 0

    async def _get_buffer_statistics(self) -> Dict[str, Any]:
        """Get detailed buffer statistics from database."""
        try:
            # Use PostgreSQL aggregation functions for efficiency
            result = await self._execute_query(
                table="conversation_buffers",
                operation="select",
                filters=self._build_base_filters(),
                select_columns="""
                    COUNT(*) as message_count,
                    MIN(created_at) as oldest_message,
                    MAX(created_at) as newest_message,
                    role,
                    COUNT(*) as role_count
                """,
            )

            if not result["success"] or not result["data"]:
                return {
                    "message_count": 0,
                    "total_tokens": 0,
                    "by_role": {},
                    "oldest_message": None,
                    "newest_message": None,
                }

            # Process aggregated results
            message_count = 0
            by_role = {}
            oldest_message = None
            newest_message = None

            for row in result["data"]:
                role = row.get("role")
                count = row.get("role_count", 0)

                if role:
                    by_role[role] = count
                    message_count += count

                if row.get("oldest_message") and (
                    not oldest_message or row["oldest_message"] < oldest_message
                ):
                    oldest_message = row["oldest_message"]

                if row.get("newest_message") and (
                    not newest_message or row["newest_message"] > newest_message
                ):
                    newest_message = row["newest_message"]

            # Get total tokens (approximate - would need to sum from metadata)
            total_tokens = message_count * 10  # Rough estimate

            return {
                "message_count": message_count,
                "total_tokens": total_tokens,
                "by_role": by_role,
                "oldest_message": oldest_message,
                "newest_message": newest_message,
            }

        except Exception as e:
            self.logger.error(f"Error getting buffer statistics: {e}")
            return {
                "message_count": 0,
                "total_tokens": 0,
                "by_role": {},
                "oldest_message": None,
                "newest_message": None,
            }

    async def _cleanup_old_messages(self) -> None:
        """Remove old messages to maintain limits."""
        try:
            # First, enforce message count limit
            if self.max_messages > 0:
                # Get messages ordered by message_order (oldest first)
                result = await self._execute_query(
                    table="conversation_buffers",
                    operation="select",
                    filters=self._build_base_filters(),
                    select_columns="message_order",
                )

                if result["success"] and result["data"]:
                    total_messages = len(result["data"])

                    if total_messages > self.max_messages:
                        # Calculate how many messages to remove
                        messages_to_remove = total_messages - self.max_messages

                        # Get the message_order values of oldest messages
                        oldest_orders = sorted([msg["message_order"] for msg in result["data"]])[
                            :messages_to_remove
                        ]

                        # Delete oldest messages
                        for order in oldest_orders:
                            await self._execute_query(
                                table="conversation_buffers",
                                operation="delete",
                                filters={**self._build_base_filters(), "message_order": order},
                            )

                        self.logger.debug(
                            f"Removed {messages_to_remove} old messages due to count limit"
                        )

            # TODO: Implement token-based cleanup if needed
            # This would require calculating actual tokens from message content

        except Exception as e:
            self.logger.warning(f"Error during message cleanup: {e}")


__all__ = ["PersistentConversationBufferMemory"]
