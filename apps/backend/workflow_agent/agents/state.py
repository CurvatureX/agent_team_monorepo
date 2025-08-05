"""
LangGraph state management for Workflow Agent
State definitions for the 4-node architecture
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


class RetrievedDocument(TypedDict):
    """RAG retrieval result"""
    
    id: str
    node_type: NotRequired[str]
    title: NotRequired[str]
    description: NotRequired[str]
    content: str
    similarity: float
    metadata: NotRequired[Dict[str, str]]


class RAGContext(TypedDict):
    """RAG context with retrieval results"""
    results: List[RetrievedDocument] 
    query: str  
    timestamp: NotRequired[int]
    metadata: NotRequired[Dict[str, str]] 


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
    clarification_round: NotRequired[int]  # track clarification rounds for limiting
    
    # Gap analysis results
    gap_status: NotRequired[str]  # "has_gap", "no_gap", or "gap_resolved"
    identified_gaps: NotRequired[List[GapDetail]]  # detailed gap information
    selected_alternative_index: NotRequired[int]  # which alternative user selected
    
    # Workflow data
    current_workflow: NotRequired[Any]  # workflow JSON object
    template_workflow: NotRequired[Any]  # template workflow if editing
    workflow_context: NotRequired[Dict[str, Any]]  # workflow metadata
    
    # Debug information
    debug_result: NotRequired[str]
    debug_loop_count: NotRequired[int]
    
    # RAG context
    rag: NotRequired[RAGContext]
    
    # Template information
    template_id: NotRequired[str]  # template ID if using template
