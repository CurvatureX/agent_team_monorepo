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

logger = logging.getLogger(__name__)
# Don't initialize settings at module level - it might be None
# settings = get_settings()


class ExecutionService:
    """Service for workflow execution operations."""

    def __init__(self, db_session: Session):
        self.logger = logger
        self.db = db_session
        self.execution_engine = WorkflowExecutionEngine()

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

            # Get workflow definition
            from workflow_engine.services.workflow_service import WorkflowService
            workflow_service = WorkflowService(self.db)
            self.logger.info(f"About to get workflow {request.workflow_id} for user {request.user_id}")
            workflow = workflow_service.get_workflow(request.workflow_id, request.user_id)
            
            if not workflow:
                self.logger.error(f"Workflow {request.workflow_id} not found for user {request.user_id}")
                self.db.rollback()
                raise ValueError(f"Workflow {request.workflow_id} not found")
            
            self.logger.info(f"Workflow found: {workflow.name}")
            # Convert workflow to dict for execution engine
            self.logger.info(f"About to call model_dump() on workflow")
            workflow_dict = workflow.model_dump()
            self.logger.info(f"Model dump completed, keys: {list(workflow_dict.keys())}")
            
            # Start workflow execution in background (TODO: make async)
            try:
                self.logger.info(f"Starting workflow execution: {execution_id}")
                
                # Update status to RUNNING (uppercase to match DB constraint)
                db_execution.status = "RUNNING"
                self.db.commit()
                
                # Execute workflow
                execution_result = self.execution_engine.execute_workflow(
                    workflow_id=request.workflow_id,
                    execution_id=execution_id,
                    workflow_definition=workflow_dict,
                    initial_data=request.trigger_data,
                    credentials={}  # TODO: Get credentials from request or user profile
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
                
                self.db.commit()
                self.logger.info(f"Workflow execution completed: {execution_id} with status {db_execution.status}")
                
            except Exception as e:
                self.logger.error(f"Error during workflow execution: {str(e)}")
                db_execution.status = "ERROR"
                db_execution.error_message = str(e)
                db_execution.end_time = int(datetime.now().timestamp())
                self.db.commit()
                raise

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

            self.logger.info(f"Found execution record for {execution_id}")
            
            # Try to access the problematic field directly
            try:
                # Test accessing workflow_metadata
                wf_metadata = getattr(db_execution, 'workflow_metadata', None)
                self.logger.info(f"workflow_metadata access result: {wf_metadata}")
            except Exception as e:
                self.logger.error(f"Error accessing workflow_metadata: {str(e)}")
                # Use raw SQL to get the data
                result = self.db.execute(
                    "SELECT * FROM workflow_executions WHERE execution_id = :exec_id",
                    {"exec_id": execution_id}
                ).fetchone()
                if result:
                    self.logger.info(f"Raw SQL result columns: {result.keys()}")
                    self.logger.info(f"Raw metadata value: {result['metadata']}")
            
            # Convert database model to API model - avoid to_dict() for now
            self.logger.info("Converting database model to dict manually")
            
            # Manually create dict to debug the issue
            exec_dict = {
                "id": str(db_execution.id) if db_execution.id else None,
                "execution_id": db_execution.execution_id,
                "workflow_id": str(db_execution.workflow_id) if db_execution.workflow_id else None,
                "status": db_execution.status,
                "mode": getattr(db_execution, 'mode', 'MANUAL'),
                "triggered_by": getattr(db_execution, 'triggered_by', None),
                "parent_execution_id": getattr(db_execution, 'parent_execution_id', None),
                "start_time": getattr(db_execution, 'start_time', None),
                "end_time": getattr(db_execution, 'end_time', None),
                "metadata": {},  # Skip for now
                "execution_metadata": dict(getattr(db_execution, 'execution_metadata', {})) if getattr(db_execution, 'execution_metadata', None) else {},
                "run_data": getattr(db_execution, 'run_data', None),
                "error_message": getattr(db_execution, 'error_message', None),
                "error_details": dict(getattr(db_execution, 'error_details', {})) if getattr(db_execution, 'error_details', None) else None,
                "created_at": db_execution.created_at.isoformat() if hasattr(db_execution, 'created_at') and db_execution.created_at else None,
            }
            
            self.logger.info(f"Manual exec_dict created successfully")
            self.logger.info(f"exec_dict status: {exec_dict['status']}")
            self.logger.info(f"exec_dict execution_metadata: {exec_dict['execution_metadata']}")
            
            # Extract user_id from metadata or run_data
            user_id = None
            if exec_dict.get('execution_metadata') and isinstance(exec_dict['execution_metadata'], dict):
                user_id = exec_dict['execution_metadata'].get('user_id')
            if not user_id and exec_dict.get('run_data') and isinstance(exec_dict['run_data'], dict):
                user_id = exec_dict['run_data'].get('user_id')
            if not user_id:
                # Try to get from workflow
                from workflow_engine.models import WorkflowModel
                workflow = self.db.query(WorkflowModel).filter(
                    WorkflowModel.id == db_execution.workflow_id
                ).first()
                if workflow:
                    user_id = workflow.user_id
            
            # Map fields to match Execution model
            self.logger.info("About to create Execution model")
            
            # Handle run_data safely
            run_data = exec_dict.get('run_data')
            input_data = {}
            output_data = {}
            execution_run_data = None
            
            if run_data is not None:
                if isinstance(run_data, str):
                    # Parse JSON string to dict
                    try:
                        import json
                        run_data = json.loads(run_data)
                        self.logger.info("Successfully parsed run_data from JSON string")
                    except Exception as e:
                        self.logger.error(f"Failed to parse run_data JSON: {str(e)}")
                        run_data = {}
                
                if isinstance(run_data, dict):
                    # Extract traditional input/output_data for backward compatibility
                    input_data = run_data.get('input_data', {})
                    output_data = run_data.get('output_data', {})
                    
                    # Parse detailed execution data for new run_data field
                    try:
                        from shared.models import (
                            ExecutionRunData, NodeExecutionResult, 
                            ExecutionPerformanceMetrics, NodePerformanceMetrics
                        )
                        
                        # Parse node results
                        parsed_node_results = {}
                        if 'node_results' in run_data:
                            for node_id, node_result in run_data['node_results'].items():
                                # Parse performance metrics
                                perf_data = node_result.get('performance_metrics', {})
                                node_perf = NodePerformanceMetrics(
                                    execution_time=perf_data.get('execution_time', 0.0),
                                    memory_usage=perf_data.get('memory_usage', {}),
                                    cpu_usage=perf_data.get('cpu_usage', {})
                                )
                                
                                # Create NodeExecutionResult
                                parsed_node_results[node_id] = NodeExecutionResult(
                                    status=node_result.get('status', 'unknown'),
                                    logs=node_result.get('logs', []),
                                    metadata=node_result.get('metadata', {}),
                                    output_data=node_result.get('output_data', {}),
                                    error_details=node_result.get('error_details'),
                                    error_message=node_result.get('error_message'),
                                    execution_time=node_result.get('execution_time', 0.0),
                                    input_data_summary=node_result.get('input_data_summary'),
                                    output_data_summary=node_result.get('output_data_summary'),
                                    performance_metrics=node_perf
                                )
                        
                        # Parse overall performance metrics
                        overall_perf_data = run_data.get('performance_metrics', {})
                        overall_perf = ExecutionPerformanceMetrics(
                            total_execution_time=overall_perf_data.get('total_execution_time', 0.0),
                            node_execution_times=overall_perf_data.get('node_execution_times', {}),
                            memory_usage=overall_perf_data.get('memory_usage', {}),
                            cpu_usage=overall_perf_data.get('cpu_usage', {})
                        )
                        
                        # Create ExecutionRunData
                        execution_run_data = ExecutionRunData(
                            node_results=parsed_node_results,
                            execution_order=run_data.get('execution_order', []),
                            performance_metrics=overall_perf
                        )
                        
                        self.logger.info(f"Successfully parsed detailed run_data with {len(parsed_node_results)} nodes")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to parse detailed run_data: {str(e)}")
                        self.logger.error(f"run_data keys: {list(run_data.keys()) if isinstance(run_data, dict) else 'not dict'}")
                        execution_run_data = None
            
            # Handle execution_metadata safely
            execution_metadata = exec_dict.get('execution_metadata')
            if execution_metadata is None:
                session_id = None
            elif isinstance(execution_metadata, dict):
                session_id = execution_metadata.get('session_id')
            else:
                session_id = None
            
            # Add error message to logs if present
            logs = []
            if exec_dict.get('error_message'):
                from shared.models import ExecutionLog
                logs.append(ExecutionLog(
                    timestamp=int(time.time()),
                    level="ERROR",
                    message=exec_dict['error_message']
                ))
            
            print(f"[DEBUG] Creating Execution with: id={exec_dict['execution_id']}, status={exec_dict['status']}, user_id={user_id}", file=sys.stderr, flush=True)
            
            # Create the Execution object
            try:
                execution = Execution(
                    id=exec_dict['execution_id'],  # Use execution_id as id
                    workflow_id=exec_dict['workflow_id'],
                    status=exec_dict['status'],
                    started_at=exec_dict['start_time'] or int(time.time()),
                    ended_at=exec_dict['end_time'],
                    input_data=input_data,
                    output_data=output_data,
                    logs=logs,  # Include error message in logs
                    user_id=user_id or "unknown",
                    session_id=session_id,
                    run_data=execution_run_data  # Add parsed detailed execution data
                )
                print(f"[DEBUG] Execution object created successfully", file=sys.stderr, flush=True)
                return execution
            except Exception as e:
                print(f"[DEBUG] Error creating Execution object: {str(e)}", file=sys.stderr, flush=True)
                print(f"[DEBUG] Execution data: id={exec_dict['execution_id']}, workflow_id={exec_dict['workflow_id']}, status={exec_dict['status']}", file=sys.stderr, flush=True)
                raise

        except Exception as e:
            import traceback
            self.logger.error(f"Error getting execution status: {str(e)}")
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
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

    def execute_single_node(
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
                # Map node type to executor type (adding _NODE suffix)
                executor_type = f"{target_node.type}_NODE"
                self.logger.info(f"Looking for executor type: {executor_type}")
                executor = factory.create_executor(executor_type)
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
