import sys
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

# Add backend directory to Python path for shared models
backend_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session

from shared.models import (
    ExecuteWorkflowRequest, 
    ExecuteWorkflowResponse, 
    Execution,
    ExecuteSingleNodeRequest,
    SingleNodeExecutionResponse
)
from workflow_engine.models.database import get_db
from workflow_engine.services.execution_service import ExecutionService

router = APIRouter()


def get_execution_service(db: Session = Depends(get_db)):
    return ExecutionService(db)


@router.post("/workflows/{workflow_id}/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow(
    request: ExecuteWorkflowRequest, 
    request_obj: Request,
    service: ExecutionService = Depends(get_execution_service)
):
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # 获取 trace_id
        trace_id = getattr(request_obj.state, 'trace_id', None)
        if trace_id:
            logger.info(f"Executing workflow with trace_id: {trace_id}")
            
        logger.info(f"About to call service.execute_workflow for {request.workflow_id}")
        execution_id = service.execute_workflow(request)
        logger.info(f"service.execute_workflow returned execution_id: {execution_id}")
        return ExecuteWorkflowResponse(
            execution_id=execution_id,
            status="NEW",  # Changed from PENDING to NEW
            success=True,
            message="Workflow execution started",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}", response_model=Execution)
async def get_execution_status(
    execution_id: str, service: ExecutionService = Depends(get_execution_service)
):
    try:
        execution = service.get_execution_status(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        return execution
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_execution_status endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/executions/{execution_id}/cancel", response_model=dict)
async def cancel_execution(
    execution_id: str, service: ExecutionService = Depends(get_execution_service)
):
    try:
        success = service.cancel_execution(execution_id)
        if not success:
            raise HTTPException(status_code=404, detail="Execution not found")
        return {"success": True, "message": "Execution cancelled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}/executions", response_model=List[Execution])
async def get_execution_history(
    workflow_id: str, limit: int = 50, service: ExecutionService = Depends(get_execution_service)
):
    try:
        return service.get_execution_history(workflow_id, limit)
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
    """
)
async def execute_single_node(
    workflow_id: str,
    node_id: str,
    request: ExecuteSingleNodeRequest,
    service: ExecutionService = Depends(get_execution_service)
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
        result = service.execute_single_node(
            workflow_id=workflow_id,
            node_id=node_id,
            request=request
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
