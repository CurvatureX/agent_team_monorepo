from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NodeTemplate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    node_type: str
    node_subtype: str
    version: str = "1.0.0"
    is_system_template: bool = False
    default_parameters: Dict[str, Any] = Field(default_factory=dict)
    required_parameters: List[str] = Field(default_factory=list)
    parameter_schema: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
