"""
Node execution context for workflow_engine_v2.

Provides a unified context for node execution with access to input data,
node configuration, execution metadata, and utility methods.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import TriggerInfo
from shared.models.execution_new import Execution
from shared.models.workflow import Node


class NodeExecutionContext:
    """Context for node execution containing all necessary data and utilities."""

    def __init__(
        self,
        node: Node,
        input_data: Dict[str, Any],
        execution: Optional[Execution] = None,
        trigger: Optional[TriggerInfo] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.node = node
        self.input_data = input_data
        self.execution = execution
        self.trigger = trigger
        self.metadata = metadata or {}

    @property
    def node_id(self) -> str:
        """Get the node ID."""
        return self.node.id

    @property
    def node_type(self) -> str:
        """Get the node type."""
        return self.node.type

    @property
    def node_subtype(self) -> str:
        """Get the node subtype."""
        return self.node.subtype

    def get_configuration(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from the node."""
        return self.node.configurations.get(key, default)

    def get_input(self, key: str, default: Any = None) -> Any:
        """Get an input value from the input data."""
        return self.input_data.get(key, default)

    def get_trigger_data(self, key: str, default: Any = None) -> Any:
        """Get data from the trigger if available."""
        if not self.trigger or not self.trigger.trigger_data:
            return default
        return self.trigger.trigger_data.get(key, default)

    def get_execution_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the execution if available."""
        if not self.execution or not hasattr(self.execution, "metadata"):
            return default
        return getattr(self.execution, "metadata", {}).get(key, default)

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the context."""
        return self.metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata in the context."""
        self.metadata[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary representation."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "node_subtype": self.node_subtype,
            "input_data": self.input_data,
            "configurations": self.node.configurations,
            "metadata": self.metadata,
            "execution_id": self.execution.execution_id if self.execution else None,
            "trigger_type": self.trigger.trigger_type if self.trigger else None,
        }


__all__ = ["NodeExecutionContext"]
