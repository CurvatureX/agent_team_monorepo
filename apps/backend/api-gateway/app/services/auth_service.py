"""
JWT Token Verification for Frontend Authentication
"""

import structlog
from typing import Optional, Dict, Any
from app.database import get_supabase

logger = structlog.get_logger("auth_service")


async def verify_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token with Supabase Auth - Frontend authentication pattern
    
    Args:
        token: JWT access token from frontend Supabase client
        
    Returns:
        User data if token is valid, None otherwise
    """
    try:
        supabase = get_supabase()
        if not supabase:
            logger.error("🔥 Supabase client not initialized")
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
                "app_metadata": response.user.app_metadata
            }
            logger.info("🔐 Token verified for user", email=response.user.email)
            return user_data
        
        logger.error("🚫 Invalid token - no user data returned")
        return None
        
    except Exception as e:
        logger.exception("🔥 Token verification failed", error=str(e))
        return None