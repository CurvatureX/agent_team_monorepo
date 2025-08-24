"""
Supabase client configuration for workflow_scheduler
"""

import logging
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from workflow_scheduler.core.config import settings

logger = logging.getLogger(__name__)

# Global Supabase client instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance
    Uses service role key for admin operations
    """
    global _supabase_client

    if _supabase_client is None:
        if not settings.supabase_url or not settings.supabase_secret_key:
            raise ValueError("Supabase URL and secret key must be configured")

        _supabase_client = create_client(settings.supabase_url, settings.supabase_secret_key)
        logger.info("✅ Supabase client initialized successfully")

    return _supabase_client


async def query_github_triggers(repository_name: str) -> List[Dict[str, Any]]:
    """
    Query active GitHub triggers for a repository using Supabase client

    Args:
        repository_name: Repository name (e.g., "CurvatureX/agent_team_monorepo")

    Returns:
        List of trigger records
    """
    try:
        client = get_supabase_client()

        # Query trigger_index table
        response = (
            client.table("trigger_index")
            .select("*")
            .eq("trigger_type", "GITHUB")
            .eq("deployment_status", "active")
            .eq("index_key", repository_name)
            .execute()
        )

        logger.info(f"Found {len(response.data)} GitHub triggers for repository {repository_name}")
        return response.data

    except Exception as e:
        logger.error(f"Error querying GitHub triggers from Supabase: {e}", exc_info=True)
        return []


async def query_slack_triggers() -> List[Dict[str, Any]]:
    """
    Query active Slack triggers using Supabase client

    Returns:
        List of trigger records with workflow_id and trigger_config
    """
    try:
        client = get_supabase_client()

        # Query trigger_index table for active Slack triggers
        response = (
            client.table("trigger_index")
            .select("workflow_id, trigger_config")
            .eq("trigger_type", "SLACK")
            .eq("deployment_status", "active")
            .execute()
        )

        logger.info(f"Found {len(response.data)} Slack triggers via Supabase")
        return response.data

    except Exception as e:
        logger.error(f"Error querying Slack triggers from Supabase: {e}", exc_info=True)
        return []


async def health_check() -> Dict[str, Any]:
    """
    Health check for Supabase connection
    """
    try:
        client = get_supabase_client()

        # Simple query to test connection
        response = client.table("trigger_index").select("count").limit(1).execute()

        return {
            "status": "healthy",
            "supabase_url": settings.supabase_url,
            "connection": "ok",
        }

    except Exception as e:
        logger.error(f"Supabase health check failed: {e}")
        return {
            "status": "unhealthy",
            "supabase_url": settings.supabase_url,
            "error": str(e),
        }
