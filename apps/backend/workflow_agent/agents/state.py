"""
LangGraph state management for Workflow Agent
"""
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import MessagesState


class AgentState(TypedDict):
    """State for the Workflow Agent using LangGraph"""
    
    # User input and context
    user_input: str
    description: str
    context: Dict[str, Any]
    user_preferences: Dict[str, Any]
    
    # Analysis results
    requirements: Dict[str, Any]
    parsed_intent: Dict[str, Any]
    current_plan: Optional[Dict[str, Any]]
    
    # Information collection
    collected_info: Dict[str, Any]
    missing_info: List[str]
    questions_asked: List[str]
    
    # Messages and conversation
    messages: List[Dict[str, Any]]
    conversation_history: List[Dict[str, Any]]
    
    # Workflow generation
    workflow: Optional[Dict[str, Any]]
    workflow_suggestions: List[str]
    workflow_errors: List[str]
    
    # Debugging and validation
    debug_results: Optional[Dict[str, Any]]
    validation_results: Optional[Dict[str, Any]]
    
    # Process control
    current_step: str
    iteration_count: int
    max_iterations: int
    should_continue: bool
    
    # Results and feedback
    final_result: Optional[Dict[str, Any]]
    feedback: Optional[str]
    changes_made: List[str]


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