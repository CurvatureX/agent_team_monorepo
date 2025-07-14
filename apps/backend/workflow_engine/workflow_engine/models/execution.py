"""
Execution database model.
"""

from sqlalchemy import Column, String, BigInteger, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from .database import Base


class WorkflowExecution(Base):
    """Workflow execution database model."""
    
    __tablename__ = "workflow_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(String(255), unique=True, nullable=False)
    workflow_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Execution status and mode
    status = Column(String(50), nullable=False, default="NEW")
    mode = Column(String(50), nullable=False, default="MANUAL")
    
    # Execution context
    triggered_by = Column(String(255))
    parent_execution_id = Column(String(255))
    
    # Timing
    start_time = Column(BigInteger)
    end_time = Column(BigInteger)
    
    # Execution data
    run_data = Column(JSONB)
    metadata = Column(JSONB, default={})
    
    # Error information
    error_message = Column(Text)
    error_details = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<WorkflowExecution(id={self.execution_id}, status={self.status})>" 