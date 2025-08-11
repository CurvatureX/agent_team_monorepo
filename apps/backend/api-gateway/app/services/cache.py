"""
Cache service layer for API Gateway.

Provides TTL-based caching with configurable expiration,
cache invalidation strategies, and integration with rate limiting
and token validation.
"""

import asyncio
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from app.core.config import settings
from app.core.database import RedisOperations, get_redis_manager

from shared.logging_config import get_logger
logger = get_logger(__name__)


class CacheKey(Enum):
    """Predefined cache key patterns for consistency."""

    # JWT Token Validation Cache
    JWT_TOKEN = "jwt:token:{token_hash}"
    JWT_USER = "jwt:user:{user_id}"

    # Rate Limiting Cache
    RATE_LIMIT_USER = "rate_limit:user:{user_id}:{endpoint}"
    RATE_LIMIT_IP = "rate_limit:ip:{ip_address}:{endpoint}"
    RATE_LIMIT_API_KEY = "rate_limit:api_key:{api_key_hash}:{endpoint}"

    # Session State Cache
    SESSION_STATE = "session:state:{session_id}"
    SESSION_USER = "session:user:{user_id}"

    # User Information Cache
    USER_INFO = "user:info:{user_id}"
    USER_PERMISSIONS = "user:permissions:{user_id}"

    # API Response Cache
    API_RESPONSE = "api:response:{endpoint}:{param_hash}"

    # Health Check Cache
    HEALTH_CHECK = "health:check:{service_name}"


