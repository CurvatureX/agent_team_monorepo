"""Tool node runner (e.g., MCP tools)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import TriggerInfo
from shared.models.workflow_new import Node

from ..core.template import render_structure
from .base import NodeRunner


class ToolRunner(NodeRunner):
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        payload = inputs.get("main", inputs)
        engine_ctx = inputs.get("_ctx") if isinstance(inputs, dict) else None
        ctx = {
            "input": payload,
            "config": node.configurations,
            "trigger": {"type": trigger.trigger_type, "data": trigger.trigger_data},
            "nodes_id": getattr(engine_ctx, "node_outputs", {}) if engine_ctx else {},
            "nodes_name": getattr(engine_ctx, "node_outputs_by_name", {}) if engine_ctx else {},
        }
        templated_args = render_structure(payload, ctx)
        return {"main": {"tool": node.subtype, "args": templated_args, "ok": True}}


__all__ = ["ToolRunner"]
