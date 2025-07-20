"""
Execution Service - 工作流执行服务.

This module implements workflow execution-related operations.
"""

import logging
import uuid
from datetime import datetime

import grpc
from sqlalchemy.orm import Session

from workflow_engine.proto import execution_pb2
from workflow_engine.models.database import get_db
from workflow_engine.models.execution import WorkflowExecution as ExecutionModel
from workflow_engine.execution_engine import WorkflowExecutionEngine
from workflow_engine.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ExecutionService:
    """Service for workflow execution operations."""

    def __init__(self):
        self.logger = logger
        self.execution_engine = WorkflowExecutionEngine()

    def execute_workflow(
        self, 
        request: execution_pb2.ExecuteWorkflowRequest, 
        context: grpc.ServicerContext
    ) -> execution_pb2.ExecuteWorkflowResponse:
        """Execute a workflow."""
        try:
            self.logger.info(f"Executing workflow: {request.workflow_id}")
            
            # Generate execution ID
            execution_id = str(uuid.uuid4())
            
            # Create execution record
            execution = execution_pb2.ExecutionData()
            execution.execution_id = execution_id
            execution.workflow_id = request.workflow_id
            execution.status = execution_pb2.ExecutionStatus.NEW
            execution.mode = request.mode
            execution.triggered_by = request.triggered_by
            execution.start_time = int(datetime.now().timestamp())
            execution.metadata.update(request.metadata)
            
            # Save to database
            db = next(get_db())
            try:
                db_execution = ExecutionModel(
                    execution_id=execution_id,
                    workflow_id=request.workflow_id,
                    status="NEW",
                    mode=execution_pb2.ExecutionMode.Name(request.mode),
                    triggered_by=request.triggered_by,
                    start_time=execution.start_time,
                    execution_metadata=dict(request.metadata)
                )
                db.add(db_execution)
                db.commit()
                
                # TODO: Start workflow execution in background
                # This would typically involve:
                # 1. Loading the workflow definition
                # 2. Creating execution context
                # 3. Starting execution engine
                # 4. Updating status to RUNNING
                
                self.logger.info(f"Workflow execution started: {execution_id}")
                
                return execution_pb2.ExecuteWorkflowResponse(
                    execution_id=execution_id,
                    status=execution_pb2.ExecutionStatus.NEW,
                    message="Workflow execution started"
                )
                
            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error executing workflow: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to execute workflow: {str(e)}")
            
            error_data = execution_pb2.ErrorData()
            error_data.message = str(e)
            error_data.name = type(e).__name__
            
            return execution_pb2.ExecuteWorkflowResponse(
                execution_id="",
                status=execution_pb2.ExecutionStatus.ERROR,
                message=f"Error: {str(e)}",
                error=error_data
            )

    def get_execution_status(
        self, 
        request: execution_pb2.GetExecutionStatusRequest, 
        context: grpc.ServicerContext
    ) -> execution_pb2.GetExecutionStatusResponse:
        """Get execution status."""
        try:
            self.logger.info(f"Getting execution status: {request.execution_id}")
            
            db = next(get_db())
            try:
                db_execution = db.query(ExecutionModel).filter(
                    ExecutionModel.execution_id == request.execution_id
                ).first()
                
                if not db_execution:
                    return execution_pb2.GetExecutionStatusResponse(
                        found=False,
                        message="Execution not found"
                    )
                
                # Convert to protobuf
                execution = execution_pb2.ExecutionData()
                execution.execution_id = db_execution.execution_id
                execution.workflow_id = str(db_execution.workflow_id)  # Convert UUID to string
                execution.status = execution_pb2.ExecutionStatus.Value(db_execution.status)
                execution.mode = execution_pb2.ExecutionMode.Value(db_execution.mode)
                execution.triggered_by = db_execution.triggered_by or ""
                execution.start_time = db_execution.start_time or 0
                execution.end_time = db_execution.end_time or 0
                execution.metadata.update(db_execution.execution_metadata or {})
                
                # TODO: Add run_data from database
                
                return execution_pb2.GetExecutionStatusResponse(
                    execution=execution,
                    found=True,
                    message="Execution status retrieved successfully"
                )
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting execution status: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get execution status: {str(e)}")
            return execution_pb2.GetExecutionStatusResponse(
                found=False,
                message=f"Error: {str(e)}"
            )

    def cancel_execution(
        self, 
        request: execution_pb2.CancelExecutionRequest, 
        context: grpc.ServicerContext
    ) -> execution_pb2.CancelExecutionResponse:
        """Cancel a running execution."""
        try:
            self.logger.info(f"Canceling execution: {request.execution_id}")
            
            db = next(get_db())
            try:
                db_execution = db.query(ExecutionModel).filter(
                    ExecutionModel.execution_id == request.execution_id
                ).first()
                
                if not db_execution:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details("Execution not found")
                    return execution_pb2.CancelExecutionResponse(
                        success=False,
                        message="Execution not found"
                    )
                
                # Update status to CANCELED
                db_execution.status = "CANCELED"
                db_execution.end_time = int(datetime.now().timestamp())
                db.commit()
                
                # TODO: Signal execution engine to stop
                
                self.logger.info(f"Execution canceled: {request.execution_id}")
                
                return execution_pb2.CancelExecutionResponse(
                    success=True,
                    message="Execution canceled successfully"
                )
                
            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error canceling execution: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to cancel execution: {str(e)}")
            return execution_pb2.CancelExecutionResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    def get_execution_history(
        self, 
        request: execution_pb2.GetExecutionHistoryRequest, 
        context: grpc.ServicerContext
    ) -> execution_pb2.GetExecutionHistoryResponse:
        """Get execution history for a workflow."""
        try:
            self.logger.info(f"Getting execution history for workflow: {request.workflow_id}")
            
            db = next(get_db())
            try:
                db_executions = db.query(ExecutionModel).filter(
                    ExecutionModel.workflow_id == request.workflow_id
                ).order_by(ExecutionModel.start_time.desc()).limit(request.limit).all()
                
                executions = []
                for db_execution in db_executions:
                    execution = execution_pb2.ExecutionData()
                    execution.execution_id = db_execution.execution_id
                    execution.workflow_id = str(db_execution.workflow_id)  # Convert UUID to string
                    execution.status = execution_pb2.ExecutionStatus.Value(db_execution.status)
                    execution.mode = execution_pb2.ExecutionMode.Value(db_execution.mode)
                    execution.triggered_by = db_execution.triggered_by or ""
                    execution.start_time = db_execution.start_time or 0
                    execution.end_time = db_execution.end_time or 0
                    execution.metadata.update(db_execution.execution_metadata or {})
                    executions.append(execution)
                
                return execution_pb2.GetExecutionHistoryResponse(
                    executions=executions,
                    total_count=len(executions)
                )
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting execution history: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get execution history: {str(e)}")
            return execution_pb2.GetExecutionHistoryResponse(
                executions=[],
                total_count=0
            ) 