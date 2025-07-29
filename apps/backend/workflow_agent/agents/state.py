"""
LangGraph state management for Workflow Agent
Simplified architecture with only necessary classes
"""

from enum import Enum
from typing import Any, Dict, List, NotRequired, TypedDict


class WorkflowStage(str, Enum):
    """Simplified workflow stages based on new architecture"""

    CLARIFICATION = "clarification"
    NEGOTIATION = "negotiation"
    GAP_ANALYSIS = "gap_analysis"
    ALTERNATIVE_GENERATION = "alternative_generation"
    WORKFLOW_GENERATION = "workflow_generation"
    DEBUG = "debug"
    COMPLETED = "completed"


class WorkflowOrigin(str, Enum):
    """Workflow origin types - 对应proto的origin字段值"""
    CREATE = "create"
    EDIT = "edit"
    COPY = "copy"


class ClarificationPurpose(str, Enum):
    """澄清目的类型 - 对应proto的purpose字段值"""
    
    INITIAL_INTENT = "initial_intent"
    TEMPLATE_MODIFICATION = "template_modification"
    GAP_RESOLUTION = "gap_resolution"


class Conversation(TypedDict):
    """Conversation message - 完全对应proto.Conversation"""

    role: str  # user, assistant, system
    text: str
    timestamp: NotRequired[int]  # timestamp in milliseconds
    metadata: NotRequired[Dict[str, str]]  # additional metadata


class ClarificationContext(TypedDict):
    """Context for clarification stage - 完全对应proto.ClarificationContext"""

    purpose: NotRequired[ClarificationPurpose]  # 对应proto.purpose
    collected_info: NotRequired[Dict[str, str]]  # 对应proto.collected_info
    pending_questions: List[str]  # 对应proto.pending_questions
    origin: WorkflowOrigin  # 对应proto.origin


class RetrievedDocument(TypedDict):
    """RAG检索结果 - 对应proto.RAGResult"""
    
    id: str  # 对应proto.id
    node_type: NotRequired[str]  # 对应proto.node_type
    title: NotRequired[str]  # 对应proto.title
    description: NotRequired[str]  # 对应proto.description
    content: str  # 对应proto.content
    similarity: float  # 对应proto.similarity
    metadata: NotRequired[Dict[str, str]]  # 对应proto.metadata


class RAGContext(TypedDict):
    results: List[RetrievedDocument] 
    query: str  
    timestamp: NotRequired[int]
    metadata: NotRequired[Dict[str, str]] 


class AlternativeOption(TypedDict):
    """Alternative solution option - 对应proto.AlternativeOption"""
    
    id: str
    title: str
    description: str
    approach: str  # 技术方案描述
    trade_offs: List[str]  # 权衡说明
    complexity: str  # simple, medium, complex


class WorkflowState(TypedDict):
    session_id: str
    user_id: str
    created_at: int  # timestamp in milliseconds
    updated_at: int  # timestamp in milliseconds

    # 当前阶段 (对应proto: stage, previous_stage)
    stage: WorkflowStage
    previous_stage: NotRequired[WorkflowStage]
    intent_summary: str

    execution_history: NotRequired[List[str]]
    clarification_context: ClarificationContext

    conversations: List[Conversation]

    gaps: List[str]
    alternatives: List[AlternativeOption]  # 改为对象列表而非字符串

    current_workflow: object  # 将序列化为current_workflow_json
    debug_result: str
    debug_loop_count: int

    workflow_context: NotRequired[Dict[str, Any]]  # 将映射到WorkflowContext

    # RAG上下文 (对应proto: rag_context)
    rag: NotRequired[RAGContext]
