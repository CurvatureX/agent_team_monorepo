"""
Node executor factory for creating appropriate executors.
"""

from typing import Dict, Optional, Type
from .base import BaseNodeExecutor


class NodeExecutorFactory:
    """Factory for creating node executors."""
    
    def __init__(self):
        self._executors: Dict[str, Type[BaseNodeExecutor]] = {}
        self._instances: Dict[str, BaseNodeExecutor] = {}
    
    def register_executor(self, node_type: str, executor_class: Type[BaseNodeExecutor]) -> None:
        """Register an executor class for a node type."""
        self._executors[node_type] = executor_class
    
    def get_executor(self, node_type: str) -> Optional[BaseNodeExecutor]:
        """Get executor instance for a node type."""
        if node_type not in self._executors:
            return None
        
        # Use singleton pattern for executors
        if node_type not in self._instances:
            executor_class = self._executors[node_type]
            self._instances[node_type] = executor_class()
        
        return self._instances[node_type]
    
    def get_executor_for_node(self, node) -> Optional[BaseNodeExecutor]:
        """Get executor for a specific node based on its type."""
        if hasattr(node, 'type'):
            # Convert protobuf enum to string if needed
            node_type = str(node.type).split('.')[-1] if hasattr(node.type, 'name') else str(node.type)
            return self.get_executor(node_type)
        return None
    
    def list_supported_types(self) -> list:
        """List all supported node types."""
        return list(self._executors.keys())
    
    def clear(self) -> None:
        """Clear all registered executors."""
        self._executors.clear()
        self._instances.clear()


# Global factory instance
_factory = NodeExecutorFactory()

def get_node_executor_factory() -> NodeExecutorFactory:
    """Get the global node executor factory."""
    return _factory

def register_default_executors() -> None:
    """Register all default node executors."""
    # Import here to avoid circular imports
    try:
        from .trigger_node import TriggerNodeExecutor
        from .ai_agent_node import AIAgentNodeExecutor
        from .external_action_node import ExternalActionNodeExecutor
        from .action_node import ActionNodeExecutor
        from .flow_node import FlowNodeExecutor
        from .human_loop_node import HumanLoopNodeExecutor
        from .tool_node import ToolNodeExecutor
        from .memory_node import MemoryNodeExecutor
        
        factory = get_node_executor_factory()
        factory.register_executor("TRIGGER_NODE", TriggerNodeExecutor)
        factory.register_executor("AI_AGENT_NODE", AIAgentNodeExecutor)
        factory.register_executor("EXTERNAL_ACTION_NODE", ExternalActionNodeExecutor)
        factory.register_executor("ACTION_NODE", ActionNodeExecutor)
        factory.register_executor("FLOW_NODE", FlowNodeExecutor)
        factory.register_executor("HUMAN_IN_THE_LOOP_NODE", HumanLoopNodeExecutor)
        factory.register_executor("TOOL_NODE", ToolNodeExecutor)
        factory.register_executor("MEMORY_NODE", MemoryNodeExecutor)
    except ImportError:
        # Executors not yet implemented
        pass 