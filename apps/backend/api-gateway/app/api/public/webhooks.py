"""
Webhook API endpoints for external integrations
Handles webhook requests from GitHub, workflow triggers, and other external systems
"""

import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional

import httpx
from app.core.config import get_settings
from fastapi import APIRouter, Body, Header, HTTPException, Request, Response

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


@router.post("/webhook/{workflow_id}")
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

        # Forward to workflow_scheduler GitHub webhook handler
        scheduler_url = f"{settings.workflow_scheduler_http_url}/api/v1/github/webhook"

        github_webhook_data = {
            "event_type": x_github_event,
            "delivery_id": x_github_delivery,
            "payload": event_data,
            "signature": x_hub_signature_256,
        }

        async with httpx.AsyncClient() as client:
            scheduler_response = await client.post(
                scheduler_url, json=github_webhook_data, timeout=30.0
            )

            if scheduler_response.status_code == 200:
                result = scheduler_response.json()
                logger.info(f"GitHub webhook processed successfully: {x_github_event}")

                return {
                    "message": "GitHub webhook processed",
                    "event_type": x_github_event,
                    "delivery_id": x_github_delivery,
                    "processed_workflows": result.get("processed_workflows", 0),
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
                        "/api/v1/public/webhook/{workflow_id}",
                        "/api/v1/public/webhooks/github",
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
