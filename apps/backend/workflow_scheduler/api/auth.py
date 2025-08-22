import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from workflow_scheduler.core.config import settings
from workflow_scheduler.core.supabase_client import get_supabase_client
from workflow_scheduler.dependencies import get_trigger_manager
from workflow_scheduler.services.trigger_manager import TriggerManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class GitHubInstallationData(BaseModel):
    """GitHub App installation callback data"""

    installation_id: int
    setup_action: str
    state: Optional[str] = None
    code: Optional[str] = None


class SlackOAuthData(BaseModel):
    """Slack OAuth callback data"""

    code: str
    state: Optional[str] = None


@router.post("/github/callback", response_model=Dict[str, Any])
async def github_installation_callback(
    installation_data: GitHubInstallationData,
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
):
    """
    Handle GitHub App installation callback from API Gateway
    Processes GitHub App installations and updates trigger configuration
    """
    try:
        logger.info(
            f"GitHub installation callback received: installation_id={installation_data.installation_id}, "
            f"action={installation_data.setup_action}, state={installation_data.state}"
        )

        # For now, we'll just acknowledge the installation
        # In the future, this could:
        # 1. Store installation credentials for the GitHub trigger
        # 2. Update existing GitHub triggers with new installation ID
        # 3. Validate installation permissions
        # 4. Sync repository information

        result = {
            "installation_id": installation_data.installation_id,
            "setup_action": installation_data.setup_action,
            "status": "processed",
            "message": "GitHub App installation processed successfully",
        }

        # If we have installation details, we could fetch more info
        if installation_data.setup_action in ["install", "update"]:
            # TODO: In the future, we could:
            # 1. Use the GitHub API to get installation details
            # 2. Get list of repositories this installation has access to
            # 3. Update our internal trigger configurations
            # 4. Validate webhook endpoints are set up correctly

            result.update(
                {
                    "account_login": f"installation_{installation_data.installation_id}",
                    "account_type": "organization",  # or "user" - we'd need to fetch this
                    "repositories": [],  # We'd fetch this from GitHub API
                }
            )

        logger.info(
            f"GitHub installation processed successfully: installation_id={installation_data.installation_id}"
        )

        return result

    except Exception as e:
        logger.error(f"Error processing GitHub installation callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"GitHub installation callback processing failed: {str(e)}"
        )


@router.post("/slack/callback", response_model=Dict[str, Any])
async def slack_oauth_callback(
    oauth_data: SlackOAuthData,
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
):
    """
    Handle Slack OAuth callback from API Gateway
    Processes Slack app installations and OAuth exchanges
    """
    try:
        logger.info(
            f"Slack OAuth callback received: code={'present' if oauth_data.code else 'missing'}, "
            f"state={oauth_data.state}"
        )

        # Exchange authorization code for access tokens
        token_url = "https://slack.com/api/oauth.v2.access"

        token_data = {
            "client_id": settings.slack_client_id,
            "client_secret": settings.slack_client_secret,
            "code": oauth_data.code,
            "redirect_uri": settings.slack_redirect_uri,
        }

        logger.info(
            f"🔧 Slack OAuth token exchange request - client_id: {settings.slack_client_id}, redirect_uri: {settings.slack_redirect_uri}"
        )

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url, data=token_data, headers=headers, timeout=30.0
            )

            if token_response.status_code != 200:
                logger.error(
                    f"Slack token exchange failed: {token_response.status_code} - {token_response.text}"
                )
                raise HTTPException(
                    status_code=token_response.status_code,
                    detail=f"Slack token exchange failed: {token_response.text}",
                )

            token_result = token_response.json()
            logger.info(f"Slack OAuth token exchange response: {token_result}")

            if not token_result.get("ok"):
                error = token_result.get("error", "Unknown error")
                logger.error(f"Slack OAuth error: {error}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Slack OAuth error: {error}",
                )

            # Extract OAuth response data
            # In Slack OAuth v2, access_token is the bot token when using bot scopes
            bot_access_token = token_result.get("access_token")  # Bot token (for posting messages)
            bot_user_id = token_result.get("bot_user_id")

            # User token is under authed_user if user scopes were requested
            authed_user = token_result.get("authed_user", {})
            user_access_token = authed_user.get("access_token")  # User token (optional)
            team_info = token_result.get("team", {})
            team_name = team_info.get("name", "Unknown Team")
            team_id = team_info.get("id", "unknown")

            logger.info(f"Slack OAuth successful for team: {team_name} ({team_id})")

            # Store the integration data if user_id provided in state
            db_store_success = False
            if oauth_data.state:
                logger.info(
                    f"🔄 Attempting to store Slack integration for user_id: {oauth_data.state}"
                )
                try:
                    db_store_success = await _store_slack_integration(
                        oauth_data.state, bot_access_token, team_id, team_name, token_result
                    )
                    if not db_store_success:
                        logger.warning(
                            f"⚠️ Failed to store Slack integration data for user {oauth_data.state}"
                        )
                    else:
                        logger.info(
                            f"✅ Successfully stored Slack integration for user {oauth_data.state}"
                        )
                except Exception as e:
                    logger.error(f"❌ Error storing Slack integration: {e}", exc_info=True)
            else:
                logger.warning(
                    "⚠️ No state (user_id) provided in OAuth callback - cannot store integration"
                )

            result = {
                "team_name": team_name,
                "team_id": team_id,
                "installation_id": oauth_data.state,
                "status": "processed",
                "message": "Slack OAuth processed successfully",
                "stored_in_database": db_store_success,
            }

            logger.info(
                f"Slack OAuth processed successfully: team={team_name}, state={oauth_data.state}"
            )

            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Slack OAuth callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Slack OAuth callback processing failed: {str(e)}"
        )


