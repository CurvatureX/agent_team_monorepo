"""
Workflow API endpoints with authentication and enhanced gRPC client integration
支持认证的工作流API端点
"""

import logging
import time
from typing import Optional

from app.core.config import get_settings
from app.dependencies import AuthenticatedDeps
from app.exceptions import NotFoundError, ValidationError
from app.models import (
    DeploymentResult,
    DeploymentStatus,
    ExecutionResult,
    ManualTriggerSpec,
    NodeTemplateListResponse,
    ResponseModel,
    Workflow,
    WorkflowCreate,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowResponse,
    WorkflowUpdate,
)
from app.services.workflow_engine_http_client import get_workflow_engine_client
from app.services.workflow_scheduler_http_client import get_workflow_scheduler_client

# Node converter no longer needed - using unified models directly
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()

# Workflow validation and data cache
WORKFLOW_CACHE = {}
CACHE_TTL = 300  # 5 minutes TTL for workflow data


def _get_cached_workflow(workflow_id: str, user_id: str):
    """Get cached workflow data if available and not expired"""
    cache_key = f"{workflow_id}_{user_id}"
    if cache_key in WORKFLOW_CACHE:
        cached_data, timestamp = WORKFLOW_CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            logger.info(f"📋 Using cached workflow data for {workflow_id}")
            return cached_data
        else:
            # Remove expired cache entry
            del WORKFLOW_CACHE[cache_key]
    return None


def _cache_workflow(workflow_id: str, user_id: str, workflow_data: dict):
    """Cache workflow data for future use"""
    cache_key = f"{workflow_id}_{user_id}"
    WORKFLOW_CACHE[cache_key] = (workflow_data, time.time())
    logger.info(f"📋 Cached workflow data for {workflow_id}")


