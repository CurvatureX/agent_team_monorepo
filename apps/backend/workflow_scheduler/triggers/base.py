import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from shared.models.execution_new import ExecutionStatus
from shared.models.trigger import TriggerStatus
from shared.models.workflow import WorkflowExecutionResponse
from workflow_scheduler.core.config import settings
from workflow_scheduler.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Note: We now use the actual workflow owner's user_id from the database


class BaseTrigger(ABC):
    """Base class for all trigger types"""

    def __init__(self, workflow_id: str, trigger_config: Dict[str, Any]):
        # Coerce workflow_id to string to avoid UUID-type leakage into responses
        self.workflow_id = str(workflow_id)
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
        self, trigger_data: Optional[Dict[str, Any]] = None, access_token: Optional[str] = None
    ) -> WorkflowExecutionResponse:
        """
        Trigger workflow execution by calling workflow_engine HTTP API
        """
        if not self.enabled:
            logger.warning(
                f"Trigger {self.trigger_type} for workflow {self.workflow_id} is disabled"
            )
            return WorkflowExecutionResponse(
                execution_id=f"exec_{self.workflow_id}",
                workflow_id=self.workflow_id,
                status=ExecutionStatus.SKIPPED,
                message="Trigger is disabled",
            )

        # Smart trigger detection: Check if this should resume a paused workflow
        resume_check = await self._check_for_resume_opportunity(trigger_data)
        if resume_check["should_resume"]:
            return await self._resume_paused_workflow(resume_check["execution_id"], trigger_data)

        # Otherwise, start new execution
        execution_id = f"exec_{uuid.uuid4()}"

        try:
            # Execute workflow
            execution_result = await self._execute_workflow(
                execution_id, trigger_data, access_token
            )
            return execution_result

        except Exception as e:
            error_msg = f"Error triggering workflow: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return WorkflowExecutionResponse(
                workflow_id=self.workflow_id,
                execution_id=execution_id,
                status=ExecutionStatus.ERROR,
                message=error_msg,
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
        self,
        execution_id: str,
        trigger_data: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None,
    ) -> WorkflowExecutionResponse:
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
                return WorkflowExecutionResponse(
                    workflow_id=self.workflow_id,
                    execution_id=execution_id,
                    status=ExecutionStatus.ERROR,
                    message="Could not determine workflow owner",
                )

            # Prepare execution payload matching ExecuteWorkflowRequest format
            payload = {
                "workflow_id": str(self.workflow_id),
                "trigger_data": formatted_trigger_data,
                "user_id": workflow_owner_id,  # Use actual workflow owner
            }

            # Call workflow_engine execute endpoint (v2 API)
            engine_url = f"{settings.workflow_engine_url}/v2/workflows/{self.workflow_id}/execute"

            logger.info(
                f"🚀 Triggering workflow {self.workflow_id} via {engine_url} (immediate execution)"
            )

            # Prepare headers with JWT token if available
            headers = {"Content-Type": "application/json"}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
                logger.info(
                    f"🔐 Forwarding JWT token to workflow engine for execution: {execution_id}"
                )

            # Execute workflow and wait for actual execution_id
            response = await self._client.post(engine_url, json=payload, headers=headers)

            if response.status_code in [200, 202]:  # OK or Accepted
                result_data = response.json()
                actual_execution_id = result_data.get("execution_id", execution_id)

                logger.info(
                    f"✅ Workflow {self.workflow_id} execution started successfully: {actual_execution_id}"
                )

                return WorkflowExecutionResponse(
                    workflow_id=self.workflow_id,
                    execution_id=actual_execution_id,
                    status=ExecutionStatus.RUNNING,
                    message="Workflow execution started successfully",
                )
            else:
                error_msg = (
                    f"Workflow execution failed: HTTP {response.status_code} - {response.text}"
                )
                logger.error(error_msg)
                return WorkflowExecutionResponse(
                    workflow_id=self.workflow_id,
                    execution_id=execution_id,
                    status=ExecutionStatus.ERROR,
                    message=error_msg,
                )

        except Exception as e:
            error_msg = f"Error calling workflow engine: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return WorkflowExecutionResponse(
                workflow_id=self.workflow_id,
                execution_id=execution_id,
                status=ExecutionStatus.ERROR,
                message=error_msg,
            )

    async def _execute_workflow_async(
        self,
        engine_url: str,
        payload: dict,
        execution_id: str,
        trigger_data: dict,
        access_token: Optional[str] = None,
    ):
        """
        Execute workflow asynchronously in the background (fire-and-forget)
        This method handles the actual HTTP call to the workflow engine without blocking the trigger
        """
        try:
            logger.info(
                f"🔄 Starting async workflow execution for {self.workflow_id}: {execution_id}"
            )

            # Prepare headers with JWT token if available
            headers = {"Content-Type": "application/json"}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
                logger.info(
                    f"🔐 Forwarding JWT token to workflow engine for execution: {execution_id}"
                )

            response = await self._client.post(engine_url, json=payload, headers=headers)

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

    async def _check_for_resume_opportunity(
        self, trigger_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check if this trigger should resume a paused workflow instead of starting new one.

        Returns:
            Dict with 'should_resume' boolean and 'execution_id' if applicable
        """
        try:
            # Query workflow engine for paused executions of this workflow (v2 API)
            engine_url = (
                f"{settings.workflow_engine_url}/v2/workflows/{self.workflow_id}/executions"
            )

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(engine_url)

                if response.status_code == 200:
                    executions = response.json()

                    # Filter for paused executions
                    paused_executions = [
                        exec_data
                        for exec_data in executions
                        if exec_data.get("status") == ExecutionStatus.PAUSED.value
                    ]

                    if paused_executions:
                        # Try to find the most relevant paused execution
                        # For HIL scenarios, prefer executions paused recently
                        most_recent = max(paused_executions, key=lambda x: x.get("started_at", 0))

                        # TODO: Enhanced matching logic could consider:
                        # - Channel/thread context for Slack HIL
                        # - User context for user-specific HIL
                        # - Interaction type for specialized HIL flows

                        execution_id = most_recent.get("execution_id")
                        logger.info(
                            f"🔄 Found paused execution {execution_id} for workflow {self.workflow_id} - will resume instead of starting new"
                        )

                        return {
                            "should_resume": True,
                            "execution_id": execution_id,
                            "paused_execution": most_recent,
                        }

                    return {"should_resume": False, "execution_id": None}
                else:
                    logger.warning(
                        f"Failed to check paused executions: HTTP {response.status_code}"
                    )
                    # If we can't check, start new execution (fail-open)
                    return {"should_resume": False, "execution_id": None}

        except Exception as e:
            logger.warning(f"Error checking for resume opportunity: {e}")
            # If we can't check, start new execution (fail-open)
            return {"should_resume": False, "execution_id": None}

    async def _resume_paused_workflow(
        self, execution_id: str, trigger_data: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecutionResponse:
        """
        Resume a paused workflow with trigger data as resume data.
        """
        try:
            logger.info(f"🔄 Resuming paused workflow execution {execution_id} with trigger data")

            # Call workflow_engine resume endpoint (v2 API)
            engine_url = f"{settings.workflow_engine_url}/v2/executions/{execution_id}/resume"

            # Format trigger data as resume data
            resume_payload = {
                "resume_data": trigger_data or {},
                "interaction_id": trigger_data.get("interaction_id") if trigger_data else None,
            }

            response = await self._client.post(
                engine_url, json=resume_payload, headers={"Content-Type": "application/json"}
            )

            if response.status_code in [200, 202]:  # OK or Accepted
                result_data = response.json()
                logger.info(f"✅ Successfully resumed workflow execution {execution_id}")

                return WorkflowExecutionResponse(
                    workflow_id=self.workflow_id,
                    execution_id=execution_id,
                    status=ExecutionStatus.RUNNING,
                    message=f"Resumed paused workflow: {result_data.get('message', 'Success')}",
                )
            else:
                error_msg = f"Resume failed: HTTP {response.status_code} - {response.text}"
                logger.error(error_msg)
                return WorkflowExecutionResponse(
                    workflow_id=self.workflow_id,
                    execution_id=execution_id,
                    status=ExecutionStatus.ERROR,
                    message=error_msg,
                )

        except Exception as e:
            error_msg = f"Error resuming workflow: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return WorkflowExecutionResponse(
                workflow_id=self.workflow_id,
                execution_id=execution_id,
                status=ExecutionStatus.ERROR,
                message=error_msg,
            )

    async def health_check(self) -> Dict[str, Any]:
        """Return health status of the trigger"""
        return {
            "trigger_type": self.trigger_type,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "enabled": self.enabled,
            "last_check": datetime.utcnow().isoformat(),
        }
