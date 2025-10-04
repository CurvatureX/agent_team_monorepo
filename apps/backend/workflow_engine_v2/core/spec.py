"""Node specification registry adapter for workflow_engine_v2 (core)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class SpecNotFoundError(KeyError):
    pass


def _import_spec_registry():
    """Import shared spec registry if available; returns callables or (None, None)."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        from shared.node_specs import get_node_spec, list_available_specs  # type: ignore

        logger.info("✅ Successfully loaded node spec registry from shared.node_specs")
        return get_node_spec, list_available_specs
    except Exception as e:
        logger.error(f"❌ Failed to import node spec registry: {type(e).__name__}: {str(e)}")
        import traceback

        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return None, None


def _to_str(x: Any) -> str:
    return x.value if hasattr(x, "value") else str(x)


def get_spec(node_type: Any, node_subtype: Any) -> BaseModel:
    get_node_spec, _ = _import_spec_registry()
    if get_node_spec is not None:
        try:
            spec = get_node_spec(_to_str(node_type), _to_str(node_subtype))
        except Exception:
            spec = None
        if spec is not None:
            return spec
    # Fallback to minimal stub spec if registry missing or invalid
    fallback_spec = _fallback_spec(_to_str(node_type), _to_str(node_subtype))
    if fallback_spec is not None:
        return fallback_spec
    raise SpecNotFoundError(f"No spec found for {_to_str(node_type)}.{_to_str(node_subtype)}")


def list_specs() -> list[str]:
    _, list_available_specs = _import_spec_registry()
    if list_available_specs is None:
        return []
    try:
        return list_available_specs()
    except Exception:
        return []


def coerce_node_to_v2(node: Any):
    from shared.models.workflow import Node as V2Node

    node_dict = node.model_dump() if hasattr(node, "model_dump") else dict(node)
    return V2Node(**node_dict)


# -------- Fallback minimal spec --------


class _StubSpec(BaseModel):
    node_type: str
    subtype: str

    def validate_configuration(self, config: dict) -> bool:
        """Stub validation - always returns True since we don't have the real spec.

        This is a fallback for when the real spec registry can't be loaded.
        Real validation should be done by the actual spec classes.
        """
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            f"Using stub spec validation for {self.node_type}.{self.subtype} - "
            f"skipping detailed validation (real spec unavailable)"
        )
        return True

    def create_node_instance(self, node_id: str, **kwargs):  # pragma: no cover - simple constructor
        from shared.models.node_enums import (
            ActionSubtype,
            FlowSubtype,
            HumanLoopSubtype,
            MemorySubtype,
            NodeType,
            TriggerSubtype,
        )
        from shared.models.workflow import Node, Port

        ntype = (
            NodeType(self.node_type)
            if self.node_type in NodeType.__members__
            else NodeType(self.node_type)
        )
        # Provide sensible default ports per subtype for validation
        inputs = [Port(id="main", name="main", data_type="any", required=False)]
        outputs = [Port(id="main", name="main", data_type="any", required=False)]
        if self.node_type == NodeType.FLOW.value and self.subtype == FlowSubtype.WAIT.value:
            outputs.append(Port(id="completed", name="completed", data_type="any", required=False))
            outputs.append(Port(id="timeout", name="timeout", data_type="any", required=False))
        if self.node_type == NodeType.FLOW.value and self.subtype == FlowSubtype.FOR_EACH.value:
            outputs.append(Port(id="iteration", name="iteration", data_type="any", required=False))
        return Node(
            id=node_id,
            name=node_id,
            description=f"Stub node for {self.node_type}.{self.subtype}",
            type=ntype,
            subtype=self.subtype,
            configurations={},
            input_params={},
            output_params={},
            input_ports=inputs,
            output_ports=outputs,
        )


def _fallback_spec(node_type: str, subtype: str) -> BaseModel | None:
    # Import enums within function scope to avoid circular imports
    from shared.models.node_enums import (
        ActionSubtype,
        AIAgentSubtype,
        ExternalActionSubtype,
        FlowSubtype,
        HumanLoopSubtype,
        MemorySubtype,
        NodeType,
        TriggerSubtype,
    )

    # Provide stubs for common nodes to keep engine usable in tests
    supported = {
        (NodeType.TRIGGER.value, TriggerSubtype.WEBHOOK.value),
        (NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value),
        (NodeType.TRIGGER.value, TriggerSubtype.CRON.value),
        (NodeType.AI_AGENT.value, AIAgentSubtype.OPENAI_CHATGPT.value),
        (NodeType.AI_AGENT.value, AIAgentSubtype.ANTHROPIC_CLAUDE.value),
        (NodeType.EXTERNAL_ACTION.value, ExternalActionSubtype.SLACK.value),
        (NodeType.EXTERNAL_ACTION.value, ExternalActionSubtype.GITHUB.value),
        (NodeType.EXTERNAL_ACTION.value, ExternalActionSubtype.NOTION.value),
        (NodeType.ACTION.value, ActionSubtype.HTTP_REQUEST.value),
        (NodeType.FLOW.value, FlowSubtype.SORT.value),
        (NodeType.FLOW.value, FlowSubtype.WAIT.value),
        (NodeType.FLOW.value, FlowSubtype.DELAY.value),
        (NodeType.FLOW.value, FlowSubtype.LOOP.value),
        (NodeType.FLOW.value, FlowSubtype.FOR_EACH.value),
        (NodeType.HUMAN_IN_THE_LOOP.value, HumanLoopSubtype.SLACK_INTERACTION.value),
        (NodeType.MEMORY.value, MemorySubtype.KEY_VALUE_STORE.value),
        (NodeType.TOOL.value, "NOTION_MCP_TOOL"),
        (NodeType.TOOL.value, "SLACK_MCP_TOOL"),
        (NodeType.TOOL.value, "DISCORD_MCP_TOOL"),
        (NodeType.TOOL.value, "GOOGLE_CALENDAR_MCP_TOOL"),
        (NodeType.TOOL.value, "FIRECRAWL_MCP_TOOL"),
    }
    if (node_type, subtype) in supported:
        return _StubSpec(node_type=node_type, subtype=subtype)
    return None


__all__ = ["get_spec", "list_specs", "coerce_node_to_v2", "SpecNotFoundError"]
