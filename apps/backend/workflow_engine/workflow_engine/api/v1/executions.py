import sys
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException

# Add backend directory to Python path for shared models
backend_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session

from shared.models import ExecuteWorkflowRequest, ExecuteWorkflowResponse, Execution
from workflow_engine.models.database import get_db
from workflow_engine.services.execution_service import ExecutionService

router = APIRouter()


def get_execution_service(db: Session = Depends(get_db)):
    return ExecutionService(db)


@router.post("/workflows/{workflow_id}/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow(
    request: ExecuteWorkflowRequest, service: ExecutionService = Depends(get_execution_service)
):
    try:
        execution_id = service.execute_workflow(request)
        return ExecuteWorkflowResponse(
            execution_id=execution_id,
            status="PENDING",
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
    except Exception as e:
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
