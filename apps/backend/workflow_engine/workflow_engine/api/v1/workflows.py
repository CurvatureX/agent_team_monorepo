import sys
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

# Add backend directory to Python path for shared models
backend_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session

from shared.models import (
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    DeleteWorkflowResponse,
    GetWorkflowResponse,
    ListWorkflowsRequest,
    ListWorkflowsResponse,
    NodeTemplate,
    UpdateWorkflowRequest,
    UpdateWorkflowResponse,
    WorkflowData,
)
from workflow_engine.models.database import get_db
from workflow_engine.services.workflow_service import WorkflowService

router = APIRouter()


def get_workflow_service(db: Session = Depends(get_db)):
    return WorkflowService(db)


@router.post("/workflows", response_model=CreateWorkflowResponse)
async def create_workflow(
    request: CreateWorkflowRequest, 
    request_obj: Request,
    service: WorkflowService = Depends(get_workflow_service)
):
    try:
        # 获取 trace_id
        trace_id = request_obj.headers.get("x-trace-id") or request_obj.headers.get("X-Trace-ID")
        if trace_id:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Creating workflow with trace_id: {trace_id}")
            
        workflow = service.create_workflow_from_data(request)
        return CreateWorkflowResponse(
            workflow=workflow, success=True, message="Workflow created successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/node-templates", response_model=List[NodeTemplate])
async def list_node_templates(
    category: Optional[str] = None,
    include_system: bool = True,
    service: WorkflowService = Depends(get_workflow_service),
):
    """
    List all available node templates, with optional filters.
    """
    try:
        templates = service.list_all_node_templates(
            category_filter=category, include_system_templates=include_system
        )
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}", response_model=GetWorkflowResponse)
async def get_workflow(
    workflow_id: str, user_id: str, service: WorkflowService = Depends(get_workflow_service)
):
    try:
        workflow = service.get_workflow(workflow_id=workflow_id, user_id=user_id)
        if workflow:
            return GetWorkflowResponse(
                workflow=workflow, found=True, message="Workflow retrieved successfully"
            )
        return GetWorkflowResponse(found=False, message="Workflow not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/workflows/{workflow_id}", response_model=UpdateWorkflowResponse)
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    service: WorkflowService = Depends(get_workflow_service),
):
    try:
        updated_workflow = service.update_workflow_from_data(
            workflow_id=workflow_id, user_id=request.user_id, update_data=request
        )
        return UpdateWorkflowResponse(
            workflow=updated_workflow, success=True, message="Workflow updated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workflows/{workflow_id}", response_model=DeleteWorkflowResponse)
async def delete_workflow(
    workflow_id: str, user_id: str, service: WorkflowService = Depends(get_workflow_service)
):
    try:
        service.delete_workflow(workflow_id=workflow_id, user_id=user_id)
        return DeleteWorkflowResponse(success=True, message="Workflow deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows", response_model=ListWorkflowsResponse)
async def list_workflows(
    user_id: str,
    active_only: bool = True,
    tags: str = "",
    limit: int = 50,
    offset: int = 0,
    service: WorkflowService = Depends(get_workflow_service),
):
    try:
        tag_list = tags.split(",") if tags else []
        request = ListWorkflowsRequest(
            user_id=user_id, active_only=active_only, tags=tag_list, limit=limit, offset=offset
        )
        workflows, total_count = service.list_workflows(request)
        return ListWorkflowsResponse(
            workflows=workflows,
            total_count=total_count,
            has_more=(offset + len(workflows)) < total_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
