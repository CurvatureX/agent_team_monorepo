"""
Workflow API endpoints with authentication and enhanced gRPC client integration
支持认证的工作流API端点
"""

import logging
from typing import Optional

from app.core.config import get_settings
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
from app.services.workflow_engine_http_client import get_workflow_engine_client
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
    List all available node templates via HTTP.
    """
    try:
        settings = get_settings()
        if not settings.USE_HTTP_CLIENT:
            raise HTTPException(status_code=503, detail="HTTP client is disabled")

        http_client = await get_workflow_engine_client()
        templates = await http_client.list_all_node_templates(
            category_filter=category,
            type_filter=node_type,
            include_system_templates=include_system,
        )
        return NodeTemplateListResponse(node_templates=templates)
    except HTTPException:
        raise
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

        # Get HTTP client
        settings = get_settings()
        if not settings.USE_HTTP_CLIENT:
            raise HTTPException(status_code=503, detail="HTTP client is disabled")

        http_client = await get_workflow_engine_client()

        # Create workflow via HTTP
        result = await http_client.create_workflow(
            name=request.name,
            description=request.description,
            nodes=request.nodes or [],
            connections=request.connections or {},
            settings=request.settings or {},
            static_data=request.static_data or {},
            tags=request.tags or [],
            user_id=deps.current_user.sub,
        )

        if not result.get("success", False) or not result.get("workflow", {}).get("id"):
            raise HTTPException(status_code=500, detail="Failed to create workflow")

        workflow_data = result["workflow"]

        logger.info(f"✅ Workflow created: {workflow_data['id']}")

        # Create workflow object
        workflow = Workflow(**workflow_data)

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

        # Get HTTP client
        settings = get_settings()
        if not settings.USE_HTTP_CLIENT:
            raise HTTPException(status_code=503, detail="HTTP client is disabled")

        http_client = await get_workflow_engine_client()

        # Get workflow via HTTP
        result = await http_client.get_workflow(workflow_id, deps.current_user.sub)
        if not result.get("success", False) or not result.get("workflow"):
            raise NotFoundError("Workflow")

        # Create workflow object
        workflow = Workflow(**result["workflow"])

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

        # Get HTTP client
        settings = get_settings()
        if not settings.USE_HTTP_CLIENT:
            raise HTTPException(status_code=503, detail="HTTP client is disabled")

        http_client = await get_workflow_engine_client()

        # Update workflow via HTTP
        result = await http_client.update_workflow(
            workflow_id=workflow_id,
            user_id=deps.current_user.sub,
            name=workflow_update.name,
            description=workflow_update.description,
            nodes=workflow_update.nodes,
            connections=workflow_update.connections,
            settings=workflow_update.settings,
            static_data=workflow_update.static_data,
            tags=workflow_update.tags,
            active=workflow_update.active,
        )

        if not result.get("success", False) or not result.get("workflow"):
            raise HTTPException(status_code=500, detail="Failed to update workflow")

        # Create workflow object
        workflow = Workflow(**result["workflow"])

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

        # Get HTTP client
        settings = get_settings()
        if not settings.USE_HTTP_CLIENT:
            raise HTTPException(status_code=503, detail="HTTP client is disabled")

        http_client = await get_workflow_engine_client()

        # Delete workflow via HTTP
        result = await http_client.delete_workflow(workflow_id, deps.current_user.sub)

        if not result.get("success", False):
            if "not found" in result.get("error", "").lower():
                raise NotFoundError("Workflow")
            raise HTTPException(status_code=500, detail="Failed to delete workflow")

        logger.info(f"✅ Workflow deleted: {workflow_id}")

        return ResponseModel(success=True, message="Workflow deleted successfully")

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=dict)
async def list_workflows(
    active_only: bool = True,
    tags: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    deps: AuthenticatedDeps = Depends(),
):
    """
    List workflows for the current user
    列出当前用户的工作流
    """
    try:
        logger.info(f"📋 Listing workflows for user {deps.current_user.sub}")

        # Get HTTP client
        settings = get_settings()
        if not settings.USE_HTTP_CLIENT:
            raise HTTPException(status_code=503, detail="HTTP client is disabled")

        http_client = await get_workflow_engine_client()

        # Parse tags
        tag_list = tags.split(",") if tags else None

        # List workflows via HTTP
        result = await http_client.list_workflows(
            user_id=deps.current_user.sub,
            active_only=active_only,
            tags=tag_list,
            limit=limit,
            offset=offset,
        )

        logger.info(f"✅ Listed {len(result.get('workflows', []))} workflows")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing workflows: {e}")
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

        # Get HTTP client
        settings = get_settings()
        if not settings.USE_HTTP_CLIENT:
            raise HTTPException(status_code=503, detail="HTTP client is disabled")

        http_client = await get_workflow_engine_client()

        # Execute workflow via HTTP
        result = await http_client.execute_workflow(
            workflow_id, deps.current_user.sub, execution_request.input_data
        )

        if not result.get("success", False) or not result.get("execution_id"):
            raise HTTPException(status_code=500, detail="Failed to execute workflow")

        logger.info(f"✅ Workflow execution started: {result['execution_id']}")

        return WorkflowExecutionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error executing workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
