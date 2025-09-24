import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.node_enums import TriggerSubtype
from shared.models.trigger import ExecutionResult, TriggerType
from shared.models.trigger_index import TriggerIndex
from workflow_scheduler.core.config import settings
from workflow_scheduler.core.database import async_session_factory
from workflow_scheduler.core.supabase_client import get_supabase_client, query_github_triggers
from workflow_scheduler.dependencies import get_trigger_manager
from workflow_scheduler.services.trigger_manager import TriggerManager

# Note: We now use the actual workflow owner's user_id from the database


async def _get_workflow_owner_id(workflow_id: str) -> Optional[str]:
    """Get the workflow owner's user_id from the database"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            logger.error("Supabase client not available")
            return None

        response = supabase.table("workflows").select("user_id").eq("id", workflow_id).execute()

        if response.data and len(response.data) > 0:
            user_id = response.data[0].get("user_id")
            logger.info(f"Found workflow owner: {user_id} for workflow {workflow_id}")
            return str(user_id) if user_id else None
        else:
            logger.warning(f"Workflow {workflow_id} not found in database")
            return None

    except Exception as e:
        logger.error(f"Error fetching workflow owner for {workflow_id}: {e}", exc_info=True)
        return None


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triggers", tags=["triggers"])


class ManualTriggerRequest(BaseModel):
    pass


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


def get_jwt_token(request: Request) -> Optional[str]:
    """Extract JWT token from Authorization header"""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix
    return None


@router.post("/workflows/{workflow_id}/manual", response_model=ExecutionResult)
async def trigger_manual(
    workflow_id: str,
    request_obj: Request,
    request: ManualTriggerRequest,
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
):
    """Manually trigger a workflow execution"""
    try:
        # Extract JWT token from Authorization header
        access_token = get_jwt_token(request_obj)
        if access_token:
            logger.info(f"🔐 JWT token received for manual trigger: {workflow_id}")

        # Get the workflow owner ID
        workflow_owner_id = await _get_workflow_owner_id(workflow_id)
        if not workflow_owner_id:
            logger.error(f"Could not determine workflow owner for {workflow_id}")
            raise HTTPException(status_code=400, detail="Could not determine workflow owner")

        logger.info(
            f"Manual trigger requested for workflow {workflow_id} by owner {workflow_owner_id}"
        )

        result = await trigger_manager.trigger_manual(
            workflow_id=workflow_id, user_id=workflow_owner_id, access_token=access_token
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


@router.post("/github/events", response_model=Dict[str, Any])
async def handle_github_events(
    github_webhook_data: Dict[str, Any],
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
):
    """
    Process GitHub webhook events forwarded from API Gateway
    Expected data format from API Gateway:
    {
        "event_type": str,
        "delivery_id": str,
        "payload": Dict[str, Any],
        "installation_id": int,
        "repository_name": str,
        "timestamp": str
    }
    """
    try:
        event_type = github_webhook_data.get("event_type")
        delivery_id = github_webhook_data.get("delivery_id")
        payload = github_webhook_data.get("payload", {})
        installation_id = github_webhook_data.get("installation_id")
        repository_name = github_webhook_data.get("repository_name")

        logger.info(
            f"GitHub webhook event received from API Gateway: {event_type} "
            f"(delivery: {delivery_id}, repo: {repository_name})"
        )

        if not all([event_type, delivery_id, payload]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: event_type, delivery_id, or payload",
            )

        # Find workflows with matching GitHub triggers
        matching_workflows = await _find_workflows_with_github_triggers(
            trigger_manager,
            installation_id=installation_id or 0,
            repository_name=repository_name or "",
            event_type=event_type,
            payload=payload,
        )

        if not matching_workflows:
            logger.info(
                f"No workflows found matching GitHub event {event_type} "
                f"for repository {repository_name}"
            )
            return {
                "message": "No matching workflows found",
                "event_type": event_type,
                "delivery_id": delivery_id,
                "processed_workflows": 0,
                "results": [],
            }

        # Process each matching workflow
        results = []
        processed_workflows = 0

        for workflow_id, trigger_config, event_config in matching_workflows:
            try:
                # Execute workflow directly via workflow engine
                result = await _execute_workflow_directly(
                    workflow_id=workflow_id,
                    trigger_type="GITHUB",
                    trigger_data={
                        "event_type": event_type,
                        "payload": payload,
                        "repository": repository_name,
                        "installation_id": installation_id,
                        "trigger_config": trigger_config,
                        "event_config": event_config,
                    },
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
                        f"GitHub workflow executed directly {workflow_id}: "
                        f"execution_id={result.execution_id}, status={result.status}"
                    )

            except Exception as e:
                logger.error(
                    f"Error executing workflow {workflow_id}: {e}",
                    exc_info=True,
                )
                results.append(
                    {
                        "workflow_id": workflow_id,
                        "execution_id": None,
                        "status": "error",
                        "message": f"Execution failed: {str(e)}",
                    }
                )

        return {
            "message": "GitHub webhook processed",
            "event_type": event_type,
            "delivery_id": delivery_id,
            "repository": repository_name,
            "installation_id": installation_id,
            "processed_workflows": processed_workflows,
            "results": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling GitHub webhook event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"GitHub webhook processing failed: {str(e)}")


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
            f"Error handling GitHub trigger {trigger_request.event_type}: {e}",
            exc_info=True,
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
    Find workflows that have GitHub triggers matching this event by querying the database
    """
    matching_workflows = []

    try:
        # Query active GitHub triggers using Supabase client (no pgbouncer issues)
        trigger_records = await query_github_triggers(repository_name)

        logger.info(
            f"Found {len(trigger_records)} GitHub triggers for repository {repository_name}"
        )

        for trigger_record in trigger_records:
            try:
                # Parse trigger configuration from Supabase record
                trigger_config = trigger_record["trigger_config"]
                workflow_id = trigger_record["workflow_id"]

                logger.info(f"Processing trigger for workflow {workflow_id}: {trigger_config}")

                # Check installation ID match
                trigger_installation_id = trigger_config.get("github_app_installation_id")
                if trigger_installation_id and str(trigger_installation_id) != str(installation_id):
                    logger.debug(
                        f"Installation ID mismatch: {trigger_installation_id} != {installation_id}"
                    )
                    continue

                # Check repository match (already filtered by index_key, but double-check)
                trigger_repository = trigger_config.get("repository")
                if trigger_repository and trigger_repository != repository_name:
                    logger.debug(f"Repository mismatch: {trigger_repository} != {repository_name}")
                    continue

                # Check event configuration
                event_config_raw = trigger_config.get("event_config", "{}")
                if isinstance(event_config_raw, str):
                    event_config = json.loads(event_config_raw)
                else:
                    event_config = event_config_raw

                # Check if this event type is configured - support both array and object formats
                if isinstance(event_config, list):
                    # Array format: ["push", "pull_request"]
                    event_supported = event_type in event_config
                    logger.info(
                        f"Checking event {event_type} in array config: {event_config} -> {event_supported}"
                    )
                else:
                    # Object format: {"pull_request": {"actions": [...]}}
                    event_supported = event_type in event_config
                    logger.info(
                        f"Checking event {event_type} in object config: {list(event_config.keys())} -> {event_supported}"
                    )

                if not event_supported:
                    logger.info(f"Event type {event_type} not supported in config: {event_config}")
                    continue

                # Check action match for pull_request events (only for object format)
                if event_type == "pull_request" and isinstance(event_config, dict):
                    action = payload.get("action")
                    expected_actions = event_config.get(event_type, {}).get("actions", [])
                    if expected_actions and action not in expected_actions:
                        logger.debug(f"Action {action} not in expected actions: {expected_actions}")
                        continue

                # This trigger matches! Add to execution list
                logger.info(
                    f"✅ Found matching trigger for workflow {workflow_id}: "
                    f"event={event_type}, repo={repository_name}, installation={installation_id}"
                )

                # Add workflow for direct execution (no trigger object needed)
                matching_workflows.append((workflow_id, trigger_config, event_config))

            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                logger.error(f"Error parsing trigger config for {workflow_id}: {e}")
                continue

    except Exception as e:
        logger.error(f"Database error finding GitHub triggers: {e}", exc_info=True)

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
        logger.error(
            f"Error getting trigger status for workflow {workflow_id}: {e}",
            exc_info=True,
        )
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


