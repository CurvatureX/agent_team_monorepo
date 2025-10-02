import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from shared.models.execution_new import ExecutionStatus
from shared.models.node_enums import TriggerSubtype
from shared.models.trigger import TriggerStatus
from shared.models.workflow_new import WorkflowExecutionResponse
from workflow_scheduler.triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class ManualTrigger(BaseTrigger):
    """Manual trigger for user-initiated workflow execution"""

    def __init__(self, workflow_id: str, trigger_config: Dict[str, Any]):
        super().__init__(workflow_id, trigger_config)

    @property
    def trigger_type(self) -> str:
        return TriggerSubtype.MANUAL.value

    async def start(self) -> bool:
        """Start the manual trigger (just mark as active)"""
        try:
            if not self.enabled:
                logger.info(f"Manual trigger for workflow {self.workflow_id} is disabled")
                self.status = TriggerStatus.PAUSED
                return True

            self.status = TriggerStatus.ACTIVE
            logger.info(f"Manual trigger started for workflow {self.workflow_id}")

            return True

        except Exception as e:
            logger.error(
                f"Failed to start manual trigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )
            self.status = TriggerStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Stop the manual trigger"""
        try:
            self.status = TriggerStatus.STOPPED
            logger.info(f"Manual trigger stopped for workflow {self.workflow_id}")

            return True

        except Exception as e:
            logger.error(
                f"Failed to stop manual trigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )
            return False

    async def trigger_manual(
        self, user_id: str, access_token: Optional[str] = None
    ) -> WorkflowExecutionResponse:
        """
        Manually trigger workflow execution

        Args:
            user_id: ID of the user requesting the trigger

        Returns:
            ExecutionResult with execution details
        """
        try:
            if not self.enabled:
                return WorkflowExecutionResponse(
                    execution_id=f"exec_{self.workflow_id}",
                    workflow_id=self.workflow_id,
                    status=ExecutionStatus.ERROR,
                    message="Manual trigger is disabled",
                )

            if self.status != TriggerStatus.ACTIVE:
                return WorkflowExecutionResponse(
                    execution_id=f"exec_{self.workflow_id}",
                    workflow_id=self.workflow_id,
                    status=ExecutionStatus.ERROR,
                    message=f"Manual trigger is not active (status: {self.status.value})",
                )

            # Prepare trigger data
            trigger_data = {
                "trigger_type": "manual",
                "user_id": user_id,
                "triggered_at": datetime.utcnow().isoformat(),
                "execution_id": f"exec_{uuid.uuid4()}",
            }

            # Execute workflow
            result = await self._trigger_workflow(trigger_data, access_token=access_token)

            if result.status == ExecutionStatus.RUNNING:
                logger.info(
                    f"Manual trigger executed successfully for workflow {self.workflow_id} by user {user_id}: {result.execution_id}"
                )
            else:
                logger.warning(
                    f"Manual trigger execution had issues for workflow {self.workflow_id}: {result.message}"
                )

            return result

        except Exception as e:
            error_msg = f"Error in manual trigger for workflow {self.workflow_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return WorkflowExecutionResponse(
                execution_id=f"exec_{self.workflow_id}",
                workflow_id=self.workflow_id,
                status="error",
                message=error_msg,
            )

    async def health_check(self) -> Dict[str, Any]:
        """Return health status of the manual trigger"""
        base_health = await super().health_check()

        manual_health = {
            **base_health,
            "ready_for_execution": self.enabled and self.status == TriggerStatus.ACTIVE,
        }

        return manual_health
