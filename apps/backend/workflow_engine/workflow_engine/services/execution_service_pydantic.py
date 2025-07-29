"""
Execution Service using Pydantic models for FastAPI endpoints.
Handles workflow execution operations using HTTP/JSON instead of gRPC.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from workflow_engine.workflow_engine.core.config import get_settings
from workflow_engine.workflow_engine.models.database import get_db
from workflow_engine.workflow_engine.models.execution import (
    ExecutionData,
    ExecutionStatus,
    NodeExecutionData,
    NodeExecutionStatus,
)
from workflow_engine.workflow_engine.models.requests import (
    CancelExecutionRequest,
    ExecuteWorkflowRequest,
    GetExecutionHistoryRequest,
    GetExecutionStatusRequest,
)
from workflow_engine.workflow_engine.models.responses import (
    CancelExecutionResponse,
    ExecuteWorkflowResponse,
    GetExecutionHistoryResponse,
    GetExecutionStatusResponse,
)
from workflow_engine.workflow_engine.services.workflow_service_pydantic import WorkflowService
from workflow_engine.workflow_engine.utils.converters import ExecutionConverter

logger = logging.getLogger(__name__)
settings = get_settings()


class ExecutionService:
    """Service for workflow execution operations using Pydantic models."""

    def __init__(self):
        self.logger = logger
        self.workflow_service = WorkflowService()
        self.active_executions: Dict[str, ExecutionData] = {}  # In-memory tracking

    async def execute_workflow(self, request: ExecuteWorkflowRequest) -> ExecuteWorkflowResponse:
        """Execute a workflow."""
        try:
            self.logger.info(
                f"Executing workflow: {request.workflow_id} for user: {request.user_id}"
            )

            # Get the workflow
            workflow = await self.workflow_service.get_workflow_by_id_internal(
                request.workflow_id, request.user_id
            )

            if not workflow:
                raise ValueError("Workflow not found")

            if not workflow.active:
                raise ValueError("Workflow is not active")

            # Create execution record
            execution_data = ExecutionConverter.create_execution_data(
                workflow_id=request.workflow_id,
                workflow_name=workflow.name,
                user_id=request.user_id,
                trigger_type="manual",
                input_data=request.input_data,
            )

            # Set execution context from request
            execution_data.execution_context.update(request.execution_options)
            execution_data.total_nodes = len(workflow.nodes)

            # Store in active executions
            self.active_executions[execution_data.id] = execution_data

            # Start async execution (fire and forget)
            asyncio.create_task(self._execute_workflow_async(execution_data, workflow))

            self.logger.info(f"Workflow execution started: {execution_data.id}")

            return ExecuteWorkflowResponse(
                execution_id=execution_data.id,
                workflow_id=execution_data.workflow_id,
                status=execution_data.status,
                message="Workflow execution started",
                started_at=execution_data.started_at,
            )

        except ValueError as e:
            self.logger.error(f"Validation error executing workflow: {str(e)}")
            raise e
        except Exception as e:
            self.logger.error(f"Error executing workflow: {str(e)}")
            raise Exception(f"Failed to execute workflow: {str(e)}")

    async def get_execution_status(
        self, request: GetExecutionStatusRequest
    ) -> GetExecutionStatusResponse:
        """Get execution status."""
        try:
            self.logger.info(
                f"Getting execution status: {request.execution_id} for user: {request.user_id}"
            )

            # Check active executions first
            execution = self.active_executions.get(request.execution_id)

            if not execution:
                # TODO: Check database for completed executions
                # This is a placeholder implementation
                return GetExecutionStatusResponse(
                    execution=None, found=False, message="Execution not found"
                )

            # Verify user authorization
            if execution.user_id != request.user_id:
                return GetExecutionStatusResponse(
                    execution=None, found=False, message="Execution not found"
                )

            return GetExecutionStatusResponse(
                execution=execution, found=True, message="Execution status retrieved successfully"
            )

        except Exception as e:
            self.logger.error(f"Error getting execution status: {str(e)}")
            raise Exception(f"Failed to get execution status: {str(e)}")

    async def cancel_execution(self, request: CancelExecutionRequest) -> CancelExecutionResponse:
        """Cancel a running execution."""
        try:
            self.logger.info(
                f"Cancelling execution: {request.execution_id} for user: {request.user_id}"
            )

            # Check active executions
            execution = self.active_executions.get(request.execution_id)

            if not execution:
                raise ValueError("Execution not found or already completed")

            # Verify user authorization
            if execution.user_id != request.user_id:
                raise ValueError("Execution not found")

            # Check if execution can be cancelled
            if execution.status in [
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
            ]:
                raise ValueError(f"Execution cannot be cancelled (status: {execution.status})")

            # Cancel the execution
            execution.status = ExecutionStatus.CANCELLED
            execution.completed_at = int(datetime.now().timestamp())
            execution.execution_time_ms = execution.completed_at - execution.started_at
            execution.error_message = request.reason or "Execution cancelled by user"

            # Cancel all running nodes
            for node_execution in execution.node_executions:
                if node_execution.status == NodeExecutionStatus.RUNNING:
                    node_execution.status = NodeExecutionStatus.CANCELLED
                    node_execution.completed_at = execution.completed_at

            self.logger.info(f"Execution cancelled: {request.execution_id}")

            return CancelExecutionResponse(
                execution_id=request.execution_id,
                success=True,
                message="Execution cancelled successfully",
            )

        except ValueError as e:
            self.logger.error(f"Validation error cancelling execution: {str(e)}")
            raise e
        except Exception as e:
            self.logger.error(f"Error cancelling execution: {str(e)}")
            raise Exception(f"Failed to cancel execution: {str(e)}")

    async def get_execution_history(
        self, request: GetExecutionHistoryRequest
    ) -> GetExecutionHistoryResponse:
        """Get execution history."""
        try:
            self.logger.info(f"Getting execution history for user: {request.user_id}")

            # TODO: Implement database query for execution history
            # This is a placeholder implementation

            executions = []

            # Include active executions for the user
            for execution in self.active_executions.values():
                if execution.user_id == request.user_id:
                    if not request.workflow_id or execution.workflow_id == request.workflow_id:
                        executions.append(execution)

            # Sort by started_at descending
            executions.sort(key=lambda x: x.started_at, reverse=True)

            # Apply pagination
            start_idx = request.offset
            end_idx = start_idx + request.limit
            paginated_executions = executions[start_idx:end_idx]

            has_more = end_idx < len(executions)

            self.logger.info(f"Retrieved {len(paginated_executions)} execution records")

            return GetExecutionHistoryResponse(
                executions=paginated_executions, total_count=len(executions), has_more=has_more
            )

        except Exception as e:
            self.logger.error(f"Error getting execution history: {str(e)}")
            raise Exception(f"Failed to get execution history: {str(e)}")

    async def _execute_workflow_async(self, execution: ExecutionData, workflow) -> None:
        """Execute workflow asynchronously."""
        try:
            self.logger.info(f"Starting async execution: {execution.id}")

            # Update status to running
            execution.status = ExecutionStatus.RUNNING

            # Execute nodes sequentially (simplified implementation)
            for i, node in enumerate(workflow.nodes):
                if execution.status == ExecutionStatus.CANCELLED:
                    break

                # Create node execution record
                node_execution = NodeExecutionData(
                    node_id=node.id,
                    node_name=node.name,
                    status=NodeExecutionStatus.RUNNING,
                    input_data={},
                    output_data={},
                    started_at=int(datetime.now().timestamp()),
                )

                execution.node_executions.append(node_execution)
                execution.current_node_id = node.id

                try:
                    # Simulate node execution
                    await self._execute_node(node_execution, node, execution)

                    # Update progress
                    execution.completed_nodes += 1
                    execution.progress_percentage = (
                        execution.completed_nodes / execution.total_nodes
                    ) * 100

                except Exception as e:
                    # Handle node execution error
                    node_execution.status = NodeExecutionStatus.FAILED
                    node_execution.error_message = str(e)
                    node_execution.completed_at = int(datetime.now().timestamp())

                    execution.status = ExecutionStatus.FAILED
                    execution.error_message = f"Node {node.name} failed: {str(e)}"
                    execution.error_node_id = node.id
                    break

            # Complete execution if not already failed or cancelled
            if execution.status == ExecutionStatus.RUNNING:
                execution.status = ExecutionStatus.COMPLETED

            # Set completion time
            execution.completed_at = int(datetime.now().timestamp())
            execution.execution_time_ms = (execution.completed_at - execution.started_at) * 1000
            execution.current_node_id = None

            self.logger.info(f"Execution completed: {execution.id} with status: {execution.status}")

            # TODO: Save execution to database for history

        except Exception as e:
            self.logger.error(f"Error in async execution: {str(e)}")
            execution.status = ExecutionStatus.FAILED
            execution.error_message = f"Execution failed: {str(e)}"
            execution.completed_at = int(datetime.now().timestamp())

    async def _execute_node(
        self, node_execution: NodeExecutionData, node, execution: ExecutionData
    ) -> None:
        """Execute a single node."""
        try:
            self.logger.info(f"Executing node: {node.name} ({node.id})")

            # Simulate node execution time
            await asyncio.sleep(1)

            # Mock successful execution
            node_execution.status = NodeExecutionStatus.COMPLETED
            node_execution.completed_at = int(datetime.now().timestamp())
            node_execution.execution_time_ms = (
                node_execution.completed_at - node_execution.started_at
            ) * 1000
            node_execution.output_data = {
                "status": "success",
                "message": f"Node {node.name} executed successfully",
            }

            # Add execution log
            node_execution.logs.append(f"Node {node.name} executed at {datetime.now().isoformat()}")

        except Exception as e:
            node_execution.status = NodeExecutionStatus.FAILED
            node_execution.error_message = str(e)
            node_execution.completed_at = int(datetime.now().timestamp())
            raise e

    def get_active_execution_count(self) -> int:
        """Get count of active executions."""
        return len(
            [
                exec
                for exec in self.active_executions.values()
                if exec.status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]
            ]
        )

    def cleanup_completed_executions(self) -> None:
        """Clean up completed executions from memory."""
        completed_ids = [
            exec_id
            for exec_id, exec in self.active_executions.items()
            if exec.status
            in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]
            and exec.completed_at
            and (datetime.now().timestamp() - exec.completed_at) > 3600  # Keep for 1 hour
        ]

        for exec_id in completed_ids:
            del self.active_executions[exec_id]

        if completed_ids:
            self.logger.info(f"Cleaned up {len(completed_ids)} completed executions")
