"""
Workflow execution database model.
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, JSON, Text
from sqlalchemy.sql import func

from workflow_engine.models.database import Base


class WorkflowExecution(Base):
    """Workflow execution database model."""
    
    __tablename__ = "workflow_executions"
    
    # Primary key
    execution_id = Column(String(36), primary_key=True, index=True)
    
    # Workflow reference
    workflow_id = Column(String(36), nullable=False, index=True)
    
    # Execution information
    status = Column(String(50), nullable=False, default="NEW")  # NEW, RUNNING, COMPLETED, FAILED, CANCELED
    mode = Column(String(50), nullable=False, default="SYNC")  # SYNC, ASYNC
    
    # Execution metadata
    triggered_by = Column(String(255), nullable=True)
    start_time = Column(Integer, nullable=True)  # Unix timestamp
    end_time = Column(Integer, nullable=True)    # Unix timestamp
    execution_metadata = Column(JSON, default=dict)  # Additional metadata (avoid SQLAlchemy reserved word)
    
    # Execution results
    run_data = Column(JSON, nullable=True)       # Runtime data
    error_message = Column(Text, nullable=True)  # Error message
    error_details = Column(JSON, nullable=True)  # Error details
    
    def __repr__(self):
        return f"<WorkflowExecution(execution_id='{self.execution_id}', workflow_id='{self.workflow_id}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'execution_id': self.execution_id,
            'workflow_id': self.workflow_id,
            'status': self.status,
            'mode': self.mode,
            'triggered_by': self.triggered_by,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'metadata': self.execution_metadata,
            'run_data': self.run_data,
            'error_message': self.error_message,
            'error_details': self.error_details
        }