def _clear_workflow_cache(workflow_id: str, user_id: str):
    """Clear cached workflow data when workflow is modified"""
    cache_key = f"{workflow_id}_{user_id}"
    if cache_key in WORKFLOW_CACHE:
        del WORKFLOW_CACHE[cache_key]
        logger.info(f"📋 Cleared cached workflow data for {workflow_id}")


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

        http_client = await get_workflow_engine_client()

        # Convert WorkflowNode objects to dicts (no format conversion needed - using unified models)
        nodes_list = []
        if request.nodes:
            nodes_list = [node.model_dump() for node in request.nodes]

        # Use connections as-is (no conversion needed - using unified models)
        connections_dict = request.connections or {}

        # Create workflow via HTTP
        result = await http_client.create_workflow(
            name=request.name,
            description=request.description,
            nodes=nodes_list,
            connections=connections_dict,
            settings=request.settings or {},
            static_data=getattr(request, "static_data", None) or {},
            tags=request.tags or [],
            user_id=deps.current_user.sub,
            trace_id=getattr(deps.request.state, "trace_id", None),
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

        http_client = await get_workflow_engine_client()

        # Get workflow via HTTP
        result = await http_client.get_workflow(workflow_id, deps.current_user.sub)
        if not result.get("found", False) or not result.get("workflow"):
            raise NotFoundError("Workflow")

        # Create workflow object using WorkflowData
        from shared.models.workflow import WorkflowData

        workflow = WorkflowData(**result["workflow"])

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

        # Clear cache since workflow was updated
        _clear_workflow_cache(workflow_id, deps.current_user.sub)

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

        http_client = await get_workflow_engine_client()

        # Delete workflow via HTTP
        result = await http_client.delete_workflow(workflow_id, deps.current_user.sub)

        if not result.get("success", False):
            if "not found" in result.get("error", "").lower():
                raise NotFoundError("Workflow")
            raise HTTPException(status_code=500, detail="Failed to delete workflow")

        # Clear cache since workflow was deleted
        _clear_workflow_cache(workflow_id, deps.current_user.sub)

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

        http_client = await get_workflow_engine_client()

        # Execute workflow via HTTP
        result = await http_client.execute_workflow(
            workflow_id,
            deps.current_user.sub,
            execution_request.inputs,
            trace_id=getattr(deps.request.state, "trace_id", None),
        )

        if not result.get("success", False) or not result.get("execution_id"):
            raise HTTPException(status_code=500, detail="Failed to execute workflow")

        logger.info(f"✅ Workflow execution started: {result['execution_id']}")

        # Add workflow_id to the result for the response model
        result["workflow_id"] = workflow_id

        return WorkflowExecutionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error executing workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{workflow_id}/trigger/manual", response_model=ExecutionResult)
async def trigger_manual_workflow(
    workflow_id: str,
    request: ManualTriggerSpec,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Manually trigger a workflow execution
    手动触发工作流执行
    """
    try:
        logger.info(
            f"🚀 Manual trigger request for workflow {workflow_id} by user {deps.current_user.sub}"
        )

        # Get workflow scheduler client
        scheduler_client = await get_workflow_scheduler_client()

        # Trigger manual workflow
        result = await scheduler_client.trigger_manual_workflow(
            workflow_id=workflow_id,
            user_id=deps.current_user.sub,
            confirmation=request.require_confirmation,
            trace_id=getattr(deps.request.state, "trace_id", None),
        )

        # Handle confirmation required case
        if result.get("status") == "confirmation_required":
            raise HTTPException(
                status_code=403,
                detail={
                    "message": result.get("message", "Confirmation required"),
                    "confirmation_required": True,
                    "trigger_data": result.get("trigger_data", {}),
                },
            )

        # Handle errors
        if not result.get("success", True) and result.get("error"):
            error_msg = result.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=404, detail="Workflow not found or no manual triggers configured"
                )
            raise HTTPException(status_code=500, detail=f"Manual trigger failed: {error_msg}")

        logger.info(
            f"✅ Manual trigger successful: {workflow_id}, execution_id: {result.get('execution_id', 'N/A')}"
        )

        # Return ExecutionResult
        return ExecutionResult(
            execution_id=result.get("execution_id", ""),
            status=result.get("status", "unknown"),
            message=result.get("message", "Manual trigger completed"),
            trigger_data=result.get("trigger_data", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error triggering manual workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{workflow_id}/deploy", response_model=DeploymentResult)
async def deploy_workflow(
    workflow_id: str,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Deploy a workflow with its trigger configuration
    部署工作流及其触发器配置
    """
    try:
        logger.info(f"📦 Deploying workflow {workflow_id} for user {deps.current_user.sub}")

        # Check cache first to avoid redundant workflow fetches
        cached_workflow = _get_cached_workflow(workflow_id, deps.current_user.sub)

        if cached_workflow:
            workflow_data = cached_workflow
            logger.info(f"📋 Using cached workflow data for deployment: {workflow_id}")
        else:
            # Get the workflow from workflow engine
            workflow_engine_client = await get_workflow_engine_client()
            workflow_result = await workflow_engine_client.get_workflow(
                workflow_id, deps.current_user.sub
            )

            # Check if workflow exists (workflow engine returns found:true/false and workflow data)
            if not workflow_result.get("found", False) or not workflow_result.get("workflow"):
                logger.error(f"❌ Error deploying workflow {workflow_id}: Workflow not found")
                raise HTTPException(status_code=404, detail="Workflow not found")

            workflow_data = workflow_result["workflow"]

            # Cache the workflow data for future deployments
            _cache_workflow(workflow_id, deps.current_user.sub, workflow_data)

        # Get workflow scheduler client
        scheduler_client = await get_workflow_scheduler_client()

        # Deploy workflow via scheduler
        result = await scheduler_client.deploy_workflow(
            workflow_id=workflow_id,
            workflow_spec=workflow_data,
            trace_id=getattr(deps.request.state, "trace_id", None),
        )

        # Handle errors
        if not result.get("success", True) and result.get("error"):
            error_msg = result.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                raise HTTPException(status_code=404, detail="Workflow not found")
            raise HTTPException(status_code=500, detail=f"Deployment failed: {error_msg}")

        logger.info(
            f"✅ Workflow deployment successful: {workflow_id}, "
            f"deployment_id: {result.get('deployment_id', 'N/A')}"
        )

        # Return DeploymentResult
        return DeploymentResult(
            deployment_id=result.get("deployment_id", ""),
            status=DeploymentStatus(result.get("status", "deployed")),
            message=result.get("message", "Workflow deployed successfully"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deploying workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{workflow_id}/deployment/status")
async def get_deployment_status(
    workflow_id: str,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Get deployment status for a workflow
    获取工作流的部署状态
    """
    try:
        logger.info(
            f"📊 Getting deployment status for workflow {workflow_id} for user {deps.current_user.sub}"
        )

        # Get workflow scheduler client
        scheduler_client = await get_workflow_scheduler_client()

        # Get deployment status
        result = await scheduler_client.get_deployment_status(workflow_id)

        # Handle not found
        if result.get("status_code") == 404:
            raise HTTPException(status_code=404, detail="Deployment not found")

        # Handle errors
        if not result.get("success", True) and result.get("error"):
            error_msg = result.get("error", "Unknown error")
            raise HTTPException(
                status_code=500, detail=f"Failed to get deployment status: {error_msg}"
            )

        logger.info(f"✅ Retrieved deployment status for workflow: {workflow_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting deployment status for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
