"""
Data models for Workflow Agent
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Node types based on the technical design"""

    TRIGGER_NODE = "trigger"
    AI_AGENT_NODE = "ai_agent"
    EXTERNAL_ACTION_NODE = "external_action"
    ACTION_NODE = "action"
    FLOW_NODE = "flow"
    HUMAN_IN_THE_LOOP_NODE = "human_in_the_loop"
    TOOL_NODE = "tool"
    MEMORY_NODE = "memory"


class ConnectionType(str, Enum):
    """Connection types"""

    MAIN = "main"
    AI_AGENT = "ai_agent"
    AI_CHAIN = "ai_chain"
    AI_DOCUMENT = "ai_document"
    AI_EMBEDDING = "ai_embedding"
    AI_LANGUAGE_MODEL = "ai_language_model"
    AI_MEMORY = "ai_memory"
    AI_OUTPUT_PARSER = "ai_output_parser"
    AI_RETRIEVER = "ai_retriever"
    AI_RERANKER = "ai_reranker"
    AI_TEXT_SPLITTER = "ai_text_splitter"
    AI_TOOL = "ai_tool"
    AI_VECTOR_STORE = "ai_vector_store"


class Position(BaseModel):
    """Node position"""

    x: float
    y: float


class Connection(BaseModel):
    """Connection definition"""

    node: str
    type: ConnectionType
    index: int = 0


class Node(BaseModel):
    """Workflow node"""

    id: str
    name: str
    type: NodeType
    subtype: Optional[str] = None
    type_version: int = 1
    position: Position
    disabled: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)
    credentials: Dict[str, str] = Field(default_factory=dict)
    on_error: str = "STOP_WORKFLOW_ON_ERROR"
    retry_policy: Dict[str, int] = Field(
        default_factory=lambda: {"max_tries": 1, "wait_between_tries": 0}
    )
    notes: Dict[str, str] = Field(default_factory=dict)
    webhooks: List[str] = Field(default_factory=list)


class ConnectionsMap(BaseModel):
    """Workflow connections mapping"""

    connections: Dict[str, Dict[str, List[Connection]]] = Field(default_factory=dict)


class WorkflowSettings(BaseModel):
    """Workflow settings"""

    timezone: Dict[str, str] = Field(default_factory=lambda: {"default": "UTC"})
    save_execution_progress: bool = True
    save_manual_executions: bool = True
    timeout: int = 300
    error_policy: str = "STOP_WORKFLOW"
    caller_policy: str = "WORKFLOW_MAIN"


class Workflow(BaseModel):
    """Complete workflow definition"""

    id: str
    name: str
    active: bool = True
    nodes: List[Node]
    connections: ConnectionsMap
    settings: WorkflowSettings = Field(default_factory=WorkflowSettings)
    static_data: Dict[str, Any] = Field(default_factory=dict)
    pin_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: int
    updated_at: int
    version: str = "1.0.0"
    tags: List[str] = Field(default_factory=list)


class WorkflowGenerationRequest(BaseModel):
    """Request for workflow generation"""

    description: str
    context: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class WorkflowGenerationResponse(BaseModel):
    """Response for workflow generation"""

    success: bool
    workflow: Optional[Workflow] = None
    suggestions: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None
    stage: Optional[str] = None
    negotiation_questions: List[str] = Field(default_factory=list)


class WorkflowRefinementRequest(BaseModel):
    """Request for workflow refinement"""

    workflow_id: str
    feedback: str
    original_workflow: Workflow
    session_id: Optional[str] = None


class WorkflowRefinementResponse(BaseModel):
    """Response for workflow refinement"""

    success: bool
    updated_workflow: Optional[Workflow] = None
    changes: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None


class CapabilityGapAnalysisRequest(BaseModel):
    """Request for capability gap analysis"""

    user_input: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class CapabilityGapAnalysisResponse(BaseModel):
    """Response for capability gap analysis"""

    success: bool
    capability_analysis: Optional[CapabilityAnalysisModel] = None
    proposed_solutions: List[SolutionModel] = Field(default_factory=list)
    negotiation_questions: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class NegotiationRequest(BaseModel):
    """Request for negotiation step"""

    session_id: str
    user_response: str
    question_id: Optional[str] = None


class NegotiationResponse(BaseModel):
    """Response for negotiation step"""

    success: bool
    next_questions: List[str] = Field(default_factory=list)
    tradeoff_analysis: Optional[Dict[str, Any]] = None
    negotiation_complete: bool = False
    final_requirements: Optional[str] = None
    errors: List[str] = Field(default_factory=list)


class WorkflowDesignRequest(BaseModel):
    """Request for workflow design"""

    session_id: str
    confirmed_requirements: str
    user_decisions: List[DecisionModel] = Field(default_factory=list)


class WorkflowDesignResponse(BaseModel):
    """Response for workflow design"""

    success: bool
    task_tree: Optional[TaskTreeModel] = None
    architecture: Optional[WorkflowArchitectureModel] = None
    workflow_dsl: Optional[WorkflowDSLModel] = None
    optimization_suggestions: List[OptimizationModel] = Field(default_factory=list)
    performance_estimate: Optional[PerformanceEstimateModel] = None
    errors: List[str] = Field(default_factory=list)


class ValidationRequest(BaseModel):
    """Request for workflow validation"""

    workflow_dsl: Dict[str, Any]
    validation_type: str = "static"  # static, dynamic, full


class ValidationResponse(BaseModel):
    """Response for workflow validation"""

    success: bool
    validation_results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    completeness_score: float = 0.0
