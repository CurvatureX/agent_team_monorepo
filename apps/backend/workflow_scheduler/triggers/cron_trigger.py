import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger as APCronTrigger

from shared.models.execution_new import ExecutionStatus
from shared.models.node_enums import TriggerSubtype
from shared.models.trigger import TriggerStatus
from workflow_scheduler.triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class CronTrigger(BaseTrigger):
    """Cron-based trigger using APScheduler"""

    def __init__(self, workflow_id: str, trigger_config: Dict[str, Any]):
        super().__init__(workflow_id, trigger_config)

        self.cron_expression = trigger_config.get("cron_expression")
        self.timezone = trigger_config.get("timezone", "UTC")
        self.lock_manager = trigger_config.get("lock_manager")

        if not self.cron_expression:
            raise ValueError("cron_expression is required for CronTrigger")

        # Validate timezone
        try:
            pytz.timezone(self.timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone {self.timezone}, using UTC")
            self.timezone = "UTC"

        # Initialize scheduler
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.job_id = f"cron_{self.workflow_id}"

    @property
    def trigger_type(self) -> str:
        return TriggerSubtype.CRON.value

    async def start(self) -> bool:
        """Start the cron trigger by scheduling the job"""
        try:
            if not self.enabled:
                logger.info(f"Cron trigger for workflow {self.workflow_id} is disabled")
                self.status = TriggerStatus.PAUSED
                return True

            # Create scheduler if not exists
            if not self.scheduler:
                self.scheduler = AsyncIOScheduler(timezone=self.timezone)
                self.scheduler.start()

            # Parse cron expression and create trigger
            try:
                # Handle different cron formats
                cron_parts = self.cron_expression.strip().split()

                if len(cron_parts) == 5:
                    # Standard cron: minute hour day month day_of_week
                    minute, hour, day, month, day_of_week = cron_parts
                elif len(cron_parts) == 6:
                    # With seconds: second minute hour day month day_of_week
                    second, minute, hour, day, month, day_of_week = cron_parts
                else:
                    raise ValueError(f"Invalid cron expression format: {self.cron_expression}")

                # Create APScheduler cron trigger
                if len(cron_parts) == 5:
                    cron_trigger = APCronTrigger(
                        minute=minute,
                        hour=hour,
                        day=day,
                        month=month,
                        day_of_week=day_of_week,
                        timezone=self.timezone,
                    )
                else:
                    cron_trigger = APCronTrigger(
                        second=second,
                        minute=minute,
                        hour=hour,
                        day=day,
                        month=month,
                        day_of_week=day_of_week,
                        timezone=self.timezone,
                    )

            except Exception as e:
                logger.error(f"Invalid cron expression {self.cron_expression}: {e}")
                self.status = TriggerStatus.ERROR
                return False

            # Add job to scheduler
            self.scheduler.add_job(
                func=self._execute_with_jitter,
                trigger=cron_trigger,
                id=self.job_id,
                replace_existing=True,
                max_instances=1,  # Prevent overlapping executions
            )

            self.status = TriggerStatus.ACTIVE
            logger.info(
                f"Cron trigger started for workflow {self.workflow_id}: {self.cron_expression}"
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to start cron trigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )
            self.status = TriggerStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Stop the cron trigger"""
        try:
            if self.scheduler and self.scheduler.running:
                # Remove the specific job
                try:
                    self.scheduler.remove_job(self.job_id)
                except Exception:
                    pass  # Job might not exist

                # Only shutdown if this is the last job
                if len(self.scheduler.get_jobs()) == 0:
                    self.scheduler.shutdown(wait=False)
                    self.scheduler = None

            self.status = TriggerStatus.STOPPED
            logger.info(f"Cron trigger stopped for workflow {self.workflow_id}")

            return True

        except Exception as e:
            logger.error(
                f"Failed to stop cron trigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )
            return False

    async def _execute_with_jitter(self) -> None:
        """Execute trigger with jitter to prevent thundering herd"""
        try:
            # Calculate jitter based on workflow ID for consistency
            jitter = self._calculate_jitter(self.workflow_id)

            logger.debug(
                f"Cron trigger for workflow {self.workflow_id} sleeping for {jitter}s jitter"
            )
            await asyncio.sleep(jitter)

            # Use distributed lock to prevent duplicate executions
            if not self.lock_manager:
                logger.warning(
                    f"No lock manager available for workflow {self.workflow_id}, executing without lock"
                )
                await self._execute_cron()
                return

            lock_key = f"workflow_{self.workflow_id}"

            async with self.lock_manager.acquire(lock_key) as acquired:
                if acquired:
                    logger.info(
                        f"Lock acquired for workflow {self.workflow_id}, executing cron trigger"
                    )
                    await self._execute_cron()
                else:
                    logger.info(
                        f"Could not acquire lock for workflow {self.workflow_id}, skipping execution (likely already running)"
                    )

        except Exception as e:
            logger.error(
                f"Error in cron execution for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )

    async def _execute_cron(self) -> None:
        """Execute the actual cron trigger"""
        try:
            trigger_data = {
                "trigger_type": self.trigger_type,
                "cron_expression": self.cron_expression,
                "scheduled_time": datetime.now(pytz.timezone(self.timezone)).isoformat(),
                "timezone": self.timezone,
            }

            result = await self._trigger_workflow(trigger_data)

            if result.status == ExecutionStatus.RUNNING:
                logger.info(
                    f"Cron trigger executed successfully for workflow {self.workflow_id}: {result.execution_id}"
                )
            else:
                logger.warning(
                    f"Cron trigger execution had issues for workflow {self.workflow_id}: {result.message}"
                )

        except Exception as e:
            logger.error(
                f"Error executing cron trigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )

    async def health_check(self) -> Dict[str, Any]:
        """Return health status of the cron trigger"""
        base_health = await super().health_check()

        cron_health = {
            **base_health,
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "scheduler_running": self.scheduler.running if self.scheduler else False,
            "job_exists": False,
        }

        # Check if job exists in scheduler
        if self.scheduler:
            try:
                job = self.scheduler.get_job(self.job_id)
                cron_health["job_exists"] = job is not None
                if job:
                    cron_health["next_run_time"] = (
                        job.next_run_time.isoformat() if job.next_run_time else None
                    )
            except Exception:
                pass

        return cron_health
