"""
Redis client wrapper for OAuth2 state management.

This module provides a Redis client wrapper specifically designed for managing
OAuth2 authorization states with proper expiration and cleanup.
"""

import json
import logging
from typing import Optional, Dict, Any
from uuid import uuid4

import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from workflow_engine.core.config import get_settings


logger = logging.getLogger(__name__)


class RedisClientError(Exception):
    """Base exception for Redis client errors."""
    pass


class RedisConnectionError(RedisClientError):
    """Raised when Redis connection fails."""
    pass


class RedisStateError(RedisClientError):
    """Raised when state operations fail."""
    pass


class RedisClient:
    """
    Redis client wrapper for OAuth2 state management.
    
    Provides methods for storing and retrieving OAuth2 authorization states
    with automatic expiration and JSON serialization.
    """
    
    def __init__(self):
        """Initialize Redis client."""
        self.settings = get_settings()
        self._redis: Optional[redis.Redis] = None
        self._state_prefix = "oauth2_state:"
        
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection with lazy initialization."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self.settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                # Test connection
                await self._redis.ping()
                logger.info(f"Redis connected to {self.settings.redis_url}")
            except (RedisConnectionError, RedisError) as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise RedisConnectionError(f"Redis connection failed: {e}")
        
        return self._redis
    
    async def store_oauth_state(
        self, 
        user_id: str, 
        provider: str, 
        redirect_uri: Optional[str] = None,
        scopes: Optional[list] = None
    ) -> str:
        """
        Store OAuth2 authorization state.
        
        Args:
            user_id: User identifier
            provider: OAuth2 provider (google_calendar, github, slack)
            redirect_uri: Optional redirect URI
            scopes: Optional list of requested scopes
            
        Returns:
            Generated state parameter for OAuth2 authorization
            
        Raises:
            RedisStateError: If state storage fails
        """
        try:
            redis_client = await self._get_redis()
            
            # Generate unique state parameter
            state = str(uuid4())
            
            # Prepare state data
            state_data = {
                "user_id": user_id,
                "provider": provider,
                "created_at": str(int(__import__("time").time())),
            }
            
            if redirect_uri:
                state_data["redirect_uri"] = redirect_uri
            if scopes:
                state_data["scopes"] = scopes
            
            # Store state with expiration
            key = f"{self._state_prefix}{state}"
            await redis_client.setex(
                key, 
                self.settings.oauth2_state_expiry, 
                json.dumps(state_data)
            )
            
            logger.info(f"OAuth2 state stored for user {user_id}, provider {provider}")
            return state
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Failed to store OAuth2 state: {e}")
            raise RedisStateError(f"State storage failed: {e}")
    
    async def get_oauth_state(self, state: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve OAuth2 authorization state.
        
        Args:
            state: State parameter from OAuth2 authorization
            
        Returns:
            State data dictionary, or None if not found/expired
            
        Raises:
            RedisStateError: If state retrieval fails
        """
        try:
            redis_client = await self._get_redis()
            
            key = f"{self._state_prefix}{state}"
            state_json = await redis_client.get(key)
            
            if state_json is None:
                logger.warning(f"OAuth2 state not found or expired: {state}")
                return None
            
            state_data = json.loads(state_json)
            logger.info(f"OAuth2 state retrieved for state: {state}")
            return state_data
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to retrieve OAuth2 state: {e}")
            raise RedisStateError(f"State retrieval failed: {e}")
    
    async def delete_oauth_state(self, state: str) -> bool:
        """
        Delete OAuth2 authorization state.
        
        Args:
            state: State parameter to delete
            
        Returns:
            True if state was deleted, False if not found
            
        Raises:
            RedisStateError: If state deletion fails
        """
        try:
            redis_client = await self._get_redis()
            
            key = f"{self._state_prefix}{state}"
            deleted = await redis_client.delete(key)
            
            if deleted:
                logger.info(f"OAuth2 state deleted: {state}")
            else:
                logger.warning(f"OAuth2 state not found for deletion: {state}")
            
            return bool(deleted)
            
        except RedisError as e:
            logger.error(f"Failed to delete OAuth2 state: {e}")
            raise RedisStateError(f"State deletion failed: {e}")
    
    async def cleanup_expired_states(self) -> int:
        """
        Clean up expired OAuth2 states.
        
        Returns:
            Number of states cleaned up
            
        Raises:
            RedisStateError: If cleanup fails
        """
        try:
            redis_client = await self._get_redis()
            
            # Get all state keys
            pattern = f"{self._state_prefix}*"
            keys = await redis_client.keys(pattern)
            
            if not keys:
                return 0
            
            # Check which keys still exist (non-expired)
            existing_keys = await redis_client.exists(*keys)
            cleaned_count = len(keys) - existing_keys
            
            logger.info(f"OAuth2 state cleanup: {cleaned_count} expired states removed")
            return cleaned_count
            
        except RedisError as e:
            logger.error(f"Failed to cleanup OAuth2 states: {e}")
            raise RedisStateError(f"State cleanup failed: {e}")
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis connection closed")


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """Get global Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


async def close_redis_client():
    """Close global Redis client instance."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None 