async def _store_slack_integration(
    user_id: str,
    access_token: str,
    team_id: str,
    team_name: str,
    token_data: dict,
) -> bool:
    """
    Store Slack integration data in oauth_tokens table

    Args:
        user_id: User ID who authorized the integration
        access_token: Slack access token
        team_id: Slack team/workspace ID
        team_name: Slack team/workspace name
        token_data: Full token response from Slack

    Returns:
        bool: True if stored successfully, False otherwise
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            logger.error("❌ Supabase client not available for Slack integration storage")
            return False

        # First, ensure the Slack integration exists
        slack_integration_result = (
            supabase.table("integrations").select("*").eq("integration_id", "slack").execute()
        )

        if not slack_integration_result.data:
            # Create the Slack integration if it doesn't exist
            logger.info("📝 Creating Slack integration entry")
            integration_data = {
                "integration_id": "slack",
                "integration_type": "slack",
                "name": "Slack Integration",
                "description": "Slack workspace integration for messaging and automation",
                "version": "1.0",
                "configuration": {
                    "api_version": "v2",
                    "callback_url": "/api/v1/public/webhooks/slack/auth",
                    "scopes": token_data.get("scope", "").split(",")
                    if token_data.get("scope")
                    else [],
                },
                "supported_operations": [
                    "channels:read",
                    "channels:write",
                    "chat:write",
                    "users:read",
                    "team:read",
                ],
                "required_scopes": ["chat:write"],
                "active": True,
                "verified": True,
            }

            integration_result = supabase.table("integrations").insert(integration_data).execute()

            if not integration_result.data:
                logger.error("❌ Failed to create Slack integration")
                return False

        # Check if this user already has a Slack integration token for this team
        existing_token_result = (
            supabase.table("oauth_tokens")
            .select("*")
            .eq("user_id", user_id)
            .eq("integration_id", "slack")
            .execute()
        )

        # Prepare the token data
        oauth_token_data = {
            "user_id": user_id,
            "integration_id": "slack",
            "provider": "slack",
            "access_token": access_token,
            "token_type": "bearer",
            "credential_data": {
                "team_id": team_id,
                "team_name": team_name,
                "scope": token_data.get("scope", ""),
                "bot_user_id": token_data.get("bot_user_id"),
                "app_id": token_data.get("app_id"),
                "enterprise": token_data.get("enterprise"),
                "is_enterprise_install": token_data.get("is_enterprise_install", False),
                "callback_timestamp": "now()",
            },
            "is_active": True,
        }

        if existing_token_result.data:
            # Update existing record
            logger.info(f"🔄 Updating existing Slack integration for user {user_id}")

            update_result = (
                supabase.table("oauth_tokens")
                .update(oauth_token_data)
                .eq("user_id", user_id)
                .eq("integration_id", "slack")
                .execute()
            )

            if not update_result.data:
                logger.error("❌ Failed to update Slack integration record")
                return False

            logger.info(
                f"✅ Slack integration updated successfully - team: {team_name}, user_id: {user_id}"
            )
        else:
            # Insert new record
            logger.info(f"➕ Creating new Slack integration record for user {user_id}")

            insert_result = supabase.table("oauth_tokens").insert(oauth_token_data).execute()

            if not insert_result.data:
                logger.error("❌ Failed to store Slack integration record")
                return False

            logger.info(
                f"✅ Slack integration stored successfully - team: {team_name}, user_id: {user_id}"
            )

        return True

    except Exception as e:
        logger.error(f"❌ Error storing Slack integration data: {str(e)}", exc_info=True)
        return False
