"""
Execution Service - 工作流执行服务.

This module implements workflow execution-related operations.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from shared.models import (
    ExecuteWorkflowRequest,
    Execution,
    ExecutionStatus,
)
from workflow_engine.models.execution import WorkflowExecution as ExecutionModel
from workflow_engine.execution_engine import EnhancedWorkflowExecutionEngine as WorkflowExecutionEngine
from workflow_engine.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


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
            
            db_execution = ExecutionModel(
                execution_id=execution_id,
                workflow_id=request.workflow_id,
                status="PENDING",
                # mode and triggered_by would need to be added to ExecuteWorkflowRequest
                # if they are still needed.
                start_time=now,
                user_id=request.user_id,
                session_id=request.session_id,
                trigger_data=request.trigger_data
            )
            self.db.add(db_execution)
            self.db.commit()
            
            # Placeholder for starting the execution in the background
            self.logger.info(f"Workflow execution created: {execution_id}")
            
            return execution_id
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error executing workflow: {str(e)}")
            raise

    def get_execution_status(self, execution_id: str) -> Optional[Execution]:
        """Get execution status."""
        try:
            self.logger.info(f"Getting execution status: {execution_id}")
            
            db_execution = self.db.query(ExecutionModel).filter(
                ExecutionModel.execution_id == execution_id
            ).first()
            
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
            
            db_execution = self.db.query(ExecutionModel).filter(
                ExecutionModel.execution_id == execution_id
            ).first()
            
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
            
            db_executions = self.db.query(ExecutionModel).filter(
                ExecutionModel.workflow_id == workflow_id
            ).order_by(ExecutionModel.start_time.desc()).limit(limit).all()
            
            return [Execution(**db_exec.to_dict()) for db_exec in db_executions]
            
        except Exception as e:
            self.logger.error(f"Error getting execution history: {str(e)}")
            raise 