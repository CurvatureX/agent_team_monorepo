"""
gRPC client for communicating with Workflow Engine
"""
from typing import Any, Dict, List, Optional

import grpc
import structlog
from google.protobuf.json_format import MessageToDict

from core.config import settings
from proto import (
    execution_pb2,
    execution_pb2_grpc,
    workflow_service_pb2,
    workflow_service_pb2_grpc,
)

logger = structlog.get_logger()


class WorkflowEngineClient:
    """gRPC client for Workflow Engine service"""

    def __init__(self):
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[workflow_service_pb2_grpc.WorkflowServiceStub] = None

    async def connect(self):
        """Connect to the Workflow Engine gRPC service"""
        try:
            server_address = (
                f"{settings.WORKFLOW_ENGINE_HOST}:{settings.WORKFLOW_ENGINE_PORT}"
            )
            self.channel = grpc.aio.insecure_channel(server_address)
            self.stub = workflow_service_pb2_grpc.WorkflowServiceStub(self.channel)
            logger.info("Connected to Workflow Engine", server_address=server_address)
        except Exception as e:
            logger.error("Failed to connect to Workflow Engine", error=str(e))
            raise

    async def close(self):
        """Close the gRPC connection"""
        if self.channel:
            await self.channel.close()
            logger.info("Closed connection to Workflow Engine")

    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow."""
        if not self.stub:
            raise RuntimeError("gRPC client not connected")
        
        request = workflow_service_pb2.CreateWorkflowRequest(workflow=workflow_data)
        response = await self.stub.CreateWorkflow(request)
        return MessageToDict(response.workflow)

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get a workflow by ID."""
        if not self.stub:
            raise RuntimeError("gRPC client not connected")
        
        request = workflow_service_pb2.GetWorkflowRequest(workflow_id=workflow_id)
        response = await self.stub.GetWorkflow(request)
        return MessageToDict(response.workflow)

    async def update_workflow(
        self, workflow_id: str, workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing workflow."""
        if not self.stub:
            raise RuntimeError("gRPC client not connected")
        
        request = workflow_service_pb2.UpdateWorkflowRequest(
            workflow_id=workflow_id, workflow=workflow_data
        )
        response = await self.stub.UpdateWorkflow(request)
        return MessageToDict(response.workflow)

    async def delete_workflow(self, workflow_id: str):
        """Delete a workflow."""
        if not self.stub:
            raise RuntimeError("gRPC client not connected")
        
        request = workflow_service_pb2.DeleteWorkflowRequest(workflow_id=workflow_id)
        await self.stub.DeleteWorkflow(request)

    async def list_workflows(self, user_id: str) -> List[Dict[str, Any]]:
        """List workflows for a user."""
        if not self.stub:
            raise RuntimeError("gRPC client not connected")
        
        request = workflow_service_pb2.ListWorkflowsRequest(user_id=user_id)
        response = await self.stub.ListWorkflows(request)
        return [MessageToDict(wf) for wf in response.workflows]

    async def execute_workflow(
        self, workflow_id: str, inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a workflow."""
        if not self.stub:
            raise RuntimeError("gRPC client not connected")

        request = execution_pb2.ExecuteWorkflowRequest(
            workflow_id=workflow_id, inputs=inputs
        )
        response = await self.stub.ExecuteWorkflow(request)
        return {"execution_id": response.execution_id}

    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status."""
        if not self.stub:
            raise RuntimeError("gRPC client not connected")

        request = execution_pb2.GetExecutionStatusRequest(execution_id=execution_id)
        response = await self.stub.GetExecutionStatus(request)
        return {
            "status": execution_pb2.ExecutionStatus.Name(response.status),
            "result": MessageToDict(response.result),
        }

    async def cancel_execution(self, execution_id: str) -> Dict[str, Any]:
        """Cancel a running execution."""
        if not self.stub:
            raise RuntimeError("gRPC client not connected")

        request = execution_pb2.CancelExecutionRequest(execution_id=execution_id)
        response = await self.stub.CancelExecution(request)
        return {"success": response.success, "message": response.message}

    async def get_execution_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get execution history for a workflow."""
        if not self.stub:
            raise RuntimeError("gRPC client not connected")
        
        request = execution_pb2.GetExecutionHistoryRequest(workflow_id=workflow_id)
        response = await self.stub.GetExecutionHistory(request)
        return [MessageToDict(ex) for ex in response.executions] 