import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from shared.models.trigger import ExecutionResult, TriggerStatus
from workflow_scheduler.core.config import settings

logger = logging.getLogger(__name__)


class BaseTrigger(ABC):
    """Base class for all trigger types"""

    def __init__(self, workflow_id: str, trigger_config: Dict[str, Any]):
        self.workflow_id = workflow_id
        self.config = trigger_config
        self.enabled = trigger_config.get("enabled", True)
        self.status = TriggerStatus.PENDING
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    @abstractmethod
    def trigger_type(self) -> str:
        """Return the trigger type identifier"""
        pass

    @abstractmethod
    async def start(self) -> bool:
        """Start the trigger (setup monitoring, scheduling, etc.)"""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Stop the trigger (cleanup resources)"""
        pass

    async def cleanup(self) -> None:
        """Cleanup resources"""
        if hasattr(self, "_client"):
            await self._client.aclose()

    async def _trigger_workflow(
        self, trigger_data: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Trigger workflow execution by calling workflow_engine HTTP API
        """
        if not self.enabled:
            logger.warning(
                f"Trigger {self.trigger_type} for workflow {self.workflow_id} is disabled"
            )
            return ExecutionResult(
                status="skipped",
                message="Trigger is disabled",
                trigger_data=trigger_data or {},
            )

        execution_id = f"exec_{uuid.uuid4()}"

        try:
            # Execute workflow
            execution_result = await self._execute_workflow(execution_id, trigger_data)
            return execution_result

        except Exception as e:
            error_msg = f"Error triggering workflow: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return ExecutionResult(
                execution_id=execution_id,
                status="error",
                message=error_msg,
                trigger_data=trigger_data or {},
            )

    async def _execute_workflow(
        self, execution_id: str, trigger_data: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute workflow by calling workflow_engine HTTP API
        """
        try:
            # Convert trigger_data to string format as expected by workflow engine
            formatted_trigger_data = {}
            if trigger_data:
                for key, value in trigger_data.items():
                    formatted_trigger_data[key] = str(value) if value is not None else ""

            # Add trigger metadata
            formatted_trigger_data.update(
                {
                    "trigger_type": str(self.trigger_type),
                    "execution_id": execution_id,
                    "triggered_at": datetime.utcnow().isoformat(),
                }
            )

            # Prepare execution payload matching ExecuteWorkflowRequest format
            payload = {
                "workflow_id": str(self.workflow_id),
                "trigger_data": formatted_trigger_data,
                "user_id": "system",  # System-triggered execution
            }

            # Call workflow_engine execute endpoint
            engine_url = f"{settings.workflow_engine_url}/v1/workflows/{self.workflow_id}/execute"

            logger.info(f"🚀 Triggering workflow {self.workflow_id} via {engine_url}")

            response = await self._client.post(
                engine_url, json=payload, headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:  # OK (FastAPI default for successful POST)
                result_data = response.json()
                actual_execution_id = result_data.get("execution_id", execution_id)
                logger.info(
                    f"✅ Workflow {self.workflow_id} execution started: {actual_execution_id}"
                )

                return ExecutionResult(
                    execution_id=actual_execution_id,
                    status="started",
                    message=result_data.get("message", "Workflow execution started successfully"),
                    trigger_data=trigger_data or {},
                )
            elif response.status_code == 202:  # Also accept 202 Accepted
                result_data = response.json()
                actual_execution_id = result_data.get("execution_id", execution_id)
                logger.info(
                    f"✅ Workflow {self.workflow_id} execution accepted: {actual_execution_id}"
                )

                return ExecutionResult(
                    execution_id=actual_execution_id,
                    status="started",
                    message=result_data.get("message", "Workflow execution accepted"),
                    trigger_data=trigger_data or {},
                )
            else:
                error_msg = f"Failed to trigger workflow: HTTP {response.status_code}"
                logger.error(f"{error_msg}: {response.text}")

                return ExecutionResult(
                    execution_id=execution_id,
                    status="failed",
                    message=error_msg,
                    trigger_data=trigger_data or {},
                )

        except Exception as e:
            error_msg = f"Error calling workflow engine: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return ExecutionResult(
                execution_id=execution_id,
                status="error",
                message=error_msg,
                trigger_data=trigger_data or {},
            )

    def _calculate_jitter(self, workflow_id: str) -> float:
        """
        Calculate jitter to distribute execution across time
        Uses hash-based jitter to ensure consistent but distributed timing
        """
        import hashlib

        # Create hash from workflow_id to ensure consistent jitter
        hash_value = int(hashlib.md5(workflow_id.encode()).hexdigest()[:8], 16)

        # Convert to float between 0 and 30 seconds
        jitter = (hash_value % 30000) / 1000.0

        return jitter

    async def health_check(self) -> Dict[str, Any]:
        """Return health status of the trigger"""
        return {
            "trigger_type": self.trigger_type,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "enabled": self.enabled,
            "last_check": datetime.utcnow().isoformat(),
        }
