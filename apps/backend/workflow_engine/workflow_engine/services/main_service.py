"""
Main gRPC Service - 主要的gRPC服务类.

This module implements the main WorkflowService gRPC service that delegates to specialized services.
"""

import logging

import grpc

from proto import workflow_service_pb2_grpc
from proto import workflow_service_pb2
from proto import execution_pb2
from workflow_engine.services.workflow_service import WorkflowService
from workflow_engine.services.execution_service import ExecutionService
# from workflow_engine.services.validation_service import ValidationService  # 暂时注释掉
from workflow_engine.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MainWorkflowService(workflow_service_pb2_grpc.WorkflowServiceServicer):
    """Main gRPC service implementation that delegates to specialized services."""

    def __init__(self):
        self.logger = logger
        self.workflow_service = WorkflowService()
        self.execution_service = ExecutionService()
        # self.validation_service = ValidationService()  # 暂时禁用

    # Workflow CRUD operations - delegate to WorkflowService
    def CreateWorkflow(
        self, 
        request: workflow_service_pb2.CreateWorkflowRequest, 
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.CreateWorkflowResponse:
        """Create a new workflow."""
        return self.workflow_service.create_workflow(request, context)

    def GetWorkflow(
        self, 
        request: workflow_service_pb2.GetWorkflowRequest, 
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.GetWorkflowResponse:
        """Get a workflow by ID."""
        return self.workflow_service.get_workflow(request, context)

    def UpdateWorkflow(
        self, 
        request: workflow_service_pb2.UpdateWorkflowRequest, 
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.UpdateWorkflowResponse:
        """Update an existing workflow."""
        return self.workflow_service.update_workflow(request, context)

    def DeleteWorkflow(
        self, 
        request: workflow_service_pb2.DeleteWorkflowRequest, 
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.DeleteWorkflowResponse:
        """Delete a workflow."""
        return self.workflow_service.delete_workflow(request, context)

    def ListWorkflows(
        self, 
        request: workflow_service_pb2.ListWorkflowsRequest, 
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.ListWorkflowsResponse:
        """List workflows for a user."""
        return self.workflow_service.list_workflows(request, context)

    # Execution operations - delegate to ExecutionService
    def ExecuteWorkflow(
        self, 
        request: execution_pb2.ExecuteWorkflowRequest, 
        context: grpc.ServicerContext
    ) -> execution_pb2.ExecuteWorkflowResponse:
        """Execute a workflow."""
        return self.execution_service.execute_workflow(request, context)

    def GetExecutionStatus(
        self, 
        request: execution_pb2.GetExecutionStatusRequest, 
        context: grpc.ServicerContext
    ) -> execution_pb2.GetExecutionStatusResponse:
        """Get execution status."""
        return self.execution_service.get_execution_status(request, context)

    def CancelExecution(
        self, 
        request: execution_pb2.CancelExecutionRequest, 
        context: grpc.ServicerContext
    ) -> execution_pb2.CancelExecutionResponse:
        """Cancel a running execution."""
        return self.execution_service.cancel_execution(request, context)

    def GetExecutionHistory(
        self, 
        request: execution_pb2.GetExecutionHistoryRequest, 
        context: grpc.ServicerContext
    ) -> execution_pb2.GetExecutionHistoryResponse:
        """Get execution history for a workflow."""
        return self.execution_service.get_execution_history(request, context)

    # Validation operations - temporarily disabled due to protobuf mismatch
    # TODO: Re-enable when protobuf definitions are updated
    # def ValidateWorkflow(self, request, context):
    #     """Validate a workflow."""
    #     pass
    
    # def TestNode(self, request, context):
    #     """Test a single node.""" 
    #     pass 