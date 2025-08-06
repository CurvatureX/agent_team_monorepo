import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import redis.asyncio as redis

from workflow_scheduler.core.config import settings

logger = logging.getLogger(__name__)


class DistributedLockManager:
    """Redis-based distributed lock manager for preventing duplicate executions"""

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
            logger.info("Distributed lock manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize distributed lock manager: {e}")
            raise

    async def cleanup(self) -> None:
        """Cleanup Redis connections"""
        if self._redis:
            await self._redis.aclose()
        if self._pool:
            await self._pool.aclose()

    @asynccontextmanager
    async def acquire(
        self, lock_key: str, timeout: Optional[int] = None, retry_delay: Optional[float] = None
    ) -> AsyncGenerator[bool, None]:
        """
        Acquire a distributed lock using Redis

        Args:
            lock_key: Unique identifier for the lock
            timeout: Lock timeout in seconds (default from settings)
            retry_delay: Delay between retry attempts (default from settings)

        Yields:
            bool: True if lock was acquired, False otherwise
        """
        if not self._redis:
            raise RuntimeError("Lock manager not initialized")

        timeout = timeout or settings.lock_timeout
        retry_delay = retry_delay or settings.lock_retry_delay

        lock_name = f"workflow_lock:{lock_key}"
        lock_value = f"{time.time()}:{id(self)}"  # Unique lock value
        acquired = False

        try:
            # Try to acquire lock with exponential backoff
            max_retries = 5
            for attempt in range(max_retries):
                acquired = await self._redis.set(
                    lock_name,
                    lock_value,
                    nx=True,  # Only set if not exists
                    ex=timeout,  # Expire after timeout seconds
                )

                if acquired:
                    logger.debug(f"Lock acquired: {lock_name}")
                    break

                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2**attempt)  # Exponential backoff
                    logger.debug(f"Lock {lock_name} busy, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

            yield bool(acquired)

        finally:
            if acquired:
                try:
                    # Only release if we still own the lock
                    lua_script = """
                    if redis.call("GET", KEYS[1]) == ARGV[1] then
                        return redis.call("DEL", KEYS[1])
                    else
                        return 0
                    end
                    """
                    await self._redis.eval(lua_script, 1, lock_name, lock_value)
                    logger.debug(f"Lock released: {lock_name}")

                except Exception as e:
                    logger.warning(f"Failed to release lock {lock_name}: {e}")

    async def is_locked(self, lock_key: str) -> bool:
        """Check if a lock is currently held"""
        if not self._redis:
            return False

        lock_name = f"workflow_lock:{lock_key}"
        exists = await self._redis.exists(lock_name)
        return bool(exists)

    async def force_release(self, lock_key: str) -> bool:
        """Force release a lock (use with caution)"""
        if not self._redis:
            return False

        lock_name = f"workflow_lock:{lock_key}"
        deleted = await self._redis.delete(lock_name)

        if deleted:
            logger.warning(f"Force released lock: {lock_name}")

        return bool(deleted)

    async def get_lock_info(self, lock_key: str) -> Optional[dict]:
        """Get information about a lock"""
        if not self._redis:
            return None

        lock_name = f"workflow_lock:{lock_key}"

        # Get lock value and TTL
        lock_value = await self._redis.get(lock_name)
        ttl = await self._redis.ttl(lock_name)

        if lock_value is None:
            return None

        return {
            "lock_key": lock_key,
            "lock_name": lock_name,
            "lock_value": lock_value.decode() if isinstance(lock_value, bytes) else lock_value,
            "ttl_seconds": ttl,
            "exists": True,
        }
