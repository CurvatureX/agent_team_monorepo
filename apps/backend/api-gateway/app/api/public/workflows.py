"""
Public Workflow API endpoints - No authentication required
公共工作流API端点 - 无需认证，用于开发和测试
"""

import logging
import time
from typing import Any, Dict

from app.core.config import get_settings
from app.models import DeploymentResult, DeploymentStatus, ResponseModel
from app.services.workflow_engine_http_client import get_workflow_engine_client
from app.services.workflow_scheduler_http_client import get_workflow_scheduler_client
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)
router = APIRouter()

# Cache for workflow data to avoid redundant fetches
WORKFLOW_CACHE = {}
CACHE_TTL = 300  # 5 minutes TTL for workflow data


def _get_cached_workflow(workflow_id: str):
    """Get cached workflow data if available and not expired"""
    cache_key = f"public_{workflow_id}"
    if cache_key in WORKFLOW_CACHE:
        cached_data, timestamp = WORKFLOW_CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            logger.info(f"📋 Using cached workflow data for {workflow_id}")
            return cached_data
        else:
            # Remove expired cache entry
            del WORKFLOW_CACHE[cache_key]
    return None


def _cache_workflow(workflow_id: str, workflow_data: dict):
    """Cache workflow data for future use"""
    cache_key = f"public_{workflow_id}"
    WORKFLOW_CACHE[cache_key] = (workflow_data, time.time())
    logger.info(f"📋 Cached workflow data for {workflow_id}")


def _clear_workflow_cache(workflow_id: str):
    """Clear cached workflow data when workflow is modified"""
    cache_key = f"public_{workflow_id}"
    if cache_key in WORKFLOW_CACHE:
        del WORKFLOW_CACHE[cache_key]
        logger.info(f"📋 Cleared cached workflow data for {workflow_id}")


@router.post("/{workflow_id}/deploy", response_model=DeploymentResult)
async def deploy_workflow_public(
    workflow_id: str,
    request: Request,
):
    """
    Deploy a workflow with its trigger configuration (Public - No Auth Required)
    部署工作流及其触发器配置（公共接口 - 无需认证）

    This endpoint is available for development and testing purposes.
    In production, use the authenticated /api/v1/app/workflows/{workflow_id}/deploy endpoint.
    """
    try:
        logger.info(f"📦 [PUBLIC] Deploying workflow {workflow_id}")

        # Get trace_id from request state if available
        trace_id = getattr(request.state, "trace_id", None)

        # Check cache first to avoid redundant workflow fetches
        cached_workflow = _get_cached_workflow(workflow_id)

        if cached_workflow:
            workflow_data = cached_workflow
            logger.info(f"📋 Using cached workflow data for deployment: {workflow_id}")
        else:
            # Get the workflow from workflow engine using admin access (no user authentication)
            workflow_engine_client = await get_workflow_engine_client()

            # For public API, we'll use admin access to get the workflow
            # This bypasses RLS for development/testing purposes
            workflow_result = await workflow_engine_client.get_workflow_admin(workflow_id)

            # Check if workflow exists
            if not workflow_result.get("found", False) or not workflow_result.get("workflow"):
                logger.error(f"❌ Error deploying workflow {workflow_id}: Workflow not found")
                raise HTTPException(status_code=404, detail="Workflow not found")

            workflow_data = workflow_result["workflow"]

            # Cache the workflow data for future deployments
            _cache_workflow(workflow_id, workflow_data)

        # Get workflow scheduler client
        scheduler_client = await get_workflow_scheduler_client()

        # Deploy workflow via scheduler
        result = await scheduler_client.deploy_workflow(
            workflow_id=workflow_id,
            workflow_spec=workflow_data,
            user_id="public_api_user",  # Use placeholder user for public API
            trace_id=trace_id,
        )

        # Handle errors
        if not result.get("success", True) and result.get("error"):
            error_msg = result.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                raise HTTPException(status_code=404, detail="Workflow not found")
            raise HTTPException(status_code=500, detail=f"Deployment failed: {error_msg}")

        logger.info(
            f"✅ [PUBLIC] Workflow deployment successful: {workflow_id}, "
            f"deployment_id: {result.get('deployment_id', 'N/A')}"
        )

        # Return DeploymentResult
        return DeploymentResult(
            deployment_id=result.get("deployment_id", ""),
            status=DeploymentStatus(result.get("status", DeploymentStatus.DEPLOYED.value)),
            message=result.get("message", "Workflow deployed successfully"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [PUBLIC] Error deploying workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{workflow_id}/undeploy", response_model=ResponseModel)
async def undeploy_workflow_public(
    workflow_id: str,
    request: Request,
):
    """
    Undeploy a workflow and cleanup its triggers (Public - No Auth Required)
    卸载工作流并清理其触发器（公共接口 - 无需认证）

    This endpoint is available for development and testing purposes.
    In production, use the authenticated /api/v1/app/workflows/{workflow_id}/undeploy endpoint.
    """
    try:
        logger.info(f"🗑️ [PUBLIC] Undeploying workflow {workflow_id}")

        # Get trace_id from request state if available
        trace_id = getattr(request.state, "trace_id", None)

        # Get workflow scheduler client
        scheduler_client = await get_workflow_scheduler_client()

        # Undeploy workflow
        result = await scheduler_client.undeploy_workflow(
            workflow_id=workflow_id,
            trace_id=trace_id,
        )

        # Handle errors
        if not result.get("success", True) and result.get("error"):
            error_msg = result.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                raise HTTPException(status_code=404, detail="Workflow deployment not found")
            raise HTTPException(status_code=500, detail=f"Undeploy failed: {error_msg}")

        # Clear cache since workflow was undeployed
        _clear_workflow_cache(workflow_id)

        logger.info(f"✅ [PUBLIC] Workflow undeployed successfully: {workflow_id}")

        return ResponseModel(success=True, message="Workflow undeployed successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [PUBLIC] Error undeploying workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{workflow_id}/deployment/status")
async def get_deployment_status_public(
    workflow_id: str,
    request: Request,
):
    """
    Get deployment status for a workflow (Public - No Auth Required)
    获取工作流的部署状态（公共接口 - 无需认证）

    This endpoint is available for development and testing purposes.
    In production, use the authenticated /api/v1/app/workflows/{workflow_id}/deployment/status endpoint.
    """
    try:
        logger.info(f"📊 [PUBLIC] Getting deployment status for workflow {workflow_id}")

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

        logger.info(f"✅ [PUBLIC] Retrieved deployment status for workflow: {workflow_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [PUBLIC] Error getting deployment status for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
