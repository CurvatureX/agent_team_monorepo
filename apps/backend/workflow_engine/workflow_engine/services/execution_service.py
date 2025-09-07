"""
Execution Service - 工作流执行服务.

This module implements workflow execution-related operations.
"""

import json
import logging
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

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
from shared.models.db_models import WorkflowModeEnum

from ..core.config import get_settings
from ..execution_engine import WorkflowExecutionEngine
from ..models import ExecutionModel
from .workflow_service import WorkflowService

logger = logging.getLogger(__name__)
settings = get_settings()


class ExecutionService:
    """Service for workflow execution operations."""

    def __init__(self, db_session: Session):
        self.logger = logger
        self.db = db_session
        self.execution_engine = WorkflowExecutionEngine()
        self.workflow_service = WorkflowService(db_session)

    async def execute_workflow(self, request: ExecuteWorkflowRequest) -> str:
        """Execute a workflow and return the execution ID immediately."""
        execution_id = str(uuid.uuid4())
        
        try:
            self.logger.info(f"🆔 Generated execution ID: {execution_id}")
            
            # Create minimal execution record - just enough to track it exists
            now = int(datetime.now().timestamp())
            trigger_source = request.trigger_data.get("trigger_source", "manual").lower()
            mode_mapping = {
                "manual": WorkflowModeEnum.MANUAL.value,
                "trigger": WorkflowModeEnum.TRIGGER.value,
                "webhook": WorkflowModeEnum.WEBHOOK.value,
                "retry": WorkflowModeEnum.RETRY.value,
            }
            execution_mode = mode_mapping.get(trigger_source, WorkflowModeEnum.MANUAL.value)

            db_execution = ExecutionModel(
                execution_id=execution_id,
                workflow_id=request.workflow_id,
                status=ExecutionStatus.NEW.value,
                mode=execution_mode,
                triggered_by=request.user_id,
                start_time=now,
                execution_metadata={
                    "trigger_data": request.trigger_data,
                    "user_id": request.user_id,
                    "session_id": getattr(request, "session_id", None),
                    "start_from_node": getattr(request, 'start_from_node', None),
                    "skip_trigger_validation": getattr(request, 'skip_trigger_validation', False),
                }
            )
            self.db.add(db_execution)
            self.db.commit()
            
            self.logger.info(f"✅ Execution record created: {execution_id}")
            
            # Schedule background task without await
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Use fire-and-forget pattern
            task = loop.create_task(
                self._handle_workflow_execution(
                    execution_id=execution_id,
                    request=request
                )
            )
            
            # Add error handler to prevent unhandled exceptions
            def handle_task_error(task):
                try:
                    task.result()
                except Exception as e:
                    self.logger.error(f"Background task error for {execution_id}: {e}")
            
            task.add_done_callback(handle_task_error)
            
            self.logger.info(f"🚀 Returning execution ID immediately: {execution_id}")
            return execution_id

        except Exception as e:
            self.logger.error(f"❌ Failed to create execution: {e}")
            # If we fail to create the record, we should still have the execution_id
            raise

    async def _handle_workflow_execution(self, execution_id: str, request: ExecuteWorkflowRequest):
        """Handle complete workflow execution in background."""
        try:
            # Log basic info
            self.logger.info(f"🔥 Background execution started for: {execution_id}")
            self.logger.info(f"📊 Workflow ID: {request.workflow_id}, User: {request.user_id}")
            
            # All heavy operations here - workflow fetch, validation, execution
            await self._prepare_and_execute_workflow(
                execution_id=execution_id,
                workflow_id=request.workflow_id,
                user_id=request.user_id,
                request=request
            )
            
        except Exception as e:
            self.logger.error(f"❌ Background execution handler error: {e}")
            self._update_execution_status(execution_id, ExecutionStatus.ERROR.value, str(e))
    
    async def _prepare_and_execute_workflow(self, execution_id: str, workflow_id: str, user_id: str, request: ExecuteWorkflowRequest):
        """准备并执行workflow的后台任务"""
        try:
            # Get workflow definition for execution
            self.logger.info(f"📖 Background task: Fetching workflow definition for: {workflow_id}")
            workflow = self.workflow_service.get_workflow(workflow_id, user_id)
            if not workflow:
                self.logger.error(
                    f"❌ Workflow not found: {workflow_id} for user: {user_id}"
                )
                # Update execution status to ERROR
                self._update_execution_status(execution_id, ExecutionStatus.ERROR.value, "Workflow not found")
                return

            self.logger.info(
                f"✅ Found workflow: {workflow.name} (nodes: {len(workflow.nodes) if workflow.nodes else 0})"
            )
            self.logger.info(f"🔗 Workflow has connections: {bool(workflow.connections)}")

            self.logger.info(f"🏁 Starting workflow execution: {execution_id}")

            # Update status to RUNNING before starting execution
            self.logger.info("📝 Updating execution status to RUNNING...")
            self._update_execution_status(execution_id, ExecutionStatus.RUNNING.value)
            self.logger.info("✅ Database status updated to RUNNING")

            # Execute the workflow using the execution engine
            self.logger.info("🚀 Calling WorkflowExecutionEngine.execute_workflow...")

            # Log the workflow definition before passing it to the engine
            workflow_dict = workflow.dict()
            self.logger.info(
                f"📋 Workflow definition nodes: {len(workflow_dict.get('nodes', []))}"
            )
            for i, node in enumerate(workflow_dict.get("nodes", [])):
                self.logger.info(
                    f"   Node {i+1}: {node.get('name', 'Unnamed')} (type: {node.get('type')}, subtype: {node.get('subtype')}, id: {node.get('id')})"
                )
            
            # 新增：处理start_from_node逻辑
            start_from_node = getattr(request, 'start_from_node', None)
            skip_trigger_validation = getattr(request, 'skip_trigger_validation', False)
            
            if start_from_node:
                # 验证节点是否存在
                if not self._validate_node_exists(workflow_dict, start_from_node):
                    raise ValueError(f"Start node '{start_from_node}' not found in workflow")
                
                self.logger.info(f"🎯 Executing from specific node: {start_from_node}")
                
                # 修改workflow_dict以支持从指定节点开始执行
                workflow_dict = self._modify_workflow_for_start_node(
                    workflow_dict, 
                    start_from_node, 
                    skip_trigger_validation
                )

            # Determine initial data based on execution mode
            # When using start_from_node with inputs, use inputs instead of trigger_data
            if start_from_node and hasattr(request, 'inputs') and request.inputs:
                initial_data = request.inputs
                self.logger.info(f"🎯 Using custom inputs for start_from_node: {list(initial_data.keys())}")
            else:
                initial_data = request.trigger_data
                self.logger.info(f"📋 Using trigger_data as initial data")
            
            # 启动后台异步执行workflow
            await self._execute_workflow_background(
                workflow_id=workflow_id,
                execution_id=execution_id,
                workflow_definition=workflow_dict,
                initial_data=initial_data,
                credentials={},  # TODO: Add credential handling
                user_id=user_id,
            )
            
        except Exception as exec_error:
            self.logger.error(f"Background workflow execution failed: {execution_id} - {exec_error}")
            self._update_execution_status(execution_id, ExecutionStatus.ERROR.value, str(exec_error))

    def _update_execution_status(self, execution_id: str, status: str, error_message: str = None):
        """辅助方法：更新执行状态"""
        try:
            db_execution = self.db.query(ExecutionModel).filter(
                ExecutionModel.execution_id == execution_id
            ).first()
            
            if db_execution:
                db_execution.status = status
                if error_message:
                    db_execution.error_message = error_message
                if status == ExecutionStatus.ERROR.value:
                    db_execution.end_time = int(datetime.now().timestamp())
                self.db.commit()
        except Exception as e:
            self.logger.error(f"Failed to update execution status: {e}")
            self.db.rollback()

    def get_execution_status(self, execution_id: str) -> Optional[Execution]:
        """Get execution status."""
        try:
            self.logger.info(f"Getting execution status: {execution_id}")

            db_execution = (
                self.db.query(ExecutionModel)
                .filter(ExecutionModel.execution_id == execution_id)
                .first()
            )

            if not db_execution:
                return None

            return Execution(**db_execution.to_dict())

        except Exception as e:
            self.logger.error(f"Error getting execution status: {str(e)}")
            raise

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        try:
            self.logger.info(f"Canceling execution: {execution_id}")

            db_execution = (
                self.db.query(ExecutionModel)
                .filter(ExecutionModel.execution_id == execution_id)
                .first()
            )

            if not db_execution:
                return False

            db_execution.status = ExecutionStatus.CANCELED.value
            db_execution.ended_at = int(datetime.now().timestamp())
            self.db.commit()

            self.logger.info(f"Execution canceled: {execution_id}")
            return True

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error canceling execution: {str(e)}")
            raise

    async def resume_workflow_execution(
        self, execution_id: str, resume_data: Optional[dict] = None
    ) -> dict:
        """Resume a paused workflow execution."""
        try:
            self.logger.info(f"🔄 ExecutionService: Resuming workflow execution {execution_id}")

            # Get the execution from database
            execution = self.db.query(ExecutionModel).filter_by(execution_id=execution_id).first()
            if not execution:
                return {"status": "ERROR", "message": f"Execution {execution_id} not found"}

            if execution.status != "PAUSED":
                return {
                    "status": "ERROR",
                    "message": f"Execution {execution_id} is not in PAUSED state (current: {execution.status})",
                }

            # Get workflow definition and credentials for resume
            workflow = self.workflow_service.get_workflow_by_id(execution.workflow_id)
            if not workflow:
                return {"status": "ERROR", "message": f"Workflow {execution.workflow_id} not found"}

            workflow_definition = (
                json.loads(workflow.definition)
                if isinstance(workflow.definition, str)
                else workflow.definition
            )

            # Get credentials if available (from original execution metadata)
            execution_metadata = (
                json.loads(execution.execution_metadata) if execution.execution_metadata else {}
            )
            user_id = execution_metadata.get("user_id")

            # TODO: Implement credential retrieval for the user
            credentials = {}

            # Resume execution through the execution engine
            result = await self.execution_engine.resume_workflow_execution(
                execution_id=execution_id,
                resume_data=resume_data,
                workflow_definition=workflow_definition,
                credentials=credentials,
                user_id=user_id,
            )

            # Update database based on resume result
            if result["status"] in ["completed", "ERROR"]:
                execution.status = result["status"].upper()
                if result["status"] == "completed":
                    execution.ended_at = int(datetime.now().timestamp())
            elif result["status"] == "PAUSED":
                # Keep as PAUSED if it paused again
                execution.status = "PAUSED"

            # Update execution result with resume information
            if execution.execution_result:
                current_result = json.loads(execution.execution_result)
            else:
                current_result = {}

            current_result.update(
                {
                    "resumed": True,
                    "resumed_at": datetime.now().isoformat(),
                    "resume_data": resume_data,
                    "resume_result": result,
                }
            )

            execution.execution_result = json.dumps(current_result)
            self.db.commit()

            self.logger.info(
                f"✅ ExecutionService: Resume completed for {execution_id} with status {result['status']}"
            )
            return result

        except Exception as e:
            self.logger.error(
                f"❌ ExecutionService: Error resuming workflow {execution_id}: {str(e)}"
            )
            self.db.rollback()
            return {"status": "ERROR", "message": f"Resume operation failed: {str(e)}"}

    def get_execution_history(self, workflow_id: str, limit: int = 50) -> List[Execution]:
        """Get execution history for a workflow."""
        try:
            self.logger.info(f"Getting execution history for workflow: {workflow_id}")

            db_executions = (
                self.db.query(ExecutionModel)
                .filter(ExecutionModel.workflow_id == workflow_id)
                .order_by(ExecutionModel.start_time.desc())
                .limit(limit)
                .all()
            )

            return [Execution(**db_exec.to_dict()) for db_exec in db_executions]

        except Exception as e:
            self.logger.error(f"Error getting execution history: {str(e)}")
            raise

    async def execute_single_node(
        self, workflow_id: str, node_id: str, request: ExecuteSingleNodeRequest
    ) -> SingleNodeExecutionResponse:
        """Execute a single node within a workflow."""
        try:
            self.logger.info(f"Executing single node: {node_id} in workflow: {workflow_id}")

            # 1. Get workflow from database
            from .workflow_service import WorkflowService

            workflow_service = WorkflowService(self.db)
            self.logger.info(f"Looking up workflow {workflow_id} for user {request.user_id}")
            workflow = workflow_service.get_workflow(workflow_id, request.user_id)

            if not workflow:
                self.logger.error(
                    f"Workflow {workflow_id} not found or access denied for user {request.user_id}"
                )
                raise ValueError(f"Workflow {workflow_id} not found or access denied")

            # 2. Find the node in workflow
            target_node = None
            for node in workflow.nodes:
                if node.id == node_id:
                    target_node = node
                    break

            if not target_node:
                self.logger.error(f"Node {node_id} not found in workflow {workflow_id}")
                raise ValueError(f"Node {node_id} not found in workflow {workflow_id}")

            # 3. Create single node execution record
            # NOTE: Only create execution_id AFTER all validation passes
            execution_id = f"single-node-{uuid.uuid4()}"
            now = int(datetime.now().timestamp())

            # Store execution record with metadata
            # Note: workflow_id needs to be converted to UUID
            db_execution = ExecutionModel(
                execution_id=execution_id,
                workflow_id=uuid.UUID(workflow_id),  # Convert string to UUID
                status=ExecutionStatus.RUNNING.value,
                mode=WorkflowModeEnum.MANUAL.value,
                triggered_by=request.user_id,
                start_time=now,
                execution_metadata={
                    "single_node_execution": True,
                    "target_node_id": node_id,
                    "user_id": request.user_id,
                    "input_data": request.input_data,
                    "execution_context": request.execution_context,
                },
            )

            try:
                # Log the exact data we're trying to insert
                self.logger.info(f"About to insert execution record:")
                self.logger.info(f"  execution_id: {db_execution.execution_id}")
                self.logger.info(f"  workflow_id: {db_execution.workflow_id}")
                self.logger.info(f"  status: {db_execution.status}")
                self.logger.info(f"  mode: {db_execution.mode}")
                self.logger.info(
                    f"  id (primary key): {db_execution.id if hasattr(db_execution, 'id') else 'Not set'}"
                )

                self.db.add(db_execution)
                self.logger.info("Added to session, about to flush...")
                self.db.flush()  # Force flush to see SQL
                self.logger.info("Flushed to database, about to commit...")
                self.db.commit()
                self.logger.info(f"Created execution record: {execution_id}")
            except Exception as e:
                self.logger.error(f"Error creating execution record: {str(e)}")
                self.logger.error(f"Error type: {type(e).__name__}")
                self.logger.error(f"Full error details: {repr(e)}")

                # Log the current transaction state
                import traceback

                self.logger.error(f"Stack trace: {traceback.format_exc()}")

                # Check if the record was actually inserted
                try:
                    self.db.rollback()
                    # Query to see if record exists
                    existing = self.db.execute(
                        "SELECT id, execution_id, status FROM workflow_executions WHERE execution_id = :exec_id",
                        {"exec_id": execution_id},
                    ).fetchone()
                    if existing:
                        self.logger.error(
                            f"Record exists in DB after error: id={existing[0]}, execution_id={existing[1]}, status={existing[2]}"
                        )
                except:
                    pass

                raise

            # 4. Get node executor
            from ..nodes.base import ExecutionStatus, NodeExecutionContext
            from ..nodes.factory import get_node_executor_factory

            try:
                factory = get_node_executor_factory()
                # Map node type to executor type - workflow engine expects unified node types without _NODE suffix
                # The node specs and executors now use unified format (TRIGGER, ACTION, etc.)
                if target_node.type.endswith("_NODE"):
                    # Remove _NODE suffix for unified format
                    executor_type = target_node.type[:-5]  # Remove "_NODE"
                else:
                    # Already in unified format
                    executor_type = target_node.type
                self.logger.info(f"Looking for executor type: {executor_type}")
                executor = factory.create_executor(executor_type, target_node.subtype)
            except Exception as e:
                self.logger.error(f"Error getting executor: {str(e)}")
                raise

            if not executor:
                raise ValueError(
                    f"No executor found for node type: {target_node.type} (tried {executor_type})"
                )

            # 5. Prepare execution context
            # Handle parameter overrides
            self.logger.info(f"Target node parameters type: {type(target_node.parameters)}")
            self.logger.info(f"Target node parameters: {target_node.parameters}")

            # Ensure parameters is a dict
            if isinstance(target_node.parameters, dict):
                node_parameters = dict(target_node.parameters)
            elif isinstance(target_node.parameters, str):
                # Try to parse JSON string
                import json

                try:
                    node_parameters = json.loads(target_node.parameters)
                    self.logger.warning(f"Parsed parameters from JSON string")
                except:
                    self.logger.error(f"Failed to parse parameters as JSON, using empty dict")
                    node_parameters = {}
            else:
                self.logger.warning(f"Unexpected parameters type, using empty dict")
                node_parameters = {}

            if request.execution_context.get("override_parameters"):
                node_parameters.update(request.execution_context["override_parameters"])

            # Create mock node with updated parameters
            class MockNode:
                def __init__(self, node_data, parameters):
                    self.id = node_data.id
                    self.name = node_data.name
                    self.type = node_data.type
                    self.subtype = node_data.subtype
                    self.parameters = parameters
                    self.credentials = node_data.credentials or {}
                    self.disabled = getattr(node_data, "disabled", False)
                    self.on_error = getattr(node_data, "on_error", "STOP_WORKFLOW_ON_ERROR")

            mock_node = MockNode(target_node, node_parameters)

            # Prepare input data
            input_data = dict(request.input_data)

            # If use_previous_results is true, try to fetch previous execution data
            if request.execution_context.get("use_previous_results"):
                previous_exec_id = request.execution_context.get("previous_execution_id")
                if previous_exec_id:
                    # TODO: Fetch previous execution results from database
                    # For now, just use the provided input_data
                    pass

            # Create execution context
            context = NodeExecutionContext(
                node=mock_node,
                workflow_id=workflow_id,
                execution_id=execution_id,
                input_data=input_data,
                static_data=workflow.static_data or {},
                credentials=request.execution_context.get("credentials", {}),
                metadata={"single_node_execution": True, "user_id": request.user_id},
            )

            # 6. Execute the node
            start_time = time.time()
            # Handle both sync and async executors
            import inspect

            if inspect.iscoroutinefunction(executor.execute):
                import asyncio

                result = await executor.execute(context)
            else:
                result = executor.execute(context)
            execution_time = time.time() - start_time

            # 7. Update execution record
            end_time = int(datetime.now().timestamp())
            # Convert status to uppercase for database
            db_status = result.status.value.upper()
            # Database expects SUCCESS not COMPLETED, ERROR not FAILED
            if db_status == "COMPLETED":
                db_status = ExecutionStatus.SUCCESS.value
            elif db_status == "FAILED":
                db_status = ExecutionStatus.ERROR.value

            db_execution.status = db_status
            db_execution.end_time = end_time
            db_execution.execution_metadata.update(
                {
                    "output_data": result.output_data,
                    "execution_time": execution_time,
                    "logs": result.logs,
                    "error_message": result.error_message,
                }
            )
            self.db.commit()

            # 8. Return response
            # Return user-friendly status names
            api_status = result.status.value.upper()
            if api_status == ExecutionStatus.ERROR.value:
                api_status = "FAILED"
            elif api_status == ExecutionStatus.SUCCESS.value:
                api_status = "COMPLETED"

            return SingleNodeExecutionResponse(
                execution_id=execution_id,
                node_id=node_id,
                workflow_id=workflow_id,
                status=api_status,
                output_data=result.output_data,
                execution_time=execution_time,
                logs=result.logs or [],
                error_message=result.error_message,
            )

        except Exception as e:
            self.logger.error(f"Error executing single node: {str(e)}")
            self.logger.error(f"About to rollback main transaction...")
            self.db.rollback()

            # Try to update execution record with error
            if "execution_id" in locals():
                self.logger.error(
                    f"Attempting to update execution record {execution_id} with error status..."
                )
                try:
                    db_execution = (
                        self.db.query(ExecutionModel)
                        .filter(ExecutionModel.execution_id == execution_id)
                        .first()
                    )
                    if db_execution:
                        self.logger.error(
                            f"Found execution record, current status: {db_execution.status}"
                        )
                        self.logger.error(f"Setting status to ERROR...")
                        db_execution.status = (
                            ExecutionStatus.ERROR.value
                        )  # Database expects ERROR not FAILED
                        db_execution.end_time = int(datetime.now().timestamp())
                        db_execution.execution_metadata["error_message"] = str(e)
                        self.logger.error(f"About to commit error status update...")
                        self.db.commit()
                        self.logger.error(
                            f"Successfully updated execution record with error status"
                        )
                    else:
                        self.logger.error(f"No execution record found for {execution_id}")
                except Exception as update_error:
                    self.logger.error(f"Failed to update execution with error: {update_error}")
                    pass

            raise

    def _validate_node_exists(self, workflow_dict: dict, node_id: str) -> bool:
        """验证指定的节点是否存在于workflow中"""
        nodes = workflow_dict.get('nodes', [])
        for node in nodes:
            if node.get('id') == node_id:
                return True
        return False
    
    def _modify_workflow_for_start_node(
        self, 
        workflow_dict: dict, 
        start_node_id: str, 
        skip_trigger_validation: bool = False
    ) -> dict:
        """
        修改workflow定义以支持从指定节点开始执行
        
        策略：
        1. 创建一个临时的MANUAL触发器节点
        2. 将该触发器连接到指定的起始节点
        3. 保留原有的节点和连接关系
        """
        self.logger.info(f"🔧 Modifying workflow to start from node: {start_node_id}")
        
        # 创建新的workflow定义副本
        modified_workflow = workflow_dict.copy()
        
        # 创建临时的MANUAL触发器节点
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
                "trigger_name": f"Start from {start_node_id}"
            },
            "credentials": {},
            "disabled": False,
            "on_error": "continue",
            "retry_policy": None,
            "notes": {},
            "webhooks": []
        }
        
        # 添加临时触发器到节点列表的开头
        if 'nodes' not in modified_workflow:
            modified_workflow['nodes'] = []
        modified_workflow['nodes'].insert(0, temp_trigger)
        
        # 修改连接：让临时触发器连接到指定的起始节点
        if 'connections' not in modified_workflow:
            modified_workflow['connections'] = {}
            
        # 添加临时触发器的连接
        modified_workflow['connections'][temp_trigger_id] = {
            "connection_types": {
                "main": {
                    "connections": [
                        {
                            "node": start_node_id,
                            "type": "main",
                            "index": 0
                        }
                    ]
                }
            }
        }
        
        self.logger.info(f"✅ Successfully modified workflow to start from {start_node_id}")
        self.logger.info(f"📊 Modified workflow now has {len(modified_workflow['nodes'])} nodes")
        
        return modified_workflow

    async def _execute_workflow_background(
        self,
        workflow_id: str,
        execution_id: str,
        workflow_definition: dict,
        initial_data: dict,
        credentials: dict,
        user_id: str,
    ):
        """在后台异步执行workflow，并更新数据库状态"""
        try:
            self.logger.info(f"🚀 Background execution started for: {execution_id}")
            
            # 执行workflow
            execution_result = await self.execution_engine.execute_workflow(
                workflow_id=workflow_id,
                execution_id=execution_id,
                workflow_definition=workflow_definition,
                initial_data=initial_data,
                credentials=credentials,
                user_id=user_id,
            )
            
            self.logger.info(
                f"🏁 Background execution completed - status: {execution_result.get('status', 'UNKNOWN')}"
            )
            
            # 更新数据库状态
            db_execution = (
                self.db.query(ExecutionModel)
                .filter(ExecutionModel.execution_id == execution_id)
                .first()
            )
            
            if db_execution:
                # Update execution record with results
                if execution_result["status"] == "completed":
                    db_execution.status = ExecutionStatus.SUCCESS.value
                elif execution_result["status"] == "ERROR":
                    db_execution.status = ExecutionStatus.ERROR.value
                    db_execution.error_message = "; ".join(execution_result.get("errors", []))
                else:
                    db_execution.status = execution_result["status"].upper()

                db_execution.end_time = int(datetime.now().timestamp())

                # Store execution results
                if "node_results" in execution_result:
                    db_execution.run_data = {
                        "node_results": execution_result["node_results"],
                        "execution_order": execution_result.get("execution_order", []),
                        "performance_metrics": execution_result.get("performance_metrics", {}),
                    }

                if execution_result.get("error"):
                    db_execution.error_message = execution_result["error"]
                    db_execution.error_details = execution_result.get("error_details", {})

                self.db.commit()
                self.logger.info(f"✅ Background execution database updated: {execution_id}")
            else:
                self.logger.error(f"❌ Execution record not found for background update: {execution_id}")
                
        except Exception as e:
            self.logger.error(f"❌ Background execution failed: {execution_id} - {e}")
            
            # 更新数据库状态为错误
            try:
                db_execution = (
                    self.db.query(ExecutionModel)
                    .filter(ExecutionModel.execution_id == execution_id)
                    .first()
                )
                
                if db_execution:
                    db_execution.status = ExecutionStatus.ERROR.value
                    db_execution.error_message = str(e)
                    db_execution.end_time = int(datetime.now().timestamp())
                    self.db.commit()
                    self.logger.info(f"✅ Background execution error status updated: {execution_id}")
            except Exception as update_error:
                self.logger.error(f"❌ Failed to update error status: {update_error}")
