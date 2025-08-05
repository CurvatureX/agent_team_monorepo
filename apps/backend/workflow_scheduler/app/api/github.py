import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..dependencies import get_trigger_manager
from ..models.triggers import ExecutionResult
from ..services.trigger_manager import TriggerManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


class GitHubWebhookRequest(BaseModel):
    event_type: str
    delivery_id: str
    payload: Dict[str, Any]
    signature: Optional[str] = None


@router.post("/webhook", response_model=Dict[str, Any])
async def github_webhook(
    webhook_data: GitHubWebhookRequest,
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
):
    """Process GitHub webhook events"""
    try:
        logger.info(
            f"GitHub webhook received: {webhook_data.event_type} (delivery: {webhook_data.delivery_id})"
        )

        result = await trigger_manager.process_github_webhook(
            event_type=webhook_data.event_type,
            delivery_id=webhook_data.delivery_id,
            payload=webhook_data.payload,
            signature=webhook_data.signature,
        )

        return {
            "message": "GitHub webhook processed",
            "event_type": webhook_data.event_type,
            "delivery_id": webhook_data.delivery_id,
            "processed_workflows": result.get("processed_workflows", 0),
            "results": result.get("results", []),
        }

    except Exception as e:
        logger.error(
            f"Error processing GitHub webhook {webhook_data.event_type}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"GitHub webhook processing failed: {str(e)}")


@router.get("/status")
async def github_status(trigger_manager: TriggerManager = Depends(get_trigger_manager)):
    """Get GitHub webhook system status"""
    try:
        # Get health status for GitHub triggers
        health_status = await trigger_manager.health_check()

        github_workflows = {}
        total_github_triggers = 0

        # Count GitHub triggers across all workflows
        for workflow_id, workflow_data in health_status.get("workflows", {}).items():
            github_triggers = workflow_data.get("triggers", {}).get("TRIGGER_GITHUB", [])
            if github_triggers:
                github_workflows[workflow_id] = len(github_triggers)
                total_github_triggers += len(github_triggers)

        return {
            "github_system": "healthy",
            "total_github_triggers": total_github_triggers,
            "github_workflows": github_workflows,
            "supported_events": [
                "push",
                "pull_request",
                "issues",
                "release",
                "pull_request_review",
                "workflow_run",
                "deployment",
            ],
        }

    except Exception as e:
        logger.error(f"Error getting GitHub status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"GitHub status check failed: {str(e)}")
