import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from shared.models.trigger import ExecutionResult, TriggerType
from workflow_scheduler.dependencies import get_trigger_manager
from workflow_scheduler.services.trigger_manager import TriggerManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triggers", tags=["triggers"])


class ManualTriggerRequest(BaseModel):
    confirmation: bool = False


class WebhookData(BaseModel):
    headers: Dict[str, str] = {}
    body: Any = None
    query_params: Dict[str, str] = {}
    method: str = "POST"
    path: str = ""
    remote_addr: str = ""


class GitHubTriggerRequest(BaseModel):
    """Request model for GitHub triggers from API Gateway"""

    trigger_type: str
    event_type: str
    delivery_id: str
    github_payload: Dict[str, Any]
    timestamp: str


@router.post("/workflows/{workflow_id}/manual", response_model=ExecutionResult)
async def trigger_manual(
    workflow_id: str,
    request: ManualTriggerRequest,
    user_id: str = "system",  # TODO: Extract from auth
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
):
    """Manually trigger a workflow execution"""
    try:
        logger.info(f"Manual trigger requested for workflow {workflow_id} by user {user_id}")

        result = await trigger_manager.trigger_manual(
            workflow_id=workflow_id, user_id=user_id, confirmation=request.confirmation
        )

        # Handle confirmation required case
        if result.status == "confirmation_required":
            raise HTTPException(
                status_code=403,
                detail={
                    "message": result.message,
                    "confirmation_required": True,
                    "trigger_data": result.trigger_data,
                },
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual trigger for workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Manual trigger failed: {str(e)}")


@router.post("/workflows/{workflow_id}/webhook", response_model=ExecutionResult)
async def process_webhook(
    workflow_id: str,
    request: Request,
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
):
    """Process webhook trigger for a workflow"""
    try:
        logger.info(f"Webhook trigger for workflow {workflow_id}")

        # Extract request data
        headers = dict(request.headers)
        query_params = dict(request.query_params)
        body = await request.body()

        # Try to parse JSON body
        try:
            if body:
                import json

                body = json.loads(body.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Keep as bytes if not JSON
            pass

        request_data = {
            "headers": headers,
            "body": body,
            "query_params": query_params,
            "method": request.method,
            "path": str(request.url.path),
            "remote_addr": request.client.host if request.client else "",
        }

        result = await trigger_manager.process_webhook(
            workflow_id=workflow_id, request_data=request_data
        )

        return result

    except Exception as e:
        logger.error(f"Error processing webhook for workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.post("/github", response_model=Dict[str, Any])
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


@router.get("/workflows/{workflow_id}/status")
async def get_trigger_status(
    workflow_id: str, trigger_manager: TriggerManager = Depends(get_trigger_manager)
):
    """Get status of all triggers for a workflow"""
    try:
        status = await trigger_manager.get_trigger_status(workflow_id)

        if not status:
            raise HTTPException(status_code=404, detail="No triggers found for workflow")

        return {"workflow_id": workflow_id, "trigger_status": status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trigger status for workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get trigger status: {str(e)}")


@router.get("/types")
async def get_trigger_types():
    """Get all available trigger types"""
    try:
        return {
            "trigger_types": [
                {
                    "type": trigger_type.value,
                    "description": {
                        "CRON": "Schedule workflow execution using cron expressions",
                        "MANUAL": "Manual trigger by user request",
                        "WEBHOOK": "HTTP webhook trigger",
                        "EMAIL": "Email-based trigger monitoring IMAP inbox",
                        "GITHUB": "GitHub webhook trigger for repository events",
                    }.get(trigger_type.name, f"{trigger_type.value} trigger"),
                }
                for trigger_type in TriggerType
            ]
        }

    except Exception as e:
        logger.error(f"Error getting trigger types: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get trigger types: {str(e)}")


@router.get("/health")
async def get_health_status(trigger_manager: TriggerManager = Depends(get_trigger_manager)):
    """Get health status of all managed triggers"""
    try:
        health_status = await trigger_manager.health_check()
        return health_status

    except Exception as e:
        logger.error(f"Error getting health status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
