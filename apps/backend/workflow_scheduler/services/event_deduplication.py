"""
Event Deduplication Service

Redis-based distributed event deduplication to prevent duplicate processing
across multiple workflow scheduler instances.
"""

import logging
import time
from typing import Optional

import redis.asyncio as redis

from workflow_scheduler.core.config import settings

logger = logging.getLogger(__name__)


class EventDeduplicationService:
    """Redis-based event deduplication service for distributed systems"""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None

    async def initialize(self) -> None:
        """Initialize Redis connection"""
        try:
            self._pool = redis.ConnectionPool.from_url(settings.redis_url)
            self._redis = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self._redis.ping()
            logger.info("Event deduplication service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize event deduplication service: {e}")
            self._redis = None

    async def cleanup(self) -> None:
        """Cleanup Redis connections"""
        try:
            if self._redis:
                await self._redis.aclose()
            if self._pool:
                await self._pool.aclose()
            logger.info("Event deduplication service cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up event deduplication service: {e}")

    async def is_duplicate_event(
        self, event_id: str, event_source: str = "slack"
    ) -> bool:
        """
        Check if an event has already been processed

        Args:
            event_id: Unique event identifier (e.g., Slack event_id)
            event_source: Source of the event (e.g., 'slack', 'github')

        Returns:
            True if event is a duplicate, False if it's new
        """
        if not self._redis or not event_id:
            logger.warning("Redis not available or event_id empty, allowing processing")
            return False

        try:
            # Use Redis key format: dedup:{source}:{event_id}
            redis_key = f"dedup:{event_source}:{event_id}"

            # Check if key exists (SET with NX only sets if key doesn't exist)
            # Use EX for expiration in seconds (300 = 5 minutes)
            was_set = await self._redis.set(
                redis_key, int(time.time()), nx=True, ex=300
            )

            if was_set:
                logger.info(
                    f"✅ New {event_source} event {event_id} marked for processing"
                )
                return False  # Not a duplicate
            else:
                logger.info(
                    f"🔄 Duplicate {event_source} event detected: {event_id}, skipping processing"
                )
                return True  # Is a duplicate

        except Exception as e:
            logger.error(f"Error checking duplicate event {event_id}: {e}")
            # On error, allow processing to avoid blocking legitimate events
            return False

    async def cleanup_expired_events(self) -> int:
        """
        Clean up expired event records (optional, Redis TTL handles this automatically)

        Returns:
            Number of keys cleaned up
        """
        if not self._redis:
            return 0

        try:
            # Get all deduplication keys
            keys = await self._redis.keys("dedup:*")

            # Check TTL for each key and count expired ones
            expired_count = 0
            for key in keys:
                ttl = await self._redis.ttl(key)
                if ttl == -2:  # Key doesn't exist (expired)
                    expired_count += 1

            if expired_count > 0:
                logger.info(
                    f"Redis TTL cleaned up {expired_count} expired event records"
                )

            return expired_count

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0

    async def get_stats(self) -> dict:
        """Get deduplication statistics"""
        if not self._redis:
            return {"error": "Redis not available"}

        try:
            keys = await self._redis.keys("dedup:*")

            # Group by source
            stats = {}
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else str(key)
                parts = key_str.split(":")
                if len(parts) >= 2:
                    source = parts[1]
                    if source not in stats:
                        stats[source] = 0
                    stats[source] += 1

            return {
                "total_active_events": len(keys),
                "by_source": stats,
                "redis_connected": True,
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}


# Global instance
_dedup_service: Optional[EventDeduplicationService] = None


async def get_deduplication_service() -> EventDeduplicationService:
    """Get or create the global event deduplication service instance"""
    global _dedup_service

    if _dedup_service is None:
        _dedup_service = EventDeduplicationService()
        await _dedup_service.initialize()

    return _dedup_service
