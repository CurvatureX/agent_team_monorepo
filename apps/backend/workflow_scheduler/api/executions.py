import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from shared.models.trigger import ExecutionResult, TriggerType
from workflow_scheduler.core.config import settings
from workflow_scheduler.core.supabase_client import get_supabase_client
from workflow_scheduler.dependencies import get_trigger_manager
from workflow_scheduler.services.trigger_manager import TriggerManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/executions", tags=["executions"])


class TriggerExecutionRequest(BaseModel):
    """Request model for triggering workflow execution"""

    trigger_metadata: Dict[str, Any]
    input_data: Optional[Dict[str, Any]] = None


class TriggerExecutionResponse(BaseModel):
    """Response model for workflow execution trigger"""

    success: bool
    execution_id: Optional[str] = None
    message: str
    error: Optional[str] = None


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


async def _trigger_workflow_engine(
    workflow_id: str,
    user_id: str,
    trigger_metadata: Dict[str, Any],
    input_data: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Trigger workflow execution via workflow engine"""

    try:
        # Convert all values to strings as required by ExecuteWorkflowRequest
        trigger_data = {}

        # Add trigger metadata (convert values to strings)
        for key, value in trigger_metadata.items():
            trigger_data[key] = str(value) if value is not None else ""

        # Add input data (convert values to strings)
        for key, value in (input_data or {}).items():
            trigger_data[key] = str(value) if value is not None else ""

        # Add execution context (all strings)
        trigger_data.update(
            {
                "trigger_source": "manual_invocation",
                "initiated_by": user_id,
                "trace_id": trace_id or str(uuid.uuid4()),
            }
        )

        # Prepare execution request in ExecuteWorkflowRequest format
        execution_request = {
            "workflow_id": workflow_id,
            "trigger_data": trigger_data,
            "user_id": user_id,
            "session_id": None,
        }

        headers = {"Content-Type": "application/json"}

        if trace_id:
            headers["X-Trace-ID"] = trace_id

        # Call workflow engine
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.workflow_engine_url}/v1/workflows/{workflow_id}/execute",
                json=execution_request,
                headers=headers,
            )
            response.raise_for_status()

            result = response.json()
            logger.info(
                f"✅ Workflow execution triggered: {workflow_id}, execution_id: {result.get('execution_id')}"
            )

            return {
                "success": True,
                "execution_id": result.get("execution_id"),
                "message": "Workflow execution started successfully",
            }

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}"
        try:
            error_response = e.response.json()
            error_msg = error_response.get("detail", error_msg)
        except Exception:
            pass

        logger.error(f"❌ HTTP error triggering workflow execution: {error_msg}")
        return {"success": False, "error": f"Workflow execution failed: {error_msg}"}

    except Exception as e:
        logger.error(f"❌ Error triggering workflow execution: {e}")
        return {"success": False, "error": f"Workflow execution failed: {str(e)}"}


@router.post("/workflows/{workflow_id}/trigger")
async def trigger_workflow_execution(
    workflow_id: str,
    request: TriggerExecutionRequest,
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    trigger_manager: TriggerManager = Depends(get_trigger_manager),
) -> TriggerExecutionResponse:
    """
    Trigger a workflow execution with custom metadata and input data.

    This endpoint is used by the API Gateway for manual trigger invocations
    and other custom execution scenarios.
    """
    try:
        logger.info(f"🚀 Triggering workflow execution: {workflow_id}")

        # Get workflow owner if user_id not provided
        if not user_id:
            user_id = await _get_workflow_owner_id(workflow_id)
            if not user_id:
                raise HTTPException(
                    status_code=404, detail="Workflow not found or user not identified"
                )

        # Validate trigger metadata
        trigger_metadata = request.trigger_metadata
        if not trigger_metadata:
            raise HTTPException(status_code=400, detail="Trigger metadata is required")

        # Add execution metadata
        enhanced_metadata = {
            **trigger_metadata,
            "workflow_id": workflow_id,
            "user_id": user_id,
            "execution_timestamp": datetime.utcnow().isoformat(),
            "scheduler_trace_id": trace_id or str(uuid.uuid4()),
        }

        # Trigger workflow execution via workflow engine
        result = await _trigger_workflow_engine(
            workflow_id=workflow_id,
            user_id=user_id,
            trigger_metadata=enhanced_metadata,
            input_data=request.input_data,
            trace_id=trace_id,
        )

        if result.get("success"):
            return TriggerExecutionResponse(
                success=True,
                execution_id=result.get("execution_id"),
                message=result.get("message", "Workflow execution triggered successfully"),
            )
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Unknown execution error")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in trigger_workflow_execution: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/workflows/{workflow_id}/executions")
async def get_workflow_executions(
    workflow_id: str, limit: int = 50, offset: int = 0, status_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get execution history for a workflow.

    This endpoint provides execution history including manual invocations.
    """
    try:
        logger.info(f"📊 Getting execution history for workflow: {workflow_id}")

        # Get executions from Supabase
        supabase = get_supabase_client()
        if not supabase:
            raise HTTPException(status_code=500, detail="Database connection not available")

        # Build query
        query = supabase.table("workflow_executions").select("*").eq("workflow_id", workflow_id)

        if status_filter:
            query = query.eq("status", status_filter)

        # Add pagination and ordering
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

        response = query.execute()

        executions = response.data or []

        logger.info(f"✅ Retrieved {len(executions)} executions for workflow {workflow_id}")

        return {
            "workflow_id": workflow_id,
            "executions": executions,
            "total_count": len(executions),
            "limit": limit,
            "offset": offset,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting workflow executions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve executions: {str(e)}")
