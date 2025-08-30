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

import json

# Import logging
import logging

import uvicorn

from workflow_agent.core.config import settings
from workflow_agent.services.fastapi_server import app


# Configure JSON logging
class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "pathname": record.pathname,
        }

        # Add extra fields if present
        if hasattr(record, "tracking_id"):
            log_obj["tracking_id"] = record.tracking_id
        if hasattr(record, "error"):
            log_obj["error"] = record.error
        if hasattr(record, "error_type"):
            log_obj["error_type"] = record.error_type
        if hasattr(record, "location"):
            log_obj["location"] = record.location
        if hasattr(record, "traceback"):
            log_obj["traceback"] = record.traceback

        # Add exception info if present
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging():
    """Configure logging based on LOG_FORMAT environment variable"""
    log_format = os.getenv("LOG_FORMAT", "simple").lower()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Remove any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)

    if log_format == "json":
        # Use JSON formatter for structured logging
        formatter = JSONFormatter()
    else:
        # Use simple format for development with extra fields support
        class SimpleFormatterWithExtras(logging.Formatter):
            def format(self, record):
                # Start with base format
                s = super().format(record)

                # Add extra fields if present
                extras = []
                # Known extra fields
                if hasattr(record, "session_id"):
                    extras.append(f"session_id={record.session_id}")
                if hasattr(record, "error"):
                    extras.append(f"error={record.error}")
                if hasattr(record, "error_type"):
                    extras.append(f"error_type={record.error_type}")
                if hasattr(record, "tracking_id"):
                    extras.append(f"tracking_id={record.tracking_id}")
                if hasattr(record, "user_message"):
                    extras.append(f"user_message={record.user_message}")
                
                # Also check for any other extra fields that were added
                # Skip standard LogRecord attributes
                standard_attrs = set(dir(logging.LogRecord('', 0, '', 0, '', (), None)))
                for key in dir(record):
                    if not key.startswith('_') and key not in standard_attrs:
                        value = getattr(record, key, None)
                        if key not in ['session_id', 'error', 'error_type', 'tracking_id', 'user_message'] and value is not None:
                            extras.append(f"{key}={value}")

                if extras:
                    s += " | " + " | ".join(extras)

                return s

        formatter = SimpleFormatterWithExtras(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d"
        )

    handler.setFormatter(formatter)

    # Configure root logger
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.addHandler(handler)

    # Also configure uvicorn's logger
    logging.getLogger("uvicorn").setLevel(getattr(logging, log_level))
    logging.getLogger("uvicorn.access").setLevel(getattr(logging, log_level))

    logger_temp = logging.getLogger(__name__)
    logger_temp.info(f"Logging configured: format={log_format}, level={log_level}")


# Setup logging before anything else
setup_logging()
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
            reload_mode = os.getenv("DEBUG", "false").lower() == "true" and not os.path.exists(
                "/app/shared"
            )

            config = uvicorn.Config(
                app,
                host=host,
                port=port,
                reload=reload_mode,
                access_log=True,
                log_level=os.getenv("LOG_LEVEL", "INFO").lower(),
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
