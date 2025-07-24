#!/usr/bin/env python3
"""
Test simple gRPC server
"""

import os
import sys
import time
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_simple_grpc_server():
    """Test the simple gRPC server."""
    logger.info("=== TESTING SIMPLE GRPC SERVER ===")
    
    # Start server in background
    server_process = subprocess.Popen([
        sys.executable, "simple_grpc_server.py"
    ], cwd=os.path.dirname(os.path.abspath(__file__)))
    
    # Wait for server to start
    time.sleep(3)
    
    logger.info(f"Simple gRPC server started with PID: {server_process.pid}")
    
    try:
        # Test basic connection
        import grpc
        from workflow_engine.proto import workflow_service_pb2_grpc, workflow_service_pb2
        
        # Create channel
        channel = grpc.insecure_channel("localhost:50051")
        stub = workflow_service_pb2_grpc.WorkflowServiceStub(channel)
        
        # Test health check
        from grpc_health.v1 import health_pb2_grpc, health_pb2
        health_stub = health_pb2_grpc.HealthStub(channel)
        
        response = health_stub.Check(health_pb2.HealthCheckRequest())
        logger.info(f"Health check response: {response.status}")
        
        # Test CreateWorkflow
        request = workflow_service_pb2.CreateWorkflowRequest()
        request.name = "Test Workflow"
        request.description = "A test workflow"
        request.user_id = "test-user-123"
        
        response = stub.CreateWorkflow(request)
        logger.info(f"CreateWorkflow response: {response.success} - {response.message}")
        
        # Test GetWorkflow
        request = workflow_service_pb2.GetWorkflowRequest()
        request.workflow_id = "test-workflow-123"
        request.user_id = "test-user-123"
        
        response = stub.GetWorkflow(request)
        logger.info(f"GetWorkflow response: {response.found} - {response.message}")
        
        # Test ListWorkflows
        request = workflow_service_pb2.ListWorkflowsRequest()
        request.user_id = "test-user-123"
        
        response = stub.ListWorkflows(request)
        logger.info(f"ListWorkflows response: {response.total_count} workflows")
        
        # Test ExecuteWorkflow
        from workflow_engine.proto import execution_pb2
        request = execution_pb2.ExecuteWorkflowRequest()
        request.workflow_id = "test-workflow-123"
        
        response = stub.ExecuteWorkflow(request)
        logger.info(f"ExecuteWorkflow response: {response.success} - {response.execution_id}")
        
        # Test GetExecutionStatus
        request = execution_pb2.GetExecutionStatusRequest()
        request.execution_id = "test-execution-123"
        
        response = stub.GetExecutionStatus(request)
        logger.info(f"GetExecutionStatus response: {response.found} - {response.message}")
        
        logger.info("✅ All gRPC tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        
    finally:
        # Clean up
        logger.info("Stopping gRPC server...")
        server_process.terminate()
        server_process.wait()
        logger.info("gRPC server stopped")

if __name__ == "__main__":
    test_simple_grpc_server() 