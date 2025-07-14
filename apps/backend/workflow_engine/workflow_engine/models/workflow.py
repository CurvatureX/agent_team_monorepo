"""
Workflow database model.
"""

from sqlalchemy import Column, String, Boolean, BigInteger, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from .database import Base


class Workflow(Base):
    """Workflow database model."""
    
    __tablename__ = "workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    active = Column(Boolean, default=True)
    
    # Store complete workflow protobuf as JSONB
    workflow_data = Column(JSONB, nullable=False)
    
    # Metadata
    version = Column(String(50), default="1.0.0")
    tags = Column(ARRAY(String))
    
    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    
    def __repr__(self):
        return f"<Workflow(id={self.id}, name={self.name})>" 