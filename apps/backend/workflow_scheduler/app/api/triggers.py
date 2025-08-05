import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..dependencies import get_trigger_manager
from ..models.triggers import ExecutionResult, TriggerType
from ..services.trigger_manager import TriggerManager

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
