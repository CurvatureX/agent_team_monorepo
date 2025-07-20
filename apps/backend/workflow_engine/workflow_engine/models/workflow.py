"""
Workflow database model.
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY

from workflow_engine.models.database import Base


class Workflow(Base):
    """Workflow database model."""
    
    __tablename__ = "workflows"
    
    # Primary key
    id = Column(String(36), primary_key=True, index=True)
    
    # User information
    user_id = Column(String(36), nullable=False, index=True)
    
    # Basic workflow information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(50), default="1.0.0")
    
    # Status and metadata
    active = Column(Boolean, default=True)
    workflow_data = Column(JSON, nullable=False)  # Store protobuf as JSONB
    tags = Column(ARRAY(Text), default=list)  # Store tags as PostgreSQL text array
    
    # Timestamps
    created_at = Column(Integer, nullable=False)  # Unix timestamp
    updated_at = Column(Integer, nullable=False)  # Unix timestamp
    
    def __repr__(self):
        return f"<Workflow(id='{self.id}', name='{self.name}', user_id='{self.user_id}')>"
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'active': self.active,
            'workflow_data': self.workflow_data,
            'tags': self.tags,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
