"""
Conversation Buffer Memory Implementation.

This implements a hybrid Redis + Supabase conversation buffer:
- Redis: Fast access to recent conversation history
- Supabase: Persistent storage for all conversation data
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis
from supabase import Client, create_client

from .base import MemoryBase

logger = logging.getLogger(__name__)


class ConversationBufferMemory(MemoryBase):
    """
    Conversation Buffer Memory with Redis + Supabase backend.

    Features:
    - Fast Redis cache for recent messages
    - Persistent Supabase storage
    - Configurable window sizes (turns, tokens, time)
    - Automatic cleanup of old data
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize conversation buffer memory.

        Args:
            config: Configuration dict with keys:
                - redis_url: Redis connection URL
                - supabase_url: Supabase project URL
                - supabase_key: Supabase service key
                - window_size: Number of messages to keep in buffer (default: 10)
                - window_type: Type of window - 'turns', 'tokens', 'time' (default: 'turns')
                - ttl_seconds: TTL for Redis cache (default: 3600)
                - include_system_messages: Include system messages (default: True)
        """
        super().__init__(config)

        # Configuration
        self.window_size = config.get("window_size", 10)
        self.window_type = config.get("window_type", "turns")
        self.ttl_seconds = config.get("ttl_seconds", 3600)
        self.include_system_messages = config.get("include_system_messages", True)

        # Storage backends
        self.redis_client: Optional[redis.Redis] = None
        self.supabase_client: Optional[Client] = None

    async def _setup(self) -> None:
        """Setup Redis and Supabase connections."""
        try:
            # Setup Redis
            redis_url = self.config.get("redis_url", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)

            # Test Redis connection
            await self.redis_client.ping()
            logger.info("Redis connection established for ConversationBufferMemory")

            # Setup Supabase
            supabase_url = self.config["supabase_url"]
            supabase_key = self.config["supabase_key"]
            self.supabase_client = create_client(supabase_url, supabase_key)

            logger.info("ConversationBufferMemory initialized successfully")

        except Exception as e:
            logger.error(f"Failed to setup ConversationBufferMemory: {str(e)}")
            raise

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store a conversation message.

        Args:
            data: Message data with keys:
                - session_id: Session identifier
                - user_id: User identifier (optional)
                - role: Message role ('user', 'assistant', 'system')
                - content: Message content
                - timestamp: Message timestamp (optional, defaults to now)
                - metadata: Additional metadata (optional)

        Returns:
            Dict with storage confirmation
        """
        await self.initialize()

        try:
            session_id = data["session_id"]
            role = data["role"]
            content = data["content"]
            user_id = data.get("user_id")
            timestamp = data.get("timestamp", datetime.utcnow().isoformat())
            metadata = data.get("metadata", {})

            # Skip system messages if not configured to include them
            if role == "system" and not self.include_system_messages:
                return {
                    "stored": False,
                    "reason": "System messages excluded",
                    "timestamp": timestamp,
                }

            # Get current message index
            message_index = await self._get_next_message_index(session_id)

            # Prepare message data
            message = {
                "session_id": session_id,
                "user_id": user_id,
                "message_index": message_index,
                "role": role,
                "content": content,
                "metadata": metadata,
                "tokens_count": self._estimate_tokens(content),
                "timestamp": timestamp,
            }

            # Store in Redis for fast access
            await self._store_in_redis(session_id, message)

            # Store in Supabase for persistence
            await self._store_in_supabase(message)

            # Maintain window size in Redis
            await self._maintain_redis_window(session_id)

            logger.debug(f"Stored message {message_index} for session {session_id}")

            return {
                "stored": True,
                "message_index": message_index,
                "session_id": session_id,
                "timestamp": timestamp,
            }

        except Exception as e:
            logger.error(f"Failed to store conversation message: {str(e)}")
            raise

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve conversation messages.

        Args:
            query: Query dict with keys:
                - session_id: Session identifier
                - limit: Maximum number of messages (optional)
                - include_metadata: Include metadata (optional, default: True)

        Returns:
            Dict with messages and metadata
        """
        await self.initialize()

        try:
            session_id = query["session_id"]
            limit = query.get("limit", self.window_size)
            include_metadata = query.get("include_metadata", True)

            # Try Redis first for recent messages
            messages = await self._get_from_redis(session_id, limit)

            # If not enough messages in Redis, fetch from Supabase
            if len(messages) < limit:
                supabase_messages = await self._get_from_supabase(session_id, limit)

                # Merge and deduplicate
                all_messages = {msg["message_index"]: msg for msg in supabase_messages}
                for msg in messages:
                    all_messages[msg["message_index"]] = msg

                # Sort by message index and take the most recent
                messages = sorted(all_messages.values(), key=lambda x: x["message_index"])[-limit:]

            # Remove metadata if not requested
            if not include_metadata:
                for msg in messages:
                    msg.pop("metadata", None)

            return {
                "messages": messages,
                "total_count": len(messages),
                "session_id": session_id,
                "retrieved_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to retrieve conversation messages: {str(e)}")
            raise

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get formatted conversation context for LLM.

        Args:
            query: Query dict with session_id and optional parameters

        Returns:
            Dict with conversation messages in proper API format
        """
        await self.initialize()

        try:
            session_id = query["session_id"]

            # Get recent messages
            messages_data = await self.retrieve(
                {"session_id": session_id, "limit": self.window_size, "include_metadata": False}
            )

            messages = messages_data["messages"]

            # Format messages for API consumption (OpenAI/Claude format)
            formatted_messages = []
            total_tokens = 0

            for msg in messages:
                # Ensure proper role mapping and content format
                role = msg["role"]
                content = msg["content"]

                # Skip system messages unless specifically configured to include them
                if role == "system" and not self.include_system_messages:
                    continue

                formatted_msg = {"role": role, "content": content}
                formatted_messages.append(formatted_msg)
                total_tokens += msg.get("tokens_count", 0)

            # Calculate window info
            window_info = {
                "window_type": self.window_type,
                "window_size": self.window_size,
                "actual_count": len(formatted_messages),
                "total_tokens": total_tokens,
                "oldest_message_time": messages[0]["timestamp"] if messages else None,
                "newest_message_time": messages[-1]["timestamp"] if messages else None,
            }

            # Import the enum
            from shared.models.node_enums import MemorySubtype

            return {
                "messages": formatted_messages,  # This is the key field for API consumption
                "total_tokens": total_tokens,
                "window_info": window_info,
                "session_id": session_id,
                "memory_type": MemorySubtype.CONVERSATION_BUFFER.value,
                "context_generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get conversation context: {str(e)}")
            raise

    async def _get_next_message_index(self, session_id: str) -> int:
        """Get the next message index for a session."""
        key = f"conv_buffer:index:{session_id}"
        return await self.redis_client.incr(key)

    async def _store_in_redis(self, session_id: str, message: Dict[str, Any]) -> None:
        """Store message in Redis."""
        key = f"conv_buffer:messages:{session_id}"

        # Add to sorted set with message index as score
        await self.redis_client.zadd(
            key, {json.dumps(message, default=str): message["message_index"]}
        )

        # Set TTL
        await self.redis_client.expire(key, self.ttl_seconds)

    async def _store_in_supabase(self, message: Dict[str, Any]) -> None:
        """Store message in Supabase."""
        try:
            result = self.supabase_client.table("conversation_buffers").insert(message).execute()
            if not result.data:
                raise Exception("Failed to insert into Supabase")
        except Exception as e:
            logger.error(f"Supabase storage failed: {str(e)}")
            # Don't raise - Redis storage is primary

    async def _maintain_redis_window(self, session_id: str) -> None:
        """Maintain the Redis window size."""
        key = f"conv_buffer:messages:{session_id}"

        # Keep only the most recent window_size messages
        await self.redis_client.zremrangebyrank(key, 0, -(self.window_size + 1))

    async def _get_from_redis(self, session_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get messages from Redis."""
        key = f"conv_buffer:messages:{session_id}"

        # Get the most recent messages
        raw_messages = await self.redis_client.zrevrange(key, 0, limit - 1)

        messages = []
        for raw_msg in raw_messages:
            try:
                msg = json.loads(raw_msg)
                messages.append(msg)
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode Redis message: {raw_msg}")

        return sorted(messages, key=lambda x: x["message_index"])

    async def _get_from_supabase(self, session_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get messages from Supabase."""
        try:
            result = (
                self.supabase_client.table("conversation_buffers")
                .select("*")
                .eq("session_id", session_id)
                .order("message_index", desc=True)
                .limit(limit)
                .execute()
            )

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"Failed to get messages from Supabase: {str(e)}")
            return []

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)."""
        return max(1, len(text) // 4)

    async def cleanup_old_data(self, retention_days: int = 30) -> Dict[str, Any]:
        """Clean up old conversation data."""
        await self.initialize()

        try:
            # Cleanup Supabase data older than retention period
            cutoff_date = (datetime.utcnow() - timedelta(days=retention_days)).isoformat()

            result = (
                self.supabase_client.table("conversation_buffers")
                .delete()
                .lt("created_at", cutoff_date)
                .execute()
            )

            deleted_count = len(result.data) if result.data else 0

            logger.info(f"Cleaned up {deleted_count} old conversation buffer records")

            return {
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date,
                "cleanup_completed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to cleanup old conversation data: {str(e)}")
            raise

    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a conversation session."""
        await self.initialize()

        try:
            # Get stats from Supabase
            result = (
                self.supabase_client.table("conversation_buffers")
                .select("role, tokens_count, timestamp")
                .eq("session_id", session_id)
                .execute()
            )

            messages = result.data if result.data else []

            if not messages:
                return {"session_id": session_id, "total_messages": 0}

            # Calculate statistics
            role_counts = {}
            total_tokens = 0
            timestamps = []

            for msg in messages:
                role = msg["role"]
                role_counts[role] = role_counts.get(role, 0) + 1
                total_tokens += msg.get("tokens_count", 0)
                timestamps.append(msg["timestamp"])

            timestamps.sort()

            return {
                "session_id": session_id,
                "total_messages": len(messages),
                "role_counts": role_counts,
                "total_tokens": total_tokens,
                "first_message": timestamps[0],
                "last_message": timestamps[-1],
                "duration_hours": (
                    datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
                    - datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
                ).total_seconds()
                / 3600,
            }

        except Exception as e:
            logger.error(f"Failed to get session stats: {str(e)}")
            raise
