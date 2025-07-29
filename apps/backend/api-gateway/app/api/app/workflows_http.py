"""
Workflow API endpoints using HTTP client (FastAPI migration)
Migrated from gRPC to HTTP for the workflow engine service.
"""

import logging
from typing import Any, Dict, List, Optional

from app.dependencies import AuthenticatedDeps
from app.exceptions import NotFoundError, ValidationError
from app.models.base import ResponseModel
from app.models.workflow import (
    Workflow,
    WorkflowCreate,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowResponse,
    WorkflowUpdate,
)
from app.services.workflow_service_http_client import WorkflowServiceHTTPClient
from app.utils import log_error, log_info, log_warning
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Global HTTP client instance
workflow_client = WorkflowServiceHTTPClient()


@router.on_event("startup")
async def startup_event():
    """Initialize workflow client on startup."""
    try:
        await workflow_client.connect()
        log_info("✅ Workflow HTTP client initialized")
    except Exception as e:
        log_error(f"❌ Failed to initialize workflow HTTP client: {e}")


@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup workflow client on shutdown."""
    try:
        await workflow_client.disconnect()
        log_info("✅ Workflow HTTP client disconnected")
    except Exception as e:
        log_error(f"❌ Error disconnecting workflow HTTP client: {e}")


@router.post("/", response_model=ResponseModel)
async def create_workflow(
    workflow_data: WorkflowCreate, deps: AuthenticatedDeps = Depends()
) -> ResponseModel:
    """
    Create a new workflow.

    - **name**: Workflow name (required)
    - **description**: Workflow description (optional)
    - **nodes**: List of workflow nodes (at least one required)
    - **connections**: Node connection configuration
    - **settings**: Workflow execution settings
    """
    try:
        log_info(f"📝 Creating workflow: {workflow_data.name} for user: {deps.user_id}")

        # Convert Pydantic model to dict format expected by HTTP client
        nodes = [node.dict() for node in workflow_data.nodes] if workflow_data.nodes else []
        connections = (
            workflow_data.connections.dict() if workflow_data.connections else {"connections": {}}
        )
        settings = workflow_data.settings.dict() if workflow_data.settings else None

        result = await workflow_client.create_workflow(
            user_id=deps.user_id,
            name=workflow_data.name,
            description=workflow_data.description,
            nodes=nodes,
            connections=connections,
            settings=settings,
            static_data=workflow_data.static_data or {},
            tags=workflow_data.tags or [],
            session_id=deps.session_id,
        )

        if result.get("success", False):
            workflow = result.get("workflow", {})
            log_info(f"✅ Workflow created successfully: {workflow.get('id', 'unknown')}")

            return ResponseModel(
                success=True,
                message="Workflow created successfully",
                data={"workflow_id": workflow.get("id"), "workflow": workflow},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to create workflow"),
            )

    except ValidationError as e:
        log_error(f"❌ Validation error creating workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        log_error(f"❌ Error creating workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create workflow"
        )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, deps: AuthenticatedDeps = Depends()) -> WorkflowResponse:
    """
    Get a workflow by ID.

    - **workflow_id**: Unique workflow identifier
    """
    try:
        log_info(f"📖 Getting workflow: {workflow_id} for user: {deps.user_id}")

        result = await workflow_client.get_workflow(workflow_id, deps.user_id)

        if result.get("found", False):
            workflow_data = result.get("workflow", {})

            # Convert to Pydantic model (simplified for now)
            workflow = Workflow(
                id=workflow_data.get("id", workflow_id),
                name=workflow_data.get("name", ""),
                description=workflow_data.get("description"),
                nodes=workflow_data.get("nodes", []),
                connections=workflow_data.get("connections", {}),
                settings=workflow_data.get("settings", {}),
                static_data=workflow_data.get("static_data", {}),
                tags=workflow_data.get("tags", []),
                active=workflow_data.get("active", True),
                created_at=workflow_data.get("created_at"),
                updated_at=workflow_data.get("updated_at"),
            )

            return WorkflowResponse(
                success=True, message="Workflow retrieved successfully", data=workflow
            )
        else:
            raise NotFoundError("Workflow not found")

    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    except Exception as e:
        log_error(f"❌ Error getting workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get workflow"
        )


@router.put("/{workflow_id}", response_model=ResponseModel)
async def update_workflow(
    workflow_id: str, workflow_data: WorkflowUpdate, deps: AuthenticatedDeps = Depends()
) -> ResponseModel:
    """
    Update an existing workflow.

    - **workflow_id**: Unique workflow identifier
    - **name**: New workflow name (optional)
    - **description**: New workflow description (optional)
    - **nodes**: Updated workflow nodes (optional)
    - **connections**: Updated node connections (optional)
    - **settings**: Updated workflow settings (optional)
    """
    try:
        log_info(f"📝 Updating workflow: {workflow_id} for user: {deps.user_id}")

        # Convert Pydantic models to dicts
        update_data = {}
        if workflow_data.name is not None:
            update_data["name"] = workflow_data.name
        if workflow_data.description is not None:
            update_data["description"] = workflow_data.description
        if workflow_data.nodes is not None:
            update_data["nodes"] = [node.dict() for node in workflow_data.nodes]
        if workflow_data.connections is not None:
            update_data["connections"] = workflow_data.connections.dict()
        if workflow_data.settings is not None:
            update_data["settings"] = workflow_data.settings.dict()
        if workflow_data.static_data is not None:
            update_data["static_data"] = workflow_data.static_data
        if workflow_data.tags is not None:
            update_data["tags"] = workflow_data.tags
        if workflow_data.active is not None:
            update_data["active"] = workflow_data.active

        update_data["session_id"] = deps.session_id

        result = await workflow_client.update_workflow(
            workflow_id=workflow_id, user_id=deps.user_id, **update_data
        )

        if result.get("success", False):
            workflow = result.get("workflow", {})
            log_info(f"✅ Workflow updated successfully: {workflow_id}")

            return ResponseModel(
                success=True,
                message="Workflow updated successfully",
                data={"workflow_id": workflow_id, "workflow": workflow},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to update workflow"),
            )

    except ValidationError as e:
        log_error(f"❌ Validation error updating workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        log_error(f"❌ Error updating workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update workflow"
        )


@router.delete("/{workflow_id}", response_model=ResponseModel)
async def delete_workflow(workflow_id: str, deps: AuthenticatedDeps = Depends()) -> ResponseModel:
    """
    Delete a workflow.

    - **workflow_id**: Unique workflow identifier
    """
    try:
        log_info(f"🗑️ Deleting workflow: {workflow_id} for user: {deps.user_id}")

        result = await workflow_client.delete_workflow(workflow_id, deps.user_id)

        if result.get("success", False):
            log_info(f"✅ Workflow deleted successfully: {workflow_id}")

            return ResponseModel(
                success=True,
                message="Workflow deleted successfully",
                data={"workflow_id": workflow_id},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to delete workflow"),
            )

    except Exception as e:
        log_error(f"❌ Error deleting workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete workflow"
        )


@router.get("/", response_model=ResponseModel)
async def list_workflows(
    active_only: bool = False,
    tags: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
    deps: AuthenticatedDeps = Depends(),
) -> ResponseModel:
    """
    List workflows for the authenticated user.

    - **active_only**: Filter to active workflows only
    - **tags**: Filter by workflow tags
    - **limit**: Maximum number of results (1-100)
    - **offset**: Pagination offset
    """
    try:
        log_info(f"📋 Listing workflows for user: {deps.user_id}")

        result = await workflow_client.list_workflows(
            user_id=deps.user_id,
            active_only=active_only,
            tags=tags or [],
            limit=min(limit, 100),  # Cap at 100
            offset=offset,
        )

        workflows = result.get("workflows", [])
        total_count = result.get("total_count", 0)
        has_more = result.get("has_more", False)

        log_info(f"✅ Listed {len(workflows)} workflows for user: {deps.user_id}")

        return ResponseModel(
            success=True,
            message=f"Listed {len(workflows)} workflows",
            data={
                "workflows": workflows,
                "total_count": total_count,
                "has_more": has_more,
                "pagination": {"limit": limit, "offset": offset},
            },
        )

    except Exception as e:
        log_error(f"❌ Error listing workflows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list workflows"
        )


@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: str,
    execution_request: WorkflowExecutionRequest,
    deps: AuthenticatedDeps = Depends(),
) -> WorkflowExecutionResponse:
    """
    Execute a workflow.

    - **workflow_id**: Unique workflow identifier
    - **input_data**: Input data for workflow execution
    - **execution_options**: Execution configuration options
    """
    try:
        log_info(f"🚀 Executing workflow: {workflow_id} for user: {deps.user_id}")

        result = await workflow_client.execute_workflow(
            workflow_id=workflow_id,
            user_id=deps.user_id,
            input_data=execution_request.input_data or {},
            execution_options=execution_request.execution_options or {},
        )

        execution_id = result.get("execution_id")
        status_value = result.get("status", "unknown")

        if execution_id:
            log_info(f"✅ Workflow execution started: {execution_id}")

            return WorkflowExecutionResponse(
                success=True,
                message="Workflow execution started",
                data={
                    "execution_id": execution_id,
                    "workflow_id": workflow_id,
                    "status": status_value,
                    "started_at": result.get("started_at"),
                },
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to start workflow execution"),
            )

    except Exception as e:
        log_error(f"❌ Error executing workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to execute workflow"
        )


@router.get("/executions/{execution_id}/status", response_model=ResponseModel)
async def get_execution_status(
    execution_id: str, deps: AuthenticatedDeps = Depends()
) -> ResponseModel:
    """
    Get execution status.

    - **execution_id**: Unique execution identifier
    """
    try:
        log_info(f"📊 Getting execution status: {execution_id} for user: {deps.user_id}")

        result = await workflow_client.get_execution_status(execution_id, deps.user_id)

        if result.get("found", False):
            execution = result.get("execution", {})

            log_info(f"✅ Execution status retrieved: {execution.get('status', 'unknown')}")

            return ResponseModel(
                success=True,
                message="Execution status retrieved successfully",
                data={"execution_id": execution_id, "execution": execution},
            )
        else:
            raise NotFoundError("Execution not found")

    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    except Exception as e:
        log_error(f"❌ Error getting execution status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get execution status",
        )


@router.post("/executions/{execution_id}/cancel", response_model=ResponseModel)
async def cancel_execution(
    execution_id: str, reason: Optional[str] = None, deps: AuthenticatedDeps = Depends()
) -> ResponseModel:
    """
    Cancel a running execution.

    - **execution_id**: Unique execution identifier
    - **reason**: Cancellation reason (optional)
    """
    try:
        log_info(f"⏹️ Cancelling execution: {execution_id} for user: {deps.user_id}")

        result = await workflow_client.cancel_execution(execution_id, deps.user_id, reason)

        if result.get("success", False):
            log_info(f"✅ Execution cancelled successfully: {execution_id}")

            return ResponseModel(
                success=True,
                message="Execution cancelled successfully",
                data={"execution_id": execution_id, "reason": reason},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to cancel execution"),
            )

    except Exception as e:
        log_error(f"❌ Error cancelling execution: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to cancel execution"
        )


@router.get("/executions/history", response_model=ResponseModel)
async def get_execution_history(
    workflow_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    deps: AuthenticatedDeps = Depends(),
) -> ResponseModel:
    """
    Get execution history.

    - **workflow_id**: Filter by workflow ID (optional)
    - **limit**: Maximum number of results (1-100)
    - **offset**: Pagination offset
    """
    try:
        log_info(f"📚 Getting execution history for user: {deps.user_id}")

        result = await workflow_client.get_execution_history(
            user_id=deps.user_id,
            workflow_id=workflow_id,
            limit=min(limit, 100),  # Cap at 100
            offset=offset,
        )

        executions = result.get("executions", [])
        total_count = result.get("total_count", 0)
        has_more = result.get("has_more", False)

        log_info(f"✅ Retrieved {len(executions)} execution records for user: {deps.user_id}")

        return ResponseModel(
            success=True,
            message=f"Retrieved {len(executions)} execution records",
            data={
                "executions": executions,
                "total_count": total_count,
                "has_more": has_more,
                "pagination": {"limit": limit, "offset": offset},
            },
        )

    except Exception as e:
        log_error(f"❌ Error getting execution history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get execution history",
        )


@router.post("/validate", response_model=ResponseModel)
async def validate_workflow(
    workflow_data: Dict[str, Any], strict_mode: bool = False, deps: AuthenticatedDeps = Depends()
) -> ResponseModel:
    """
    Validate a workflow definition.

    - **workflow_data**: Workflow data to validate
    - **strict_mode**: Enable strict validation rules
    """
    try:
        log_info(f"✅ Validating workflow definition for user: {deps.user_id}")

        result = await workflow_client.validate_workflow(workflow_data, strict_mode)

        validation_result = result.get("validation_result", {})
        is_valid = validation_result.get("valid", False)
        errors = validation_result.get("errors", [])
        warnings = validation_result.get("warnings", [])
        suggestions = validation_result.get("suggestions", [])

        log_info(
            f"✅ Workflow validation completed: valid={is_valid}, errors={len(errors)}, warnings={len(warnings)}"
        )

        return ResponseModel(
            success=True,
            message=f"Workflow validation completed with {len(errors)} errors and {len(warnings)} warnings",
            data={
                "valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "suggestions": suggestions,
            },
        )

    except Exception as e:
        log_error(f"❌ Error validating workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to validate workflow"
        )
