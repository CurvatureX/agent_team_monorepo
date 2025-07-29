from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class NodeTemplate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    node_type: str
    node_subtype: Optional[str] = None
    version: str = "1.0.0"
    is_system_template: bool = False
    default_parameters: Dict[str, Any] = Field(default_factory=dict)
    required_parameters: List[str] = Field(default_factory=list)
    parameter_schema: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        orm_mode = True 