class CacheService:
    """
    High-level cache service with business logic integration.

    Features:
    - Type-specific TTL configuration
    - Cache invalidation strategies
    - JSON serialization for complex objects
    - Cache warming and preloading
    - Statistics and monitoring
    """

    def __init__(self):
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "errors": 0}

    # JWT Token Caching
    async def cache_jwt_validation(self, token_hash: str, user_data: Dict[str, Any]) -> bool:
        """Cache JWT token validation result."""
        try:
            key = CacheKey.JWT_TOKEN.value.format(token_hash=token_hash)
            value = json.dumps(
                {
                    "user_data": user_data,
                    "cached_at": datetime.utcnow().isoformat(),
                    "expires_at": (
                        datetime.utcnow() + timedelta(seconds=settings.CACHE_TTL_JWT_TOKEN)
                    ).isoformat(),
                }
            )

            success = await RedisOperations.set_with_ttl(key, value, settings.CACHE_TTL_JWT_TOKEN)

            if success:
                self.stats["sets"] += 1
                logger.debug(f"✅ Cached JWT validation for token hash: {token_hash[:8]}...")
            else:
                self.stats["errors"] += 1
                logger.warning(
                    f"⚠️ Failed to cache JWT validation for token hash: {token_hash[:8]}..."
                )

            return success

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Error caching JWT validation: {e}")
            return False

    async def get_cached_jwt_validation(self, token_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached JWT validation result."""
        try:
            key = CacheKey.JWT_TOKEN.value.format(token_hash=token_hash)
            cached_data = await RedisOperations.get(key)

            if cached_data:
                self.stats["hits"] += 1
                data = json.loads(cached_data)
                logger.debug(f"✅ Cache hit for JWT validation: {token_hash[:8]}...")
                return data.get("user_data")
            else:
                self.stats["misses"] += 1
                logger.debug(f"⚠️ Cache miss for JWT validation: {token_hash[:8]}...")
                return None

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Error getting cached JWT validation: {e}")
            return None

    async def invalidate_jwt_cache(self, token_hash: str) -> bool:
        """Invalidate JWT token cache."""
        try:
            key = CacheKey.JWT_TOKEN.value.format(token_hash=token_hash)
            success = await RedisOperations.delete(key)

            if success:
                self.stats["deletes"] += 1
                logger.debug(f"✅ Invalidated JWT cache for token: {token_hash[:8]}...")

            return success

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Error invalidating JWT cache: {e}")
            return False

    # Rate Limiting Cache
    async def increment_rate_limit_counter(
        self, key_type: str, identifier: str, endpoint: str, window_seconds: int = None
    ) -> Optional[int]:
        """Increment rate limit counter and return current count."""
        try:
            # Determine cache key based on type
            if key_type == "user":
                cache_key = CacheKey.RATE_LIMIT_USER.value.format(
                    user_id=identifier, endpoint=endpoint
                )
            elif key_type == "ip":
                cache_key = CacheKey.RATE_LIMIT_IP.value.format(
                    ip_address=identifier, endpoint=endpoint
                )
            elif key_type == "api_key":
                cache_key = CacheKey.RATE_LIMIT_API_KEY.value.format(
                    api_key_hash=identifier, endpoint=endpoint
                )
            else:
                raise ValueError(f"Invalid rate limit key type: {key_type}")

            # Increment counter
            current_count = await RedisOperations.increment(cache_key, 1)

            if current_count is not None:
                # Set TTL if this is the first increment
                if current_count == 1:
                    ttl = window_seconds or settings.CACHE_TTL_RATE_LIMIT
                    await RedisOperations.expire(cache_key, ttl)

                logger.debug(f"✅ Rate limit counter incremented: {cache_key} = {current_count}")
                return current_count
            else:
                self.stats["errors"] += 1
                return None

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Error incrementing rate limit counter: {e}")
            return None

    async def get_rate_limit_count(self, key_type: str, identifier: str, endpoint: str) -> int:
        """Get current rate limit count."""
        try:
            # Determine cache key based on type
            if key_type == "user":
                cache_key = CacheKey.RATE_LIMIT_USER.value.format(
                    user_id=identifier, endpoint=endpoint
                )
            elif key_type == "ip":
                cache_key = CacheKey.RATE_LIMIT_IP.value.format(
                    ip_address=identifier, endpoint=endpoint
                )
            elif key_type == "api_key":
                cache_key = CacheKey.RATE_LIMIT_API_KEY.value.format(
                    api_key_hash=identifier, endpoint=endpoint
                )
            else:
                raise ValueError(f"Invalid rate limit key type: {key_type}")

            cached_value = await RedisOperations.get(cache_key)
            return int(cached_value) if cached_value else 0

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Error getting rate limit count: {e}")
            return 0

    # User Information Cache
    async def cache_user_info(self, user_id: str, user_info: Dict[str, Any]) -> bool:
        """Cache user information."""
        try:
            key = CacheKey.USER_INFO.value.format(user_id=user_id)
            value = json.dumps({"user_info": user_info, "cached_at": datetime.utcnow().isoformat()})

            success = await RedisOperations.set_with_ttl(key, value, settings.CACHE_TTL_USER_INFO)

            if success:
                self.stats["sets"] += 1
                logger.debug(f"✅ Cached user info for user: {user_id}")
            else:
                self.stats["errors"] += 1

            return success

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Error caching user info: {e}")
            return False

    async def get_cached_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user information."""
        try:
            key = CacheKey.USER_INFO.value.format(user_id=user_id)
            cached_data = await RedisOperations.get(key)

            if cached_data:
                self.stats["hits"] += 1
                data = json.loads(cached_data)
                logger.debug(f"✅ Cache hit for user info: {user_id}")
                return data.get("user_info")
            else:
                self.stats["misses"] += 1
                return None

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Error getting cached user info: {e}")
            return None

    # Session State Cache
    async def cache_session_state(self, session_id: str, state_data: Dict[str, Any]) -> bool:
        """Cache session state for SSE connections."""
        try:
            key = CacheKey.SESSION_STATE.value.format(session_id=session_id)
            value = json.dumps(
                {
                    "state_data": state_data,
                    "cached_at": datetime.utcnow().isoformat(),
                    "last_activity": datetime.utcnow().isoformat(),
                }
            )

            success = await RedisOperations.set_with_ttl(
                key, value, settings.CACHE_TTL_SESSION_STATE
            )

            if success:
                self.stats["sets"] += 1
                logger.debug(f"✅ Cached session state: {session_id}")
            else:
                self.stats["errors"] += 1

            return success

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Error caching session state: {e}")
            return False

    async def get_cached_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached session state."""
        try:
            key = CacheKey.SESSION_STATE.value.format(session_id=session_id)
            cached_data = await RedisOperations.get(key)

            if cached_data:
                self.stats["hits"] += 1
                data = json.loads(cached_data)
                logger.debug(f"✅ Cache hit for session state: {session_id}")
                return data.get("state_data")
            else:
                self.stats["misses"] += 1
                return None

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Error getting cached session state: {e}")
            return None

    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp."""
        try:
            key = CacheKey.SESSION_STATE.value.format(session_id=session_id)
            cached_data = await RedisOperations.get(key)

            if cached_data:
                data = json.loads(cached_data)
                data["last_activity"] = datetime.utcnow().isoformat()

                success = await RedisOperations.set_with_ttl(
                    key, json.dumps(data), settings.CACHE_TTL_SESSION_STATE
                )

                if success:
                    logger.debug(f"✅ Updated session activity: {session_id}")
                return success
            else:
                logger.debug(f"⚠️ Session not found in cache: {session_id}")
                return False

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Error updating session activity: {e}")
            return False

    # Cache Invalidation
    async def invalidate_user_cache(self, user_id: str) -> Dict[str, bool]:
        """Invalidate all cache entries for a user."""
        results = {}

        try:
            # Invalidate user info cache
            user_info_key = CacheKey.USER_INFO.value.format(user_id=user_id)
            results["user_info"] = await RedisOperations.delete(user_info_key)

            # Invalidate user permissions cache
            permissions_key = CacheKey.USER_PERMISSIONS.value.format(user_id=user_id)
            results["permissions"] = await RedisOperations.delete(permissions_key)

            # Invalidate session cache
            session_key = CacheKey.SESSION_USER.value.format(user_id=user_id)
            results["session"] = await RedisOperations.delete(session_key)

            successful_invalidations = sum(1 for success in results.values() if success)
            logger.info(
                f"✅ Invalidated {successful_invalidations} cache entries for user: {user_id}"
            )

            return results

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Error invalidating user cache: {e}")
            return {"error": False}

    # Cache Statistics and Monitoring
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_operations = sum(self.stats.values())
        hit_rate = (
            (self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])) * 100
            if (self.stats["hits"] + self.stats["misses"]) > 0
            else 0
        )

        return {
            **self.stats,
            "total_operations": total_operations,
            "hit_rate_percent": round(hit_rate, 2),
            "error_rate_percent": round((self.stats["errors"] / total_operations) * 100, 2)
            if total_operations > 0
            else 0,
        }

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "errors": 0}
        logger.info("📊 Cache statistics reset")

    async def health_check(self) -> Dict[str, Any]:
        """Perform cache service health check."""
        try:
            # Test Redis connectivity
            redis_healthy = await get_redis_manager().is_healthy()

            # Test basic operations
            test_key = "health:check:test"
            test_value = "healthy"

            set_success = await RedisOperations.set_with_ttl(test_key, test_value, 60)
            get_success = await RedisOperations.get(test_key) == test_value
            delete_success = await RedisOperations.delete(test_key)

            operations_healthy = set_success and get_success and delete_success

            return {
                "healthy": redis_healthy and operations_healthy,
                "redis_connection": redis_healthy,
                "basic_operations": operations_healthy,
                "stats": self.get_stats(),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Cache health check failed: {e}")
            return {"healthy": False, "error": str(e), "timestamp": datetime.utcnow().isoformat()}


# Global cache service instance
cache_service = CacheService()


# Dependency injection helpers
async def get_cache_service() -> CacheService:
    """FastAPI dependency for getting cache service."""
    return cache_service


# Utility functions for common caching patterns
async def cached_function(cache_key: str, func, ttl_seconds: int = None, *args, **kwargs) -> Any:
    """
    Generic function caching decorator.

    Usage:
        result = await cached_function(
            "my_key",
            expensive_function,
            3600,  # TTL
            arg1, arg2,
            kwarg1=value1
        )
    """
    try:
        # Try to get from cache first
        cached_result = await RedisOperations.get(cache_key)
        if cached_result:
            cache_service.stats["hits"] += 1
            return json.loads(cached_result)

        # Execute function and cache result
        result = (
            await func(*args, **kwargs)
            if asyncio.iscoroutinefunction(func)
            else func(*args, **kwargs)
        )

        # Cache the result
        ttl = ttl_seconds or settings.CACHE_TTL_DEFAULT
        await RedisOperations.set_with_ttl(cache_key, json.dumps(result), ttl)
        cache_service.stats["sets"] += 1
        cache_service.stats["misses"] += 1

        return result

    except Exception as e:
        cache_service.stats["errors"] += 1
        logger.error(f"❌ Error in cached_function: {e}")
        # Fall back to executing function without caching
        return (
            await func(*args, **kwargs)
            if asyncio.iscoroutinefunction(func)
            else func(*args, **kwargs)
        )


# Export commonly used items
__all__ = ["CacheService", "CacheKey", "cache_service", "get_cache_service", "cached_function"]
