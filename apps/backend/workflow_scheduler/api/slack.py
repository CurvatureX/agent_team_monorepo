"""
Slack API endpoints for workflow_scheduler

This module handles incoming Slack events and routes them to appropriate triggers.
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Dict

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from workflow_scheduler.core.config import settings
from workflow_scheduler.services.slack_event_router import SlackEventRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/slack", tags=["slack"])


def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """
    Verify Slack webhook signature

    Args:
        body: Raw request body
        timestamp: X-Slack-Request-Timestamp header
        signature: X-Slack-Signature header

    Returns:
        bool: True if signature is valid
    """
    if not settings.SLACK_SIGNING_SECRET:
        logger.warning("SLACK_SIGNING_SECRET not configured, skipping signature verification")
        return True

    try:
        # Check timestamp freshness (prevent replay attacks)
        current_time = int(time.time())
        request_time = int(timestamp)

        if abs(current_time - request_time) > 60 * 5:  # 5 minutes
            logger.warning("Slack request timestamp too old")
            return False

        # Create signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        my_signature = (
            "v0="
            + hmac.new(
                settings.SLACK_SIGNING_SECRET.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        # Compare signatures
        return hmac.compare_digest(my_signature, signature)

    except Exception as e:
        logger.error(f"Error verifying Slack signature: {e}")
        return False


@router.post("/events")
async def handle_slack_events(
    request: Request,
    x_slack_signature: str = Header(..., alias="X-Slack-Signature"),
    x_slack_request_timestamp: str = Header(..., alias="X-Slack-Request-Timestamp"),
):
    """
    Handle Slack Events API webhooks

    This endpoint receives all Slack events and routes them to appropriate triggers.
    """
    try:
        # Get raw body for signature verification
        body = await request.body()

        # Verify Slack signature
        if not verify_slack_signature(body, x_slack_request_timestamp, x_slack_signature):
            logger.warning("Invalid Slack signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse JSON payload
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in Slack payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON")

        # Handle URL verification challenge
        if payload.get("type") == "url_verification":
            challenge = payload.get("challenge")
            logger.info("Responding to Slack URL verification challenge")
            return {"challenge": challenge}

        # Handle event callback
        if payload.get("type") == "event_callback":
            event_data = payload.get("event", {})
            team_id = payload.get("team_id")

            # Add team_id to event data for workspace filtering
            event_data["team_id"] = team_id

            logger.info(
                f"📨 Received Slack event: {event_data.get('type', 'unknown')} from team {team_id}"
            )

            # Route event to matching triggers
            slack_router = await SlackEventRouter.get_instance()
            results = await slack_router.route_event(event_data)

            # Log results
            successful_triggers = len(
                [r for r in results if r.status not in ["error", "trigger_error", "router_error"]]
            )
            logger.info(
                f"✅ Processed Slack event: {successful_triggers}/{len(results)} workflows triggered successfully"
            )

            # Return success response
            return {
                "status": "processed",
                "triggered_workflows": successful_triggers,
                "total_results": len(results),
                "event_type": event_data.get("type"),
                "team_id": team_id,
            }

        # Handle other event types
        logger.info(f"Received unknown Slack event type: {payload.get('type')}")
        return {"status": "ignored", "reason": "Unknown event type"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error handling Slack event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/commands")
async def handle_slack_commands(
    request: Request,
    x_slack_signature: str = Header(..., alias="X-Slack-Signature"),
    x_slack_request_timestamp: str = Header(..., alias="X-Slack-Request-Timestamp"),
):
    """
    Handle Slack slash commands

    This endpoint handles slash commands like /workflow.
    """
    try:
        # Get raw body for signature verification
        body = await request.body()

        # Verify Slack signature
        if not verify_slack_signature(body, x_slack_request_timestamp, x_slack_signature):
            logger.warning("Invalid Slack signature for slash command")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse form data (slash commands send form-encoded data)
        form_data = await request.form()

        command = form_data.get("command", "")
        text = form_data.get("text", "")
        user_id = form_data.get("user_id", "")
        channel_id = form_data.get("channel_id", "")
        team_id = form_data.get("team_id", "")

        logger.info(
            f"📱 Received Slack command: {command} from user {user_id} in channel {channel_id}"
        )

        # Create event data for slash command
        event_data = {
            "type": "slash_command",
            "command": command,
            "text": text,
            "user": user_id,
            "channel": channel_id,
            "team_id": team_id,
        }

        # Route command to matching triggers
        slack_router = await SlackEventRouter.get_instance()
        results = await slack_router.route_event(event_data)

        # Count successful triggers
        successful_triggers = len(
            [r for r in results if r.status not in ["error", "trigger_error", "router_error"]]
        )

        if successful_triggers > 0:
            response_text = f"✅ Triggered {successful_triggers} workflow(s)"
        else:
            response_text = "ℹ️ No workflows matched your command"

        logger.info(
            f"✅ Processed slash command: {successful_triggers}/{len(results)} workflows triggered"
        )

        # Return response to Slack
        return {
            "response_type": "ephemeral",
            "text": response_text,
        }  # Only visible to the user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error handling Slack command: {e}", exc_info=True)
        return {
            "response_type": "ephemeral",
            "text": "❌ Sorry, there was an error processing your command",
        }


@router.get("/health")
async def slack_health_check():
    """
    Health check endpoint for Slack integration
    """
    try:
        slack_router = await SlackEventRouter.get_instance()
        health_status = await slack_router.health_check()

        return {
            "service": "slack_integration",
            "status": "healthy",
            "router_health": health_status,
            "timestamp": int(time.time()),
        }

    except Exception as e:
        logger.error(f"Slack health check failed: {e}")
        raise HTTPException(status_code=503, detail="Slack service unhealthy")


@router.get("/stats")
async def slack_stats():
    """
    Get Slack event router statistics
    """
    try:
        slack_router = await SlackEventRouter.get_instance()
        stats = await slack_router.get_router_stats()

        return {
            "service": "slack_integration",
            "statistics": stats,
            "timestamp": int(time.time()),
        }

    except Exception as e:
        logger.error(f"Failed to get Slack stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")
