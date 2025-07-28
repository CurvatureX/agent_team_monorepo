"""
Workflow API endpoints with authentication and enhanced gRPC client integration
支持认证的工作流API端点
"""

from typing import Optional

from app.dependencies import AuthenticatedDeps
from app.exceptions import NotFoundError, ValidationError
from app.models.base import ResponseModel
from app.models.workflow import (
    Workflow,
    WorkflowCreate,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowUpdate,
)
from app.services.enhanced_grpc_client import get_workflow_client
from app.utils.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException

logger = get_logger(__name__)
router = APIRouter()


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
        workflow_data = {
            "user_id": deps.current_user.sub,
            "name": request.name,
            "description": request.description,
            "nodes": request.nodes,
            "connections": request.connections,
            "metadata": request.metadata,
        }

        # Create workflow via gRPC
        result = await grpc_client.create_workflow(workflow_data)
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
    Get workflow by ID with user access control
    通过ID获取工作流（支持用户访问控制）
    """
    try:
        logger.info(f"🔍 Getting workflow {workflow_id} for user {deps.current_user.sub}")

        # Get gRPC client
        grpc_client = await get_workflow_client()
        if not grpc_client:
            raise HTTPException(status_code=500, detail="Workflow service unavailable")

        # Get workflow with user context
        result = await grpc_client.get_workflow(workflow_id, user_id=deps.current_user.sub)
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
        result = await grpc_client.update_workflow(
            workflow_id, update_data, user_id=deps.current_user.sub
        )

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
        success = await grpc_client.delete_workflow(workflow_id, user_id=deps.current_user.sub)

        if not success:
            raise NotFoundError("Workflow")

        logger.info(f"✅ Workflow deleted: {workflow_id}")

        return ResponseModel(success=True, message="Workflow deleted successfully")

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=WorkflowListResponse)
async def list_user_workflows(
    page: int = 1, page_size: int = 20, deps: AuthenticatedDeps = Depends()
):
    """
    List all workflows for the current authenticated user
    列出当前认证用户的所有工作流
    """
    try:
        logger.info(f"📋 Listing workflows for user {deps.current_user.sub}")

        # Get gRPC client
        grpc_client = await get_workflow_client()
        if not grpc_client:
            raise HTTPException(status_code=500, detail="Workflow service unavailable")

        # Get all workflows for this user
        workflows_data = await grpc_client.list_workflows(
            user_id=deps.current_user.sub, page=page, page_size=page_size
        )

        if not workflows_data:
            workflows_data = []

        # Convert to Workflow objects
        workflows = [Workflow(**workflow_data) for workflow_data in workflows_data]

        logger.info(f"✅ Retrieved {len(workflows)} workflows for user {deps.current_user.sub}")

        return WorkflowListResponse(
            workflows=workflows,
            total_count=len(workflows),
            page=page,
            page_size=page_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing workflows for user {deps.current_user.sub}: {e}")
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
        result = await grpc_client.execute_workflow(
            workflow_id, execution_request.inputs, user_id=deps.current_user.sub
        )

        if not result or not result.get("execution_id"):
            raise HTTPException(status_code=500, detail="Failed to execute workflow")

        logger.info(f"✅ Workflow execution started: {result['execution_id']}")

        return WorkflowExecutionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error executing workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{workflow_id}/execution_history")
async def get_execution_history(workflow_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Get the execution history for a workflow
    获取工作流的执行历史
    """
    try:
        logger.info(
            f"📊 Getting execution history for workflow {workflow_id}, user {deps.current_user.sub}"
        )

        # Get gRPC client
        grpc_client = await get_workflow_client()
        if not grpc_client:
            raise HTTPException(status_code=500, detail="Workflow service unavailable")

        # Get execution history with user context
        history_result = await grpc_client.get_execution_history(
            workflow_id, user_id=deps.current_user.sub
        )

        if not history_result:
            history_result = []

        logger.info(f"✅ Retrieved {len(history_result)} executions for workflow {workflow_id}")

        return {"executions": history_result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting execution history for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
