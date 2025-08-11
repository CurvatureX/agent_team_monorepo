"""
Execution Service - 工作流执行服务.

This module implements workflow execution-related operations.
"""

import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Add backend directory to Python path for shared models
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import (
    ExecuteWorkflowRequest, 
    Execution, 
    ExecutionStatus,
    ExecuteSingleNodeRequest,
    SingleNodeExecutionResponse
)
from workflow_engine.core.config import get_settings
from workflow_engine.execution_engine import (
    EnhancedWorkflowExecutionEngine as WorkflowExecutionEngine,
)
from workflow_engine.models import ExecutionModel
from workflow_engine.services.workflow_service import WorkflowService

from shared.logging_config import get_logger
logger = get_logger(__name__)
settings = get_settings()


class ExecutionService:
    """Service for workflow execution operations."""

    def __init__(self, db_session: Session):
        self.logger = logger
        self.db = db_session
        self.execution_engine = WorkflowExecutionEngine()
        self.workflow_service = WorkflowService(db_session)

    def execute_workflow(self, request: ExecuteWorkflowRequest) -> str:
        """Execute a workflow and return the execution ID."""
        try:
            self.logger.info(f"Executing workflow: {request.workflow_id}")

            execution_id = str(uuid.uuid4())
            now = int(datetime.now().timestamp())

            # Determine execution mode based on trigger_source
            trigger_source = request.trigger_data.get("trigger_source", "manual").lower()
            mode_mapping = {
                "manual": "MANUAL",
                "trigger": "TRIGGER",
                "webhook": "WEBHOOK",
                "retry": "RETRY"
            }
            execution_mode = mode_mapping.get(trigger_source, "MANUAL")

            db_execution = ExecutionModel(
                execution_id=execution_id,
                workflow_id=request.workflow_id,
                status="NEW",  # Changed from PENDING to NEW
                mode=execution_mode,  # Dynamic based on trigger_source
                triggered_by=request.user_id,  # Store user_id in triggered_by field temporarily
                start_time=now,
                execution_metadata={
                    "trigger_data": request.trigger_data,
                    "user_id": request.user_id,  # Also store in metadata for reference
                    "session_id": request.session_id if hasattr(request, 'session_id') else None
                }
                # user_id=request.user_id,  # TODO: Add user_id field to WorkflowExecution model
                # session_id=request.session_id,  # TODO: Add session_id field to WorkflowExecution model
            )
            self.db.add(db_execution)
            self.db.commit()

            # Get workflow definition for execution
            workflow = self.workflow_service.get_workflow(request.workflow_id, request.user_id)
            if not workflow:
                raise ValueError(f"Workflow not found: {request.workflow_id}")

            self.logger.info(f"Starting workflow execution: {execution_id}")
            
            # Start workflow execution in the background
            try:
                # Update status to RUNNING before starting execution
                db_execution.status = "RUNNING"
                self.db.commit()
                
                # Execute the workflow using the execution engine
                execution_result = self.execution_engine.execute_workflow(
                    workflow_id=request.workflow_id,
                    execution_id=execution_id,
                    workflow_definition=workflow.dict(),
                    initial_data=request.trigger_data,
                    credentials={}  # TODO: Add credential handling
                )
                
                # Update execution record with results
                if execution_result["status"] == "completed":
                    db_execution.status = "SUCCESS"
                elif execution_result["status"] == "ERROR":
                    db_execution.status = "ERROR"
                    db_execution.error_message = "; ".join(execution_result.get("errors", []))
                else:
                    db_execution.status = execution_result["status"].upper()
                
                db_execution.end_time = int(datetime.now().timestamp())
                
                # Store execution results
                if "node_results" in execution_result:
                    db_execution.run_data = {
                        "node_results": execution_result["node_results"],
                        "execution_order": execution_result.get("execution_order", []),
                        "performance_metrics": execution_result.get("performance_metrics", {})
                    }
                
                if execution_result.get("error"):
                    db_execution.error_message = execution_result["error"]
                    db_execution.error_details = execution_result.get("error_details", {})
                
                self.db.commit()
                self.logger.info(f"Workflow execution completed: {execution_id}")
                
            except Exception as exec_error:
                # Update status to ERROR if execution fails
                db_execution.status = "ERROR"
                db_execution.error_message = str(exec_error)
                db_execution.end_time = int(datetime.now().timestamp())
                self.db.commit()
                self.logger.error(f"Workflow execution failed: {execution_id} - {exec_error}")
                # Don't re-raise the exception, just log it and return the execution_id

            return execution_id

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error executing workflow: {str(e)}")
            raise

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

            db_execution.status = "CANCELLED"
            db_execution.ended_at = int(datetime.now().timestamp())
            self.db.commit()

            self.logger.info(f"Execution canceled: {execution_id}")
            return True

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error canceling execution: {str(e)}")
            raise

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
        self,
        workflow_id: str,
        node_id: str,
        request: ExecuteSingleNodeRequest
    ) -> SingleNodeExecutionResponse:
        """Execute a single node within a workflow."""
        try:
            self.logger.info(f"Executing single node: {node_id} in workflow: {workflow_id}")
            
            # 1. Get workflow from database
            from workflow_engine.services.workflow_service import WorkflowService
            workflow_service = WorkflowService(self.db)
            self.logger.info(f"Looking up workflow {workflow_id} for user {request.user_id}")
            workflow = workflow_service.get_workflow(workflow_id, request.user_id)
            
            if not workflow:
                self.logger.error(f"Workflow {workflow_id} not found or access denied for user {request.user_id}")
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
                status="RUNNING",
                mode="MANUAL",
                triggered_by=request.user_id,
                start_time=now,
                execution_metadata={
                    "single_node_execution": True,
                    "target_node_id": node_id,
                    "user_id": request.user_id,
                    "input_data": request.input_data,
                    "execution_context": request.execution_context
                }
            )
            
            try:
                # Log the exact data we're trying to insert
                self.logger.info(f"About to insert execution record:")
                self.logger.info(f"  execution_id: {db_execution.execution_id}")
                self.logger.info(f"  workflow_id: {db_execution.workflow_id}")
                self.logger.info(f"  status: {db_execution.status}")
                self.logger.info(f"  mode: {db_execution.mode}")
                self.logger.info(f"  id (primary key): {db_execution.id if hasattr(db_execution, 'id') else 'Not set'}")
                
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
                        {"exec_id": execution_id}
                    ).fetchone()
                    if existing:
                        self.logger.error(f"Record exists in DB after error: id={existing[0]}, execution_id={existing[1]}, status={existing[2]}")
                except:
                    pass
                    
                raise
            
            # 4. Get node executor
            from workflow_engine.nodes.factory import get_node_executor_factory
            from workflow_engine.nodes.base import NodeExecutionContext, ExecutionStatus
            
            try:
                factory = get_node_executor_factory()
                # Map node type to executor type (add _NODE suffix only if not already present)
                if target_node.type.endswith("_NODE"):
                    executor_type = target_node.type
                else:
                    executor_type = f"{target_node.type}_NODE"
                self.logger.info(f"Looking for executor type: {executor_type}")
                executor = factory.create_executor(executor_type, target_node.subtype)
            except Exception as e:
                self.logger.error(f"Error getting executor: {str(e)}")
                raise
            
            if not executor:
                raise ValueError(f"No executor found for node type: {target_node.type} (tried {executor_type})")
            
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
                    self.disabled = getattr(node_data, 'disabled', False)
                    self.on_error = getattr(node_data, 'on_error', 'STOP_WORKFLOW_ON_ERROR')
            
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
                metadata={
                    "single_node_execution": True,
                    "user_id": request.user_id
                }
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
            if db_status == 'COMPLETED':
                db_status = 'SUCCESS'
            elif db_status == 'FAILED':
                db_status = 'ERROR'
            
            db_execution.status = db_status
            db_execution.end_time = end_time
            db_execution.execution_metadata.update({
                "output_data": result.output_data,
                "execution_time": execution_time,
                "logs": result.logs,
                "error_message": result.error_message
            })
            self.db.commit()
            
            # 8. Return response
            # Return user-friendly status names
            api_status = result.status.value.upper()
            if api_status == 'ERROR':
                api_status = 'FAILED'
            elif api_status == 'SUCCESS':
                api_status = 'COMPLETED'
                
            return SingleNodeExecutionResponse(
                execution_id=execution_id,
                node_id=node_id,
                workflow_id=workflow_id,
                status=api_status,
                output_data=result.output_data,
                execution_time=execution_time,
                logs=result.logs or [],
                error_message=result.error_message
            )
            
        except Exception as e:
            self.logger.error(f"Error executing single node: {str(e)}")
            self.logger.error(f"About to rollback main transaction...")
            self.db.rollback()
            
            # Try to update execution record with error
            if 'execution_id' in locals():
                self.logger.error(f"Attempting to update execution record {execution_id} with error status...")
                try:
                    db_execution = self.db.query(ExecutionModel).filter(
                        ExecutionModel.execution_id == execution_id
                    ).first()
                    if db_execution:
                        self.logger.error(f"Found execution record, current status: {db_execution.status}")
                        self.logger.error(f"Setting status to ERROR...")
                        db_execution.status = "ERROR"  # Database expects ERROR not FAILED
                        db_execution.end_time = int(datetime.now().timestamp())
                        db_execution.execution_metadata["error_message"] = str(e)
                        self.logger.error(f"About to commit error status update...")
                        self.db.commit()
                        self.logger.error(f"Successfully updated execution record with error status")
                    else:
                        self.logger.error(f"No execution record found for {execution_id}")
                except Exception as update_error:
                    self.logger.error(f"Failed to update execution with error: {update_error}")
                    pass
            
            raise
