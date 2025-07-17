"""
MVP Data Models for Workflow Agent
Complete implementation of data structures for MVP architecture
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStage(str, Enum):
    """Workflow generation stages"""

    LISTENING = "listening"
    REQUIREMENT_NEGOTIATION = "requirement_negotiation"
    DESIGN = "design"
    CONFIGURATION = "configuration"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    LEARNING = "learning"


class GapSeverity(str, Enum):
    """Capability gap severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SolutionType(str, Enum):
    """Solution implementation types"""

    NATIVE = "native"
    CODE_NODE = "code_node"
    API_INTEGRATION = "api_integration"
    EXTERNAL_SERVICE = "external_service"


class SolutionReliability(str, Enum):
    """Solution reliability levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DeploymentStatus(str, Enum):
    """Deployment status"""

    PENDING = "pending"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    FAILED = "failed"
    STOPPED = "stopped"


class Solution(BaseModel):
    """Solution for capability gaps"""

    type: SolutionType
    complexity: int = Field(ge=1, le=10)  # 1-10
    setup_time: str  # "30分钟", "2-4小时"
    requires_user_action: str  # "需要API密钥", "需要代码编写"
    reliability: SolutionReliability
    description: str


class Constraint(BaseModel):
    """Technical or business constraint"""

    type: str
    description: str
    severity: GapSeverity
    impact: str


class Decision(BaseModel):
    """User decision during negotiation"""

    question: str
    answer: str
    timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0)


class NegotiationStep(BaseModel):
    """Single step in negotiation process"""

    question: str
    user_response: str
    analysis: Dict[str, Any]
    recommendations: List[str]
    timestamp: datetime


class CapabilityAnalysis(BaseModel):
    """Capability analysis results"""

    required_capabilities: List[str]  # ["email_monitoring", "notion_integration"]
    available_capabilities: List[str]  # WORKFLOW Engine原生支持的能力
    capability_gaps: List[str]  # 缺失的能力
    gap_severity: Dict[str, GapSeverity]  # {gap: severity}
    potential_solutions: Dict[str, List[Solution]]  # {gap: [solutions]}
    complexity_scores: Dict[str, int]  # {capability: complexity_score}


class TaskNode(BaseModel):
    """Task node in task tree"""

    id: str
    name: str
    description: str
    type: str  # "sequential|parallel|conditional"
    dependencies: List[str] = Field(default_factory=list)
    estimated_complexity: int = Field(ge=1, le=10, default=5)
    critical_path: bool = False
    resource_estimate: Optional[Dict[str, Any]] = None


class TaskTree(BaseModel):
    """Task decomposition tree"""

    root_task: str
    subtasks: List[TaskNode]
    dependencies: List[Dict[str, str]]
    parallel_opportunities: List[List[str]]


class WorkflowNode(BaseModel):
    """Workflow node definition"""

    id: str
    name: str
    type: str
    task_id: Optional[str] = None
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowConnection(BaseModel):
    """Workflow connection definition"""

    source: str
    target: str
    type: str = "sequential"
    condition: Optional[str] = None
    data_mapping: Optional[Dict[str, Any]] = None


class WorkflowArchitecture(BaseModel):
    """Workflow architecture design"""

    pattern_used: str
    nodes: List[WorkflowNode]
    connections: List[WorkflowConnection]
    data_flow: Dict[str, Any]
    error_handling: Dict[str, Any]
    performance_considerations: List[str]


class WorkflowDSL(BaseModel):
    """Generated workflow DSL"""

    version: str
    metadata: Dict[str, Any]
    nodes: List[Dict[str, Any]]
    connections: Dict[str, Any]
    settings: Dict[str, Any]
    error_handling: Optional[Dict[str, Any]] = None
    optimizations: List[Dict[str, Any]] = Field(default_factory=list)


class Optimization(BaseModel):
    """Optimization suggestion"""

    type: str
    category: str
    description: str
    impact_score: int = Field(ge=1, le=10)
    implementation_complexity: int = Field(ge=1, le=10)
    priority: str  # "low|medium|high"


class PerformanceEstimate(BaseModel):
    """Performance estimation"""

    avg_execution_time: str
    throughput: str
    resource_usage: Dict[str, Any]
    reliability_score: float = Field(ge=0.0, le=1.0)
    scalability: Optional[Dict[str, Any]] = None
    bottlenecks: List[str] = Field(default_factory=list)


class Parameter(BaseModel):
    """Missing parameter info"""

    name: str
    type: str
    description: str
    required: bool
    default_value: Optional[Any] = None


class ValidationResult(BaseModel):
    """Validation result"""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class Template(BaseModel):
    """Configuration template"""

    name: str
    description: str
    parameters: Dict[str, Any]


class AutoFillRecord(BaseModel):
    """Auto-filled parameter record"""

    parameter: str
    value: Any
    source: str
    confidence: float = Field(ge=0.0, le=1.0)


class NodeConfig(BaseModel):
    """Node configuration"""

    node_id: str
    node_type: str
    parameters: Dict[str, Any]
    validation_status: str


class PreviewResult(BaseModel):
    """Preview validation result"""

    node_id: str
    preview_data: Dict[str, Any]
    validation_status: str
    issues: List[str] = Field(default_factory=list)


class StaticValidation(BaseModel):
    """Static validation results"""

    syntax_valid: bool
    logic_valid: bool
    completeness_score: float = Field(ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)


class ConfigurationCheck(BaseModel):
    """Configuration completeness check"""

    complete: bool
    missing_parameters: List[str] = Field(default_factory=list)
    invalid_parameters: List[str] = Field(default_factory=list)
    completeness_percentage: float = Field(ge=0.0, le=1.0)


class MVPWorkflowState(BaseModel):
    """
    Complete MVP workflow state with proper Pydantic validation
    """

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Current stage
    stage: WorkflowStage = WorkflowStage.REQUIREMENT_NEGOTIATION

    # Requirement negotiation state - complete implementation
    requirement_negotiation: Dict[str, Any] = Field(default_factory=dict)

    # Design state - complete implementation
    design_state: Dict[str, Any] = Field(default_factory=dict)

    # Configuration state - complete implementation
    configuration_state: Dict[str, Any] = Field(default_factory=dict)

    # Simplified execution state for MVP
    execution_state: Dict[str, Any] = Field(default_factory=dict)

    # Additional compatibility fields
    user_input: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    current_user_input: str = ""
    user_id: str = "anonymous"
    session_id: str = ""

    # Runtime fields
    current_step: str = "requirement_negotiation"
    should_continue: bool = True
    errors: List[str] = Field(default_factory=list)
    next_questions: List[str] = Field(default_factory=list)
    tradeoff_analysis: Optional[Dict[str, Any]] = None

    # Results
    task_tree: Optional[TaskTree] = None
    architecture: Optional[WorkflowArchitecture] = None
    workflow_dsl: Optional[WorkflowDSL] = None
    optimization_suggestions: List[Optimization] = Field(default_factory=list)
    performance_estimate: Optional[PerformanceEstimate] = None
    design_patterns: List[str] = Field(default_factory=list)
    validation_result: Optional[ValidationResult] = None
    completeness_check: Optional[ConfigurationCheck] = None
    final_result: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)


# Request/Response models for API


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
    workflow: Optional[WorkflowDSL] = None
    suggestions: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None
    stage: Optional[str] = None
    negotiation_questions: List[str] = Field(default_factory=list)
    performance_estimate: Optional[PerformanceEstimate] = None
    validation_result: Optional[ValidationResult] = None


class ConversationContinueRequest(BaseModel):
    """Request to continue conversation"""

    session_id: str
    user_response: str
    thread_id: Optional[str] = None


class ConversationContinueResponse(BaseModel):
    """Response for continuing conversation"""

    success: bool
    session_id: str
    stage: str
    errors: List[str] = Field(default_factory=list)
    next_questions: List[str] = Field(default_factory=list)
    tradeoff_analysis: Optional[Dict[str, Any]] = None
    workflow: Optional[WorkflowDSL] = None
    validation_result: Optional[ValidationResult] = None
    performance_estimate: Optional[PerformanceEstimate] = None
    optimization_suggestions: List[Optimization] = Field(default_factory=list)


class CapabilityGapAnalysisRequest(BaseModel):
    """Request for capability gap analysis"""

    user_input: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class CapabilityGapAnalysisResponse(BaseModel):
    """Response for capability gap analysis"""

    success: bool
    capability_analysis: Optional[CapabilityAnalysis] = None
    proposed_solutions: List[Solution] = Field(default_factory=list)
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
    user_decisions: List[Decision] = Field(default_factory=list)


class WorkflowDesignResponse(BaseModel):
    """Response for workflow design"""

    success: bool
    task_tree: Optional[TaskTree] = None
    architecture: Optional[WorkflowArchitecture] = None
    workflow_dsl: Optional[WorkflowDSL] = None
    optimization_suggestions: List[Optimization] = Field(default_factory=list)
    performance_estimate: Optional[PerformanceEstimate] = None
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
    completeness_score: float = Field(ge=0.0, le=1.0, default=0.0)


class WorkflowRefinementRequest(BaseModel):
    """Request for workflow refinement"""

    workflow_id: str
    feedback: str
    original_workflow: Dict[str, Any]
    session_id: Optional[str] = None


class WorkflowRefinementResponse(BaseModel):
    """Response for workflow refinement"""

    success: bool
    updated_workflow: Optional[Dict[str, Any]] = None
    changes: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None
