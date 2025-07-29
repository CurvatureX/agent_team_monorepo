"""
Workflow API endpoints.
FastAPI router for workflow CRUD operations, replacing gRPC WorkflowService.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from workflow_engine.workflow_engine.core.config import get_settings
from workflow_engine.workflow_engine.models.requests import (
    CancelExecutionRequest,
    CreateWorkflowRequest,
    DeleteWorkflowRequest,
    ExecuteWorkflowRequest,
    GetExecutionHistoryRequest,
    GetExecutionStatusRequest,
    GetWorkflowRequest,
    ListWorkflowsRequest,
    TestNodeRequest,
    UpdateWorkflowRequest,
    ValidateWorkflowRequest,
)
from workflow_engine.workflow_engine.models.responses import (
    CancelExecutionResponse,
    CreateWorkflowResponse,
    DeleteWorkflowResponse,
    ErrorResponse,
    ExecuteWorkflowResponse,
    GetExecutionHistoryResponse,
    GetExecutionStatusResponse,
    GetWorkflowResponse,
    ListWorkflowsResponse,
    TestNodeResponse,
    UpdateWorkflowResponse,
    ValidateWorkflowResponse,
)
from workflow_engine.workflow_engine.services.execution_service_pydantic import ExecutionService
from workflow_engine.workflow_engine.services.validation_service_pydantic import ValidationService
from workflow_engine.workflow_engine.services.workflow_service_pydantic import WorkflowService

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])


# Dependency injection
def get_workflow_service() -> WorkflowService:
    return WorkflowService()


def get_execution_service() -> ExecutionService:
    return ExecutionService()


def get_validation_service() -> ValidationService:
    return ValidationService()


@router.post("", response_model=CreateWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: CreateWorkflowRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> CreateWorkflowResponse:
    """
    Create a new workflow.

    - **name**: Workflow name (required)
    - **description**: Workflow description (optional)
    - **nodes**: List of workflow nodes (at least one required)
    - **connections**: Node connection configuration
    - **settings**: Workflow execution settings
    - **user_id**: User ID who owns the workflow
    """
    try:
        logger.info(f"Creating workflow: {request.name} for user: {request.user_id}")

        result = await workflow_service.create_workflow(request)

        logger.info(f"Workflow created successfully: {result.workflow.id}")
        return result

    except ValueError as e:
        logger.error(f"Validation error creating workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}",
        )


@router.get("/{workflow_id}", response_model=GetWorkflowResponse)
async def get_workflow(
    workflow_id: str,
    user_id: str,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> GetWorkflowResponse:
    """
    Get a workflow by ID.

    - **workflow_id**: Unique workflow identifier
    - **user_id**: User ID for authorization
    """
    try:
        logger.info(f"Getting workflow: {workflow_id} for user: {user_id}")

        request = GetWorkflowRequest(workflow_id=workflow_id, user_id=user_id)
        result = await workflow_service.get_workflow(request)

        if not result.found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow: {str(e)}",
        )


@router.put("/{workflow_id}", response_model=UpdateWorkflowResponse)
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> UpdateWorkflowResponse:
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
        logger.info(f"Updating workflow: {workflow_id} for user: {request.user_id}")

        # Set workflow_id from path parameter
        request.workflow_id = workflow_id
        result = await workflow_service.update_workflow(request)

        logger.info(f"Workflow updated successfully: {workflow_id}")
        return result

    except ValueError as e:
        logger.error(f"Validation error updating workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error updating workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workflow: {str(e)}",
        )


@router.delete("/{workflow_id}", response_model=DeleteWorkflowResponse)
async def delete_workflow(
    workflow_id: str,
    user_id: str,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> DeleteWorkflowResponse:
    """
    Delete a workflow.

    - **workflow_id**: Unique workflow identifier
    - **user_id**: User ID for authorization
    """
    try:
        logger.info(f"Deleting workflow: {workflow_id} for user: {user_id}")

        request = DeleteWorkflowRequest(workflow_id=workflow_id, user_id=user_id)
        result = await workflow_service.delete_workflow(request)

        logger.info(f"Workflow deleted successfully: {workflow_id}")
        return result

    except Exception as e:
        logger.error(f"Error deleting workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workflow: {str(e)}",
        )


@router.get("", response_model=ListWorkflowsResponse)
async def list_workflows(
    user_id: str,
    active_only: bool = False,
    tags: List[str] = [],
    limit: int = 50,
    offset: int = 0,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> ListWorkflowsResponse:
    """
    List workflows for a user.

    - **user_id**: User ID to filter workflows
    - **active_only**: Filter to active workflows only
    - **tags**: Filter by workflow tags
    - **limit**: Maximum number of results (1-100)
    - **offset**: Pagination offset
    """
    try:
        logger.info(f"Listing workflows for user: {user_id}")

        request = ListWorkflowsRequest(
            user_id=user_id, active_only=active_only, tags=tags, limit=limit, offset=offset
        )
        result = await workflow_service.list_workflows(request)

        logger.info(f"Listed {len(result.workflows)} workflows for user: {user_id}")
        return result

    except ValueError as e:
        logger.error(f"Validation error listing workflows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error listing workflows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}",
        )


@router.post("/{workflow_id}/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow(
    workflow_id: str,
    request: ExecuteWorkflowRequest,
    execution_service: ExecutionService = Depends(get_execution_service),
) -> ExecuteWorkflowResponse:
    """
    Execute a workflow.

    - **workflow_id**: Unique workflow identifier
    - **user_id**: User ID for authorization
    - **input_data**: Input data for workflow execution
    - **execution_options**: Execution configuration options
    """
    try:
        logger.info(f"Executing workflow: {workflow_id} for user: {request.user_id}")

        # Set workflow_id from path parameter
        request.workflow_id = workflow_id
        result = await execution_service.execute_workflow(request)

        logger.info(f"Workflow execution started: {result.execution_id}")
        return result

    except ValueError as e:
        logger.error(f"Validation error executing workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}",
        )


@router.get("/executions/{execution_id}/status", response_model=GetExecutionStatusResponse)
async def get_execution_status(
    execution_id: str,
    user_id: str,
    execution_service: ExecutionService = Depends(get_execution_service),
) -> GetExecutionStatusResponse:
    """
    Get execution status.

    - **execution_id**: Unique execution identifier
    - **user_id**: User ID for authorization
    """
    try:
        logger.info(f"Getting execution status: {execution_id} for user: {user_id}")

        request = GetExecutionStatusRequest(execution_id=execution_id, user_id=user_id)
        result = await execution_service.get_execution_status(request)

        if not result.found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution status: {str(e)}",
        )


@router.post("/executions/{execution_id}/cancel", response_model=CancelExecutionResponse)
async def cancel_execution(
    execution_id: str,
    request: CancelExecutionRequest,
    execution_service: ExecutionService = Depends(get_execution_service),
) -> CancelExecutionResponse:
    """
    Cancel a running execution.

    - **execution_id**: Unique execution identifier
    - **user_id**: User ID for authorization
    - **reason**: Cancellation reason (optional)
    """
    try:
        logger.info(f"Cancelling execution: {execution_id} for user: {request.user_id}")

        # Set execution_id from path parameter
        request.execution_id = execution_id
        result = await execution_service.cancel_execution(request)

        logger.info(f"Execution cancelled: {execution_id}")
        return result

    except Exception as e:
        logger.error(f"Error cancelling execution: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel execution: {str(e)}",
        )


@router.get("/executions/history", response_model=GetExecutionHistoryResponse)
async def get_execution_history(
    user_id: str,
    workflow_id: str = None,
    limit: int = 50,
    offset: int = 0,
    execution_service: ExecutionService = Depends(get_execution_service),
) -> GetExecutionHistoryResponse:
    """
    Get execution history.

    - **user_id**: User ID for authorization
    - **workflow_id**: Filter by workflow ID (optional)
    - **limit**: Maximum number of results (1-100)
    - **offset**: Pagination offset
    """
    try:
        logger.info(f"Getting execution history for user: {user_id}")

        request = GetExecutionHistoryRequest(
            workflow_id=workflow_id, user_id=user_id, limit=limit, offset=offset
        )
        result = await execution_service.get_execution_history(request)

        logger.info(f"Retrieved {len(result.executions)} execution records")
        return result

    except ValueError as e:
        logger.error(f"Validation error getting execution history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting execution history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution history: {str(e)}",
        )


@router.post("/validate", response_model=ValidateWorkflowResponse)
async def validate_workflow(
    request: ValidateWorkflowRequest,
    validation_service: ValidationService = Depends(get_validation_service),
) -> ValidateWorkflowResponse:
    """
    Validate a workflow definition.

    - **workflow**: Workflow data to validate
    - **strict_mode**: Enable strict validation rules
    """
    try:
        logger.info("Validating workflow definition")

        result = await validation_service.validate_workflow(request)

        logger.info(f"Workflow validation completed: {result.validation_result.valid}")
        return result

    except Exception as e:
        logger.error(f"Error validating workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate workflow: {str(e)}",
        )


@router.post("/test-node", response_model=TestNodeResponse)
async def test_node(
    request: TestNodeRequest,
    validation_service: ValidationService = Depends(get_validation_service),
) -> TestNodeResponse:
    """
    Test a single workflow node.

    - **node**: Node configuration to test
    - **input_data**: Test input data
    - **user_id**: User ID for authorization
    """
    try:
        logger.info(f"Testing node: {request.node.id} for user: {request.user_id}")

        result = await validation_service.test_node(request)

        logger.info(f"Node test completed: {result.success}")
        return result

    except Exception as e:
        logger.error(f"Error testing node: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test node: {str(e)}",
        )
