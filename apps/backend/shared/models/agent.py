from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .workflow import WorkflowData


class WorkflowGenerationRequest(BaseModel):
    description: str = Field(..., description="Natural language workflow description")
    context: Dict[str, str] = Field(default_factory=dict, description="Additional context")
    user_preferences: Dict[str, str] = Field(default_factory=dict, description="User preferences")


class WorkflowGenerationResponse(BaseModel):
    success: bool
    workflow: Optional[WorkflowData] = None
    suggestions: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class WorkflowRefinementRequest(BaseModel):
    workflow_id: str
    feedback: str
    original_workflow: WorkflowData


class WorkflowRefinementResponse(BaseModel):
    success: bool
    updated_workflow: WorkflowData
    changes: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class WorkflowValidationRequest(BaseModel):
    workflow_data: Dict[str, str]


class WorkflowValidationResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
