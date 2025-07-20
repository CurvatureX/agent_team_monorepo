"""
Node Executor Factory.

Factory for creating node executors based on node type.
"""

from typing import Dict, Type, Optional
from .base import BaseNodeExecutor
from .trigger_node import TriggerNodeExecutor
from .ai_agent_node import AIAgentNodeExecutor
from .action_node import ActionNodeExecutor
from .flow_node import FlowNodeExecutor
from .human_loop_node import HumanLoopNodeExecutor
from .tool_node import ToolNodeExecutor
from .memory_node import MemoryNodeExecutor


class NodeExecutorFactory:
    """Factory for creating node executors."""
    
    _executors: Dict[str, Type[BaseNodeExecutor]] = {}
    
    @classmethod
    def register_executor(cls, node_type: str, executor_class: Type[BaseNodeExecutor]) -> None:
        """Register a node executor for a specific node type."""
        cls._executors[node_type] = executor_class
    
    @classmethod
    def create_executor(cls, node_type: str) -> Optional[BaseNodeExecutor]:
        """Create a node executor for the given node type."""
        executor_class = cls._executors.get(node_type)
        if executor_class:
            return executor_class()
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
    """Register all default node executors."""
    factory = get_node_executor_factory()
    factory.register_executor("TRIGGER_NODE", TriggerNodeExecutor)
    factory.register_executor("AI_AGENT_NODE", AIAgentNodeExecutor)
    factory.register_executor("ACTION_NODE", ActionNodeExecutor)
    factory.register_executor("FLOW_NODE", FlowNodeExecutor)
    factory.register_executor("HUMAN_IN_THE_LOOP_NODE", HumanLoopNodeExecutor)
    factory.register_executor("TOOL_NODE", ToolNodeExecutor)
    factory.register_executor("MEMORY_NODE", MemoryNodeExecutor)


# Register all executors
register_default_executors()
