"""
MVP Data Models for Workflow Agent
Complete implementation of data structures for MVP architecture
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStage(str, Enum):
    """Workflow generation stages matching architecture design"""

    LISTENING = "listening"
    CONSULTANT = "consultant"
    REQUIREMENT_NEGOTIATION = "requirement_negotiation"
    DESIGN = "design"
    CONFIGURATION = "configuration"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
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


class NodeType(str, Enum):
    """Node types from architecture design"""

    # Consultant Nodes
    LISTEN = "listen"
    CAPTURE = "capture"
    SCAN = "scan"
    ASSESS_SEVERITY = "assess_severity"
    SEARCH_SIMPLE = "search_simple"
    SEARCH_MULTIPLE = "search_multiple"
    NEGOTIATE_REQ = "negotiate_req"
    SUGGEST_ALT = "suggest_alt"
    PRESENT_OPTIONS = "present_options"
    ADJUST_REQ = "adjust_req"
    CONFIRM_REQ = "confirm_req"
    GUIDED_CLARIFY = "guided_clarify"

    # Design Nodes
    EXTRACT_TASKS = "extract_tasks"
    MAP_CAPABILITIES = "map_capabilities"
    CREATE_PLAN = "create_plan"
    GEN_ARCHITECTURE = "gen_architecture"
    DESIGN_NODES = "design_nodes"
    DEFINE_FLOW = "define_flow"
    CREATE_DSL = "create_dsl"

    # Configuration Nodes
    START_CONFIG = "start_config"
    SELECT_NODE = "select_node"
    CONFIG_PARAMS = "config_params"
    REQUEST_INFO = "request_info"

    # Testing Nodes
    PREP_TEST = "prep_test"
    EXEC_TEST = "exec_test"
    ANALYZE_RESULTS = "analyze_results"
    FIX_PARAMS = "fix_params"
    FIX_STRUCTURE = "fix_structure"
    CHECK_DEPS = "check_deps"

    # Deployment Nodes
    PREP_DEPLOY = "prep_deploy"
    DEPLOY = "deploy"
    VERIFY_DEPLOY = "verify_deploy"
    NOTIFY_SUCCESS = "notify_success"
    ROLLBACK = "rollback"

    # Decision Nodes
    CHECK_GAPS = "check_gaps"
    SEVERITY_CHECK = "severity_check"
    VALIDATE_ADJ = "validate_adj"
    USER_CHOICE = "user_choice"
    MORE_QUESTIONS = "more_questions"
    VALIDATE_PLAN = "validate_plan"
    STRUCTURE_OK = "structure_ok"
    VALIDATE_CONFIG = "validate_config"
    MORE_NODES = "more_nodes"
    TEST_SUCCESS = "test_success"
    ERROR_TYPE = "error_type"
    RETRY_COUNT = "retry_count"
    DEPLOY_SUCCESS = "deploy_success"


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
    rag_insights: Dict[str, Any] = Field(default_factory=dict)  # RAG insights from vector store


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


class ParsedIntent(BaseModel):
    """Parsed user intent"""

    primary_goal: str
    secondary_goals: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)


class RuntimeMetrics(BaseModel):
    """Runtime performance metrics"""

    response_times: List[float] = Field(default_factory=list)
    error_rate: float = 0.0
    throughput: float = 0.0
    resource_usage: Dict[str, Any] = Field(default_factory=dict)


class OptimizationOpportunity(BaseModel):
    """Optimization opportunity"""

    type: str
    description: str
    potential_impact: str
    estimated_effort: str


class AlertConfig(BaseModel):
    """Alert configuration"""

    type: str
    threshold: float
    action: str
    enabled: bool = True


class HealthStatus(BaseModel):
    """Health status"""

    status: str  # "healthy", "degraded", "unhealthy"
    checks: Dict[str, bool] = Field(default_factory=dict)
    last_check: datetime = Field(default_factory=datetime.now)


class Pattern(BaseModel):
    """Pattern for learning"""

    type: str
    frequency: int
    confidence: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OptimizationHistory(BaseModel):
    """Optimization history record"""

    optimization_type: str
    applied_at: datetime
    impact: str
    metrics_before: Dict[str, Any] = Field(default_factory=dict)
    metrics_after: Dict[str, Any] = Field(default_factory=dict)


class Feedback(BaseModel):
    """User feedback"""

    type: str
    rating: int
    comment: str
    timestamp: datetime = Field(default_factory=datetime.now)


class TestResult(BaseModel):
    """Test execution result"""

    test_id: str
    test_type: str
    success: bool
    execution_time: float
    output: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


class TestCoverage(BaseModel):
    """Test coverage metrics"""

    node_coverage: float
    path_coverage: float
    condition_coverage: float
    total_coverage: float


class ErrorRecord(BaseModel):
    """Error record"""

    error_id: str
    error_type: str
    message: str
    stack_trace: str
    timestamp: datetime = Field(default_factory=datetime.now)
    resolved: bool = False


class PerformanceMetrics(BaseModel):
    """Performance metrics"""

    execution_time: float
    memory_usage: float
    cpu_usage: float
    network_io: float
    disk_io: float


class RollbackPoint(BaseModel):
    """Rollback point"""

    point_id: str
    timestamp: datetime
    state_snapshot: Dict[str, Any] = Field(default_factory=dict)
    description: str


class WorkflowState(BaseModel):
    """Complete workflow state matching architecture design"""

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=lambda: {
            "session_id": "",
            "user_id": "anonymous",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "version": "1.0.0",
            "interaction_count": 0,
        }
    )

    # Current stage
    stage: WorkflowStage = WorkflowStage.REQUIREMENT_NEGOTIATION

    # Requirement negotiation state
    requirement_negotiation: Dict[str, Any] = Field(
        default_factory=lambda: {
            "original_requirements": "",
            "parsed_intent": {},
            "capability_analysis": {},
            "identified_constraints": [],
            "proposed_solutions": [],
            "user_decisions": [],
            "negotiation_history": [],
            "final_requirements": "",
            "confidence_score": 0.0,
            "need_clarification": None,  # Boolean: True=needs clarification, False=clear input, None=not assessed
        }
    )

    # Design state
    design_state: Dict[str, Any] = Field(
        default_factory=lambda: {
            "task_tree": {},
            "architecture": {},
            "workflow_dsl": {},
            "optimization_suggestions": [],
            "design_patterns_used": [],
            "estimated_performance": {},
        }
    )

    # Configuration state
    configuration_state: Dict[str, Any] = Field(
        default_factory=lambda: {
            "current_node_index": 0,
            "node_configurations": [],
            "missing_parameters": [],
            "validation_results": [],
            "configuration_templates": [],
            "auto_filled_params": [],
        }
    )

    # Execution state
    execution_state: Dict[str, Any] = Field(
        default_factory=lambda: {
            "test_results": [],
            "test_coverage": {},
            "errors": [],
            "performance_metrics": {},
            "deployment_status": "pending",
            "rollback_points": [],
        }
    )

    # Monitoring state
    monitoring_state: Dict[str, Any] = Field(
        default_factory=lambda: {
            "runtime_metrics": {},
            "optimization_opportunities": [],
            "alert_configurations": [],
            "health_status": {},
        }
    )

    # Learning state
    learning_state: Dict[str, Any] = Field(
        default_factory=lambda: {
            "execution_patterns": [],
            "failure_patterns": [],
            "optimization_history": [],
            "user_feedback": [],
        }
    )

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


# Keep MVPWorkflowState for backward compatibility
class MVPWorkflowState(WorkflowState):
    """
    MVP workflow state - extends WorkflowState for backward compatibility
    """

    pass


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
