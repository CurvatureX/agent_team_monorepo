#!/usr/bin/env python3
"""
Start debug gRPC server
"""

import subprocess
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_debug_server():
    """Start the debug gRPC server."""
    logger.info("Starting debug gRPC server...")
    
    # Start server in background
    server_process = subprocess.Popen([
        sys.executable, "simple_grpc_server.py"
    ], cwd=os.path.dirname(os.path.abspath(__file__)))
    
    # Wait for server to start
    time.sleep(3)
    
    logger.info(f"Debug gRPC server started with PID: {server_process.pid}")
    logger.info("Server is running on localhost:50051")
    logger.info("Press Ctrl+C to stop the server")
    
    try:
        # Keep the server running
        server_process.wait()
    except KeyboardInterrupt:
        logger.info("Stopping debug gRPC server...")
        server_process.terminate()
        server_process.wait()
        logger.info("Debug gRPC server stopped")

if __name__ == "__main__":
    import os
    start_debug_server() 