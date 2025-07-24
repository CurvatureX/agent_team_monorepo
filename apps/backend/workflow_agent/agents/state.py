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
    GENERATION = "generation"
    DEBUGGING = "debugging"
    COMPLETED = "completed"


class WorkflowOrigin(str, Enum):
    """Workflow origin types"""

    NEW_WORKFLOW = "new_workflow"
    FROM_TEMPLATE = "from_template"


class Conversation(TypedDict):
    """Conversation message"""

    role: str
    text: str


class ClarificationContext(TypedDict):
    """Context for clarification stage"""

    origin: WorkflowOrigin
    pending_questions: List[str]  # 当前 Clarification 阶段待确认的问题


class TemplateWorkflow(TypedDict):
    """Template workflow information"""

    id: str  # 模板 ID
    original_workflow: object  # 模板的原始内容
    description: str  # 模板的描述


class RetrievedDocument(TypedDict):
    id: str  # Vector store ID or URL
    content: str  # Document content or snippet
    metadata: Dict[str, Any]  # Source info (title, date, etc.)
    score: float  # Relevance score


class RAGContext(TypedDict):
    last_query: str  # The query that triggered retrieval
    retrieved: List[RetrievedDocument]  # Raw retrieval results
    selected: List[str]  # IDs of docs chosen for generation
    summary: NotRequired[str]  # Optional summary of selected docs


class WorkflowState(TypedDict):
    """Simplified workflow state based on new architecture"""

    # 元数据
    metadata: Dict[str, Any]

    # 当前阶段
    stage: WorkflowStage
    # 前一个阶段
    previous_stage: NotRequired[str]

    # 执行历史记录
    execution_history: NotRequired[List[str]]
    # 澄清阶段上下文
    clarification_context: ClarificationContext

    conversations: List[Conversation]  # 用户和AI Agent的全部对话
    intent_summary: str  # AI根据对话总结的用户意图
    gaps: List[str]  # 能力差距分析结果
    alternatives: List[str]  # 提供的替代方案

    # 模板工作流支持
    template_workflow: NotRequired[TemplateWorkflow]

    current_workflow: object  # 当前生成的workflow
    debug_result: str  # 调试结果
    debug_loop_count: int

    # RAG-specific context
    rag: NotRequired[RAGContext]