# Slack endpoints that the API Gateway expects
@router.post("/slack/events", response_model=Dict[str, Any])
async def handle_slack_events(
    slack_event_data: Dict[str, Any],
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
):
    """
    Process Slack events forwarded from API Gateway
    Expected data format from API Gateway:
    {
        "team_id": str,
        "event_data": Dict[str, Any]
    }
    """
    try:
        team_id = slack_event_data.get("team_id")
        event_data = slack_event_data.get("event_data", {})
        event_type = event_data.get("type", "unknown")
        event_id = event_data.get("event_id", "")
        event_time = event_data.get("event_time", 0)

        logger.info(f"Slack event received from API Gateway for team {team_id}")
        logger.info(f"Processing Slack event type: {event_type}, event_id: {event_id}")
        logger.info(f"Full event data: {event_data}")

        # Check for duplicate event processing using Redis-based deduplication
        if event_id:
            from workflow_scheduler.services.event_deduplication import get_deduplication_service

            dedup_service = await get_deduplication_service()
            is_duplicate = await dedup_service.is_duplicate_event(event_id, "slack")

            if is_duplicate:
                return {
                    "message": "Duplicate event, already processed",
                    "event_id": event_id,
                    "team_id": team_id,
                    "processed_workflows": 0,
                    "results": [],
                }

        # Query for workflows with Slack triggers using Supabase client
        try:
            from workflow_scheduler.core.supabase_client import query_slack_triggers

            trigger_records = await query_slack_triggers()

            # Convert Supabase response to expected format (workflow_id, trigger_config)
            matching_workflows = [
                (record["workflow_id"], record["trigger_config"]) for record in trigger_records
            ]

        except Exception as e:
            logger.error(f"Supabase Slack triggers query failed: {e}", exc_info=True)
            # Fallback to empty results if database query fails
            matching_workflows = []

        if not matching_workflows:
            logger.info("No Slack triggers found in database")
            return {
                "message": "No Slack triggers configured",
                "team_id": team_id,
                "processed_workflows": 0,
                "results": [],
            }

        # Process each matching workflow
        results = []
        processed_workflows = 0

        # Import SlackTrigger here to avoid circular imports
        from workflow_scheduler.triggers.slack_trigger import SlackTrigger

        for workflow_id, trigger_config in matching_workflows:
            try:
                # Create SlackTrigger instance and check if event matches
                slack_trigger = SlackTrigger(workflow_id, trigger_config)

                # Check if this event should trigger the workflow
                should_trigger = await slack_trigger.process_slack_event(event_data)

                if should_trigger:
                    logger.info(f"🚀 TRIGGERING WORKFLOW {workflow_id} - Slack trigger matched!")

                    # Execute workflow via SlackTrigger method (includes proper channel context)
                    result = await slack_trigger.trigger_from_slack_event(event_data)

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
                            f"✅ WORKFLOW {workflow_id} EXECUTION COMPLETED: "
                            f"execution_id={result.execution_id}, status={result.status}"
                        )
                    else:
                        logger.error(f"❌ WORKFLOW {workflow_id}: Trigger failed to produce result")
                else:
                    logger.info(
                        f"⏭️ WORKFLOW {workflow_id}: Event filters not matched - workflow skipped"
                    )

            except Exception as e:
                logger.error(
                    f"Error processing Slack trigger for workflow {workflow_id}: {e}",
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

        logger.info(
            f"Processed {processed_workflows} Slack workflows from {len(matching_workflows)} triggers"
        )

        return {
            "message": "Slack event processed",
            "team_id": team_id,
            "event_type": event_type,
            "processed_workflows": processed_workflows,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error handling Slack event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Slack event processing failed: {str(e)}")


@router.post("/slack/interactive", response_model=Dict[str, Any])
async def handle_slack_interactive(
    slack_interactive_data: Dict[str, Any],
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
):
    """
    Process Slack interactive components forwarded from API Gateway
    Expected data format from API Gateway:
    {
        "team_id": str,
        "payload": Dict[str, Any]
    }
    """
    try:
        team_id = slack_interactive_data.get("team_id")
        payload = slack_interactive_data.get("payload", {})

        logger.info(f"Slack interactive component received from API Gateway for team {team_id}")

        # For now, just acknowledge the interaction
        # In the future, this could route to appropriate Slack triggers
        return {
            "message": "Slack interactive component processed",
            "team_id": team_id,
            "slack_response": {"ok": True},
        }

    except Exception as e:
        logger.error(f"Error handling Slack interactive component: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Slack interactive component processing failed: {str(e)}",
        )


@router.post("/slack/commands", response_model=Dict[str, Any])
async def handle_slack_commands(
    command_data: Dict[str, Any],
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
):
    """
    Process Slack slash commands forwarded from API Gateway
    Expected data format from API Gateway: form data as dict
    """
    try:
        team_id = command_data.get("team_id")
        command = command_data.get("command")
        text = command_data.get("text", "")
        user_name = command_data.get("user_name")

        logger.info(
            f"Slack slash command received from API Gateway: {command} from {user_name} in team {team_id}"
        )

        # For now, just acknowledge the command
        # In the future, this could route to appropriate Slack triggers
        return {
            "message": "Slack command processed",
            "team_id": team_id,
            "slack_response": {
                "response_type": "ephemeral",
                "text": f"Command `{command}` received and processed",
            },
        }

    except Exception as e:
        logger.error(f"Error handling Slack command: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Slack command processing failed: {str(e)}")


@router.get("/health")
async def get_health_status(
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
):
    """Get health status of all managed triggers"""
    try:
        health_status = await trigger_manager.health_check()
        return health_status

    except Exception as e:
        logger.error(f"Error getting health status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


async def _execute_workflow_directly(
    workflow_id: str, trigger_type: str, trigger_data: Dict[str, Any]
) -> ExecutionResult:
    """
    Send Slack notification instead of executing workflow (for testing)
    This allows us to verify the GitHub webhook processing works end-to-end
    """
    execution_id = f"exec_{uuid.uuid4()}"

    try:
        # Import notification service here to avoid circular imports
        from workflow_scheduler.services.notification_service import NotificationService

        # Create notification service
        notification_service = NotificationService()

        # Prepare notification message
        event_type = trigger_data.get("event_type", "unknown")
        repository = trigger_data.get("repository", "unknown")
        payload = trigger_data.get("payload", {})

        # Extract relevant info from payload for different event types
        if event_type == "pull_request":
            action = payload.get("action", "unknown")
            pr_title = payload.get("pull_request", {}).get("title", "Unknown PR")
            pr_number = payload.get("pull_request", {}).get("number", "N/A")
            pr_url = payload.get("pull_request", {}).get("html_url", "")
            user = payload.get("pull_request", {}).get("user", {}).get("login", "unknown")

            message = (
                f"🎯 **GitHub Webhook Triggered Successfully!**\n"
                f"**Event**: {event_type} - {action}\n"
                f"**Repository**: {repository}\n"
                f"**PR**: #{pr_number} - {pr_title}\n"
                f"**Author**: {user}\n"
                f"**Workflow ID**: {workflow_id}\n"
                f"**Execution ID**: {execution_id}\n"
                f"**URL**: {pr_url}\n\n"
                f"✅ Webhook processing completed successfully!"
            )
        else:
            message = (
                f"🎯 **GitHub Webhook Triggered Successfully!**\n"
                f"**Event**: {event_type}\n"
                f"**Repository**: {repository}\n"
                f"**Workflow ID**: {workflow_id}\n"
                f"**Execution ID**: {execution_id}\n\n"
                f"✅ Webhook processing completed successfully!"
            )

        # Send Slack notification
        await notification_service.send_trigger_notification(
            workflow_id=workflow_id,
            trigger_type=trigger_type,
            trigger_data=trigger_data,
        )

        logger.info(
            f"✅ Slack notification sent for workflow {workflow_id} (GitHub {event_type} event)"
        )

        return ExecutionResult(
            execution_id=execution_id,
            status="started",
            message="GitHub webhook processed successfully - Slack notification sent",
            trigger_data=trigger_data,
        )

    except Exception as e:
        error_msg = f"Exception during workflow notification: {str(e)}"
        logger.error(
            f"❌ Failed to send notification for workflow {workflow_id}: {error_msg}",
            exc_info=True,
        )

        return ExecutionResult(
            execution_id=execution_id,
            status="error",
            message=error_msg,
            trigger_data=trigger_data,
        )
