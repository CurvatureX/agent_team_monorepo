"""
V2 Execution Endpoints (Modern API)

Modern workflow execution endpoints with comprehensive logging and progress tracking.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from shared.models.execution_new import ExecutionStatus, TriggerInfo
from shared.models.node_enums import TriggerSubtype
from shared.models.workflow import Workflow, WorkflowMetadata
from workflow_engine_v2.api.models import (
    CancelExecutionResponse,
    ExecuteWorkflowRequest,
    ExecuteWorkflowResponse,
    ExecutionProgressResponse,
    ExecutionStatusResponse,
    LogMilestoneRequest,
    LogMilestoneResponse,
)
from workflow_engine_v2.core.engine import ExecutionEngine
from workflow_engine_v2.services.supabase_repository_v2 import SupabaseExecutionRepository
from workflow_engine_v2.services.workflow import WorkflowServiceV2
from workflow_engine_v2.services.workflow_status_manager import WorkflowStatusManagerV2

logger = logging.getLogger(__name__)

router = APIRouter(tags=["V2 Executions"])

# Global engine instance with user-friendly logging enabled
try:
    execution_repository = SupabaseExecutionRepository()
except Exception as repo_error:  # pragma: no cover - runtime safeguard
    execution_repository = None
    logger.warning(
        "⚠️ [v2] Supabase execution repository unavailable, falling back to in-memory store: %s",
        repo_error,
    )

engine = ExecutionEngine(
    repository=execution_repository,
    enable_user_friendly_logging=True,
)
workflow_service = WorkflowServiceV2()


@router.post("/workflows/{workflow_id}/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow_by_id(
    workflow_id: str,
    request: dict,
    background_tasks: BackgroundTasks,
):
    """Execute a workflow by ID with comprehensive logging"""
    try:
        logger.info(f"📝 [v2] Received workflow execution request for workflow {workflow_id}")

        # Extract parameters from API Gateway request format
        trigger_payload = request.get("trigger", {}) or {}
        trigger_data = request.get("trigger_data") or request.get("input_data") or trigger_payload
        trace_id = request.get("trace_id")
        async_execution = request.get("async_execution", True)
        start_from = request.get("start_from_node")
        start_nodes: Optional[List[str]] = None
        if start_from:
            if isinstance(start_from, (list, tuple)):
                start_nodes = [str(node) for node in start_from]
            else:
                start_nodes = [str(start_from)]

        node_inputs = request.get("inputs")
        if node_inputs and not isinstance(node_inputs, dict):
            logger.warning(
                "⚠️ [v2] Ignoring non-dict inputs payload (%s)", type(node_inputs).__name__
            )
            node_inputs = None
        elif isinstance(node_inputs, dict) and not node_inputs:
            node_inputs = None
        elif isinstance(node_inputs, dict) and not start_nodes:
            start_nodes = [str(node_id) for node_id in node_inputs.keys()]

        # Retrieve the actual workflow and user_id from the workflow service
        workflow_result = workflow_service.get_workflow_with_user_id(workflow_id)
        if not workflow_result:
            logger.error(f"❌ [v2] Workflow {workflow_id} not found")
            return ExecuteWorkflowResponse(
                success=False,
                execution_id="",
                execution=None,
                error=f"Workflow {workflow_id} not found",
            )

        workflow, user_id = workflow_result
        logger.info(f"📋 [v2] Retrieved workflow {workflow_id} for user {user_id}")

        # Check if workflow is deployed before execution
        from shared.models.workflow import WorkflowDeploymentStatus

        if workflow.metadata.deployment_status != WorkflowDeploymentStatus.DEPLOYED:
            error_msg = (
                f"Workflow {workflow_id} is not deployed (status: {workflow.metadata.deployment_status}). "
                f"Only deployed workflows can be executed."
            )
            logger.error(f"❌ [v2] {error_msg}")
            return ExecuteWorkflowResponse(
                success=False,
                execution_id="",
                execution=None,
                error=error_msg,
            )

        # Determine trigger type from payload if provided
        incoming_type = (
            (trigger_payload.get("trigger_type") if isinstance(trigger_payload, dict) else None)
            or (trigger_data.get("trigger_type") if isinstance(trigger_data, dict) else None)
            or TriggerSubtype.MANUAL.value
        )

        # Create TriggerInfo object
        trigger = TriggerInfo(
            trigger_type=str(incoming_type),
            trigger_data=trigger_data if isinstance(trigger_data, dict) else {},
            user_id=user_id,
            timestamp=int(time.time() * 1000),
        )

        logger.info(
            f"🎯 [v2] Executing workflow: {workflow.metadata.name} (async: {async_execution})"
        )

        if async_execution:
            # Return immediately for async execution
            execution_id = str(uuid.uuid4())
            logger.info(f"⚡ [v2] ASYNC: Starting background execution for {execution_id}")

            async def execute_in_background():
                try:
                    logger.info(f"🚀 [v2] Background execution started for {execution_id}")
                    execution = await engine.execute_workflow(
                        workflow=workflow,
                        trigger=trigger,
                        trace_id=trace_id,
                        execution_id=execution_id,
                        start_nodes=start_nodes,
                        initial_inputs=node_inputs,
                    )
                    logger.info(
                        f"✅ [v2] Background execution completed for {execution_id}: {execution.status}"
                    )
                except Exception as e:
                    logger.error(f"❌ [v2] Background execution failed for {execution_id}: {e}")

            background_tasks.add_task(execute_in_background)

            return ExecuteWorkflowResponse(
                success=True,
                execution_id=execution_id,
                execution={
                    "id": execution_id,
                    "execution_id": execution_id,
                    "workflow_id": workflow_id,
                    "status": ExecutionStatus.RUNNING.value,
                    "start_time": int(time.time() * 1000),
                    "end_time": None,
                },
            )
        else:
            # Execute synchronously
            execution = await engine.execute_workflow(
                workflow=workflow,
                trigger=trigger,
                trace_id=trace_id,
                start_nodes=start_nodes,
                initial_inputs=node_inputs,
            )

            logger.info(
                f"✅ [v2] Workflow execution completed: {execution.execution_id} (status: {execution.status})"
            )

            return ExecuteWorkflowResponse(
                success=execution.status == ExecutionStatus.COMPLETED,
                execution_id=execution.execution_id,
                execution={
                    "id": execution.id,
                    "execution_id": execution.execution_id,
                    "workflow_id": execution.workflow_id,
                    "status": execution.status.value,
                    "start_time": execution.start_time,
                    "end_time": execution.end_time,
                },
            )

    except Exception as e:
        logger.error(f"❌ [v2] Workflow execution failed: {str(e)}")
        import traceback

        logger.error(f"❌ [v2] Full traceback: {traceback.format_exc()}")
        return ExecuteWorkflowResponse(success=False, execution_id="", error=str(e))


@router.post("/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow(request: ExecuteWorkflowRequest, background_tasks: BackgroundTasks):
    """Execute a workflow with comprehensive logging (original endpoint)"""
    try:
        logger.info(f"📝 [v2] Received workflow execution request (original endpoint)")

        # Convert dict to Workflow object
        workflow_dict = request.workflow
        trigger_dict = request.trigger

        # Create Workflow object
        from shared.models.workflow import WorkflowDeploymentStatus

        workflow = Workflow(
            metadata=WorkflowMetadata(
                id=workflow_dict.get("id", "unknown"),
                name=workflow_dict.get("name", "Unnamed Workflow"),
                description=workflow_dict.get("description", ""),
                version=workflow_dict.get("version", 1),
                deployment_status=WorkflowDeploymentStatus(
                    workflow_dict.get("deployment_status", WorkflowDeploymentStatus.DEPLOYED.value)
                ),
            ),
            nodes=workflow_dict.get("nodes", []),
            connections=workflow_dict.get("connections", []),
        )

        # Check if workflow is deployed before execution
        if workflow.metadata.deployment_status != WorkflowDeploymentStatus.DEPLOYED:
            error_msg = (
                f"Workflow {workflow.metadata.id} is not deployed (status: {workflow.metadata.deployment_status}). "
                f"Only deployed workflows can be executed."
            )
            logger.error(f"❌ [v2] {error_msg}")
            return ExecuteWorkflowResponse(
                success=False,
                execution_id="",
                execution=None,
                error=error_msg,
            )

        # Create TriggerInfo object
        trigger = TriggerInfo(
            type=trigger_dict.get("type", TriggerSubtype.MANUAL.value),
            source=trigger_dict.get("source", "api"),
            timestamp=trigger_dict.get("timestamp"),
        )

        logger.info(
            f"🎯 [v2] Executing workflow: {workflow.metadata.name} ({len(workflow.nodes)} nodes)"
        )

        # Execute workflow
        execution = await engine.execute_workflow(
            workflow=workflow, trigger=trigger, trace_id=request.trace_id
        )

        logger.info(
            f"✅ [v2] Workflow execution completed: {execution.execution_id} (status: {execution.status})"
        )

        return ExecuteWorkflowResponse(
            success=execution.status == ExecutionStatus.COMPLETED,
            execution_id=execution.execution_id,
            execution={
                "id": execution.id,
                "execution_id": execution.execution_id,
                "workflow_id": execution.workflow_id,
                "status": execution.status.value,
                "start_time": execution.start_time,
                "end_time": execution.end_time,
            },
        )

    except Exception as e:
        logger.error(f"❌ [v2] Workflow execution failed: {str(e)}")
        import traceback

        logger.error(f"❌ [v2] Full traceback: {traceback.format_exc()}")
        return ExecuteWorkflowResponse(success=False, execution_id="", error=str(e))


@router.get("/executions/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(execution_id: str):
    """Get execution status"""
    try:
        # Use workflow status manager to get real execution status
        status_manager = WorkflowStatusManagerV2()

        # Get execution status from database
        execution_status = await status_manager.get_execution_status(execution_id)

        if execution_status:
            return ExecutionStatusResponse(
                id=execution_id,
                execution_id=execution_id,
                workflow_id=execution_status.get("workflow_id", "unknown"),
                status=execution_status.get("status", "UNKNOWN"),
                start_time=execution_status.get("start_time"),
                end_time=execution_status.get("end_time"),
                created_at=execution_status.get("created_at"),
                updated_at=execution_status.get("updated_at"),
            )
        else:
            # Execution not found
            raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [v2] Error getting execution status for {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}/progress", response_model=ExecutionProgressResponse)
async def get_execution_progress(execution_id: str):
    """Get execution progress"""
    try:
        progress = engine.get_execution_progress(execution_id)
        return ExecutionProgressResponse(execution_id=execution_id, progress=progress)
    except Exception as e:
        return ExecutionProgressResponse(execution_id=execution_id, progress={"error": str(e)})


@router.post("/executions/{execution_id}/milestone", response_model=LogMilestoneResponse)
async def log_milestone(execution_id: str, request: LogMilestoneRequest):
    """Log a custom milestone for an execution"""
    try:
        engine.log_milestone(execution_id, request.message, request.user_message, request.data)
        return LogMilestoneResponse(success=True, execution_id=execution_id)
    except Exception as e:
        return LogMilestoneResponse(success=False, execution_id=execution_id)


@router.get("/workflows/{workflow_id}/executions")
async def get_execution_history(workflow_id: str, limit: int = 50):
    """Get execution history for a workflow"""
    try:
        logger.info(f"📋 [v2] Getting execution history for workflow {workflow_id}")

        # Use workflow status manager to get real execution data
        status_manager = WorkflowStatusManagerV2()

        # Get execution summary which includes recent executions
        summary = await status_manager.get_workflow_execution_summary(workflow_id)

        # Extract recent executions from summary
        executions = summary.get("recent_executions", [])

        # If we have executions, format them properly
        formatted_executions = []
        for execution in executions[:limit]:
            formatted_executions.append(
                {
                    "id": execution.get("execution_id", execution.get("id")),
                    "execution_id": execution.get("execution_id", execution.get("id")),
                    "workflow_id": workflow_id,
                    "status": execution.get("status", "UNKNOWN"),
                    "start_time": execution.get("start_time"),
                    "end_time": execution.get("end_time"),
                    "created_at": execution.get("created_at"),
                    "updated_at": execution.get("updated_at"),
                }
            )

        return {
            "workflows": formatted_executions,
            "total_count": summary.get("total_executions", len(formatted_executions)),
            "has_more": summary.get("total_executions", 0) > limit,
        }
    except Exception as e:
        logger.error(f"❌ [v2] Error getting execution history for workflow {workflow_id}: {e}")
        return {"workflows": [], "total_count": 0, "has_more": False}


@router.post("/executions/{execution_id}/cancel", response_model=CancelExecutionResponse)
async def cancel_execution(execution_id: str):
    """Cancel execution"""
    try:
        logger.info(f"🛑 [v2] Cancel request for execution {execution_id}")

        # Use workflow status manager to cancel real execution
        status_manager = WorkflowStatusManagerV2()

        # Update execution status to CANCELLED
        success = await status_manager.update_execution_status(
            execution_id,
            ExecutionStatus.CANCELLED,
            error_message="Execution cancelled by user request",
        )

        return CancelExecutionResponse(
            success=success,
            message=f"Execution {execution_id} cancellation {'completed' if success else 'failed'}",
            execution_id=execution_id,
        )
    except Exception as e:
        logger.error(f"❌ [v2] Error canceling execution {execution_id}: {e}")
        return CancelExecutionResponse(success=False, message=str(e), execution_id=execution_id)
