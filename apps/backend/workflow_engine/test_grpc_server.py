#!/usr/bin/env python3
"""
Simple gRPC server test script
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

def start_grpc_server():
    """Start the gRPC server."""
    logger.info("Starting gRPC server...")
    
    # Start server in background
    server_process = subprocess.Popen([
        sys.executable, "-m", "workflow_engine.main"
    ], cwd=os.path.dirname(os.path.abspath(__file__)))
    
    # Wait for server to start
    time.sleep(5)
    
    logger.info(f"gRPC server started with PID: {server_process.pid}")
    return server_process

def test_grpc_connection():
    """Test gRPC connection."""
    try:
        import grpc
        from workflow_engine.proto import workflow_service_pb2_grpc
        
        # Create channel
        channel = grpc.insecure_channel("localhost:50051")
        stub = workflow_service_pb2_grpc.WorkflowServiceStub(channel)
        
        # Test health check
        from grpc_health.v1 import health_pb2_grpc, health_pb2
        health_stub = health_pb2_grpc.HealthStub(channel)
        
        response = health_stub.Check(health_pb2.HealthCheckRequest())
        logger.info(f"Health check response: {response.status}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect to gRPC server: {e}")
        return False

def main():
    """Main test function."""
    logger.info("=== TESTING GRPC SERVER ===")
    
    # Start server
    server_process = start_grpc_server()
    
    try:
        # Test connection
        if test_grpc_connection():
            logger.info("✅ gRPC server is working!")
        else:
            logger.error("❌ gRPC server connection failed!")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        
    finally:
        # Clean up
        logger.info("Stopping gRPC server...")
        server_process.terminate()
        server_process.wait()
        logger.info("gRPC server stopped")

if __name__ == "__main__":
    main() 