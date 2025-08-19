"""
User Integrations API
用户集成API，获取用户授权的外部应用和服务
需要Supabase OAuth认证
"""

import logging
from typing import Dict, List, Optional

from app.core.database import get_supabase_admin
from app.dependencies import AuthenticatedDeps
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class IntegrationInfo(BaseModel):
    """Integration information model"""

    id: str
    integration_id: str
    provider: str
    integration_type: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str
    credential_data: Optional[Dict] = None
    configuration: Optional[Dict] = None


class UserIntegrationsResponse(BaseModel):
    """User integrations response model"""

    success: bool
    user_id: str
    integrations: List[IntegrationInfo]
    total_count: int


class InstallLinksResponse(BaseModel):
    """Integration install links response model"""

    github: str
    notion: str
    slack: str


@router.get(
    "/integrations",
    response_model=UserIntegrationsResponse,
    summary="Get User Integrations",
    description="""
    Retrieve all integrations (OAuth tokens and app installations) for the authenticated user.

    This includes:
    - GitHub App installations
    - Slack workspace connections
    - Other OAuth-based integrations

    Requires authentication via Supabase JWT token.
    """,
)
async def get_user_integrations(deps: AuthenticatedDeps = Depends()):
    """
    Get all integrations for the authenticated user.

    Returns:
        UserIntegrationsResponse with list of user's integrations
    """
    try:
        user_id = deps.user_data["id"]
        logger.info(f"🔍 Retrieving integrations for user {user_id}")

        supabase_admin = get_supabase_admin()

        if not supabase_admin:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection unavailable",
            )

        # Query oauth_tokens with integration details via JOIN
        result = (
            supabase_admin.table("oauth_tokens")
            .select(
                """
            id,
            integration_id,
            provider,
            is_active,
            created_at,
            updated_at,
            credential_data,
            integrations!oauth_tokens_integration_id_fkey (
                integration_type,
                name,
                description,
                configuration
            )
            """
            )
            .eq("user_id", user_id)
            .execute()
        )

        integrations = []
        for token_data in result.data or []:
            # Handle the joined integration data
            integration_info = token_data.get("integrations", {}) or {}

            integrations.append(
                IntegrationInfo(
                    id=token_data["id"],
                    integration_id=token_data["integration_id"],
                    provider=token_data["provider"],
                    integration_type=integration_info.get("integration_type", "unknown"),
                    name=integration_info.get("name", f"{token_data['provider']} Integration"),
                    description=integration_info.get("description"),
                    is_active=token_data["is_active"],
                    created_at=token_data["created_at"],
                    updated_at=token_data["updated_at"],
                    credential_data=token_data.get("credential_data"),
                    configuration=integration_info.get("configuration"),
                )
            )

        logger.info(f"📋 Found {len(integrations)} integrations for user {user_id}")

        return UserIntegrationsResponse(
            success=True, user_id=user_id, integrations=integrations, total_count=len(integrations)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"❌ Error retrieving user integrations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user integrations",
        )


@router.get(
    "/integrations/install-links",
    response_model=InstallLinksResponse,
    summary="Get Integration Install Links",
    description="""
    Get installation links for integrating external services into the system.

    Currently supports:
    - GitHub App installation with user context
    - Notion workspace integration with OAuth flow
    - Slack workspace integration with OAuth flow

    The links include the user_id as state parameter for proper OAuth flow.

    Requires authentication via Supabase JWT token.
    """,
)
async def get_install_links(deps: AuthenticatedDeps = Depends()):
    """
    Get installation links for external integrations.

    Returns:
        InstallLinksResponse with installation URLs
    """
    try:
        user_id = deps.user_data["id"]
        logger.info(f"🔗 Generating install links for user {user_id}")

        # Generate GitHub App installation link with user_id as state
        github_install_url = f"https://github.com/apps/starmates/installations/new?state={user_id}"

        # Generate Notion OAuth link with user_id as state
        # Notion OAuth requires these parameters:
        # - client_id: Your Notion integration's OAuth client ID
        # - redirect_uri: Must match exactly what's configured in Notion
        # - response_type: Always "code" for authorization code flow
        # - owner: "user" (for personal workspaces only) or omit to allow user/organization selection
        # - state: Optional state parameter for security/user tracking

        from app.config import settings

        notion_oauth_url = (
            f"https://api.notion.com/v1/oauth/authorize"
            f"?client_id={settings.NOTION_CLIENT_ID}"
            f"&redirect_uri={settings.NOTION_REDIRECT_URI}"
            f"&response_type=code"
            f"&state={user_id}"
        )

        # Generate Slack OAuth link with user_id as state
        # Slack OAuth requires these parameters:
        # - client_id: Your Slack app's client ID
        # - scope: Permissions requested (comma-separated)
        # - redirect_uri: Must match exactly what's configured in Slack app
        # - response_type: Always "code" for authorization code flow
        # - state: Optional state parameter for security/user tracking

        slack_oauth_url = (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={settings.SLACK_CLIENT_ID}"
            f"&scope=app_mentions:read,assistant:write,calls:read,calls:write,chat:write,reminders:read,reminders:write,im:read,chat:write.public"
            f"&user_scope=email,identity.basic"
            f"&redirect_uri={settings.SLACK_REDIRECT_URI}"
            f"&response_type=code"
            f"&state={user_id}"
        )

        logger.info(f"✅ Generated install links for user {user_id}")

        return InstallLinksResponse(
            github=github_install_url, notion=notion_oauth_url, slack=slack_oauth_url
        )

    except Exception as e:
        logger.error(f"❌ Error generating install links: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate install links",
        )


