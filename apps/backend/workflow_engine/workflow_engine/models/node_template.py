"""
Node Template Database Model.
"""

from sqlalchemy import Column, String, Boolean, JSON, text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid

from .database import Base

class NodeTemplate(Base):
    __tablename__ = 'node_templates'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    category = Column(String)
    node_type = Column(String, nullable=False)
    node_subtype = Column(String, nullable=False)
    version = Column(String, default='1.0.0')
    is_system_template = Column(Boolean, default=False)
    default_parameters = Column(JSON)
    required_parameters = Column(ARRAY(String))
    parameter_schema = Column(JSON) 