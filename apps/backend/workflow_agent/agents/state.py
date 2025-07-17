"""
LangGraph state management for Workflow Agent
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, NotRequired, Optional, TypedDict

from langgraph.graph import MessagesState


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


class Solution(TypedDict):
    """Solution for capability gaps"""

    type: SolutionType
    complexity: int  # 1-10
    setup_time: str  # "30分钟", "2-4小时"
    requires_user_action: str  # "需要API密钥", "需要代码编写"
    reliability: SolutionReliability
    description: str


class Constraint(TypedDict):
    """Technical or business constraint"""

    type: str
    description: str
    severity: GapSeverity
    impact: str


class Decision(TypedDict):
    """User decision during negotiation"""

    question: str
    answer: str
    timestamp: datetime
    confidence: float


class NegotiationStep(TypedDict):
    """Single step in negotiation process"""

    question: str
    user_response: str
    analysis: Dict[str, Any]
    recommendations: List[str]
    timestamp: datetime


class CapabilityAnalysis(TypedDict):
    """Capability analysis results"""

    required_capabilities: List[str]  # ["email_monitoring", "notion_integration"]
    available_capabilities: List[str]  # WORKFLOW Engine原生支持的能力
    capability_gaps: List[str]  # 缺失的能力
    gap_severity: Dict[str, GapSeverity]  # {gap: severity}
    potential_solutions: Dict[str, List[Solution]]  # {gap: [solutions]}
    complexity_scores: Dict[str, int]  # {capability: complexity_score}


class TaskTree(TypedDict):
    """Task decomposition tree"""

    root_task: str
    subtasks: List[Dict[str, Any]]
    dependencies: List[Dict[str, str]]
    parallel_opportunities: List[List[str]]


class WorkflowArchitecture(TypedDict):
    """Workflow architecture design"""

    nodes: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    data_flow: Dict[str, Any]
    error_handling: Dict[str, Any]
    performance_considerations: List[str]


class WorkflowDSL(TypedDict):
    """Generated workflow DSL"""

    version: str
    nodes: List[Dict[str, Any]]
    connections: Dict[str, Any]
    settings: Dict[str, Any]
    metadata: Dict[str, Any]


class Optimization(TypedDict):
    """Optimization suggestion"""

    type: str
    description: str
    impact: str
    implementation_complexity: int


class PerformanceEstimate(TypedDict):
    """Performance estimation"""

    avg_execution_time: str
    throughput: str
    resource_usage: Dict[str, Any]
    reliability_score: float


class Parameter(TypedDict):
    """Missing parameter info"""

    name: str
    type: str
    description: str
    required: bool
    default_value: Optional[Any]


class ValidationResult(TypedDict):
    """Validation result"""

    valid: bool
    errors: List[str]
    warnings: List[str]


class Template(TypedDict):
    """Configuration template"""

    name: str
    description: str
    parameters: Dict[str, Any]


class AutoFillRecord(TypedDict):
    """Auto-filled parameter record"""

    parameter: str
    value: Any
    source: str
    confidence: float


class NodeConfig(TypedDict):
    """Node configuration"""

    node_id: str
    node_type: str
    parameters: Dict[str, Any]
    validation_status: str


class PreviewResult(TypedDict):
    """Preview validation result"""

    node_id: str
    preview_data: Dict[str, Any]
    validation_status: str
    issues: List[str]


class StaticValidation(TypedDict):
    """Static validation results"""

    syntax_valid: bool
    logic_valid: bool
    completeness_score: float
    issues: List[str]


class ConfigurationCheck(TypedDict):
    """Configuration completeness check"""

    complete: bool
    missing_parameters: List[str]
    invalid_parameters: List[str]
    completeness_percentage: float


class WorkflowState(TypedDict):
    """Complete workflow agent state based on architecture design"""

    # Metadata
    metadata: Dict[str, Any]

    # Current stage
    stage: WorkflowStage

    # Requirement negotiation state
    requirement_negotiation: Dict[str, Any]

    # Design state
    design_state: Dict[str, Any]

    # Configuration state
    configuration_state: Dict[str, Any]

    # Execution state (simplified for MVP)
    execution_state: Dict[str, Any]

    # Monitoring state
    monitoring_state: NotRequired[Dict[str, Any]]

    # Learning state
    learning_state: NotRequired[Dict[str, Any]]


class MVPWorkflowState(TypedDict):
    """MVP version of workflow state"""

    # Metadata
    metadata: Dict[str, Any]

    # Current stage
    stage: WorkflowStage

    # Requirement negotiation state - complete implementation
    requirement_negotiation: Dict[str, Any]

    # Design state - complete implementation
    design_state: Dict[str, Any]

    # Configuration state - complete implementation
    configuration_state: Dict[str, Any]

    # Simplified execution state for MVP
    execution_state: Dict[str, Any]


# Legacy compatibility - keep existing AgentState for backward compatibility
class AgentState(TypedDict):
    """Legacy state for backward compatibility"""

    # Required user input
    user_input: str

    # Optional context and preferences
    context: NotRequired[Dict[str, Any]]
    user_preferences: NotRequired[Dict[str, Any]]

    # Analysis results (filled during execution)
    requirements: NotRequired[Dict[str, Any]]
    parsed_intent: NotRequired[Dict[str, Any]]
    current_plan: NotRequired[Optional[Dict[str, Any]]]

    # Information collection (filled during execution)
    collected_info: NotRequired[Dict[str, Any]]
    missing_info: NotRequired[List[str]]
    questions_asked: NotRequired[List[str]]

    # Messages and conversation (filled during execution)
    messages: NotRequired[List[Dict[str, Any]]]
    conversation_history: NotRequired[List[Dict[str, Any]]]

    # Workflow generation (filled during execution)
    workflow: NotRequired[Optional[Dict[str, Any]]]
    workflow_suggestions: NotRequired[List[str]]
    workflow_errors: NotRequired[List[str]]

    # Debugging and validation (filled during execution)
    debug_results: NotRequired[Optional[Dict[str, Any]]]
    validation_results: NotRequired[Optional[Dict[str, Any]]]

    # Process control (filled during execution)
    current_step: NotRequired[str]
    iteration_count: NotRequired[int]
    max_iterations: NotRequired[int]
    should_continue: NotRequired[bool]

    # Results and feedback (filled during execution)
    final_result: NotRequired[Optional[Dict[str, Any]]]
    feedback: NotRequired[Optional[str]]
    changes_made: NotRequired[List[str]]


class WorkflowGenerationState(MessagesState):
    """Extended state for workflow generation with LangGraph MessagesState"""

    # Core workflow data
    workflow_data: Optional[Dict[str, Any]]
    node_library: Dict[str, Any]
    template_library: Dict[str, Any]

    # Generation process
    generation_step: str
    node_count: int
    max_nodes: int

    # Quality control
    validation_errors: List[str]
    quality_score: float
    complexity_score: float
