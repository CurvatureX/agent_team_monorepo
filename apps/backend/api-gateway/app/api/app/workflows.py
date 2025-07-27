"""
API endpoints for managing and executing workflows.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.services.grpc_client import workflow_client

router = APIRouter()


# Dependency to get the gRPC client
def get_grpc_client():
    return workflow_client


# Pydantic Models for API data validation
class WorkflowCreate(BaseModel):
    name: str = Field(..., description="Name of the workflow")
    description: Optional[str] = Field(None, description="Description of the workflow")
    nodes: List[Dict[str, Any]] = Field(..., description="List of nodes in the workflow")
    connections: Dict[str, Any] = Field(..., description="Connections between nodes")


class WorkflowResponse(BaseModel):
    workflow_id: str
    name: str
    description: Optional[str]
    nodes: List[Dict[str, Any]]
    connections: Dict[str, Any]
    created_at: str
    updated_at: str


class WorkflowExecutionRequest(BaseModel):
    inputs: Dict[str, Any] = Field(..., description="Inputs for the workflow execution")


class WorkflowExecutionResponse(BaseModel):
    execution_id: str


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, description="New name of the workflow")
    description: Optional[str] = Field(None, description="New description of the workflow")
    nodes: Optional[List[Dict[str, Any]]] = Field(None, description="New list of nodes")
    connections: Optional[Dict[str, Any]] = Field(None, description="New connections between nodes")


class ExecutionStatusResponse(BaseModel):
    status: str
    result: Optional[Dict[str, Any]]


class ExecutionHistoryResponse(BaseModel):
    executions: List[Dict[str, Any]]


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    client=Depends(get_grpc_client),
):
    """
    Create a new workflow.
    """
    try:
        workflow_dict = await client.create_workflow(workflow_data.dict())
        return WorkflowResponse(**workflow_dict)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    client=Depends(get_grpc_client),
):
    """
    Get a workflow by its ID.
    """
    try:
        workflow_dict = await client.get_workflow(workflow_id)
        if not workflow_dict:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        return WorkflowResponse(**workflow_dict)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    workflow_data: WorkflowUpdate,
    client=Depends(get_grpc_client),
):
    """
    Update an existing workflow.
    """
    try:
        update_data = workflow_data.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field must be provided for update.",
            )
        workflow_dict = await client.update_workflow(workflow_id, update_data)
        return WorkflowResponse(**workflow_dict)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    client=Depends(get_grpc_client),
):
    """
    Delete a workflow.
    """
    try:
        await client.delete_workflow(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    user_id: str,  # Assuming user_id is passed as a query parameter for now
    client=Depends(get_grpc_client),
):
    """
    List all workflows for a user.
    """
    try:
        workflows_list = await client.list_workflows(user_id)
        return [WorkflowResponse(**wf) for wf in workflows_list]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: str,
    execution_request: WorkflowExecutionRequest,
    client=Depends(get_grpc_client),
):
    """
    Execute a workflow.
    """
    try:
        execution_result = await client.execute_workflow(workflow_id, execution_request.inputs)
        return WorkflowExecutionResponse(**execution_result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/executions/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(
    execution_id: str,
    client=Depends(get_grpc_client),
):
    """
    Get the status of a workflow execution.
    """
    try:
        status_result = await client.get_execution_status(execution_id)
        return ExecutionStatusResponse(**status_result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    client=Depends(get_grpc_client),
):
    """
    Cancel a running workflow execution.
    """
    try:
        result = await client.cancel_execution(execution_id)
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message")
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{workflow_id}/history", response_model=ExecutionHistoryResponse)
async def get_execution_history(
    workflow_id: str,
    client=Depends(get_grpc_client),
):
    """
    Get the execution history for a workflow.
    """
    try:
        history_result = await client.get_execution_history(workflow_id)
        return ExecutionHistoryResponse(executions=history_result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
