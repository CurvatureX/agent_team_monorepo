"""
JWT Token Verification for Frontend Authentication with Caching
支持缓存的JWT令牌验证服务
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.database import get_supabase
from app.services.cache import cache_service
from app.utils import log_error, log_exception, log_info


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
        # Create token hash for caching
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Try to get from cache first
        if use_cache:
            cached_user_data = await cache_service.get_cached_jwt_validation(token_hash)
            if cached_user_data:
                log_info(f"🚀 Cache hit for JWT token: {token_hash[:8]}...")
                return cached_user_data

        # Token not in cache or cache disabled, verify with Supabase
        supabase = get_supabase()
        if not supabase:
            log_error("🔥 Supabase client not initialized")
            return None

        # Get user data from JWT token
        response = supabase.auth.get_user(token)

        if response and response.user and response.user.id:
            user_data = {
                "sub": response.user.id,
                "email": response.user.email,
                "email_confirmed_at": response.user.email_confirmed_at,
                "created_at": response.user.created_at,
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
                    log_info(f"💾 JWT validation cached for token: {token_hash[:8]}...")
                else:
                    log_error(f"⚠️ Failed to cache JWT validation for token: {token_hash[:8]}...")

            log_info(f"🔐 Token verified for user: {response.user.email}")
            return user_data

        log_error("🚫 Invalid token - no user data returned")
        return None

    except Exception as e:
        log_exception(f"🔥 Token verification failed: {str(e)}")
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
        log_info(f"✅ Invalidated {successful_invalidations} cache entries for user: {user_id}")

        return successful_invalidations > 0

    except Exception as e:
        log_exception(f"❌ Error invalidating user token cache: {str(e)}")
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
            log_info(f"✅ Invalidated token cache: {token_hash[:8]}...")
        else:
            log_error(f"⚠️ Failed to invalidate token cache: {token_hash[:8]}...")

        return success

    except Exception as e:
        log_exception(f"❌ Error invalidating token cache: {str(e)}")
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
        log_exception(f"❌ Error getting auth cache stats: {str(e)}")
        return {"error": str(e), "cache_enabled": False}
