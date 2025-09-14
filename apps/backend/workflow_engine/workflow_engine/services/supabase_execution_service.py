"""
Supabase-based Execution Service - 工作流执行服务.

This module implements workflow execution-related operations using Supabase SDK.
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add backend directory to Python path for shared models
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import (
    ExecuteSingleNodeRequest,
    ExecuteWorkflowRequest,
    Execution,
    ExecutionStatus,
    SingleNodeExecutionResponse,
)

from ..core.config import get_settings
from ..execution_engine import WorkflowExecutionEngine
from .supabase_repository import SupabaseWorkflowRepository
from .supabase_workflow_service import SupabaseWorkflowService

logger = logging.getLogger(__name__)
settings = get_settings()


class SupabaseExecutionService:
    """Service for workflow execution operations using Supabase SDK."""

    def __init__(self, access_token: Optional[str] = None):
        self.logger = logger
        self.repository = SupabaseWorkflowRepository(access_token)
        self.execution_engine = WorkflowExecutionEngine()
        self.workflow_service = SupabaseWorkflowService(access_token)

    async def execute_workflow(self, request: ExecuteWorkflowRequest) -> str:
        """Execute a workflow and return the execution ID immediately using Supabase."""
        execution_id = str(uuid.uuid4())

        try:
            self.logger.info(f"🆔 Generated execution ID: {execution_id}")

            # Create minimal execution record
            now = datetime.now()
            trigger_source = request.trigger_data.get("trigger_source", "manual").lower()

            execution_data = {
                "id": execution_id,
                "workflow_id": request.workflow_id,
                "user_id": request.user_id,
                "status": ExecutionStatus.PENDING.value,
                "trigger_source": trigger_source,
                "trigger_data": request.trigger_data or {},
                "execution_data": {},
                "result_data": {},
                "error_data": {},
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "started_at": None,
                "completed_at": None,
            }

            # Create execution record in Supabase
            created_execution = await self.repository.create_execution(execution_data)

            if not created_execution:
                raise ValueError("Failed to create execution record")

            # Start asynchronous execution (similar to original implementation)
            # Note: In production, this would typically be handled by a background task queue
            self.logger.info(f"🚀 Starting background execution for {execution_id}")

            # Update execution status to running
            await self.repository.update_execution(
                execution_id,
                {
                    "status": ExecutionStatus.RUNNING.value,
                    "started_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                },
            )

            # Here you would typically queue the actual execution
            # For now, we'll just return the execution ID

            return execution_id

        except Exception as e:
            self.logger.error(f"Error starting workflow execution: {e}")

            # Update execution with error status if it was created
            try:
                await self.repository.update_execution(
                    execution_id,
                    {
                        "status": ExecutionStatus.FAILED.value,
                        "error_data": {"error": str(e)},
                        "completed_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                    },
                )
            except:
                pass  # Ignore errors in error handling

            raise

    async def get_execution_status(self, execution_id: str) -> Optional[Execution]:
        """Get execution status using Supabase."""
        try:
            execution_dict = await self.repository.get_execution(execution_id)

            if not execution_dict:
                return None

            return self._dict_to_execution(execution_dict)

        except Exception as e:
            self.logger.error(f"Error getting execution status {execution_id}: {e}")
            return None

    async def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Execution]:
        """List executions using Supabase."""
        try:
            executions, _ = await self.repository.list_executions(
                workflow_id=workflow_id, status_filter=status_filter, limit=limit, offset=offset
            )

            return [self._dict_to_execution(execution) for execution in executions]

        except Exception as e:
            self.logger.error(f"Error listing executions: {e}")
            return []

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution using Supabase."""
        try:
            # Update execution status to cancelled
            updated_execution = await self.repository.update_execution(
                execution_id,
                {
                    "status": ExecutionStatus.CANCELLED.value,
                    "completed_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                },
            )

            if updated_execution:
                self.logger.info(f"✅ Cancelled execution {execution_id}")
                return True
            else:
                self.logger.error(f"❌ Failed to cancel execution {execution_id} - not found")
                return False

        except Exception as e:
            self.logger.error(f"Error cancelling execution {execution_id}: {e}")
            return False

    async def update_execution_status(
        self,
        execution_id: str,
        status: ExecutionStatus,
        result_data: Optional[dict] = None,
        error_data: Optional[dict] = None,
    ) -> bool:
        """Update execution status and data using Supabase."""
        try:
            update_data = {"status": status.value, "updated_at": datetime.now().isoformat()}

            if result_data:
                update_data["result_data"] = result_data

            if error_data:
                update_data["error_data"] = error_data

            if status in [
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
            ]:
                update_data["completed_at"] = datetime.now().isoformat()

            updated_execution = await self.repository.update_execution(execution_id, update_data)

            return updated_execution is not None

        except Exception as e:
            self.logger.error(f"Error updating execution status {execution_id}: {e}")
            return False

    async def execute_single_node(
        self, request: ExecuteSingleNodeRequest
    ) -> SingleNodeExecutionResponse:
        """Execute a single node using Supabase for workflow access."""
        try:
            self.logger.info(
                f"Executing single node {request.node_id} from workflow {request.workflow_id}"
            )

            # Get workflow data from Supabase
            workflow = await self.workflow_service.get_workflow_by_id(request.workflow_id)

            if not workflow:
                return SingleNodeExecutionResponse(
                    success=False,
                    error=f"Workflow {request.workflow_id} not found",
                    node_id=request.node_id,
                    execution_id=None,
                    result_data={},
                )

            # Find the specific node
            target_node = None
            for node in workflow.nodes:
                if node.id == request.node_id:
                    target_node = node
                    break

            if not target_node:
                return SingleNodeExecutionResponse(
                    success=False,
                    error=f"Node {request.node_id} not found in workflow",
                    node_id=request.node_id,
                    execution_id=None,
                    result_data={},
                )

            # Create execution context and execute node
            from ..execution_engine.node_execution_context import NodeExecutionContext

            context = NodeExecutionContext(
                node_id=target_node.id,
                workflow_id=request.workflow_id,
                execution_id=str(uuid.uuid4()),
                parameters=request.input_data or {},
                workflow_context={},
                user_credentials={},
            )

            # Execute the node using the execution engine
            result = await self.execution_engine.execute_single_node(target_node, context)

            return SingleNodeExecutionResponse(
                success=result.status == "success",
                error=result.error_message if result.status == "error" else None,
                node_id=request.node_id,
                execution_id=context.execution_id,
                result_data=result.output_data or {},
            )

        except Exception as e:
            self.logger.error(f"Error executing single node: {e}")
            return SingleNodeExecutionResponse(
                success=False,
                error=str(e),
                node_id=request.node_id,
                execution_id=None,
                result_data={},
            )

    def _dict_to_execution(self, execution_dict: dict) -> Execution:
        """Convert dictionary from Supabase to Execution object."""
        return Execution(
            id=execution_dict["id"],
            execution_id=execution_dict["execution_id"],
            workflow_id=execution_dict["workflow_id"],
            status=ExecutionStatus(execution_dict["status"]),
            mode=execution_dict.get("mode"),
            triggered_by=execution_dict.get("triggered_by"),
            start_time=execution_dict.get("start_time"),
            end_time=execution_dict.get("end_time"),
            run_data=execution_dict.get("run_data", {}),
            metadata=execution_dict.get("metadata", {}),
            execution_metadata=execution_dict.get("execution_metadata", {}),
            error_message=execution_dict.get("error_message"),
            error_details=execution_dict.get("error_details", {}),
            created_at=execution_dict.get("created_at"),
            updated_at=execution_dict.get("updated_at"),
        )
