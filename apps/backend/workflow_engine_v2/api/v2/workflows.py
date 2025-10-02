"""
V2 Workflow Endpoints (Modern API)

Modern workflow CRUD operations with enhanced features.
"""

import logging
import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from shared.models.workflow import WorkflowDeploymentStatus

# Import shared node specs service
from shared.services.node_specs_api_service import get_node_specs_api_service
from workflow_engine_v2.api.models import (
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    DeleteWorkflowResponse,
    GetWorkflowResponse,
)
from workflow_engine_v2.services.workflow import WorkflowServiceV2

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["V2 Workflows"])

# Global workflow service instance
workflow_service = WorkflowServiceV2()

# Global node specs service instance
node_specs_service = get_node_specs_api_service()


@router.post("", response_model=CreateWorkflowResponse)
async def create_workflow(request: CreateWorkflowRequest):
    """Create a new workflow"""
    try:
        logger.info(f"📝 [v2] Creating workflow: {request.name} for user {request.created_by}")

        # Use provided workflow ID or generate one
        workflow_id = request.workflow_id or str(uuid.uuid4())
        created_time_ms = request.created_time_ms or int(time.time() * 1000)

        # Create workflow using the service
        workflow = workflow_service.create_workflow(
            workflow_id=workflow_id,
            name=request.name,
            created_by=request.created_by,
            created_time_ms=created_time_ms,
            nodes=request.nodes,
            connections=request.connections,
            triggers=request.triggers or [],
            metadata={},
        )

        logger.info(f"✅ [v2] Workflow created: {workflow_id}")

        # Convert workflow to dict for response
        workflow_dict = workflow.model_dump()

        # Add additional fields expected by API Gateway
        workflow_dict.update(
            {
                "id": workflow_id,
                "user_id": request.created_by,
                "active": True,
                "created_at": created_time_ms,
                "updated_at": created_time_ms,
                "deployment_status": WorkflowDeploymentStatus.PENDING.value,
                "latest_execution_status": None,
                "latest_execution_time": None,
                "latest_execution_id": None,
            }
        )

        return CreateWorkflowResponse(workflow=workflow_dict)

    except Exception as e:
        logger.error(f"❌ [v2] Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {str(e)}")


@router.get("/node-templates")
async def list_node_templates(
    category_filter: Optional[str] = Query(None, alias="category"),
    type_filter: Optional[str] = Query(None, alias="node_type"),
    include_system_templates: bool = Query(True, alias="include_system"),
):
    """
    List all available node templates from node specs.

    This endpoint provides compatibility with the old workflow_engine v1 API
    but uses the modern node_specs system for retrieving templates.
    """
    try:
        logger.info(
            f"📋 [v2] Listing node templates (category={category_filter}, type={type_filter})"
        )

        # Use the shared node specs service to get templates
        templates = node_specs_service.list_all_node_templates(
            category_filter=category_filter,
            type_filter=type_filter,
            include_system_templates=include_system_templates,
        )

        # Convert to dict format for API response
        template_dicts = [template.model_dump() for template in templates]

        logger.info(f"✅ [v2] Retrieved {len(template_dicts)} node templates")
        return {"node_templates": template_dicts, "total_count": len(template_dicts)}

    except Exception as e:
        logger.error(f"❌ [v2] Error listing node templates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list node templates: {str(e)}")


@router.get("/{workflow_id}", response_model=GetWorkflowResponse)
async def get_workflow(workflow_id: str):
    """Get a workflow by ID"""
    try:
        logger.info(f"🔍 [v2] Getting workflow: {workflow_id}")

        workflow = workflow_service.get_workflow(workflow_id)
        if workflow:
            workflow_dict = workflow.model_dump()
            return GetWorkflowResponse(found=True, workflow=workflow_dict)
        else:
            return GetWorkflowResponse(found=False, message="Workflow not found")

    except Exception as e:
        logger.error(f"❌ [v2] Error getting workflow {workflow_id}: {e}")
        return GetWorkflowResponse(found=False, message=f"Error: {str(e)}")


@router.get("")
async def list_workflows(
    active_only: bool = True,
    tags: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    request: Request = None,
):
    """List workflows with filtering using Supabase RLS"""
    try:
        # Extract access token for RLS-based filtering
        access_token = None
        if request and request.headers.get("authorization"):
            auth_header = request.headers.get("authorization")
            if auth_header.startswith("Bearer "):
                access_token = auth_header[7:]  # Remove "Bearer " prefix
                logger.info("🔐 [v2] Using JWT token for RLS-based filtering")

        # Use Supabase RLS to filter workflows by user automatically
        workflows = workflow_service.list_workflows(access_token=access_token)

        # Parse tags if provided
        tag_list = tags.split(",") if tags else []

        # Filter workflows (RLS already handles user filtering)
        filtered_workflows = []
        for workflow in workflows:
            workflow_dict = workflow.model_dump()

            # Apply active filter
            if active_only and not workflow_dict["metadata"].get("active", True):
                continue

            # Apply tag filter
            if tag_list:
                workflow_tags = workflow_dict["metadata"].get("tags", [])
                if not any(tag in workflow_tags for tag in tag_list):
                    continue

            # Convert to API format
            filtered_workflows.append(
                {
                    "id": workflow_dict["metadata"]["id"],
                    "name": workflow_dict["metadata"]["name"],
                    "description": workflow_dict["metadata"].get("description"),
                    "deployment_status": workflow_dict["metadata"].get(
                        "deployment_status", "pending"
                    ),
                    "created_at": workflow_dict["metadata"]["created_time"],
                    "updated_at": workflow_dict["metadata"]["created_time"],
                    "user_id": workflow_dict["metadata"]["created_by"],
                    "active": workflow_dict["metadata"].get("active", True),
                    "tags": workflow_dict["metadata"].get("tags", []),
                    "icon_url": workflow_dict["metadata"].get("icon_url"),
                    "latest_execution_status": None,  # TODO: Implement from execution history
                    "latest_execution_time": None,  # TODO: Implement from execution history
                    "nodes": workflow_dict["nodes"],
                    "connections": workflow_dict["connections"],
                }
            )

        # Apply pagination
        total_count = len(filtered_workflows)
        paginated_workflows = filtered_workflows[offset : offset + limit]
        has_more = (offset + limit) < total_count

        logger.info(f"✅ [v2] Listed {len(paginated_workflows)} workflows")
        return {
            "workflows": paginated_workflows,
            "total_count": total_count,
            "has_more": has_more,
        }

    except Exception as e:
        logger.error(f"❌ [v2] Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{workflow_id}", response_model=DeleteWorkflowResponse)
async def delete_workflow(workflow_id: str, user_id: Optional[str] = None):
    """Delete a workflow"""
    try:
        logger.info(f"🗑️ [v2] Deleting workflow {workflow_id}")

        success = workflow_service.delete_workflow(workflow_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

        return DeleteWorkflowResponse(
            success=True, message=f"Workflow {workflow_id} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [v2] Error deleting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
