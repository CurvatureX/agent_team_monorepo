import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from workflow_scheduler.dependencies import get_trigger_manager
from workflow_scheduler.models.triggers import ExecutionResult
from workflow_scheduler.services.trigger_manager import TriggerManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


class GitHubWebhookRequest(BaseModel):
    event_type: str
    delivery_id: str
    payload: Dict[str, Any]
    signature: Optional[str] = None


class GitHubTriggerRequest(BaseModel):
    """Request model for GitHub triggers from API Gateway"""

    trigger_type: str
    event_type: str
    delivery_id: str
    github_payload: Dict[str, Any]
    timestamp: str


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


@router.post("/trigger", response_model=Dict[str, Any])
async def handle_github_trigger(
    trigger_request: GitHubTriggerRequest,
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
):
    """
    Process GitHub webhook event forwarded from API Gateway
    This is the main endpoint that implements the architecture flow:
    GitHub App -> API Gateway -> Workflow Scheduler -> Workflow Engine
    """
    try:
        logger.info(
            f"GitHub trigger received from API Gateway: {trigger_request.event_type} "
            f"(delivery: {trigger_request.delivery_id})"
        )

        # Extract repository and installation info for filtering
        payload = trigger_request.github_payload
        installation_id = payload.get("installation", {}).get("id")
        repository = payload.get("repository", {})
        repository_name = repository.get("full_name", "") if repository else ""

        if not installation_id or not repository_name:
            logger.warning(
                f"Missing installation_id or repository info in GitHub webhook: "
                f"installation_id={installation_id}, repo={repository_name}"
            )
            return {
                "message": "Invalid GitHub webhook data",
                "event_type": trigger_request.event_type,
                "delivery_id": trigger_request.delivery_id,
                "processed_workflows": 0,
                "results": [],
            }

        # Find workflows with matching GitHub triggers
        matching_workflows = await _find_workflows_with_github_triggers(
            trigger_manager,
            installation_id=installation_id,
            repository_name=repository_name,
            event_type=trigger_request.event_type,
            payload=payload,
        )

        if not matching_workflows:
            logger.info(
                f"No workflows found matching GitHub event {trigger_request.event_type} "
                f"for repository {repository_name}"
            )
            return {
                "message": "No matching workflows found",
                "event_type": trigger_request.event_type,
                "delivery_id": trigger_request.delivery_id,
                "processed_workflows": 0,
                "results": [],
            }

        # Process each matching workflow
        results = []
        processed_workflows = 0

        for workflow_id, trigger in matching_workflows:
            try:
                # Process the GitHub event through the trigger
                result = await trigger.process_github_event(
                    trigger_request.event_type, trigger_request.github_payload
                )

                if result:
                    results.append(
                        {
                            "workflow_id": workflow_id,
                            "execution_id": result.execution_id,
                            "status": result.status,
                            "message": result.message,
                        }
                    )
                    processed_workflows += 1

                    logger.info(
                        f"GitHub trigger processed workflow {workflow_id}: "
                        f"execution_id={result.execution_id}, status={result.status}"
                    )
                else:
                    logger.debug(f"GitHub trigger filtered out for workflow {workflow_id}")

            except Exception as e:
                logger.error(
                    f"Error processing GitHub trigger for workflow {workflow_id}: {e}",
                    exc_info=True,
                )
                results.append(
                    {
                        "workflow_id": workflow_id,
                        "execution_id": None,
                        "status": "error",
                        "message": f"Processing failed: {str(e)}",
                    }
                )

        return {
            "message": "GitHub trigger processed",
            "event_type": trigger_request.event_type,
            "delivery_id": trigger_request.delivery_id,
            "repository": repository_name,
            "installation_id": installation_id,
            "processed_workflows": processed_workflows,
            "results": results,
        }

    except Exception as e:
        logger.error(
            f"Error handling GitHub trigger {trigger_request.event_type}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"GitHub trigger processing failed: {str(e)}")


async def _find_workflows_with_github_triggers(
    trigger_manager: TriggerManager,
    installation_id: int,
    repository_name: str,
    event_type: str,
    payload: Dict[str, Any],
) -> list:
    """
    Find workflows that have GitHub triggers matching this event
    """
    matching_workflows = []

    # Get all workflows with triggers
    for workflow_id, triggers in trigger_manager._triggers.items():
        # Find GitHub triggers for this workflow
        github_triggers = [t for t in triggers if t.trigger_type == "TRIGGER_GITHUB" and t.enabled]

        for trigger in github_triggers:
            # Check if this trigger matches the event
            if (
                hasattr(trigger, "installation_id")
                and hasattr(trigger, "repository")
                and hasattr(trigger, "events")
            ):
                # Match installation ID
                if trigger.installation_id != installation_id:
                    continue

                # Match repository
                if trigger.repository != repository_name:
                    continue

                # Match event type
                if trigger.events and event_type not in trigger.events:
                    continue

                # This trigger matches
                matching_workflows.append((workflow_id, trigger))

    return matching_workflows


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
