"""
Workflow API endpoints with authentication and enhanced gRPC client integration
支持认证的工作流API端点
"""

import logging
from typing import Optional

import grpc
from app.dependencies import AuthenticatedDeps
from app.exceptions import NotFoundError, ValidationError
from app.models.base import ResponseModel
from app.models.workflow import (
    NodeTemplateListResponse,
    Workflow,
    WorkflowCreate,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowResponse,
    WorkflowUpdate,
)
from app.services.enhanced_grpc_client import GRPC_AVAILABLE, get_workflow_client
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/node-templates", response_model=NodeTemplateListResponse)
async def list_all_node_templates(
    category: Optional[str] = None,
    node_type: Optional[str] = None,
    include_system: bool = True,
    deps: AuthenticatedDeps = Depends(),
):
    """
    List all available node templates.
    """
    if not GRPC_AVAILABLE:
        raise HTTPException(status_code=503, detail="gRPC service is not available")
    try:
        grpc_client = await get_workflow_client()
        response = await grpc_client.ListAllNodeTemplates(
            category_filter=category,
            type_filter=node_type,
            include_system_templates=include_system,
        )
        return NodeTemplateListResponse(node_templates=response.node_templates)
    except grpc.aio.AioRpcError as e:
        logger.error(f"gRPC error listing node templates: {e.details()}")
        raise HTTPException(status_code=500, detail=f"gRPC error: {e.details()}")
    except Exception as e:
        logger.error(f"Error listing node templates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=WorkflowResponse)
async def create_workflow(request: WorkflowCreate, deps: AuthenticatedDeps = Depends()):
    """
    Create a new workflow
    创建新的工作流
    """
    try:
        logger.info(f"📝 Creating workflow for user {deps.current_user.sub}")

        # Get gRPC client
        grpc_client = await get_workflow_client()
        if not grpc_client:
            raise HTTPException(status_code=500, detail="Workflow service unavailable")

        # Prepare workflow data with user context
        grpc_request = request.to_grpc()


        # Create workflow via gRPC
        result = await grpc_client.CreateWorkflow(grpc_request)
        if not result or not result.get("workflow_id"):
            raise HTTPException(status_code=500, detail="Failed to create workflow")

        logger.info(f"✅ Workflow created: {result['workflow_id']}")

        # Create workflow object
        workflow = Workflow(**result)

        return WorkflowResponse(workflow=workflow, message="Workflow created successfully")

    except (ValidationError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Get a workflow with user access control
    通过ID获取工作流（支持用户访问控制）
    """
    try:
        logger.info(f"🔍 Getting workflow {workflow_id} for user {deps.current_user.sub}")

        # Get gRPC client
        grpc_client = await get_workflow_client()
        if not grpc_client:
            raise HTTPException(status_code=500, detail="Workflow service unavailable")

        # Get workflow with user context
        result = await grpc_client.GetWorkflow(workflow_id=workflow_id)
        if not result:
            raise NotFoundError("Workflow")

        # Create workflow object
        workflow = Workflow(**result)

        logger.info(f"✅ Workflow retrieved: {workflow_id}")

        return WorkflowResponse(workflow=workflow, message="Workflow retrieved successfully")

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error getting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    workflow_update: WorkflowUpdate,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Update a workflow with user access control
    更新工作流（支持用户访问控制）
    """
    try:
        logger.info(f"📝 Updating workflow {workflow_id} for user {deps.current_user.sub}")

        # Prepare update data (only include non-None fields)
        update_data = workflow_update.model_dump(exclude_none=True)

        if not update_data:
            raise ValidationError("No update data provided")

        # Get gRPC client
        grpc_client = await get_workflow_client()
        if not grpc_client:
            raise HTTPException(status_code=500, detail="Workflow service unavailable")

        # Update workflow with user context
        grpc_request = workflow_update.to_grpc(workflow_id)
        result = await grpc_client.UpdateWorkflow(grpc_request)

        if not result:
            raise NotFoundError("Workflow")

        # Create workflow object
        workflow = Workflow(**result)

        logger.info(f"✅ Workflow updated: {workflow_id}")

        return WorkflowResponse(workflow=workflow, message="Workflow updated successfully")

    except (ValidationError, NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error updating workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{workflow_id}", response_model=ResponseModel)
async def delete_workflow(workflow_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Delete a workflow with user access control
    删除工作流（支持用户访问控制）
    """
    try:
        logger.info(f"🗑️ Deleting workflow {workflow_id} for user {deps.current_user.sub}")

        # Get gRPC client
        grpc_client = await get_workflow_client()
        if not grpc_client:
            raise HTTPException(status_code=500, detail="Workflow service unavailable")

        # Delete workflow with user context
        success = await grpc_client.DeleteWorkflow(workflow_id=workflow_id)

        if not success:
            raise NotFoundError("Workflow")

        logger.info(f"✅ Workflow deleted: {workflow_id}")

        return ResponseModel(success=True, message="Workflow deleted successfully")

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: str,
    execution_request: WorkflowExecutionRequest,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Execute a workflow with user access control
    执行工作流（支持用户访问控制）
    """
    try:
        logger.info(f"🚀 Executing workflow {workflow_id} for user {deps.current_user.sub}")

        # Get gRPC client
        grpc_client = await get_workflow_client()
        if not grpc_client:
            raise HTTPException(status_code=500, detail="Workflow service unavailable")

        # Execute workflow with user context
        grpc_request = execution_request.to_grpc(workflow_id)
        result = await grpc_client.ExecuteWorkflow(grpc_request)

        if not result or not result.get("execution_id"):
            raise HTTPException(status_code=500, detail="Failed to execute workflow")

        logger.info(f"✅ Workflow execution started: {result['execution_id']}")

        return WorkflowExecutionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error executing workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
