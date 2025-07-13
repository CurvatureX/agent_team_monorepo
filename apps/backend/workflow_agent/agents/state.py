"""
LangGraph state management for Workflow Agent
"""

from typing import Dict, Any, List, Optional, TypedDict, NotRequired
from langgraph.graph import MessagesState


class AgentState(TypedDict):
    """State for the Workflow Agent using LangGraph"""

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
