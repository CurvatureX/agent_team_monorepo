"""
Main gRPC server application.
"""

import asyncio
import logging
import signal
import sys
from concurrent import futures
from typing import Optional

import grpc

from workflow_engine.core.config import get_settings
from workflow_engine.models.database import init_db
from workflow_engine.services.main_service import MainWorkflowService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GRPCServer:
    """gRPC server manager."""
    
    def __init__(self):
        self.settings = get_settings()
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
        from workflow_engine.proto import workflow_service_pb2_grpc
        workflow_service_pb2_grpc.add_WorkflowServiceServicer_to_server(
            MainWorkflowService(), server
        )
        
        # Add health check service
        from grpc_health.v1 import health_pb2_grpc
        from grpc_health.v1.health import HealthServicer
        health_servicer = HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
        
        # Set all services as serving
        health_servicer.set("", health_pb2_grpc.HealthCheckResponse.SERVING)
        health_servicer.set("WorkflowService", health_pb2_grpc.HealthCheckResponse.SERVING)
        
        # Add listening port
        listen_addr = f"{self.settings.grpc_host}:{self.settings.grpc_port}"
        server.add_insecure_port(listen_addr)
        
        logger.info(f"gRPC server configured to listen on {listen_addr}")
        return server
    
    def start(self):
        """Start the gRPC server."""
        try:
            # Initialize database
            logger.info("Initializing database...")
            init_db()
            
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
    logger.info("Starting Workflow Engine gRPC Server")
    
    server = GRPCServer()
    server.start()


if __name__ == "__main__":
    main() 