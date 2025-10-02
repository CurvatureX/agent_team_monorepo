"""
Shared Supabase client creation utilities.

This module provides utilities for creating Supabase clients consistently
across all backend services in the workflow_engine_v2 architecture.
"""

import logging
import os
from typing import Optional

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

logger = logging.getLogger(__name__)


def create_supabase_client() -> Optional[Client]:
    """
    Create a Supabase client using environment variables.

    Uses SUPABASE_URL and SUPABASE_SECRET_KEY from environment.

    Returns:
        Optional[Client]: Supabase client instance or None if configuration is missing
    """
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY")

        if not supabase_url or not supabase_secret_key:
            logger.warning("Missing SUPABASE_URL or SUPABASE_SECRET_KEY environment variables")
            return None

        # Create client with service role key for administrative operations
        client_options = ClientOptions(
            schema="public", headers={}, auto_refresh_token=False, persist_session=False
        )

        client = create_client(supabase_url, supabase_secret_key, options=client_options)
        logger.debug("✅ Supabase client created successfully")

        return client

    except Exception as e:
        logger.error(f"❌ Failed to create Supabase client: {e}")
        return None


def create_supabase_anon_client() -> Optional[Client]:
    """
    Create a Supabase client using anonymous key for RLS operations.

    Uses SUPABASE_URL and SUPABASE_ANON_KEY from environment.

    Returns:
        Optional[Client]: Supabase client instance or None if configuration is missing
    """
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_anon_key:
            logger.warning("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")
            return None

        client = create_client(supabase_url, supabase_anon_key)
        logger.debug("✅ Supabase anonymous client created successfully")

        return client

    except Exception as e:
        logger.error(f"❌ Failed to create Supabase anonymous client: {e}")
        return None


def create_user_supabase_client(access_token: str) -> Optional[Client]:
    """
    Create a user-specific Supabase client with RLS authentication.

    Args:
        access_token: User's JWT access token for RLS

    Returns:
        Optional[Client]: Supabase client with user context or None if configuration is missing
    """
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_anon_key or not access_token:
            logger.error("Missing SUPABASE_URL, SUPABASE_ANON_KEY, or access_token for user client")
            return None

        # Create client using ANON_KEY and set user access_token for RLS
        client = create_client(supabase_url, supabase_anon_key)

        # Set the user's access token in headers for RLS authentication
        client.options.headers["Authorization"] = f"Bearer {access_token}"

        logger.debug("✅ User-specific Supabase client created successfully")
        return client

    except Exception as e:
        logger.error(f"❌ Failed to create user-specific Supabase client: {e}")
        return None


__all__ = ["create_supabase_client", "create_supabase_anon_client", "create_user_supabase_client"]
