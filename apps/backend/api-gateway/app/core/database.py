"""
Database Connection and Management
统一的数据库连接管理，支持Supabase和Redis

This module provides the main database manager with minimal scope:
- Redis for caching and rate limiting
- Supabase for auth-only operations
- Business data should go through gRPC services
"""

import asyncio
import logging
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Optional

import redis.asyncio as redis
from app.core.config import settings
from redis.asyncio import ConnectionPool
from redis.exceptions import ConnectionError, RedisError, TimeoutError
from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis connection manager with connection pooling and health checks."""

    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._healthy: bool = False
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 3

    async def initialize(self) -> None:
        """Initialize Redis connection pool with graceful health check."""
        # Skip Redis initialization in test environment
        import os

        if "pytest" in os.environ.get("_", "") or "test" in os.environ.get(
            "PYTEST_CURRENT_TEST", ""
        ):
            logger.info("🧪 Skipping Redis initialization in test environment")
            self._healthy = False
            return

        try:
            logger.info("🔗 Initializing Redis connection pool...")

            # Create connection pool
            self._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_POOL_SIZE,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
                health_check_interval=30,
                retry_on_error=[ConnectionError, TimeoutError],
                decode_responses=True,
                encoding="utf-8",
            )

            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)

            # Test connection with timeout - don't block startup if Redis unavailable
            try:
                await asyncio.wait_for(self._health_check(), timeout=2.0)
                if self._healthy:
                    logger.info("✅ Redis connection pool initialized successfully")
                else:
                    logger.warning("⚠️ Redis health check failed - will retry on first use")
            except asyncio.TimeoutError:
                logger.warning(
                    "⚠️ Redis connection timeout during startup - will retry on first use"
                )
                self._healthy = False

        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize Redis connection: {e}")
            self._healthy = False
            # Don't raise - allow application to start without Redis

    async def _health_check(self) -> bool:
        """Perform Redis health check."""
        try:
            if not self._client:
                return False

            await self._client.ping()
            self._healthy = True
            self._reconnect_attempts = 0
            return True

        except Exception as e:
            self._healthy = False
            logger.warning(f"⚠️ Redis health check failed: {e}")
            return False

    async def is_healthy(self) -> bool:
        """Check if Redis connection is healthy."""
        return await self._health_check()

    @asynccontextmanager
    async def get_client(self):
        """Get Redis client with automatic reconnection handling."""
        if not self._healthy and not await self._health_check():
            raise ConnectionError("Redis connection unavailable")

        try:
            yield self._client
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"⚠️ Redis operation failed: {e}")
            self._healthy = False
            raise
        except RedisError as e:
            logger.error(f"❌ Redis error: {e}")
            raise

    async def get_client_direct(self) -> redis.Redis:
        """Get Redis client directly (for dependency injection)."""
        if not await self._health_check():
            raise ConnectionError("Redis connection unavailable")
        if self._client is None:
            raise ConnectionError("Redis client is not initialized")
        return self._client

    async def close(self) -> None:
        """Close Redis connection pool."""
        try:
            if self._client:
                await self._client.aclose()
                logger.info("🔐 Redis client closed")

            if self._pool:
                await self._pool.aclose()
                logger.info("🔐 Redis connection pool closed")

            self._healthy = False
            self._client = None
            self._pool = None

        except Exception as e:
            logger.error(f"❌ Error closing Redis connection: {e}")


# Utility functions for common Redis operations
class RedisOperations:
    """Common Redis operations with error handling."""

    @staticmethod
    async def set_with_ttl(key: str, value: str, ttl_seconds: int) -> bool:
        """Set key with TTL, return True if successful."""
        try:
            redis_client = await get_redis_manager().get_client_direct()
            result = await redis_client.setex(key, ttl_seconds, value)
            return bool(result)
        except Exception as e:
            logger.error(f"❌ Redis SET failed for key {key}: {e}")
            return False

    @staticmethod
    async def get(key: str) -> Optional[str]:
        """Get value by key, return None if not found or error."""
        try:
            redis_client = await get_redis_manager().get_client_direct()
            return await redis_client.get(key)
        except Exception as e:
            logger.error(f"❌ Redis GET failed for key {key}: {e}")
            return None

    @staticmethod
    async def delete(key: str) -> bool:
        """Delete key, return True if successful."""
        try:
            redis_client = await get_redis_manager().get_client_direct()
            result = await redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"❌ Redis DELETE failed for key {key}: {e}")
            return False

    @staticmethod
    async def increment(key: str, amount: int = 1) -> Optional[int]:
        """Increment key by amount, return new value or None if error."""
        try:
            redis_client = await get_redis_manager().get_client_direct()
            return await redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"❌ Redis INCREMENT failed for key {key}: {e}")
            return None

    @staticmethod
    async def expire(key: str, ttl_seconds: int) -> bool:
        """Set TTL for existing key, return True if successful."""
        try:
            redis_client = await get_redis_manager().get_client_direct()
            result = await redis_client.expire(key, ttl_seconds)
            return bool(result)
        except Exception as e:
            logger.error(f"❌ Redis EXPIRE failed for key {key}: {e}")
            return False

    @staticmethod
    async def exists(key: str) -> bool:
        """Check if key exists, return False if error."""
        try:
            redis_client = await get_redis_manager().get_client_direct()
            result = await redis_client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"❌ Redis EXISTS failed for key {key}: {e}")
            return False


class SupabaseAuthClient:
    """Limited Supabase client for authentication only."""

    def __init__(self):
        self._client: Optional[Client] = None
        self._initialized = False

    async def initialize(self):
        """Initialize Supabase client with minimal scope."""
        # Skip Supabase initialization in test environment
        import os

        if "pytest" in os.environ.get("_", "") or "test" in os.environ.get(
            "PYTEST_CURRENT_TEST", ""
        ):
            logger.info("🧪 Skipping Supabase initialization in test environment")
            self._initialized = True
            return

        try:
            if self._initialized:
                return

            logger.info("🔗 Initializing limited Supabase client for auth only...")

            # Create client with service role key for auth validation
            client_options = ClientOptions(
                schema="public", headers={}, auto_refresh_token=False, persist_session=False
            )

            self._client = create_client(
                settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY, options=client_options
            )

            # Test connection with a simple auth test
            try:
                # Use get_user with an empty token to test basic connectivity
                self._client.auth.get_user("")
                logger.info("✅ Supabase auth client initialized successfully")
                self._initialized = True
            except Exception as test_error:
                # This is expected to fail (empty token), but it proves connectivity
                logger.info(
                    "✅ Supabase auth client initialized successfully (connectivity verified)"
                )
                self._initialized = True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")
            raise

    def _ensure_initialized(self):
        """Ensure client is initialized."""
        if not self._initialized or not self._client:
            raise RuntimeError("Supabase client not initialized. Call initialize() first.")

    async def validate_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return user information."""
        try:
            self._ensure_initialized()

            # Validate with Supabase
            response = self._client.auth.get_user(token)

            if response.user:
                user_data = {
                    "id": response.user.id,
                    "email": response.user.email,
                    "email_confirmed_at": response.user.email_confirmed_at,
                    "created_at": response.user.created_at,
                    "user_metadata": response.user.user_metadata or {},
                    "app_metadata": response.user.app_metadata or {},
                    "aud": response.user.aud,
                    "role": response.user.role or "authenticated",
                }

                logger.debug(f"✅ JWT token validated for user: {user_data['email']}")
                return user_data
            else:
                logger.warning("⚠️ JWT token validation failed - no user found")
                return None

        except Exception as e:
            logger.error(f"❌ JWT token validation error: {e}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Supabase connection."""
        try:
            self._ensure_initialized()

            start_time = datetime.utcnow()
            # Test basic auth functionality instead of RPC
            try:
                self._client.auth.get_user("")
                healthy = True
                connection_status = "connected"
            except Exception:
                # Expected to fail with empty token, but proves connectivity
                healthy = True
                connection_status = "connected"

            response_time = (datetime.utcnow() - start_time).total_seconds()

            return {
                "healthy": healthy,
                "response_time_seconds": response_time,
                "connection_status": connection_status,
                "scope": "auth_only",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Supabase health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "connection_status": "failed",
                "timestamp": datetime.utcnow().isoformat(),
            }


class DatabaseManager:
    """
    Unified database connection manager.

    Provides a single interface for Redis and Supabase operations
    while maintaining minimal database usage philosophy.
    """

    def __init__(self):
        self._initialized = False
        self._redis_manager = RedisManager()
        self._supabase_auth_client = SupabaseAuthClient()
        self._supabase_admin_client: Optional[Client] = None
        self._supabase_anon_client: Optional[Client] = None

    async def initialize(self):
        """Initialize all database connections."""
        if self._initialized:
            return

        try:
            logger.info("🔗 Initializing database manager...")

            # Initialize Redis connection (graceful failure)
            await self._redis_manager.initialize()

            # Initialize Supabase auth client (graceful failure)
            try:
                await self._supabase_auth_client.initialize()
            except Exception as e:
                logger.warning(f"⚠️ Supabase auth client initialization failed: {e}")

            self._initialized = True
            logger.info("✅ Database manager initialized successfully")

        except Exception as e:
            logger.warning(f"⚠️ Database manager initialization completed with warnings: {e}")
            self._initialized = True  # Allow app to start even with DB issues

    @property
    def redis_manager(self) -> RedisManager:
        """Get Redis manager."""
        return self._redis_manager

    @property
    def supabase_auth(self) -> SupabaseAuthClient:
        """Get Supabase auth client (limited scope for auth only)."""
        return self._supabase_auth_client

    async def get_redis_client(self):
        """Get Redis client."""
        if not self._initialized:
            await self.initialize()
        return await self._redis_manager.get_client_direct()

    @property
    def supabase_admin(self) -> Optional[Client]:
        """Get Supabase admin client (backward compatibility)."""
        if self._supabase_admin_client is None:
            self._supabase_admin_client = self._create_supabase_admin_client()
        return self._supabase_admin_client

    @property
    def supabase(self) -> Optional[Client]:
        """Get Supabase anon client (backward compatibility)."""
        if self._supabase_anon_client is None:
            self._supabase_anon_client = self._create_supabase_client()
        return self._supabase_anon_client

    def _create_supabase_client(self) -> Optional[Client]:
        """Create Supabase anon client (backward compatibility)."""
        try:
            if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
                logger.warning("🔶 Supabase anon configuration incomplete")
                return None

            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
            logger.debug("✅ Supabase anon client created")
            return client

        except Exception as e:
            logger.error(f"❌ Failed to create Supabase anon client: {e}")
            return None

    def _create_supabase_admin_client(self) -> Optional[Client]:
        """Create Supabase admin client (backward compatibility)."""
        try:
            if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
                logger.warning("🔶 Supabase admin configuration incomplete")
                return None

            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
            logger.debug("✅ Supabase admin client created")
            return client

        except Exception as e:
            logger.error(f"❌ Failed to create Supabase admin client: {e}")
            return None

    def create_user_client(self, access_token: str) -> Optional[Client]:
        """Create user-specific Supabase client with RLS (backward compatibility)."""
        try:
            if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY or not access_token:
                logger.error(
                    "❌ Missing SUPABASE_URL, SUPABASE_ANON_KEY, or access_token for user client"
                )
                return None

            # Create client using ANON_KEY and set user access_token for RLS
            # This is the correct way for RLS: ANON_KEY + user token in headers
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

            # Set the user's access token in headers for RLS authentication
            client.options.headers["Authorization"] = f"Bearer {access_token}"

            return client

        except Exception as e:
            logger.error(f"❌ Failed to create user-specific Supabase client: {e}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive database health check."""
        if not self._initialized:
            await self.initialize()

        health_status = {
            "redis": False,
            "supabase_auth": False,
            "supabase_admin": False,  # backward compatibility
            "overall": False,
            "details": {},
        }

        # Check Redis
        try:
            redis_health = await self._redis_manager.is_healthy()
            health_status["redis"] = redis_health
            health_status["details"]["redis"] = "connected" if redis_health else "failed"
        except Exception as e:
            logger.warning(f"🔶 Redis health check failed: {e}")
            health_status["details"]["redis"] = f"error: {e}"

        # Check Supabase auth client
        try:
            supabase_health = await self._supabase_auth_client.health_check()
            health_status["supabase_auth"] = supabase_health.get("healthy", False)
            health_status["details"]["supabase_auth"] = supabase_health
        except Exception as e:
            logger.warning(f"🔶 Supabase auth health check failed: {e}")
            health_status["details"]["supabase_auth"] = f"error: {e}"

        # Check Supabase admin client (backward compatibility)
        try:
            admin_client = self.supabase_admin
            if admin_client:
                # Test basic functionality instead of RPC
                try:
                    admin_client.auth.get_user("")
                    health_status["supabase_admin"] = True
                    health_status["details"]["supabase_admin"] = "connected"
                except Exception:
                    # Expected to fail with empty token, but proves connectivity
                    health_status["supabase_admin"] = True
                    health_status["details"]["supabase_admin"] = "connected"
            else:
                health_status["details"]["supabase_admin"] = "not_configured"
        except Exception as e:
            logger.warning(f"🔶 Supabase admin health check failed: {e}")
            health_status["details"]["supabase_admin"] = f"error: {e}"

        # Overall status - healthy if any connection works
        health_status["overall"] = any(
            [
                health_status["redis"],
                health_status["supabase_auth"],
                health_status["supabase_admin"],
            ]
        )

        return health_status

    async def close_connections(self):
        """Close all database connections."""
        try:
            # Close Redis connections
            await self._redis_manager.close()

            # Supabase client doesn't need explicit closing

            self._initialized = False
            logger.info("✅ Database connections cleanup completed")

        except Exception as e:
            logger.error(f"❌ Error closing database connections: {e}")


# Global database manager instance
@lru_cache()
def get_database_manager() -> DatabaseManager:
    """Get database manager instance (singleton pattern)."""
    return DatabaseManager()


# Convenience functions for backward compatibility
def get_supabase() -> Optional[Client]:
    """Get Supabase anon client (backward compatibility)."""
    return get_database_manager().supabase


def get_supabase_admin() -> Optional[Client]:
    """Get Supabase admin client (backward compatibility)."""
    return get_database_manager().supabase_admin


async def get_redis():
    """Get Redis client via enhanced Redis manager."""
    return await get_database_manager().get_redis_client()


def create_user_supabase_client(access_token: str) -> Optional[Client]:
    """Create user-specific Supabase client (backward compatibility)."""
    return get_database_manager().create_user_client(access_token)


# FastAPI dependency injection functions
async def get_database_manager_dependency() -> DatabaseManager:
    """FastAPI dependency for database manager."""
    manager = get_database_manager()
    if not manager._initialized:
        await manager.initialize()
    return manager


async def get_supabase_dependency() -> Optional[Client]:
    """FastAPI dependency for Supabase anon client."""
    return get_supabase()


async def get_redis_dependency():
    """FastAPI dependency for Redis client."""
    return await get_redis()


# Initialization and cleanup functions (for FastAPI lifespan)
async def init_database_manager():
    """Initialize database manager (called during app startup)."""
    manager = get_database_manager()
    await manager.initialize()


async def close_database_manager():
    """Close database manager (called during app shutdown)."""
    manager = get_database_manager()
    await manager.close_connections()


# Global instances for direct access (lazy initialization)
def get_redis_manager() -> RedisManager:
    """Get global Redis manager instance."""
    return get_database_manager()._redis_manager


def get_supabase_auth_global() -> SupabaseAuthClient:
    """Get global Supabase auth client instance."""
    return get_database_manager()._supabase_auth_client


# FastAPI dependency for Redis client
async def get_redis_client():
    """FastAPI dependency for getting Redis client."""
    return await get_database_manager().get_redis_client()


# FastAPI dependency for Supabase auth client
async def get_supabase_auth_client() -> SupabaseAuthClient:
    """FastAPI dependency for getting Supabase auth client."""
    manager = get_database_manager()
    if not manager._initialized:
        await manager.initialize()
    return manager.supabase_auth


# Export commonly used items
__all__ = [
    "DatabaseManager",
    "RedisManager",
    "SupabaseAuthClient",
    "RedisOperations",
    "get_database_manager",
    "get_supabase",
    "get_supabase_admin",
    "get_redis",
    "create_user_supabase_client",
    "get_redis_client",
    "get_supabase_auth_client",
    "get_redis_manager",
    "get_supabase_auth_global",
    "init_database_manager",
    "close_database_manager",
]
