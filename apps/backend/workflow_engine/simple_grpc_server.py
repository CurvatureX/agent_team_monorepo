#!/usr/bin/env python3
"""
Simple gRPC server for testing
"""

import asyncio
import logging
import signal
import sys
from concurrent import futures
from typing import Optional
import time

import grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import protobuf files
from proto import workflow_service_pb2_grpc, workflow_service_pb2

class SimpleWorkflowService(workflow_service_pb2_grpc.WorkflowServiceServicer):
    """Simple workflow service for testing."""
    
    def __init__(self):
        self.workflows = {}  # In-memory storage for workflows
        self.executions = {}  # In-memory storage for executions
    
    def CreateWorkflow(self, request, context):
        """Create a workflow."""
        logger.info(f"CreateWorkflow called with name: {request.name}")
        logger.info(f"Number of nodes: {len(request.nodes)}")
        
        # Create a simple response
        response = workflow_service_pb2.CreateWorkflowResponse()
        response.success = True
        response.message = "Workflow created successfully"
        
        # Create a workflow object with all the data
        from proto import workflow_pb2
        workflow = workflow_pb2.Workflow()
        workflow.id = f"workflow-{int(time.time())}"
        workflow.name = request.name
        workflow.description = request.description
        workflow.active = True
        workflow.version = "1.0.0"
        workflow.created_at = int(time.time())
        workflow.updated_at = int(time.time())
        
        # Copy nodes from request
        for node in request.nodes:
            workflow.nodes.append(node)
        
        # Copy static data
        for key, value in request.static_data.items():
            workflow.static_data[key] = value
        
        # Copy tags
        workflow.tags.extend(request.tags)
        
        # Store workflow in memory
        self.workflows[workflow.id] = workflow
        
        response.workflow.CopyFrom(workflow)
        
        logger.info(f"Workflow created with ID: {workflow.id}, Nodes: {len(workflow.nodes)}")
        return response
    
    def GetWorkflow(self, request, context):
        """Get a workflow."""
        logger.info(f"GetWorkflow called with ID: {request.workflow_id}")
        
        response = workflow_service_pb2.GetWorkflowResponse()
        
        if request.workflow_id in self.workflows:
            workflow = self.workflows[request.workflow_id]
            response.found = True
            response.message = "Workflow found"
            response.workflow.CopyFrom(workflow)
            logger.info(f"Workflow found: {workflow.name}, Nodes: {len(workflow.nodes)}")
        else:
            response.found = False
            response.message = "Workflow not found"
            logger.warning(f"Workflow not found: {request.workflow_id}")
        
        return response
    
    def ListWorkflows(self, request, context):
        """List workflows."""
        logger.info(f"ListWorkflows called for user: {request.user_id}")
        
        response = workflow_service_pb2.ListWorkflowsResponse()
        
        # Filter workflows by user_id if needed
        user_workflows = []
        for workflow in self.workflows.values():
            # For simplicity, assume all workflows belong to the user
            user_workflows.append(workflow)
        
        response.total_count = len(user_workflows)
        response.has_more = False
        
        # Add workflows to response
        for workflow in user_workflows:
            response.workflows.append(workflow)
        
        logger.info(f"Listed {len(user_workflows)} workflows")
        return response
    
    def ExecuteWorkflow(self, request, context):
        """Execute a workflow."""
        logger.info(f"ExecuteWorkflow called with ID: {request.workflow_id}")
        
        from proto import execution_pb2
        response = execution_pb2.ExecuteWorkflowResponse()
        
        # Check if workflow exists
        if request.workflow_id in self.workflows:
            workflow = self.workflows[request.workflow_id]
            execution_id = f"execution-{int(time.time())}"
            
            response.execution_id = execution_id
            response.status = execution_pb2.ExecutionStatus.RUNNING
            response.message = "Workflow execution started"
            
            # Create execution record
            execution = execution_pb2.ExecutionData()
            execution.execution_id = execution_id
            execution.workflow_id = request.workflow_id
            execution.status = execution_pb2.ExecutionStatus.RUNNING
            execution.start_time = int(time.time())
            execution.mode = request.mode
            execution.triggered_by = request.triggered_by
            
            # Copy input data
            for key, value in request.input_data.items():
                execution.metadata[key] = value
            
            # Copy metadata
            for key, value in request.metadata.items():
                execution.metadata[key] = value
            
            # Store execution
            self.executions[execution_id] = execution
            
            logger.info(f"Execution started: {execution_id} for workflow: {workflow.name}")
        else:
            response.execution_id = ""
            response.status = execution_pb2.ExecutionStatus.FAILED
            response.message = "Workflow not found"
            logger.error(f"Workflow not found for execution: {request.workflow_id}")
        
        return response
    
    def GetExecutionStatus(self, request, context):
        """Get execution status."""
        logger.info(f"GetExecutionStatus called with ID: {request.execution_id}")
        
        from proto import execution_pb2
        response = execution_pb2.GetExecutionStatusResponse()
        
        if request.execution_id in self.executions:
            execution = self.executions[request.execution_id]
            response.found = True
            response.message = "Execution found"
            response.execution.CopyFrom(execution)
            logger.info(f"Execution found: {execution.execution_id}, Status: {execution.status}")
        else:
            response.found = False
            response.message = "Execution not found"
            logger.warning(f"Execution not found: {request.execution_id}")
        
        return response

class GRPCServer:
    """Simple gRPC server manager."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 50051):
        self.host = host
        self.port = port
        self.server: Optional[grpc.Server] = None
        
    def create_server(self) -> grpc.Server:
        """Create and configure gRPC server."""
        # Create server with thread pool
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=10),
            options=[
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 5000),
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
                ('grpc.http2.min_ping_interval_without_data_ms', 300000),
            ]
        )
        
        # Add services
        workflow_service_pb2_grpc.add_WorkflowServiceServicer_to_server(
            SimpleWorkflowService(), server
        )
        
        # Add health check service
        from grpc_health.v1 import health_pb2_grpc, health_pb2
        from grpc_health.v1.health import HealthServicer
        health_servicer = HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
        
        # Set all services as serving
        health_servicer.set("", health_pb2.HealthCheckResponse.ServingStatus.SERVING)
        health_servicer.set("WorkflowService", health_pb2.HealthCheckResponse.ServingStatus.SERVING)
        
        # Add listening port
        listen_addr = f"{self.host}:{self.port}"
        server.add_insecure_port(listen_addr)
        
        logger.info(f"gRPC server configured to listen on {listen_addr}")
        return server
    
    def start(self):
        """Start the gRPC server."""
        try:
            # Create and start server
            self.server = self.create_server()
            self.server.start()
            
            logger.info("gRPC server started successfully")
            
            # Set up signal handlers
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, shutting down...")
                self.stop()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Wait for termination
            self.server.wait_for_termination()
            
        except Exception as e:
            logger.error(f"Failed to start gRPC server: {e}")
            sys.exit(1)
    
    def stop(self):
        """Stop the gRPC server."""
        if self.server:
            logger.info("Stopping gRPC server...")
            self.server.stop(grace=30)
            logger.info("gRPC server stopped")

def main():
    """Main entry point."""
    logger.info("Starting Simple Workflow Engine gRPC Server")
    
    server = GRPCServer()
    server.start()

if __name__ == "__main__":
    main() 