@router.get(
    "/integrations/{provider}",
    summary="Get User Integrations by Provider",
    description="""
    Retrieve integrations for a specific provider (e.g., 'github', 'slack').

    Requires authentication via Supabase JWT token.
    """,
)
async def get_user_integrations_by_provider(provider: str, deps: AuthenticatedDeps = Depends()):
    """
    Get integrations for the authenticated user filtered by provider.

    Args:
        provider: The provider name (e.g., 'github', 'slack')

    Returns:
        Filtered list of user's integrations for the specified provider
    """
    try:
        user_id = deps.user_data["id"]
        logger.info(f"🔍 Retrieving {provider} integrations for user {user_id}")

        supabase_admin = get_supabase_admin()

        if not supabase_admin:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection unavailable",
            )

        # Query oauth_tokens filtered by provider
        result = (
            supabase_admin.table("oauth_tokens")
            .select(
                """
            id,
            integration_id,
            provider,
            is_active,
            created_at,
            updated_at,
            credential_data,
            integrations!oauth_tokens_integration_id_fkey (
                integration_type,
                name,
                description,
                configuration
            )
            """
            )
            .eq("user_id", user_id)
            .eq("provider", provider)
            .execute()
        )

        integrations = []
        for token_data in result.data or []:
            # Handle the joined integration data
            integration_info = token_data.get("integrations", {}) or {}

            integrations.append(
                IntegrationInfo(
                    id=token_data["id"],
                    integration_id=token_data["integration_id"],
                    provider=token_data["provider"],
                    integration_type=integration_info.get("integration_type", "unknown"),
                    name=integration_info.get("name", f"{token_data['provider']} Integration"),
                    description=integration_info.get("description"),
                    is_active=token_data["is_active"],
                    created_at=token_data["created_at"],
                    updated_at=token_data["updated_at"],
                    credential_data=token_data.get("credential_data"),
                    configuration=integration_info.get("configuration"),
                )
            )

        logger.info(f"📋 Found {len(integrations)} {provider} integrations for user {user_id}")

        return {
            "success": True,
            "user_id": user_id,
            "provider": provider,
            "integrations": integrations,
            "total_count": len(integrations),
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"❌ Error retrieving {provider} integrations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve {provider} integrations",
        )


@router.delete(
    "/integrations/{integration_token_id}",
    summary="Revoke User Integration",
    description="""
    Revoke/delete a specific integration for the authenticated user.

    This will mark the integration as inactive and remove access.

    Requires authentication via Supabase JWT token.
    """,
)
async def revoke_user_integration(integration_token_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Revoke a specific integration for the authenticated user.

    Args:
        integration_token_id: The ID of the oauth_tokens record to revoke

    Returns:
        Success confirmation
    """
    try:
        user_id = deps.user_data["id"]
        logger.info(f"🗑️ Revoking integration {integration_token_id} for user {user_id}")

        supabase_admin = get_supabase_admin()

        if not supabase_admin:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection unavailable",
            )

        # First check if the integration belongs to this user
        check_result = (
            supabase_admin.table("oauth_tokens")
            .select("id, integration_id, provider")
            .eq("id", integration_token_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not check_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found or doesn't belong to this user",
            )

        integration_info = check_result.data[0]

        # Mark as inactive instead of deleting (for audit purposes)
        update_result = (
            supabase_admin.table("oauth_tokens")
            .update({"is_active": False, "updated_at": "now()"})
            .eq("id", integration_token_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke integration",
            )

        logger.info(
            f"✅ Integration revoked successfully - "
            f"id: {integration_token_id}, provider: {integration_info['provider']}, user: {user_id}"
        )

        return {
            "success": True,
            "message": "Integration revoked successfully",
            "integration_id": integration_token_id,
            "provider": integration_info["provider"],
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"❌ Error revoking integration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to revoke integration"
        )
