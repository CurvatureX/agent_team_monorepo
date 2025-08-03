"""
Workflow Agent Service - FastAPI-based AI Agent for workflow generation
Migrated from gRPC to FastAPI while preserving the same logic
"""

import asyncio
import signal
import sys
import os
from pathlib import Path

# Load environment variables early
from dotenv import load_dotenv
load_dotenv()

# Note: 遥测组件现在在 services/fastapi_server.py 中定义

# Import logging
import logging

from core.config import settings
from services.fastapi_server import app
import uvicorn

logger = logging.getLogger(__name__)


class FastAPIServer:
    """FastAPI 服务器包装器，提供优雅关闭功能"""
    
    def __init__(self):
        self.server = None
        
    async def start(self):
        """启动 FastAPI 服务器"""
        try:
            port = settings.FASTAPI_PORT
            host = settings.HOST
            
            logger.info("🚀 Starting Workflow Agent FastAPI Server")
            logger.info(f"   Address: http://{host}:{port}")
            logger.info(f"   Docs: http://{host}:{port}/docs")
            logger.info(f"   Health Check: http://{host}:{port}/health")
            
            # 在 Docker 环境中禁用 reload 模式
            reload_mode = os.getenv('DEBUG', 'false').lower() == 'true' and not os.path.exists('/app/shared')
            
            config = uvicorn.Config(
                app,
                host=host,
                port=port,
                reload=reload_mode,
                access_log=True,
                log_level="info"
            )
            self.server = uvicorn.Server(config)
            
            logger.info(f"FastAPI server started successfully on port {port}")
            await self.server.serve()
            
        except Exception as e:
            logger.error(f"Failed to start FastAPI server: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
        logger.info(f"Received shutdown signal {signum}")
        asyncio.create_task(server.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("Starting FastAPI server...")
        await server.start()
        logger.info(f"Workflow Agent Service started successfully on port {settings.FASTAPI_PORT}")

        # Keep the server running
        logger.info("Waiting for server termination...")
        await server.wait_for_termination()

    except Exception as e:
        logger.error(f"Failed to start Workflow Agent Service: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    finally:
        logger.info("Workflow Agent Service stopped")


if __name__ == "__main__":
    logger.info("Starting main execution")
    asyncio.run(main())