"""
JWT Token Verification for Frontend Authentication with Caching
支持缓存的JWT令牌验证服务
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.services.cache import cache_service

logger = logging.getLogger("app.services.auth_service")


def _validate_jwt_format(token: str) -> bool:
    """
    Validate JWT token format before sending to Supabase
    JWT should have exactly 3 segments separated by dots
    """
    if not token or not isinstance(token, str):
        return False

    # JWT tokens should have exactly 3 parts separated by dots
    parts = token.split(".")
    if len(parts) != 3:
        return False

    # Each part should be non-empty
    if any(not part or part.strip() == "" for part in parts):
        return False

    # Basic length check - JWT parts are typically base64 encoded and have minimum lengths
    if any(len(part) < 4 for part in parts):
        return False

    return True


async def verify_supabase_token(token: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token with Supabase Auth with caching support
    支持缓存的JWT令牌验证

    Args:
        token: JWT access token from frontend Supabase client
        use_cache: Whether to use cache for token validation (default: True)

    Returns:
        User data if token is valid, None otherwise
    """
    try:
        # Log token analysis for debugging
        token_info = {
            "token_length": len(token) if token else 0,
            "token_prefix": token[:10] + "..." if token and len(token) > 10 else token,
            "segment_count": len(token.split(".")) if token else 0,
        }
        logger.debug(f"JWT token analysis: {token_info}")

        # Early validation of JWT format
        if not _validate_jwt_format(token):
            logger.warning(
                f"Invalid JWT token format: token does not contain exactly 3 segments. "
                f"Token info: {token_info}"
            )
            return None

        # Create token hash for caching
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Try to get from cache first
        if use_cache:
            cached_user_data = await cache_service.get_cached_jwt_validation(token_hash)
            if cached_user_data:
                logger.info(f"Cache hit for JWT token {token_hash[:8]}...")
                return cached_user_data

        # Token not in cache or cache disabled, verify with Supabase
        # Create a new Supabase client to avoid DNS caching issues
        from app.core.config import settings
        from supabase import create_client

        if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
            logger.error("Supabase configuration missing")
            return None

        # Create client with retry for DNS issues
        max_retries = 3
        for attempt in range(max_retries):
            try:
                supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
                response = supabase.auth.get_user(token)
                break
            except Exception as e:
                if "name resolution" in str(e) and attempt < max_retries - 1:
                    logger.warning(
                        f"DNS resolution failed, retrying... "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    import time

                    time.sleep(1)  # Wait 1 second before retry
                    continue
                else:
                    raise

        if response and response.user and response.user.id:
            user_data = {
                "id": response.user.id,  # AuthUser expects 'id' field
                "sub": response.user.id,
                "email": response.user.email,
                "email_confirmed_at": (
                    response.user.email_confirmed_at.isoformat()
                    if response.user.email_confirmed_at
                    else None
                ),
                "created_at": (
                    response.user.created_at.isoformat() if response.user.created_at else None
                ),
                "user_metadata": response.user.user_metadata,
                "app_metadata": response.user.app_metadata,
                # Add token validation metadata
                "validated_at": datetime.now().isoformat(),
                "token_hash": token_hash[:16],  # Store partial hash for debugging
            }

            # Cache the validation result if cache is enabled
            if use_cache:
                cache_success = await cache_service.cache_jwt_validation(token_hash, user_data)
                if cache_success:
                    logger.info(f"JWT validation cached for token {token_hash[:8]}...")
                else:
                    logger.error(f"Failed to cache JWT validation for token {token_hash[:8]}...")

            logger.info(f"Token verified for user: {response.user.email}")
            return user_data

        logger.error("Invalid token - no user data returned")
        return None

    except Exception as e:
        logger.exception(f"Token verification failed: {e}")
        return None


async def invalidate_user_token_cache(user_id: str) -> bool:
    """
    Invalidate all cached tokens for a specific user
    使某个用户的所有缓存令牌失效

    Args:
        user_id: User ID to invalidate tokens for

    Returns:
        True if invalidation was successful
    """
    try:
        # Invalidate user-specific caches
        invalidation_results = await cache_service.invalidate_user_cache(user_id)

        successful_invalidations = sum(1 for success in invalidation_results.values() if success)
        logger.info(f"Invalidated {successful_invalidations} cache entries for user {user_id}")

        return successful_invalidations > 0

    except Exception as e:
        logger.exception(f"Error invalidating user token cache: {e}")
        return False


async def invalidate_token_cache(token: str) -> bool:
    """
    Invalidate cache for a specific token
    使特定令牌的缓存失效

    Args:
        token: JWT token to invalidate

    Returns:
        True if invalidation was successful
    """
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        success = await cache_service.invalidate_jwt_cache(token_hash)

        if success:
            logger.info(f"Invalidated token cache {token_hash[:8]}...")
        else:
            logger.error(f"Failed to invalidate token cache {token_hash[:8]}...")

        return success

    except Exception as e:
        logger.exception(f"Error invalidating token cache: {e}")
        return False


async def get_auth_cache_stats() -> Dict[str, Any]:
    """
    Get authentication cache statistics
    获取认证缓存统计信息

    Returns:
        Dictionary containing cache statistics
    """
    try:
        stats = cache_service.get_stats()
        health = await cache_service.health_check()

        return {
            "cache_stats": stats,
            "health_status": health,
            "cache_enabled": True,
            "features": {
                "jwt_token_caching": True,
                "user_info_caching": True,
                "rate_limiting": True,
                "session_state_caching": True,
            },
        }

    except Exception as e:
        logger.exception(f"Error getting auth cache stats: {e}")
        return {"error": str(e), "cache_enabled": False}
