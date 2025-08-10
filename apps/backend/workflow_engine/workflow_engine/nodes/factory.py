"""
Node Executor Factory.

Factory for creating node executors based on node type.
Uses unified enums for consistent node type handling.
"""

from typing import Dict, Optional, Type

try:
    from shared.models import NodeType
except ImportError:
    # Fallback if shared models not available
    NodeType = None

from .action_node import ActionNodeExecutor
from .ai_agent_node import AIAgentNodeExecutor
from .base import BaseNodeExecutor
from .external_action_node import ExternalActionNodeExecutor
from .flow_node import FlowNodeExecutor
from .human_loop_node import HumanLoopNodeExecutor
from .memory_node import MemoryNodeExecutor
from .tool_node import ToolNodeExecutor
from .trigger_node import TriggerNodeExecutor


class NodeExecutorFactory:
    """Factory for creating node executors."""

    _executors: Dict[str, Type[BaseNodeExecutor]] = {}

    @classmethod
    def register_executor(cls, node_type: str, executor_class: Type[BaseNodeExecutor]) -> None:
        """Register a node executor for a specific node type."""
        cls._executors[node_type] = executor_class

    @classmethod
    def create_executor(
        cls, node_type: str, subtype: Optional[str] = None
    ) -> Optional[BaseNodeExecutor]:
        """Create a node executor for the given node type."""
        # Use node type directly - no conversion needed
        executor_class = cls._executors.get(node_type)
        if executor_class:
            # Pass subtype to constructor if provided
            executor = executor_class(subtype=subtype)
            return executor
        return None

    @classmethod
    def get_supported_node_types(cls) -> list[str]:
        """Get list of supported node types."""
        return list(cls._executors.keys())

    @classmethod
    def is_supported(cls, node_type: str) -> bool:
        """Check if a node type is supported."""
        return node_type in cls._executors


# Global factory instance
_node_executor_factory = NodeExecutorFactory()


def get_node_executor_factory() -> NodeExecutorFactory:
    """Get the global node executor factory instance."""
    return _node_executor_factory


def register_default_executors() -> None:
    """Register all default node executors using authoritative shared model enums."""
    factory = get_node_executor_factory()

    if NodeType:
        # Use authoritative shared model enums directly
        factory.register_executor(NodeType.TRIGGER.value, TriggerNodeExecutor)
        factory.register_executor(NodeType.AI_AGENT.value, AIAgentNodeExecutor)
        factory.register_executor(NodeType.ACTION.value, ActionNodeExecutor)
        factory.register_executor(NodeType.FLOW.value, FlowNodeExecutor)
        factory.register_executor(NodeType.HUMAN_IN_THE_LOOP.value, HumanLoopNodeExecutor)
        factory.register_executor(NodeType.TOOL.value, ToolNodeExecutor)
        factory.register_executor(NodeType.MEMORY.value, MemoryNodeExecutor)
        factory.register_executor(NodeType.EXTERNAL_ACTION.value, ExternalActionNodeExecutor)

        # Register legacy format aliases for backward compatibility
        factory.register_executor("TRIGGER_NODE", TriggerNodeExecutor)
        factory.register_executor("AI_AGENT_NODE", AIAgentNodeExecutor)
        factory.register_executor("ACTION_NODE", ActionNodeExecutor)
        factory.register_executor("FLOW_NODE", FlowNodeExecutor)
        factory.register_executor("HUMAN_IN_THE_LOOP_NODE", HumanLoopNodeExecutor)
        factory.register_executor("TOOL_NODE", ToolNodeExecutor)
        factory.register_executor("MEMORY_NODE", MemoryNodeExecutor)
        factory.register_executor("EXTERNAL_ACTION_NODE", ExternalActionNodeExecutor)
    else:
        # Fallback - should not be needed with proper shared models
        raise ImportError("Cannot import shared models NodeType - check shared models installation")


# Register all executors
register_default_executors()
