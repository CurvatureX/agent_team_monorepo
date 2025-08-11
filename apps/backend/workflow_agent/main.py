"""
Workflow Agent Service - FastAPI-based AI Agent for workflow generation
"""

import asyncio
import os
import signal
import sys
from pathlib import Path

# Load environment variables early
from dotenv import load_dotenv

load_dotenv()

# Note: 遥测组件现在在 services/fastapi_server.py 中定义

# Import logging
import logging

import uvicorn

# Add shared to path for logging module
shared_path = Path(__file__).parent.parent / "shared"
if str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

from shared.logging_config import setup_logging
from workflow_agent.core.config import settings
from workflow_agent.services.fastapi_server import app

# Setup unified logging
logger = setup_logging(
    service_name="workflow-agent",
    log_level=os.getenv("LOG_LEVEL", "INFO")
)


class FastAPIServer:
    """FastAPI 服务器包装器，提供优雅关闭功能"""

    def __init__(self):
        self.server = None

    async def start(self):
        """启动 FastAPI 服务器"""
        try:
            port = settings.FASTAPI_PORT
            host = settings.HOST

            logger.info("Starting Workflow Agent FastAPI Server")
            logger.info(f"Address: http://{host}:{port}")
            logger.info(f"Docs: http://{host}:{port}/docs")
            logger.info(f"Health Check: http://{host}:{port}/health")

            # 在 Docker 环境中禁用 reload 模式
            reload_mode = os.getenv("DEBUG", "false").lower() == "true" and not os.path.exists(
                "/app/shared"
            )

            config = uvicorn.Config(
                app, host=host, port=port, reload=reload_mode, access_log=True, log_level="info"
            )
            self.server = uvicorn.Server(config)

            logger.info("FastAPI server started successfully", extra={"port": port})
            await self.server.serve()

        except Exception as e:
            logger.error("Failed to start FastAPI server", extra={"error": str(e)})
            import traceback

            logger.error("Traceback details", extra={"traceback": traceback.format_exc()})
            raise

    async def stop(self):
        """停止 FastAPI 服务器"""
        if self.server:
            logger.info("Stopping FastAPI server")
            self.server.should_exit = True
            logger.info("FastAPI server stopped")

    async def wait_for_termination(self):
        """等待服务器终止"""
        if self.server:
            # FastAPI server will handle termination internally
            pass


async def main():
    """Main entry point for the Workflow Agent service"""
    logger.info("Starting Workflow Agent Service (FastAPI)")

    server = FastAPIServer()
    logger.info("FastAPIServer instance created successfully")

    # Setup graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal", extra={"signum": signum})
        asyncio.create_task(server.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("Starting FastAPI server...")
        await server.start()
        logger.info(
            "Workflow Agent Service started successfully", extra={"port": settings.FASTAPI_PORT}
        )

        # Keep the server running
        logger.info("Waiting for server termination...")
        await server.wait_for_termination()

    except Exception as e:
        logger.error("Failed to start Workflow Agent Service", extra={"error": str(e)})
        import traceback

        logger.error("Traceback details", extra={"traceback": traceback.format_exc()})
        sys.exit(1)
    finally:
        logger.info("Workflow Agent Service stopped")


if __name__ == "__main__":
    logger.info("Starting main execution")
    asyncio.run(main())
