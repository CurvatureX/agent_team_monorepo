#!/usr/bin/env python3
"""
Unified gRPC Server for Workflow Engine
整合所有gRPC服务的统一启动脚本
"""

import asyncio
import logging
import signal
import sys
import time
from concurrent import futures
from typing import Optional

import grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import all necessary modules
from workflow_engine.core.config import get_settings
from workflow_engine.models.database import init_db, test_db_connection
from workflow_engine.services.main_service import MainWorkflowService

class UnifiedGRPCServer:
    """Unified gRPC server that combines all workflow engine services."""
    
    def __init__(self):
        self.settings = get_settings()
        self.server: Optional[grpc.Server] = None
        self.services = {}
        
    def create_server(self) -> grpc.Server:
        """Create and configure unified gRPC server."""
        logger.info("Creating unified gRPC server...")
        
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
        
        # Add Main Workflow Service (includes all sub-services)
        logger.info("Adding Main Workflow Service...")
        from workflow_engine.proto import workflow_service_pb2_grpc
        main_service = MainWorkflowService()
        workflow_service_pb2_grpc.add_WorkflowServiceServicer_to_server(
            main_service, server
        )
        self.services['main_workflow'] = main_service
        logger.info("✅ Main Workflow Service added (includes Workflow + Execution services)")
        
        # Add health check service
        logger.info("Adding Health Check Service...")
        from grpc_health.v1 import health_pb2_grpc, health_pb2
        from grpc_health.v1.health import HealthServicer
        health_servicer = HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
        
        # Set all services as serving
        health_servicer.set("", health_pb2.HealthCheckResponse.ServingStatus.SERVING)
        health_servicer.set("WorkflowService", health_pb2.HealthCheckResponse.ServingStatus.SERVING)
        
        # Add listening port
        listen_addr = f"{self.settings.grpc_host}:{self.settings.grpc_port}"
        server.add_insecure_port(listen_addr)
        
        logger.info(f"✅ Unified gRPC server configured to listen on {listen_addr}")
        return server
    
    def initialize_database(self):
        """Initialize database connection and tables."""
        logger.info("Initializing database...")
        
        # Test database connection
        if not test_db_connection():
            logger.error("❌ Database connection failed")
            raise Exception("Database connection failed")
        
        logger.info("✅ Database connection successful")
        
        # Initialize database tables
        try:
            init_db()
            logger.info("✅ Database tables initialized")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def start(self):
        """Start the unified gRPC server."""
        try:
            logger.info("🚀 Starting Unified Workflow Engine gRPC Server")
            
            # Initialize database
            self.initialize_database()
            
            # Create and start server
            self.server = self.create_server()
            self.server.start()
            
            logger.info("✅ Unified gRPC server started successfully")
            logger.info(f"📊 Services loaded: {list(self.services.keys())}")
            logger.info(f"🌐 Server listening on: {self.settings.grpc_host}:{self.settings.grpc_port}")
            
            # Set up signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
                self.stop()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Wait for termination
            self.server.wait_for_termination()
            
        except Exception as e:
            logger.error(f"❌ Failed to start unified gRPC server: {e}")
            sys.exit(1)
    
    def stop(self):
        """Stop the unified gRPC server."""
        if self.server:
            logger.info("🛑 Stopping unified gRPC server...")
            
            # Stop all services gracefully
            for service_name, service in self.services.items():
                try:
                    if hasattr(service, 'cleanup'):
                        service.cleanup()
                    logger.info(f"✅ {service_name} service stopped")
                except Exception as e:
                    logger.warning(f"⚠️ Error stopping {service_name} service: {e}")
            
            # Stop the server
            self.server.stop(grace=30)
            logger.info("✅ Unified gRPC server stopped")

def main():
    """Main entry point."""
    logger.info("🎯 Workflow Engine - Unified Server")
    logger.info("=" * 50)
    
    # Create and start server
    server = UnifiedGRPCServer()
    server.start()

if __name__ == "__main__":
    main() 