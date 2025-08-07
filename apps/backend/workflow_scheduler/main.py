import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.models.trigger import TriggerType
from workflow_scheduler.api import deployment, github, slack, triggers
from workflow_scheduler.core.config import settings
from workflow_scheduler.dependencies import (
    get_lock_manager,
    get_trigger_manager,
    set_global_services,
)
from workflow_scheduler.services.deployment_service import DeploymentService
from workflow_scheduler.services.lock_manager import DistributedLockManager
from workflow_scheduler.services.trigger_manager import TriggerManager
from workflow_scheduler.triggers.cron_trigger import CronTrigger
from workflow_scheduler.triggers.email_trigger import EmailTrigger
from workflow_scheduler.triggers.github_trigger import GitHubTrigger
from workflow_scheduler.triggers.manual_trigger import ManualTrigger
from workflow_scheduler.triggers.slack_trigger import SlackTrigger
from workflow_scheduler.triggers.webhook_trigger import WebhookTrigger

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if settings.log_format == "text"
    else "%(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Global service instances will be managed through dependencies.py


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    # Initialize variables outside try block to ensure they're accessible in finally
    lock_manager = None
    trigger_manager = None
    deployment_service = None

    logger.info("Starting workflow_scheduler service")
    logger.info(f"Redis URL configured: {settings.redis_url}")

    try:
        # Initialize distributed lock manager
        lock_manager = DistributedLockManager()
        await lock_manager.initialize()

        # Initialize trigger manager
        trigger_manager = TriggerManager(lock_manager)

        # Register trigger classes
        trigger_manager.register_trigger_class(TriggerType.CRON, CronTrigger)
        trigger_manager.register_trigger_class(TriggerType.MANUAL, ManualTrigger)
        trigger_manager.register_trigger_class(TriggerType.WEBHOOK, WebhookTrigger)
        trigger_manager.register_trigger_class(TriggerType.EMAIL, EmailTrigger)
        trigger_manager.register_trigger_class(TriggerType.GITHUB, GitHubTrigger)
        trigger_manager.register_trigger_class(TriggerType.SLACK, SlackTrigger)

        # Initialize deployment service
        deployment_service = DeploymentService(trigger_manager)

        # Set global services for dependency injection
        set_global_services(deployment_service, trigger_manager, lock_manager)

        logger.info("workflow_scheduler service started successfully")

        yield

    except Exception as e:
        logger.error(f"Failed to start workflow_scheduler service: {e}", exc_info=True)
        raise

    finally:
        # Cleanup
        logger.info("Shutting down workflow_scheduler service")

        if trigger_manager:
            await trigger_manager.cleanup()

        if lock_manager:
            await lock_manager.cleanup()

        logger.info("workflow_scheduler service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Workflow Scheduler Service",
    description="Trigger Management and Scheduling for Workflows",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependencies are now managed through dependencies.py

# Include routers
app.include_router(deployment.router, prefix="/api/v1")
app.include_router(triggers.router, prefix="/api/v1")
app.include_router(github.router, prefix="/api/v1")
app.include_router(slack.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "workflow_scheduler", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        health_status = {
            "service": "workflow_scheduler",
            "status": "healthy",
            "version": "0.1.0",
            "components": {},
        }

        # Check lock manager
        try:
            lock_manager = get_lock_manager()
            if lock_manager:
                try:
                    # Simple Redis ping
                    await lock_manager._redis.ping()
                    health_status["components"]["lock_manager"] = "healthy"
                except Exception as e:
                    health_status["components"]["lock_manager"] = f"unhealthy: {str(e)}"
                    health_status["status"] = "degraded"
            else:
                health_status["components"]["lock_manager"] = "not_initialized"
                health_status["status"] = "unhealthy"
        except Exception:
            health_status["components"]["lock_manager"] = "not_available"
            health_status["status"] = "unhealthy"

        # Check trigger manager
        try:
            trigger_manager = get_trigger_manager()
            if trigger_manager:
                trigger_health = await trigger_manager.health_check()
                health_status["components"]["trigger_manager"] = trigger_health
            else:
                health_status["components"]["trigger_manager"] = "not_initialized"
                health_status["status"] = "unhealthy"
        except Exception:
            health_status["components"]["trigger_manager"] = "not_available"
            health_status["status"] = "unhealthy"

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {"service": "workflow_scheduler", "status": "unhealthy", "error": str(e)}


@app.get("/metrics")
async def get_metrics():
    """Metrics endpoint for monitoring"""
    try:
        metrics = {
            "service": "workflow_scheduler",
            "uptime": "unknown",  # TODO: Track uptime
            "total_workflows": 0,
            "total_triggers": 0,
            "trigger_types": {},
        }

        try:
            trigger_manager = get_trigger_manager()
            if trigger_manager:
                health_data = await trigger_manager.health_check()
                metrics["total_workflows"] = health_data.get("total_workflows", 0)
                metrics["total_triggers"] = health_data.get("total_triggers", 0)

                # Count trigger types
                for workflow_data in health_data.get("workflows", {}).values():
                    for trigger_type in workflow_data.get("triggers", {}).keys():
                        metrics["trigger_types"][trigger_type] = (
                            metrics["trigger_types"].get(trigger_type, 0) + 1
                        )
        except Exception:
            pass  # Use default values

        return metrics

    except Exception as e:
        logger.error(f"Metrics collection failed: {e}", exc_info=True)
        return {"error": str(e)}


def main():
    """Main entry point"""
    uvicorn.run(
        "workflow_scheduler.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
