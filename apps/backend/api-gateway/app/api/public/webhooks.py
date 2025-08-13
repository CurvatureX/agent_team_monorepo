"""
Webhook API endpoints for external integrations
Handles webhook requests from GitHub, workflow triggers, and other external systems
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional

import httpx
from app.core.config import get_settings
from app.core.database import get_supabase_admin
from fastapi import APIRouter, Body, Form, Header, HTTPException, Request, Response

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


@router.post("/webhook/workflow/{workflow_id}")
async def workflow_webhook(workflow_id: str, request: Request, response: Response):
    """
    Generic workflow webhook endpoint
    Routes webhook requests to workflow_scheduler service
    """
    try:
        logger.info(f"Webhook received for workflow {workflow_id}")

        # Extract request data
        headers = dict(request.headers)
        query_params = dict(request.query_params)
        body = await request.body()

        # Try to parse JSON body
        parsed_body = None
        try:
            if body:
                parsed_body = json.loads(body.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Keep as bytes if not JSON
            parsed_body = body.decode() if body else None

        # Prepare request data for workflow_scheduler
        webhook_data = {
            "headers": headers,
            "body": parsed_body,
            "query_params": query_params,
            "method": request.method,
            "path": str(request.url.path),
            "remote_addr": request.client.host if request.client else "",
        }

        # Forward to workflow_scheduler
        scheduler_url = f"{settings.workflow_scheduler_http_url}/api/v1/triggers/workflows/{workflow_id}/webhook"

        async with httpx.AsyncClient() as client:
            scheduler_response = await client.post(scheduler_url, json=webhook_data, timeout=30.0)

            if scheduler_response.status_code == 200:
                result = scheduler_response.json()
                logger.info(
                    f"Webhook processed successfully for workflow {workflow_id}: {result.get('execution_id', 'unknown')}"
                )

                # Return appropriate response
                response.status_code = 200
                return {
                    "message": "Webhook processed successfully",
                    "workflow_id": workflow_id,
                    "execution_id": result.get("execution_id"),
                    "status": result.get("status"),
                }
            else:
                logger.error(
                    f"Workflow scheduler returned error: {scheduler_response.status_code} - {scheduler_response.text}"
                )
                raise HTTPException(
                    status_code=scheduler_response.status_code,
                    detail=f"Workflow scheduler error: {scheduler_response.text}",
                )

    except httpx.TimeoutException:
        logger.error(f"Timeout forwarding webhook to workflow_scheduler for workflow {workflow_id}")
        raise HTTPException(status_code=504, detail="Webhook processing timeout")

    except httpx.RequestError as e:
        logger.error(f"Request error forwarding webhook for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=502, detail="Unable to process webhook")

    except Exception as e:
        logger.error(f"Error processing webhook for workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error processing webhook")


@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
):
    """
    GitHub webhook endpoint
    Handles GitHub App webhooks and routes them to workflow_scheduler
    """
    try:
        logger.info(f"GitHub webhook received: {x_github_event} (delivery: {x_github_delivery})")

        # Get raw payload for signature verification
        payload = await request.body()

        # Verify GitHub webhook signature if secret is configured
        if hasattr(settings, "GITHUB_WEBHOOK_SECRET") and settings.GITHUB_WEBHOOK_SECRET:
            if not x_hub_signature_256:
                raise HTTPException(status_code=401, detail="Missing signature")

            if not _verify_github_signature(
                payload, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET
            ):
                raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse JSON payload
        try:
            event_data = json.loads(payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse GitHub webhook payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        # Extract repository and installation info for logging
        installation_id = event_data.get("installation", {}).get("id")
        repository = event_data.get("repository", {})
        repo_name = repository.get("full_name", "unknown")

        logger.info(
            f"GitHub webhook processing: event={x_github_event}, repo={repo_name}, installation={installation_id}"
        )

        # Forward to workflow_scheduler GitHub webhook handler
        scheduler_url = f"{settings.workflow_scheduler_http_url}/api/v1/triggers/github/events"

        github_webhook_data = {
            "event_type": x_github_event,
            "delivery_id": x_github_delivery,
            "payload": event_data,
            "installation_id": installation_id,
            "repository_name": repo_name,
            "timestamp": event_data.get("timestamp")
            or payload.decode("utf-8", errors="ignore")[:100],  # Fallback timestamp
        }

        async with httpx.AsyncClient() as client:
            scheduler_response = await client.post(
                scheduler_url, json=github_webhook_data, timeout=30.0
            )

            if scheduler_response.status_code == 200:
                result = scheduler_response.json()
                logger.info(
                    f"GitHub webhook processed successfully: event={x_github_event}, repo={repo_name}, workflows={result.get('processed_workflows', 0)}"
                )

                return {
                    "status": "received",
                    "message": "GitHub webhook processed successfully",
                    "event_type": x_github_event,
                    "delivery_id": x_github_delivery,
                    "repository": repo_name,
                    "installation_id": installation_id,
                    "processed_workflows": result.get("processed_workflows", 0),
                    "results": result.get("results", []),
                }
            else:
                logger.error(
                    f"Workflow scheduler GitHub webhook error: {scheduler_response.status_code} - {scheduler_response.text}"
                )
                raise HTTPException(
                    status_code=scheduler_response.status_code,
                    detail=f"GitHub webhook processing error: {scheduler_response.text}",
                )

    except HTTPException:
        raise

    except httpx.TimeoutException:
        logger.error(f"Timeout processing GitHub webhook: {x_github_event}")
        raise HTTPException(status_code=504, detail="GitHub webhook processing timeout")

    except httpx.RequestError as e:
        logger.error(f"Request error processing GitHub webhook: {e}")
        raise HTTPException(status_code=502, detail="Unable to process GitHub webhook")

    except Exception as e:
        logger.error(f"Error processing GitHub webhook {x_github_event}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error processing GitHub webhook"
        )


@router.post("/webhooks/slack/events")
async def slack_events_webhook(
    request: Request,
    x_slack_signature: str = Header(..., alias="X-Slack-Signature"),
    x_slack_request_timestamp: str = Header(..., alias="X-Slack-Request-Timestamp"),
):
    """
    Slack Events API webhook endpoint
    Handles Slack workspace events and routes them to workflow_scheduler
    """
    try:
        logger.info("Slack events webhook received")
        body = await request.body()

        # Verify Slack request signature
        if not _verify_slack_signature(x_slack_request_timestamp, x_slack_signature, body):
            raise HTTPException(status_code=401, detail="Invalid Slack signature")

        # Parse event data
        try:
            event_data = json.loads(body.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse Slack event payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        # Handle URL verification challenge
        if event_data.get("type") == "url_verification":
            logger.info("Slack URL verification challenge received")
            return {"challenge": event_data.get("challenge")}

        # Extract team_id
        team_id = event_data.get("team_id")
        if not team_id:
            raise HTTPException(status_code=400, detail="Missing team_id in Slack event")

        # Forward to workflow_scheduler
        scheduler_url = f"{settings.workflow_scheduler_http_url}/api/v1/triggers/slack/events"

        slack_event_data = {"team_id": team_id, "event_data": event_data}

        async with httpx.AsyncClient() as client:
            scheduler_response = await client.post(
                scheduler_url, json=slack_event_data, timeout=30.0
            )

            if scheduler_response.status_code == 200:
                result = scheduler_response.json()
                logger.info(
                    f"Slack event processed successfully: {result.get('processed_triggers', 0)} triggers"
                )

                return {
                    "ok": True,
                    "processed_triggers": result.get("processed_triggers", 0),
                    "results": result.get("results", []),
                }
            else:
                logger.error(
                    f"Workflow scheduler Slack event error: {scheduler_response.status_code} - {scheduler_response.text}"
                )
                raise HTTPException(
                    status_code=scheduler_response.status_code,
                    detail=f"Slack event processing error: {scheduler_response.text}",
                )

    except HTTPException:
        raise

    except httpx.TimeoutException:
        logger.error("Timeout processing Slack event")
        raise HTTPException(status_code=504, detail="Slack event processing timeout")

    except httpx.RequestError as e:
        logger.error(f"Request error processing Slack event: {e}")
        raise HTTPException(status_code=502, detail="Unable to process Slack event")

    except Exception as e:
        logger.error(f"Error processing Slack event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error processing Slack event")


@router.post("/webhooks/slack/interactive")
async def slack_interactive_webhook(
    request: Request,
    x_slack_signature: str = Header(..., alias="X-Slack-Signature"),
    x_slack_request_timestamp: str = Header(..., alias="X-Slack-Request-Timestamp"),
):
    """
    Slack Interactive Components webhook endpoint
    Handles button clicks, modal submissions, select menus, and other interactive elements
    """
    try:
        logger.info("Slack interactive webhook received")
        body = await request.body()

        # Verify Slack request signature
        if not _verify_slack_signature(x_slack_request_timestamp, x_slack_signature, body):
            raise HTTPException(status_code=401, detail="Invalid Slack signature")

        # Parse form data (interactive components send form-encoded data)
        form_data = await request.form()
        payload_str = form_data.get("payload")

        if not payload_str:
            raise HTTPException(status_code=400, detail="Missing payload in interactive request")

        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Slack interactive payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON in payload")

        # Extract team_id
        team_id = payload.get("team", {}).get("id")
        if not team_id:
            raise HTTPException(
                status_code=400, detail="Missing team_id in Slack interactive payload"
            )

        # Forward to workflow_scheduler
        scheduler_url = f"{settings.workflow_scheduler_http_url}/api/v1/triggers/slack/interactive"

        slack_interactive_data = {"team_id": team_id, "payload": payload}

        async with httpx.AsyncClient() as client:
            scheduler_response = await client.post(
                scheduler_url, json=slack_interactive_data, timeout=30.0
            )

            if scheduler_response.status_code == 200:
                result = scheduler_response.json()
                logger.info("Slack interactive component processed successfully")

                # Return response expected by Slack
                return result.get("slack_response", {"ok": True})
            else:
                logger.error(
                    f"Workflow scheduler Slack interactive error: {scheduler_response.status_code} - {scheduler_response.text}"
                )
                raise HTTPException(
                    status_code=scheduler_response.status_code,
                    detail=f"Slack interactive processing error: {scheduler_response.text}",
                )

    except HTTPException:
        raise

    except httpx.TimeoutException:
        logger.error("Timeout processing Slack interactive component")
        raise HTTPException(status_code=504, detail="Slack interactive processing timeout")

    except httpx.RequestError as e:
        logger.error(f"Request error processing Slack interactive component: {e}")
        raise HTTPException(status_code=502, detail="Unable to process Slack interactive component")

    except Exception as e:
        logger.error(f"Error processing Slack interactive component: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error processing Slack interactive component"
        )


@router.post("/webhooks/slack/commands")
async def slack_slash_commands_webhook(
    request: Request,
    x_slack_signature: str = Header(..., alias="X-Slack-Signature"),
    x_slack_request_timestamp: str = Header(..., alias="X-Slack-Request-Timestamp"),
):
    """
    Slack Slash Commands webhook endpoint
    Handles slash commands like /workflow, /ai-help, etc.
    """
    try:
        logger.info("Slack slash command webhook received")
        body = await request.body()

        # Verify Slack request signature
        if not _verify_slack_signature(x_slack_request_timestamp, x_slack_signature, body):
            raise HTTPException(status_code=401, detail="Invalid Slack signature")

        # Parse form data
        form_data = await request.form()

        command_data = {
            "token": form_data.get("token"),
            "team_id": form_data.get("team_id"),
            "team_domain": form_data.get("team_domain"),
            "channel_id": form_data.get("channel_id"),
            "channel_name": form_data.get("channel_name"),
            "user_id": form_data.get("user_id"),
            "user_name": form_data.get("user_name"),
            "command": form_data.get("command"),
            "text": form_data.get("text", ""),
            "response_url": form_data.get("response_url"),
            "trigger_id": form_data.get("trigger_id"),
        }

        team_id = command_data.get("team_id")
        if not team_id:
            raise HTTPException(status_code=400, detail="Missing team_id in Slack command")

        logger.info(
            f"Processing Slack command: {command_data.get('command')} from user {command_data.get('user_name')}"
        )

        # Forward to workflow_scheduler
        scheduler_url = f"{settings.workflow_scheduler_http_url}/api/v1/triggers/slack/commands"

        async with httpx.AsyncClient() as client:
            scheduler_response = await client.post(scheduler_url, json=command_data, timeout=30.0)

            if scheduler_response.status_code == 200:
                result = scheduler_response.json()
                logger.info("Slack slash command processed successfully")

                # Return response expected by Slack
                return result.get(
                    "slack_response",
                    {"response_type": "ephemeral", "text": "Command processed successfully"},
                )
            else:
                logger.error(
                    f"Workflow scheduler Slack command error: {scheduler_response.status_code} - {scheduler_response.text}"
                )
                return {
                    "response_type": "ephemeral",
                    "text": f"Error processing command: {scheduler_response.text}",
                }

    except HTTPException:
        raise

    except httpx.TimeoutException:
        logger.error("Timeout processing Slack slash command")
        return {
            "response_type": "ephemeral",
            "text": "Timeout processing command. Please try again.",
        }

    except httpx.RequestError as e:
        logger.error(f"Request error processing Slack slash command: {e}")
        return {
            "response_type": "ephemeral",
            "text": "Unable to process command. Please try again later.",
        }

    except Exception as e:
        logger.error(f"Error processing Slack slash command: {e}", exc_info=True)
        return {
            "response_type": "ephemeral",
            "text": "Internal error processing command. Please contact support.",
        }


@router.get("/webhooks/slack/auth")
async def slack_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """
    Slack OAuth callback endpoint
    Handles Slack app installation OAuth flow
    """
    try:
        logger.info(f"Slack OAuth callback received: code={'present' if code else 'missing'}")

        # Check for OAuth errors
        if error:
            logger.error(f"Slack OAuth error: {error} - {error_description}")
            raise HTTPException(
                status_code=400,
                detail=f"Slack OAuth error: {error} - {error_description or 'Unknown error'}",
            )

        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")

        # Forward to workflow_scheduler to handle the OAuth exchange
        scheduler_url = f"{settings.workflow_scheduler_http_url}/api/v1/auth/slack/callback"

        oauth_data = {"code": code, "state": state}

        async with httpx.AsyncClient() as client:
            scheduler_response = await client.post(scheduler_url, json=oauth_data, timeout=30.0)

            if scheduler_response.status_code == 200:
                result = scheduler_response.json()
                logger.info(
                    f"Slack OAuth callback processed successfully for team: {result.get('team_name')}"
                )

                # Return success page or redirect
                return {
                    "success": True,
                    "message": "Slack app installed successfully!",
                    "team_name": result.get("team_name"),
                    "team_id": result.get("team_id"),
                    "installation_id": result.get("installation_id"),
                }
            else:
                logger.error(
                    f"Workflow scheduler OAuth error: {scheduler_response.status_code} - {scheduler_response.text}"
                )
                raise HTTPException(
                    status_code=scheduler_response.status_code,
                    detail=f"OAuth processing error: {scheduler_response.text}",
                )

    except HTTPException:
        raise

    except httpx.TimeoutException:
        logger.error("Timeout processing Slack OAuth callback")
        raise HTTPException(status_code=504, detail="OAuth processing timeout")

    except httpx.RequestError as e:
        logger.error(f"Request error processing Slack OAuth callback: {e}")
        raise HTTPException(status_code=502, detail="Unable to process OAuth callback")

    except Exception as e:
        logger.error(f"Error processing Slack OAuth callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error processing OAuth callback"
        )


async def _store_github_installation(user_id: str, installation_id: str, setup_action: str) -> bool:
    """
    Store GitHub installation data in oauth_tokens table

    Args:
        user_id: User ID who authorized the installation
        installation_id: GitHub installation ID
        setup_action: Setup action (install/update)

    Returns:
        bool: True if stored successfully, False otherwise
    """
    try:
        supabase_admin = get_supabase_admin()

        if not supabase_admin:
            logger.error("❌ Database connection unavailable for GitHub installation storage")
            return False

        # First, ensure the GitHub integration exists
        github_integration_result = (
            supabase_admin.table("integrations")
            .select("*")
            .eq("integration_id", "github_app")
            .execute()
        )

        if not github_integration_result.data:
            # Create the GitHub integration if it doesn't exist
            logger.info("📝 Creating GitHub integration entry")
            integration_data = {
                "integration_id": "github_app",
                "integration_type": "github",
                "name": "GitHub App Integration",
                "description": "GitHub App for repository access and automation",
                "version": "1.0",
                "configuration": {
                    "app_name": "starmates",
                    "callback_url": "/api/v1/public/webhooks/github/auth",
                },
                "supported_operations": [
                    "repositories:read",
                    "repositories:write",
                    "issues:read",
                    "actions:read",
                ],
                "required_scopes": ["repo", "issues", "actions"],
                "active": True,
                "verified": True,
            }

            integration_result = (
                supabase_admin.table("integrations").insert(integration_data).execute()
            )

            if not integration_result.data:
                logger.error("❌ Failed to create GitHub integration")
                return False

        # Check if this user already has a GitHub installation token
        existing_token_result = (
            supabase_admin.table("oauth_tokens")
            .select("*")
            .eq("user_id", user_id)
            .eq("integration_id", "github_app")
            .execute()
        )

        # Prepare the token data
        token_data = {
            "user_id": user_id,
            "integration_id": "github_app",
            "provider": "github",
            "access_token": f"github_installation_{installation_id}",  # Placeholder - replace with actual token when fetched
            "token_type": "installation",
            "credential_data": {
                "installation_id": installation_id,
                "setup_action": setup_action,
                "callback_timestamp": "now()",
            },
            "is_active": True,
        }

        if existing_token_result.data:
            # Update existing record
            logger.info(f"🔄 Updating existing GitHub installation for user {user_id}")

            update_result = (
                supabase_admin.table("oauth_tokens")
                .update(token_data)
                .eq("user_id", user_id)
                .eq("integration_id", "github_app")
                .execute()
            )

            if not update_result.data:
                logger.error("❌ Failed to update GitHub installation record")
                return False

            logger.info(
                f"✅ GitHub installation updated successfully - installation_id: {installation_id}, user_id: {user_id}"
            )
        else:
            # Insert new record
            logger.info(f"➕ Creating new GitHub installation record for user {user_id}")

            insert_result = supabase_admin.table("oauth_tokens").insert(token_data).execute()

            if not insert_result.data:
                logger.error("❌ Failed to store GitHub installation record")
                return False

            logger.info(
                f"✅ GitHub installation stored successfully - installation_id: {installation_id}, user_id: {user_id}"
            )

        return True

    except Exception as e:
        logger.error(f"❌ Error storing GitHub installation data: {str(e)}", exc_info=True)
        return False


@router.get("/webhooks/github/auth")
async def github_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    installation_id: Optional[str] = None,
    setup_action: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """
    GitHub OAuth callback endpoint
    Handles GitHub App installation OAuth flow
    """
    try:
        logger.info(
            f"GitHub OAuth callback received: code={'present' if code else 'missing'}, installation_id={installation_id}"
        )

        # Check for OAuth errors
        if error:
            logger.error(f"GitHub OAuth error: {error} - {error_description}")
            raise HTTPException(
                status_code=400,
                detail=f"GitHub OAuth error: {error} - {error_description or 'Unknown error'}",
            )

        # Handle app installation flow
        if setup_action == "install" or setup_action == "update":
            if not installation_id:
                raise HTTPException(
                    status_code=400, detail="Missing installation_id for app installation"
                )

            logger.info(f"GitHub App installation completed: installation_id={installation_id}")

            # Store installation data in database if user_id is provided in state
            db_store_success = False
            if state:
                # First validate that the user exists
                try:
                    supabase_admin = get_supabase_admin()
                    if supabase_admin:
                        # Check if user exists in auth.users table
                        user_check = (
                            supabase_admin.table("auth.users")
                            .select("id")
                            .eq("id", state)
                            .execute()
                        )

                        if user_check.data:
                            # User exists in auth.users, proceed with installation storage
                            db_store_success = await _store_github_installation(
                                state, installation_id, setup_action
                            )
                            if not db_store_success:
                                logger.warning(
                                    f"⚠️ Failed to store GitHub installation data in database for user {state}"
                                )
                        else:
                            logger.warning(
                                f"⚠️ User {state} not found in auth.users, skipping installation storage"
                            )
                    else:
                        logger.warning(
                            "⚠️ Database connection unavailable, skipping installation storage"
                        )
                except Exception as e:
                    logger.error(f"❌ Error validating user {state}: {e}")
                    db_store_success = False

            # Forward to workflow_scheduler to handle the installation (if service is available)
            scheduler_url = f"{settings.workflow_scheduler_http_url}/api/v1/auth/github/callback"
            scheduler_success = False

            installation_data = {
                "installation_id": int(installation_id),
                "setup_action": setup_action,
                "state": state,
                "code": code,
            }

            try:
                async with httpx.AsyncClient() as client:
                    scheduler_response = await client.post(
                        scheduler_url, json=installation_data, timeout=30.0
                    )

                    if scheduler_response.status_code == 200:
                        result = scheduler_response.json()
                        logger.info(
                            f"GitHub App installation processed successfully for account: {result.get('account_login')}"
                        )
                        scheduler_success = True

                        # Return success page or redirect
                        return {
                            "success": True,
                            "message": "GitHub App installed successfully!",
                            "installation_id": result.get("installation_id"),
                            "account_login": result.get("account_login"),
                            "account_type": result.get("account_type"),
                            "repositories": result.get("repositories", []),
                            "user_id": state if state else None,
                            "stored_in_database": db_store_success if state else False,
                        }
                    else:
                        logger.warning(
                            f"Workflow scheduler GitHub installation error: {scheduler_response.status_code} - {scheduler_response.text}"
                        )
                        scheduler_success = False

            except Exception as e:
                logger.warning(f"Failed to forward to workflow_scheduler: {e}")
                scheduler_success = False

            # If scheduler failed but we have the installation data, still return success
            # The installation was successful, just the workflow_scheduler integration failed
            logger.info(
                f"GitHub App installation completed (scheduler_success: {scheduler_success}, db_stored: {db_store_success})"
            )

            return {
                "success": True,
                "message": "GitHub App installed successfully!",
                "installation_id": installation_id,
                "user_id": state if state else None,
                "stored_in_database": db_store_success if state else False,
                "scheduler_processed": scheduler_success,
                "note": "Installation successful. Some backend services may still be initializing."
                if not scheduler_success
                else None,
            }

        # Handle OAuth authorization code flow (if needed)
        elif code:
            if not code:
                raise HTTPException(status_code=400, detail="Missing authorization code")

            # Forward OAuth code to workflow_scheduler
            scheduler_url = f"{settings.workflow_scheduler_http_url}/api/v1/auth/github/callback"

            oauth_data = {
                "code": code,
                "state": state,
                "installation_id": int(installation_id) if installation_id else None,
            }

            async with httpx.AsyncClient() as client:
                scheduler_response = await client.post(scheduler_url, json=oauth_data, timeout=30.0)

                if scheduler_response.status_code == 200:
                    result = scheduler_response.json()
                    logger.info(f"GitHub OAuth callback processed successfully")

                    return {
                        "success": True,
                        "message": "GitHub authorization completed successfully!",
                        "installation_id": result.get("installation_id"),
                        "user_info": result.get("user_info"),
                    }
                else:
                    logger.error(
                        f"Workflow scheduler GitHub OAuth error: {scheduler_response.status_code} - {scheduler_response.text}"
                    )
                    raise HTTPException(
                        status_code=scheduler_response.status_code,
                        detail=f"GitHub OAuth processing error: {scheduler_response.text}",
                    )

        else:
            raise HTTPException(
                status_code=400, detail="Missing required parameters for GitHub callback"
            )

    except HTTPException:
        raise

    except httpx.TimeoutException:
        logger.error("Timeout processing GitHub OAuth callback")
        raise HTTPException(status_code=504, detail="GitHub OAuth processing timeout")

    except httpx.RequestError as e:
        logger.error(f"Request error processing GitHub OAuth callback: {e}")
        raise HTTPException(status_code=502, detail="Unable to process GitHub OAuth callback")

    except Exception as e:
        logger.error(f"Error processing GitHub OAuth callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error processing GitHub OAuth callback"
        )


def _verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify GitHub webhook signature

    Args:
        payload: Raw webhook payload bytes
        signature: GitHub signature header (sha256=...)
        secret: Webhook secret

    Returns:
        bool: True if signature is valid
    """
    try:
        if not signature.startswith("sha256="):
            return False

        expected_signature = (
            "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        )

        return hmac.compare_digest(signature, expected_signature)

    except Exception as e:
        logger.error(f"Error verifying GitHub signature: {e}")
        return False


def _verify_slack_signature(timestamp: str, signature: str, body: bytes) -> bool:
    """
    Verify Slack webhook signature

    Args:
        timestamp: Slack request timestamp
        signature: Slack signature header (v0=...)
        body: Raw webhook payload bytes

    Returns:
        bool: True if signature is valid
    """
    try:
        # Check timestamp to prevent replay attacks (5 minutes tolerance)
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 60 * 5:
            logger.warning(f"Slack request timestamp too old: {timestamp}")
            return False

        # Get Slack signing secret from settings
        # This would need to be added to settings configuration
        signing_secret = getattr(settings, "slack_signing_secret", None)
        if not signing_secret:
            logger.error("Slack signing secret not configured")
            return False

        # Create signature basestring
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"

        # Compute expected signature
        expected_signature = (
            "v0="
            + hmac.new(
                signing_secret.encode("utf-8"), sig_basestring.encode("utf-8"), hashlib.sha256
            ).hexdigest()
        )

        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)

    except Exception as e:
        logger.error(f"Error verifying Slack signature: {e}")
        return False


