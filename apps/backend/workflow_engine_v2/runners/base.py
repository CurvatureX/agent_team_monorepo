"""Base runner types for workflow_engine_v2."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import TriggerInfo
from shared.models.node_enums import NodeType
from shared.models.workflow_new import Node


class NodeRunner(ABC):
    @abstractmethod
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        raise NotImplementedError


class TriggerRunner(NodeRunner):
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        return {"main": trigger.trigger_data}


class PassthroughRunner(NodeRunner):
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        if "main" in inputs:
            return {"main": inputs["main"]}
        return {"main": inputs}


__all__ = [
    "NodeRunner",
    "TriggerRunner",
    "PassthroughRunner",
]
