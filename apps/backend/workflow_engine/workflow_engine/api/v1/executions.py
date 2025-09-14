import sys
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

# Add backend directory to Python path for shared models
backend_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from typing import Any, Dict, Optional

from pydantic import BaseModel

from shared.models import (
    ExecuteSingleNodeRequest,
    ExecuteWorkflowRequest,
    ExecuteWorkflowResponse,
    Execution,
    SingleNodeExecutionResponse,
)
from workflow_engine.services.supabase_execution_service import SupabaseExecutionService

router = APIRouter()


class ResumeWorkflowRequest(BaseModel):
    """Request model for resuming a paused workflow."""

    resume_data: Optional[Dict[str, Any]] = None
    interaction_id: Optional[str] = None
    approved: Optional[bool] = None
    output_port: Optional[str] = None


class ResumeWorkflowResponse(BaseModel):
    """Response model for workflow resume operation."""

    execution_id: str
    status: str
    message: str
    completed: bool
    paused_again: bool
    remaining_nodes: Optional[List[str]] = None


def get_jwt_token(request: Request) -> Optional[str]:
    """Extract JWT token from Authorization header for RLS."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix
    return None


def get_execution_service(request: Request) -> SupabaseExecutionService:
    """Get SupabaseExecutionService with JWT token for RLS."""
    access_token = get_jwt_token(request)
    return SupabaseExecutionService(access_token=access_token)


@router.post("/workflows/{workflow_id}/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow(
    request: ExecuteWorkflowRequest,
    request_obj: Request,
):
    try:
        # 获取 trace_id
        trace_id = getattr(request_obj.state, "trace_id", None)
        if trace_id:
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"Executing workflow with trace_id: {trace_id}")

        # Get Supabase service with JWT token for RLS
        service = get_execution_service(request_obj)
        execution_id = await service.execute_workflow(request)
        return ExecuteWorkflowResponse(
            execution_id=execution_id,
            status="NEW",  # Changed from PENDING to NEW
            success=True,
            message="Workflow execution started",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}", response_model=Execution)
async def get_execution_status(execution_id: str, request_obj: Request):
    try:
        # Get Supabase service with JWT token for RLS
        service = get_execution_service(request_obj)
        execution = await service.get_execution_status(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        return execution
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/executions/{execution_id}/cancel", response_model=dict)
async def cancel_execution(execution_id: str, request_obj: Request):
    try:
        # Get Supabase service with JWT token for RLS
        service = get_execution_service(request_obj)
        success = await service.cancel_execution(execution_id)
        if not success:
            raise HTTPException(status_code=404, detail="Execution not found")
        return {"success": True, "message": "Execution cancelled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/executions/{execution_id}/resume",
    response_model=ResumeWorkflowResponse,
    summary="Resume a paused workflow",
    description="""
    Resume a paused workflow execution with optional human response data.

    This endpoint is used to continue workflow execution after a Human-in-the-Loop
    node has paused the workflow awaiting human input.

    The request can include:
    - resume_data: Custom data from human interaction
    - interaction_id: ID of the HIL interaction being resolved
    - approved: Boolean for approval/rejection workflows
    - output_port: Specific output port to use for resume
    """,
)
async def resume_workflow(
    execution_id: str,
    request: ResumeWorkflowRequest,
    request_obj: Request,
):
    """
    Resume a paused workflow execution.

    Args:
        execution_id: The ID of the paused execution to resume
        request: Resume request with human response data

    Returns:
        ResumeWorkflowResponse with resume results

    Raises:
        404: If execution not found or not in paused state
        500: If resume operation fails
    """
    try:
        # Get trace_id for logging
        trace_id = getattr(request_obj.state, "trace_id", None)
        if trace_id:
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"Resuming workflow {execution_id} with trace_id: {trace_id}")

        # Prepare resume data from request
        resume_data = request.resume_data or {}

        # Add standard HIL response fields if provided
        if request.interaction_id:
            resume_data["interaction_id"] = request.interaction_id
        if request.approved is not None:
            resume_data["approved"] = request.approved
        if request.output_port:
            resume_data["output_port"] = request.output_port

        # Get Supabase service with JWT token for RLS
        service = get_execution_service(request_obj)

        # Note: resume_workflow_execution is not implemented in SupabaseExecutionService yet
        # This would need to be implemented if resume functionality is needed
        raise HTTPException(
            status_code=501,
            detail="Resume workflow functionality not implemented in Supabase service yet",
        )

        if result["status"] == "ERROR":
            if "not found" in result["message"]:
                raise HTTPException(status_code=404, detail=result["message"])
            else:
                raise HTTPException(status_code=500, detail=result["message"])

        return ResumeWorkflowResponse(
            execution_id=execution_id,
            status=result["status"],
            message=result["message"],
            completed=result.get("completed", False),
            paused_again=result.get("paused_again", False),
            remaining_nodes=result.get("remaining_nodes"),
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume operation failed: {str(e)}")


@router.get("/workflows/{workflow_id}/executions", response_model=List[Execution])
async def get_execution_history(workflow_id: str, limit: int = 50, request_obj: Request = None):
    try:
        # Get Supabase service with JWT token for RLS
        service = get_execution_service(request_obj)
        executions = await service.list_executions(workflow_id=workflow_id, limit=limit)
        return executions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/workflows/{workflow_id}/nodes/{node_id}/execute",
    response_model=SingleNodeExecutionResponse,
    summary="Execute a single node",
    description="""
    Execute a single node within a workflow without running the entire workflow.

    This endpoint is useful for:
    - Testing individual nodes
    - Re-running failed nodes
    - Manual node execution
    - Debugging workflow components
    """,
)
async def execute_single_node(
    workflow_id: str,
    node_id: str,
    request: ExecuteSingleNodeRequest,
    request_obj: Request,
):
    """
    Execute a single node in a workflow.

    Args:
        workflow_id: The ID of the workflow containing the node
        node_id: The ID of the node to execute
        request: Execution request containing input data and context

    Returns:
        SingleNodeExecutionResponse with execution results

    Raises:
        404: If workflow or node not found
        500: If execution fails
    """
    try:
        # Get Supabase service with JWT token for RLS
        service = get_execution_service(request_obj)

        # Set the workflow_id and node_id in the request if not already set
        if not hasattr(request, "workflow_id") or not request.workflow_id:
            request.workflow_id = workflow_id
        if not hasattr(request, "node_id") or not request.node_id:
            request.node_id = node_id

        result = await service.execute_single_node(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
