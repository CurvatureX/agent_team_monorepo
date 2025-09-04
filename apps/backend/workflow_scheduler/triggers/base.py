import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from shared.models.trigger import ExecutionResult, TriggerStatus
from workflow_scheduler.core.config import settings
from workflow_scheduler.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Note: We now use the actual workflow owner's user_id from the database


class BaseTrigger(ABC):
    """Base class for all trigger types"""

    def __init__(self, workflow_id: str, trigger_config: Dict[str, Any]):
        self.workflow_id = workflow_id
        self.config = trigger_config
        self.enabled = trigger_config.get("enabled", True)
        self.status = TriggerStatus.PENDING
        self._client = httpx.AsyncClient(timeout=7200.0)  # 2 hours for human-in-the-loop nodes

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

    async def _get_workflow_owner_id(self, workflow_id: str) -> Optional[str]:
        """
        Get the workflow owner's user_id from the database
        """
        try:
            supabase = get_supabase_client()
            if not supabase:
                logger.error("Supabase client not available")
                return None

            response = supabase.table("workflows").select("user_id").eq("id", workflow_id).execute()

            if response.data and len(response.data) > 0:
                user_id = response.data[0].get("user_id")
                logger.info(f"Found workflow owner: {user_id} for workflow {workflow_id}")
                return str(user_id) if user_id else None
            else:
                logger.warning(f"Workflow {workflow_id} not found in database")
                return None

        except Exception as e:
            logger.error(f"Error fetching workflow owner for {workflow_id}: {e}", exc_info=True)
            return None

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

            # Get the workflow owner's user_id
            workflow_owner_id = await self._get_workflow_owner_id(str(self.workflow_id))
            if not workflow_owner_id:
                logger.error(f"Could not determine workflow owner for {self.workflow_id}")
                return ExecutionResult(
                    execution_id=execution_id,
                    status="error",
                    message="Could not determine workflow owner",
                    trigger_data=trigger_data or {},
                )

            # Prepare execution payload matching ExecuteWorkflowRequest format
            payload = {
                "workflow_id": str(self.workflow_id),
                "trigger_data": formatted_trigger_data,
                "user_id": workflow_owner_id,  # Use actual workflow owner
            }

            # Call workflow_engine execute endpoint
            engine_url = f"{settings.workflow_engine_url}/v1/workflows/{self.workflow_id}/execute"

            logger.info(
                f"🚀 Triggering workflow {self.workflow_id} via {engine_url} (async execution)"
            )

            # Fire-and-forget execution - don't wait for completion, especially for human-in-the-loop workflows
            asyncio.create_task(
                self._execute_workflow_async(engine_url, payload, execution_id, trigger_data)
            )

            logger.info(
                f"✅ Workflow {self.workflow_id} execution started asynchronously: {execution_id}"
            )

            return ExecutionResult(
                execution_id=execution_id,
                status="started",
                message="Workflow execution started asynchronously",
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

    async def _execute_workflow_async(
        self, engine_url: str, payload: dict, execution_id: str, trigger_data: dict
    ):
        """
        Execute workflow asynchronously in the background (fire-and-forget)
        This method handles the actual HTTP call to the workflow engine without blocking the trigger
        """
        try:
            logger.info(
                f"🔄 Starting async workflow execution for {self.workflow_id}: {execution_id}"
            )

            response = await self._client.post(
                engine_url, json=payload, headers={"Content-Type": "application/json"}
            )

            if response.status_code in [200, 202]:  # OK or Accepted
                result_data = response.json()
                actual_execution_id = result_data.get("execution_id", execution_id)
                logger.info(
                    f"✅ Async workflow {self.workflow_id} execution successful: {actual_execution_id}"
                )
            else:
                error_msg = f"Async workflow execution failed: HTTP {response.status_code}"
                logger.error(f"{error_msg}: {response.text}")

        except Exception as e:
            error_msg = f"Error in async workflow execution: {str(e)}"
            logger.error(f"❌ Async workflow {self.workflow_id} failed: {error_msg}", exc_info=True)

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
