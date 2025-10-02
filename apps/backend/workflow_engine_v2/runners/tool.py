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
from shared.models.workflow import Node
from workflow_engine_v2.core.template import render_structure
from workflow_engine_v2.runners.base import NodeRunner


class ToolRunner(NodeRunner):
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        payload = inputs.get("result", inputs)
        engine_ctx = inputs.get("_ctx") if isinstance(inputs, dict) else None
        ctx = {
            "input": payload,
            "config": node.configurations,
            "trigger": {"type": trigger.trigger_type, "data": trigger.trigger_data},
            "nodes_id": getattr(engine_ctx, "node_outputs", {}) if engine_ctx else {},
            "nodes_name": getattr(engine_ctx, "node_outputs_by_name", {}) if engine_ctx else {},
        }
        templated = render_structure(payload, ctx)
        tool_name = templated.get("tool_name") if isinstance(templated, dict) else None
        function_args = templated.get("function_args") if isinstance(templated, dict) else None
        # Stub implementation: echo back inputs in a schema-aligned envelope
        result = {
            "tool": node.subtype,
            "invoked": bool(tool_name),
            "tool_name": tool_name,
            "args": function_args or templated,
        }
        out = {
            "result": result,
            "success": True,
            "error_message": "",
            "execution_time": 0.0,
            "cached": False,
        }
        return {"result": out}


__all__ = ["ToolRunner"]
