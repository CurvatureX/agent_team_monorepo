"""
LangGraph state management for Workflow Agent
State definitions for the 4-node architecture
Based on main branch, updated for MCP integration
"""

from enum import Enum
from typing import Any, Dict, List, NotRequired, TypedDict


class WorkflowStage(str, Enum):
    """Workflow stages for 4-node architecture"""

    CLARIFICATION = "clarification"
    GAP_ANALYSIS = "gap_analysis"
    WORKFLOW_GENERATION = "workflow_generation"
    DEBUG = "debug"
    COMPLETED = "completed"


class WorkflowOrigin(str, Enum):
    """Workflow origin types"""
    CREATE = "create"
    EDIT = "edit"
    COPY = "copy"


class ClarificationPurpose(str, Enum):
    """Purpose of clarification"""
    
    INITIAL_INTENT = "initial_intent"
    TEMPLATE_MODIFICATION = "template_modification"
    GAP_NEGOTIATION = "gap_negotiation"  # When negotiating gap alternatives with user
    DEBUG_ISSUE = "debug_issue"


class Conversation(TypedDict):
    """Conversation message"""

    role: str  # user, assistant, system
    text: str
    timestamp: NotRequired[int]  # timestamp in milliseconds
    metadata: NotRequired[Dict[str, str]]  # additional metadata


class ClarificationContext(TypedDict):
    """Context for clarification stage"""

    purpose: NotRequired[str]  # purpose of clarification
    collected_info: NotRequired[Dict[str, str]]  # collected information
    pending_questions: NotRequired[List[str]]  # questions awaiting user response
    origin: NotRequired[str]  # workflow origin


class GapDetail(TypedDict):
    """Detailed gap information from gap analysis"""
    required_capability: str
    missing_component: str
    alternatives: List[str]


class WorkflowState(TypedDict):
    """Complete workflow state for LangGraph processing in 4-node architecture"""
    
    # Session and user info
    session_id: str
    user_id: str
    created_at: int  # timestamp in milliseconds
    updated_at: int  # timestamp in milliseconds

    # Stage tracking
    stage: WorkflowStage
    previous_stage: NotRequired[WorkflowStage]
    
    # Core workflow data
    intent_summary: str
    conversations: List[Conversation]
    execution_history: NotRequired[List[str]]
    
    # Clarification context
    clarification_context: ClarificationContext
    clarification_ready: NotRequired[bool]  # Whether clarification is complete and ready to proceed
    
    # Gap analysis results
    gap_status: NotRequired[str]  # "no_gap", "has_gap", "gap_resolved"
    identified_gaps: NotRequired[List[GapDetail]]  # detailed gap information
    
    # Workflow data
    current_workflow: NotRequired[Any]  # workflow JSON object
    template_workflow: NotRequired[Any]  # template workflow if editing
    workflow_context: NotRequired[Dict[str, Any]]  # workflow metadata
    
    # Debug information - updated to support structured output
    debug_result: NotRequired[Dict[str, Any]]  # structured debug result from prompt
    debug_loop_count: NotRequired[int]
    
    # Template information
    template_id: NotRequired[str]  # template ID if using template


# Helper functions for extracting data from state
def get_user_message(state: WorkflowState) -> str:
    """Get latest user message from conversations"""
    for conv in reversed(state.get("conversations", [])):
        if conv.get("role") == "user":
            return conv.get("text", "")
    return ""


def get_intent_summary(state: WorkflowState) -> str:
    """Get intent summary from state"""
    return state.get("intent_summary", "")


def get_gap_status(state: WorkflowState) -> str:
    """Get gap status from state"""
    return state.get("gap_status", "no_gap")


def get_identified_gaps(state: WorkflowState) -> List[Dict[str, Any]]:
    """Get identified gaps from state"""
    gaps = state.get("identified_gaps", [])
    return [dict(gap) for gap in gaps]


def get_current_workflow(state: WorkflowState) -> Any:
    """Get current workflow from state"""
    return state.get("current_workflow")


def get_debug_errors(state: WorkflowState) -> List[str]:
    """Get debug errors from structured debug result"""
    debug_result = state.get("debug_result", {})
    return debug_result.get("errors", [])