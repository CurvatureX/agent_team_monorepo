"""
LangGraph state management for Workflow Agent
State definitions for the optimized 2-node architecture
Simplified for better user experience with automatic gap handling
"""

from enum import Enum
from typing import Any, Dict, List, NotRequired, TypedDict


class WorkflowStage(str, Enum):
    """Workflow stages for 2-node architecture"""

    CLARIFICATION = "clarification"
    WORKFLOW_GENERATION = "workflow_generation"
    COMPLETED = "completed"
    FAILED = "failed"  # Workflow generation failed after max attempts


class WorkflowOrigin(str, Enum):
    """Workflow origin types"""

    CREATE = "create"
    EDIT = "edit"
    COPY = "copy"


class ClarificationPurpose(str, Enum):
    """Purpose of clarification"""

    INITIAL_INTENT = "initial_intent"
    TEMPLATE_MODIFICATION = "template_modification"
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


class WorkflowState(TypedDict):
    """Complete workflow state for LangGraph processing in 2-node architecture"""

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

    # Clarification context
    clarification_context: ClarificationContext

    # Workflow data
    current_workflow: NotRequired[Any]  # workflow JSON object
    template_workflow: NotRequired[Any]  # template workflow if editing
    workflow_context: NotRequired[Dict[str, Any]]  # workflow metadata

    # Workflow creation tracking (new fields for moved workflow creation)
    workflow_id: NotRequired[str]  # ID of created workflow in workflow_engine
    workflow_creation_result: NotRequired[
        Dict[str, Any]
    ]  # Full creation result from workflow_engine
    workflow_creation_error: NotRequired[str]  # Error message if workflow creation failed
    generation_loop_count: NotRequired[int]  # Counter for workflow generation retry attempts

    # Failure information
    workflow_generation_failed: NotRequired[bool]  # True if generation failed after max attempts
    final_error_message: NotRequired[str]  # Final error message for failed generation

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


def get_current_workflow(state: WorkflowState) -> Any:
    """Get current workflow from state"""
    return state.get("current_workflow")


def is_clarification_ready(state: WorkflowState) -> bool:
    """
    Determine if clarification is ready to proceed to next stage.
    This is derived from the state rather than stored.

    Returns True when:
    - No pending questions in clarification_context
    - Intent summary is not empty
    - Not coming from gap analysis with unresolved gaps
    """
    clarification_context = state.get("clarification_context", {})
    pending_questions = clarification_context.get("pending_questions", [])
    intent_summary = state.get("intent_summary", "")

    # If there are pending questions, not ready
    if pending_questions:
        return False

    # If no intent summary collected yet, not ready
    if not intent_summary:
        return False

    # Otherwise, we're ready to proceed
    return True
