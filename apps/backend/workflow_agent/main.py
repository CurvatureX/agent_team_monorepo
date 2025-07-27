"""
Workflow Agent Service - LangGraph-based AI Agent for workflow generation
"""

import asyncio
import signal
import sys
import os
from pathlib import Path

# Load environment variables early
from dotenv import load_dotenv
load_dotenv()

# Import logging first
import structlog
# Import our modules - these work when run from workflow_agent directory
from core.config import settings
from services.grpc_server import WorkflowAgentServer

logger = structlog.get_logger()


async def main():
    """Main entry point for the Workflow Agent service"""
    logger.info("Starting Workflow Agent Service")

    # Create and start the gRPC server
    logger.info("Creating WorkflowAgentServer instance")
    server = WorkflowAgentServer()
    logger.info("WorkflowAgentServer instance created successfully")

    # Setup graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal", signal=signum)
        asyncio.create_task(server.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Signal handlers registered")

    try:
        logger.info("Starting gRPC server...")
        await server.start()
        logger.info("Workflow Agent Service started successfully", port=settings.GRPC_PORT)

        # Keep the server running
        logger.info("Waiting for server termination...")
        await server.wait_for_termination()

    except Exception as e:
        logger.error("Failed to start Workflow Agent Service", error=str(e))
        import traceback
        logger.error("Traceback:", traceback=traceback.format_exc())
        sys.exit(1)
    finally:
        logger.info("Workflow Agent Service stopped")


if __name__ == "__main__":
    logger.info("Starting main execution")
    asyncio.run(main())
