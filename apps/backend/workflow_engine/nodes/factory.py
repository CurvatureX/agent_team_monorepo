"""
Node Executor Factory.

Simplified factory pattern for creating node executors.
"""

import logging
from typing import Dict, Optional, Set, Type

from .base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class NodeExecutorFactory:
    """Factory for creating node executors."""

    _executors: Dict[str, Type[BaseNodeExecutor]] = {}
    _registered_types: Set[str] = set()

    @classmethod
    def register(cls, node_type: str) -> callable:
        """Decorator to register a node executor."""

        def decorator(executor_class: Type[BaseNodeExecutor]) -> Type[BaseNodeExecutor]:
            cls.register_executor(node_type, executor_class)
            return executor_class

        return decorator

    @classmethod
    def register_executor(cls, node_type: str, executor_class: Type[BaseNodeExecutor]) -> None:
        """Register a node executor for a specific node type."""
        cls._executors[node_type] = executor_class
        cls._registered_types.add(node_type)
        logger.info(f"Registered executor for node type: {node_type}")

    @classmethod
    def create_executor(cls, node_type: str, subtype: Optional[str] = None) -> BaseNodeExecutor:
        """Create a node executor for the given node type."""
        logger.info(f"🔧 DEBUG: Available executors: {list(cls._executors.keys())}")
        logger.info(f"🔧 DEBUG: Requested node type: {node_type}")

        executor_class = cls._executors.get(node_type)

        if executor_class:
            logger.debug(f"Creating executor for node type: {node_type} (subtype: {subtype})")
            return executor_class(node_type, subtype)
        else:
            logger.error(f"No executor found for node type: {node_type}")
            raise ValueError(
                f"Unsupported node type: {node_type}. No executor registered for this type."
            )

    @classmethod
    def get_registered_types(cls) -> Set[str]:
        """Get all registered node types."""
        return cls._registered_types.copy()

    @classmethod
    def is_registered(cls, node_type: str) -> bool:
        """Check if a node type is registered."""
        return node_type in cls._registered_types

    @classmethod
    def list_executors(cls) -> Dict[str, str]:
        """List all registered executors."""
        return {
            node_type: executor_class.__name__
            for node_type, executor_class in cls._executors.items()
        }
