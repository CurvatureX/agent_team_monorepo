"""Runner factory mapping node type/subtype to a concrete runner."""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.node_enums import ActionSubtype, AIAgentSubtype, FlowSubtype, NodeType

# Use absolute imports
from shared.models.workflow import Node

from .action import DataTransformationRunner, HttpRequestRunner
from .ai import AIAgentRunner
from .ai_anthropic import AnthropicClaudeRunner
from .ai_gemini import GoogleGeminiRunner
from .ai_openai import OpenAIChatGPTRunner
from .base import PassthroughRunner, TriggerRunner
from .external import ExternalActionRunner
from .flow import DelayRunner, FilterRunner, IfRunner, MergeRunner, SortRunner
from .hil import HILRunner
from .memory import MemoryRunner
from .tool import ToolRunner


def _as_node_type(t) -> NodeType:
    return t if isinstance(t, NodeType) else NodeType(str(t))


def default_runner_for(node: Node):
    ntype = _as_node_type(node.type)
    subtype = str(node.subtype)
    if ntype == NodeType.TRIGGER:
        return TriggerRunner()
    if ntype == NodeType.FLOW:
        try:
            fsub = FlowSubtype(subtype)
        except Exception:
            fsub = None
        if fsub == FlowSubtype.IF:
            return IfRunner()
        if fsub == FlowSubtype.MERGE:
            return MergeRunner()
        if fsub == FlowSubtype.SPLIT:
            from .flow import SplitRunner

            return SplitRunner()
        if fsub == FlowSubtype.FILTER:
            return FilterRunner()
        if fsub == FlowSubtype.SORT:
            return SortRunner()
        if fsub == FlowSubtype.WAIT:
            from .flow import WaitRunner

            return WaitRunner()
        if fsub == FlowSubtype.DELAY:
            return DelayRunner()
        if fsub == FlowSubtype.TIMEOUT:
            from .flow import TimeoutRunner

            return TimeoutRunner()
        if fsub == FlowSubtype.LOOP:
            from .flow import LoopRunner

            return LoopRunner()
        if fsub == FlowSubtype.FOR_EACH:
            from .flow import ForEachRunner

            return ForEachRunner()
        return PassthroughRunner()
    if ntype == NodeType.ACTION:
        try:
            asub = ActionSubtype(subtype)
        except Exception:
            asub = None
        if asub == ActionSubtype.HTTP_REQUEST:
            return HttpRequestRunner()
        return DataTransformationRunner()
    if ntype == NodeType.EXTERNAL_ACTION:
        return ExternalActionRunner()
    if ntype == NodeType.MEMORY:
        return MemoryRunner()
    if ntype == NodeType.TOOL:
        return ToolRunner()
    if ntype == NodeType.AI_AGENT:
        # Route to dedicated runner based on AI provider subtype
        try:
            ai_subtype = AIAgentSubtype(subtype)
        except Exception:
            ai_subtype = None

        if ai_subtype == AIAgentSubtype.ANTHROPIC_CLAUDE:
            return AnthropicClaudeRunner()
        elif ai_subtype == AIAgentSubtype.OPENAI_CHATGPT:
            return OpenAIChatGPTRunner()
        elif ai_subtype == AIAgentSubtype.GOOGLE_GEMINI:
            return GoogleGeminiRunner()

        # Fallback to generic AIAgentRunner for unknown subtypes
        return AIAgentRunner()
    if ntype == NodeType.HUMAN_IN_THE_LOOP:
        return HILRunner()
    return PassthroughRunner()


__all__ = ["default_runner_for"]
