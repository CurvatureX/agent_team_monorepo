"""
Workflow Agent Service - LangGraph-based AI Agent for workflow generation
"""

import asyncio
import signal
import sys

import structlog
from dotenv import load_dotenv

from .core.config import settings
from .services.grpc_server import WorkflowAgentServer

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def main():
    """Main entry point for the Workflow Agent service"""
    logger.info("Starting Workflow Agent Service")

    # Create and start the gRPC server
    server = WorkflowAgentServer()

    # Setup graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal", signal=signum)
        asyncio.create_task(server.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await server.start()
        logger.info("Workflow Agent Service started successfully", port=settings.GRPC_PORT)

        # Keep the server running
        await server.wait_for_termination()

    except Exception as e:
        logger.error("Failed to start Workflow Agent Service", error=str(e))
        sys.exit(1)
    finally:
        logger.info("Workflow Agent Service stopped")


if __name__ == "__main__":
    asyncio.run(main())