@router.get("/webhooks/status")
async def webhook_status():
    """
    Get webhook system status
    Used for monitoring webhook processing health
    """
    try:
        # Check workflow_scheduler health for webhook processing
        scheduler_url = f"{settings.workflow_scheduler_http_url}/health"

        async with httpx.AsyncClient() as client:
            response = await client.get(scheduler_url, timeout=10.0)

            if response.status_code == 200:
                scheduler_health = response.json()
                return {
                    "webhook_system": "healthy",
                    "scheduler_status": scheduler_health.get("status", "unknown"),
                    "available_endpoints": [
                        "/api/v1/public/webhook/workflow/{workflow_id}",
                        "/api/v1/public/webhooks/github",
                        "/api/v1/public/webhooks/github/auth",
                        "/api/v1/public/webhooks/slack/events",
                        "/api/v1/public/webhooks/slack/interactive",
                        "/api/v1/public/webhooks/slack/commands",
                        "/api/v1/public/webhooks/slack/auth",
                        "/api/v1/public/webhooks/status",
                    ],
                }
            else:
                return {
                    "webhook_system": "degraded",
                    "scheduler_status": "unhealthy",
                    "error": f"Scheduler health check failed: {response.status_code}",
                }

    except Exception as e:
        logger.error(f"Error checking webhook status: {e}", exc_info=True)
        return {"webhook_system": "error", "scheduler_status": "unknown", "error": str(e)}
