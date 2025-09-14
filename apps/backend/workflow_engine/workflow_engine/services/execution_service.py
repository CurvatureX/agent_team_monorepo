"""
Execution Service - 工作流执行服务.

This module implements workflow execution-related operations using Supabase SDK.
Consolidated from both execution_service.py and supabase_execution_service.py.
"""

import asyncio
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

from shared.models.execution import Execution, ExecutionStatus
from shared.models.workflow import (
    ExecuteSingleNodeRequest,
    ExecuteWorkflowRequest,
    SingleNodeExecutionResponse,
)

from ..core.config import get_settings
from ..execution_engine import WorkflowExecutionEngine
from .supabase_repository import SupabaseWorkflowRepository
from .workflow_service import WorkflowService

logger = logging.getLogger(__name__)
settings = get_settings()


class ExecutionService:
    """Service for workflow execution operations using Supabase SDK."""

    def __init__(self, access_token: Optional[str] = None):
        self.logger = logger
        self.repository = SupabaseWorkflowRepository(access_token)
        self.execution_engine = WorkflowExecutionEngine()
        self.workflow_service = WorkflowService(access_token)

    async def execute_workflow(self, request: ExecuteWorkflowRequest) -> str:
        """Execute a workflow and return the execution ID immediately using Supabase."""
        execution_id = str(uuid.uuid4())

        try:
            self.logger.info(f"🆔 Generated execution ID: {execution_id}")

            # Create minimal execution record
            now = datetime.now()
            trigger_source = request.trigger_data.get("trigger_source", "manual").lower()

            execution_data = {
                "execution_id": execution_id,
                "workflow_id": request.workflow_id,
                "status": ExecutionStatus.NEW.value,
                "mode": "MANUAL",
                "triggered_by": request.user_id,
                "start_time": None,
                "end_time": None,
                "run_data": request.trigger_data or {},
                "metadata": {},
                "error_message": None,
                "error_details": None,
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
                    "start_time": int(datetime.now().timestamp() * 1000),  # Convert to milliseconds
                },
            )

            # Start the actual workflow execution asynchronously
            asyncio.create_task(self._execute_workflow_async(execution_id, request))

            return execution_id

        except Exception as e:
            self.logger.error(f"Error starting workflow execution: {e}")

            # Update execution with error status if it was created
            try:
                await self.repository.update_execution(
                    execution_id,
                    {
                        "status": ExecutionStatus.ERROR.value,
                        "error_message": str(e),
                        "error_details": {"error": str(e)},
                        "end_time": int(
                            datetime.now().timestamp() * 1000
                        ),  # Convert to milliseconds
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
                workflow_id=workflow_id,
                status_filter=status_filter,
                limit=limit,
                offset=offset,
            )

            return [self._dict_to_execution(exec_dict) for exec_dict in executions]

        except Exception as e:
            self.logger.error(f"Error listing executions: {e}")
            return []

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        try:
            self.logger.info(f"Canceling execution: {execution_id}")

            updated_execution = await self.repository.update_execution(
                execution_id,
                {
                    "status": ExecutionStatus.CANCELED.value,
                    "end_time": int(datetime.now().timestamp() * 1000),
                },
            )

            if updated_execution:
                self.logger.info(f"Execution canceled: {execution_id}")
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"Error canceling execution: {str(e)}")
            return False

    async def update_execution_status(
        self,
        execution_id: str,
        status: str,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Update execution status."""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat(),
            }

            if error_message:
                update_data["error_message"] = error_message

            if metadata:
                update_data["metadata"] = metadata

            if status in [
                ExecutionStatus.SUCCESS.value,
                ExecutionStatus.ERROR.value,
                ExecutionStatus.CANCELED.value,
            ]:
                update_data["end_time"] = int(datetime.now().timestamp() * 1000)

            updated_execution = await self.repository.update_execution(execution_id, update_data)
            return updated_execution is not None

        except Exception as e:
            self.logger.error(f"Error updating execution status: {e}")
            return False

    async def execute_single_node(
        self, workflow_id: str, node_id: str, request: ExecuteSingleNodeRequest
    ) -> SingleNodeExecutionResponse:
        """Execute a single node within a workflow."""
        try:
            self.logger.info(f"Executing single node: {node_id} in workflow: {workflow_id}")

            # Get workflow definition
            workflow = await self.workflow_service.get_workflow_by_id(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow {workflow_id} not found or access denied")

            # Find the target node
            target_node = None
            for node in workflow.nodes:
                if node.id == node_id:
                    target_node = node
                    break

            if not target_node:
                raise ValueError(f"Node {node_id} not found in workflow {workflow_id}")

            # Create single node execution record
            execution_id = f"single-node-{uuid.uuid4()}"

            execution_data = {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": ExecutionStatus.RUNNING.value,
                "mode": "MANUAL",
                "triggered_by": request.user_id,
                "start_time": int(datetime.now().timestamp() * 1000),
                "end_time": None,
                "run_data": request.input_data or {},
                "metadata": {
                    "single_node_execution": True,
                    "target_node_id": node_id,
                    "user_id": request.user_id,
                },
                "error_message": None,
                "error_details": None,
            }

            # Create execution record
            created_execution = await self.repository.create_execution(execution_data)
            if not created_execution:
                raise ValueError("Failed to create single node execution record")

            # Convert workflow to dictionary format
            workflow_definition = {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "nodes": [
                    node.model_dump() if hasattr(node, "model_dump") else node
                    for node in workflow.nodes
                ],
                "connections": workflow.connections,
            }

            # Execute single node using execution engine
            result = await self.execution_engine.execute_single_node(
                workflow_id=workflow_id,
                node_id=node_id,
                workflow_definition=workflow_definition,
                input_data=request.input_data,
                user_id=request.user_id,
                execution_id=execution_id,
            )

            # Update execution status based on result
            if result.get("success", False):
                await self.repository.update_execution(
                    execution_id,
                    {
                        "status": ExecutionStatus.SUCCESS.value,
                        "end_time": int(datetime.now().timestamp() * 1000),
                        "metadata": {**execution_data["metadata"], "result": result},
                    },
                )
            else:
                error_msg = result.get("error", "Single node execution failed")
                await self.repository.update_execution(
                    execution_id,
                    {
                        "status": ExecutionStatus.ERROR.value,
                        "end_time": int(datetime.now().timestamp() * 1000),
                        "error_message": error_msg,
                        "error_details": {"result": result},
                    },
                )

            return SingleNodeExecutionResponse(
                success=result.get("success", False),
                execution_id=execution_id,
                node_id=node_id,
                output_data=result.get("output_data"),
                error=result.get("error"),
                execution_time=result.get("execution_time"),
            )

        except Exception as e:
            self.logger.error(f"Error executing single node: {e}")
            return SingleNodeExecutionResponse(
                success=False,
                execution_id=f"single-node-{uuid.uuid4()}",
                node_id=node_id,
                error=str(e),
            )

    async def get_execution_history(self, workflow_id: str, limit: int = 50) -> List[Execution]:
        """Get execution history for a workflow."""
        return await self.list_executions(workflow_id=workflow_id, limit=limit)

    async def resume_workflow_execution(
        self, execution_id: str, resume_data: Optional[dict] = None
    ) -> dict:
        """Resume a paused workflow execution."""
        try:
            self.logger.info(f"🔄 Resuming workflow execution {execution_id}")

            # Get the execution from database
            execution_dict = await self.repository.get_execution(execution_id)
            if not execution_dict:
                return {"status": "ERROR", "message": f"Execution {execution_id} not found"}

            if execution_dict.get("status") != "PAUSED":
                return {
                    "status": "ERROR",
                    "message": f"Execution {execution_id} is not in PAUSED state (current: {execution_dict.get('status')})",
                }

            # Get workflow definition for resume
            workflow = await self.workflow_service.get_workflow_by_id(execution_dict["workflow_id"])
            if not workflow:
                return {"status": "ERROR", "message": "Workflow not found"}

            # Convert workflow to dictionary format
            workflow_definition = {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "nodes": [
                    node.model_dump() if hasattr(node, "model_dump") else node
                    for node in workflow.nodes
                ],
                "connections": workflow.connections,
            }

            # Resume execution using execution engine
            resume_result = await self.execution_engine.resume_workflow(
                execution_id=execution_id,
                workflow_definition=workflow_definition,
                resume_data=resume_data,
            )

            # Update execution status
            if resume_result.get("success"):
                await self.repository.update_execution(
                    execution_id,
                    {
                        "status": ExecutionStatus.RUNNING.value,
                        "metadata": {
                            **execution_dict.get("metadata", {}),
                            "resumed_at": datetime.now().isoformat(),
                        },
                    },
                )
            else:
                error_msg = resume_result.get("error", "Resume failed")
                await self.repository.update_execution(
                    execution_id,
                    {
                        "status": ExecutionStatus.ERROR.value,
                        "error_message": error_msg,
                        "end_time": int(datetime.now().timestamp() * 1000),
                    },
                )

            return resume_result

        except Exception as e:
            self.logger.error(f"Error resuming workflow execution: {e}")
            return {"status": "ERROR", "message": str(e)}

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
            updated_at=execution_dict.get(
                "created_at"
            ),  # Use created_at since updated_at doesn't exist in schema
        )

    async def _execute_workflow_async(self, execution_id: str, request: ExecuteWorkflowRequest):
        """Execute the workflow asynchronously."""
        try:
            self.logger.info(
                f"🔄 Starting async execution for workflow {request.workflow_id}, execution {execution_id}"
            )

            # Get workflow definition
            workflow = await self.workflow_service.get_workflow_by_id(request.workflow_id)
            if not workflow:
                raise ValueError(f"Workflow {request.workflow_id} not found")

            self.logger.info(f"✅ Retrieved workflow definition: {workflow.name}")

            # Convert workflow to dictionary format expected by execution engine
            workflow_definition = {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "nodes": [
                    node.model_dump() if hasattr(node, "model_dump") else node
                    for node in workflow.nodes
                ],
                "connections": workflow.connections,
            }

            # Execute the workflow
            self.logger.info(f"🚀 Executing workflow with {len(workflow_definition['nodes'])} nodes")
            execution_result = await self.execution_engine.execute_workflow(
                workflow_id=request.workflow_id,
                execution_id=execution_id,
                workflow_definition=workflow_definition,
                initial_data=request.trigger_data,
                user_id=request.user_id,
            )

            # Update execution status based on result
            # Check the actual status field returned by execution engine
            execution_status = execution_result.get("status", "").lower()

            if execution_status == "completed":
                await self.repository.update_execution(
                    execution_id,
                    {
                        "status": ExecutionStatus.SUCCESS.value,
                        "end_time": int(datetime.now().timestamp() * 1000),
                        "metadata": execution_result.get("metadata", {}),
                    },
                )
                self.logger.info(f"✅ Workflow execution completed successfully: {execution_id}")
            elif execution_status == "paused":
                await self.repository.update_execution(
                    execution_id,
                    {
                        "status": ExecutionStatus.PAUSED.value,
                        "metadata": execution_result.get("metadata", {}),
                    },
                )
                self.logger.info(f"⏸️ Workflow execution paused: {execution_id}")
            else:
                # Handle error case - extract error message from errors array or node results
                error_msg = "Unknown execution error"
                errors = execution_result.get("errors", [])
                if errors:
                    error_msg = "; ".join(errors)
                else:
                    # Check for node-level errors
                    node_results = execution_result.get("node_results", {})
                    node_errors = []
                    for node_id, result in node_results.items():
                        if result.get("status") == "ERROR" and result.get("error_message"):
                            node_errors.append(f"{node_id}: {result['error_message']}")
                    if node_errors:
                        error_msg = "; ".join(node_errors)

                await self.repository.update_execution(
                    execution_id,
                    {
                        "status": ExecutionStatus.ERROR.value,
                        "end_time": int(datetime.now().timestamp() * 1000),
                        "error_message": error_msg,
                        "error_details": {"execution_result": execution_result},
                    },
                )
                self.logger.error(f"❌ Workflow execution failed: {execution_id} - {error_msg}")

        except Exception as e:
            self.logger.error(f"❌ Error in async workflow execution {execution_id}: {e}")

            # Update execution status to error
            try:
                await self.repository.update_execution(
                    execution_id,
                    {
                        "status": ExecutionStatus.ERROR.value,
                        "end_time": int(datetime.now().timestamp() * 1000),
                        "error_message": str(e),
                        "error_details": {"exception": str(e)},
                    },
                )
            except Exception as update_error:
                self.logger.error(f"❌ Failed to update execution error status: {update_error}")

    def _validate_node_exists(self, workflow_dict: dict, node_id: str) -> bool:
        """Validate that the specified node exists in the workflow."""
        nodes = workflow_dict.get("nodes", [])
        for node in nodes:
            if node.get("id") == node_id:
                return True
        return False

    def _modify_workflow_for_start_node(
        self, workflow_dict: dict, start_node_id: str, skip_trigger_validation: bool = False
    ) -> dict:
        """
        Modify workflow definition to support starting execution from specified node.

        Strategy:
        1. Create a temporary MANUAL trigger node
        2. Connect this trigger to the specified start node
        3. Preserve original nodes and connections
        """
        self.logger.info(f"🔧 Modifying workflow to start from node: {start_node_id}")

        # Create copy of workflow definition
        modified_workflow = workflow_dict.copy()

        # Create temporary MANUAL trigger node
        temp_trigger_id = f"temp_trigger_for_{start_node_id}"
        temp_trigger = {
            "id": temp_trigger_id,
            "name": f"Temporary Trigger for {start_node_id}",
            "type": "TRIGGER",
            "subtype": "MANUAL",
            "type_version": 1,
            "position": {"x": 0.0, "y": 0.0},
            "parameters": {
                "description": f"Temporary trigger to start execution from {start_node_id}",
                "trigger_name": f"Start from {start_node_id}",
            },
            "credentials": {},
            "disabled": False,
            "on_error": "continue",
            "retry_policy": None,
            "notes": {},
            "webhooks": [],
        }

        # Add temporary trigger to the beginning of nodes list
        if "nodes" not in modified_workflow:
            modified_workflow["nodes"] = []
        modified_workflow["nodes"].insert(0, temp_trigger)

        # Modify connections: make temporary trigger connect to specified start node
        if "connections" not in modified_workflow:
            modified_workflow["connections"] = {}

        # Add temporary trigger connection
        modified_workflow["connections"][temp_trigger_id] = {
            "connection_types": {
                "main": {"connections": [{"node": start_node_id, "type": "main", "index": 0}]}
            }
        }

        self.logger.info(f"✅ Successfully modified workflow to start from {start_node_id}")
        self.logger.info(f"📊 Modified workflow now has {len(modified_workflow['nodes'])} nodes")

        return modified_workflow
