"""
Node Specifications System v2.0

A clean, extensible framework for defining workflow node types with complete type safety
and validation. Features provider-based AI agents where functionality is determined by
system prompts rather than hardcoded roles.

Key Components:
- Provider-based AI agents (Gemini, OpenAI, Claude)
- Type-safe parameter validation
- Port compatibility checking
- Comprehensive documentation and examples
- Flexible system prompt-driven behavior

AI Agent Revolution:
Instead of rigid predefined roles like "REPORT_GENERATOR", we now have flexible
provider-based nodes where any functionality can be achieved through system prompts.

Example:
    # Old approach: Limited, hardcoded
    "AI_AGENT_NODE.REPORT_GENERATOR"

    # New approach: Flexible, prompt-driven
    "AI_AGENT_NODE.CLAUDE_NODE" with custom system prompt
"""

# AI Agent specs
from .AI_AGENT.OPENAI_CHATGPT import OPENAI_CHATGPT_SPEC
from .base import (
    COMMON_CONFIGS,
    COMMON_PORTS,
    BaseNodeSpec,
    ConnectionSpec,
    ConnectionType,
    DataFormat,
    InputPortSpec,
    NodeSpec,
    OutputPortSpec,
    ParameterDef,
    ParameterType,
)
from .TRIGGER.CRON import CRON_TRIGGER_SPEC
from .TRIGGER.EMAIL import EMAIL_TRIGGER_SPEC
from .TRIGGER.GITHUB import GITHUB_TRIGGER_SPEC

# Import all node specifications for easy access
from .TRIGGER.MANUAL import MANUAL_TRIGGER_SPEC
from .TRIGGER.SLACK import SLACK_TRIGGER_SPEC
from .TRIGGER.WEBHOOK import WEBHOOK_TRIGGER_SPEC

try:
    from .AI_AGENT.ANTHROPIC_CLAUDE import ANTHROPIC_CLAUDE_SPEC  # type: ignore
except Exception:  # pragma: no cover - optional spec may have JSON-like examples
    ANTHROPIC_CLAUDE_SPEC = None  # type: ignore
try:
    from .AI_AGENT.GOOGLE_GEMINI import GOOGLE_GEMINI_SPEC  # type: ignore
except Exception:  # pragma: no cover - optional spec may have JSON-like examples
    GOOGLE_GEMINI_SPEC = None  # type: ignore

# External Action specs
from .EXTERNAL_ACTION.SLACK import SLACK_EXTERNAL_ACTION_SPEC

try:
    from .EXTERNAL_ACTION.GITHUB import GITHUB_EXTERNAL_ACTION_SPEC  # type: ignore
except Exception:
    GITHUB_EXTERNAL_ACTION_SPEC = None  # type: ignore
try:
    from .EXTERNAL_ACTION.NOTION import NOTION_EXTERNAL_ACTION_SPEC  # type: ignore
except Exception:
    NOTION_EXTERNAL_ACTION_SPEC = None  # type: ignore
try:
    from .EXTERNAL_ACTION.GOOGLE_CALENDAR import (
        GOOGLE_CALENDAR_EXTERNAL_ACTION_SPEC,  # type: ignore
    )
except Exception:
    GOOGLE_CALENDAR_EXTERNAL_ACTION_SPEC = None  # type: ignore
try:
    from .EXTERNAL_ACTION.FIRECRAWL import FIRECRAWL_EXTERNAL_ACTION_SPEC  # type: ignore
except Exception:
    FIRECRAWL_EXTERNAL_ACTION_SPEC = None  # type: ignore
try:
    from .EXTERNAL_ACTION.DISCORD_ACTION import DISCORD_ACTION_SPEC  # type: ignore
except Exception:
    DISCORD_ACTION_SPEC = None  # type: ignore
try:
    from .EXTERNAL_ACTION.TELEGRAM_ACTION import TELEGRAM_ACTION_SPEC  # type: ignore
except Exception:
    TELEGRAM_ACTION_SPEC = None  # type: ignore

from .ACTION.DATA_TRANSFORMATION import DATA_TRANSFORMATION_ACTION_SPEC
from .ACTION.HTTP_REQUEST import HTTP_REQUEST_ACTION_SPEC
from .FLOW.DELAY import DELAY_FLOW_SPEC
from .FLOW.FILTER import FILTER_FLOW_SPEC
from .FLOW.IF import IF_FLOW_SPEC
from .FLOW.LOOP import LOOP_FLOW_SPEC
from .FLOW.MERGE import MERGE_FLOW_SPEC
from .FLOW.SORT import SORT_FLOW_SPEC
from .FLOW.WAIT import WAIT_FLOW_SPEC

# Human-in-the-loop specs
from .HUMAN_IN_THE_LOOP.SLACK_INTERACTION import SLACK_INTERACTION_SPEC

try:
    from .HUMAN_IN_THE_LOOP.GMAIL_INTERACTION import GMAIL_INTERACTION_HIL_SPEC  # type: ignore
except Exception:
    GMAIL_INTERACTION_HIL_SPEC = None  # type: ignore
try:
    from .HUMAN_IN_THE_LOOP.OUTLOOK_INTERACTION import OUTLOOK_INTERACTION_HIL_SPEC  # type: ignore
except Exception:
    OUTLOOK_INTERACTION_HIL_SPEC = None  # type: ignore
try:
    from .HUMAN_IN_THE_LOOP.DISCORD_INTERACTION import DISCORD_INTERACTION_HIL_SPEC  # type: ignore
except Exception:
    DISCORD_INTERACTION_HIL_SPEC = None  # type: ignore
try:
    from .HUMAN_IN_THE_LOOP.TELEGRAM_INTERACTION import (
        TELEGRAM_INTERACTION_HIL_SPEC,  # type: ignore
    )
except Exception:
    TELEGRAM_INTERACTION_HIL_SPEC = None  # type: ignore
try:
    from .HUMAN_IN_THE_LOOP.MANUAL_REVIEW import MANUAL_REVIEW_HIL_SPEC  # type: ignore
except Exception:
    MANUAL_REVIEW_HIL_SPEC = None  # type: ignore

from .MEMORY.CONVERSATION_BUFFER import CONVERSATION_BUFFER_MEMORY_SPEC
from .MEMORY.KEY_VALUE_STORE import KEY_VALUE_STORE_MEMORY_SPEC
from .MEMORY.VECTOR_DATABASE import VECTOR_DATABASE_MEMORY_SPEC
from .TOOL.DISCORD_MCP_TOOL import DISCORD_MCP_TOOL_SPEC
from .TOOL.FIRECRAWL_MCP_TOOL import FIRECRAWL_MCP_TOOL_SPEC
from .TOOL.GOOGLE_CALENDAR_MCP_TOOL import GOOGLE_CALENDAR_MCP_TOOL_SPEC
from .TOOL.NOTION_MCP_TOOL import NOTION_MCP_TOOL_SPEC
from .TOOL.SLACK_MCP_TOOL import SLACK_MCP_TOOL_SPEC

# Registry of all available node specifications
NODE_SPECS_REGISTRY = {
    # TRIGGER specifications
    "TRIGGER.MANUAL": MANUAL_TRIGGER_SPEC,
    "TRIGGER.WEBHOOK": WEBHOOK_TRIGGER_SPEC,
    "TRIGGER.CRON": CRON_TRIGGER_SPEC,
    "TRIGGER.GITHUB": GITHUB_TRIGGER_SPEC,
    "TRIGGER.SLACK": SLACK_TRIGGER_SPEC,
    "TRIGGER.EMAIL": EMAIL_TRIGGER_SPEC,
    # AI_AGENT specifications
    "AI_AGENT.OPENAI_CHATGPT": OPENAI_CHATGPT_SPEC,
    **({"AI_AGENT.ANTHROPIC_CLAUDE": ANTHROPIC_CLAUDE_SPEC} if ANTHROPIC_CLAUDE_SPEC else {}),
    **({"AI_AGENT.GOOGLE_GEMINI": GOOGLE_GEMINI_SPEC} if GOOGLE_GEMINI_SPEC else {}),
    # EXTERNAL_ACTION specifications
    "EXTERNAL_ACTION.SLACK": SLACK_EXTERNAL_ACTION_SPEC,
    **(
        {"EXTERNAL_ACTION.GITHUB": GITHUB_EXTERNAL_ACTION_SPEC}
        if GITHUB_EXTERNAL_ACTION_SPEC
        else {}
    ),
    **(
        {"EXTERNAL_ACTION.NOTION": NOTION_EXTERNAL_ACTION_SPEC}
        if NOTION_EXTERNAL_ACTION_SPEC
        else {}
    ),
    **(
        {"EXTERNAL_ACTION.GOOGLE_CALENDAR": GOOGLE_CALENDAR_EXTERNAL_ACTION_SPEC}
        if GOOGLE_CALENDAR_EXTERNAL_ACTION_SPEC
        else {}
    ),
    **(
        {"EXTERNAL_ACTION.FIRECRAWL": FIRECRAWL_EXTERNAL_ACTION_SPEC}
        if FIRECRAWL_EXTERNAL_ACTION_SPEC
        else {}
    ),
    **({"EXTERNAL_ACTION.DISCORD_ACTION": DISCORD_ACTION_SPEC} if DISCORD_ACTION_SPEC else {}),
    **({"EXTERNAL_ACTION.TELEGRAM_ACTION": TELEGRAM_ACTION_SPEC} if TELEGRAM_ACTION_SPEC else {}),
    # ACTION specifications
    "ACTION.HTTP_REQUEST": HTTP_REQUEST_ACTION_SPEC,
    "ACTION.DATA_TRANSFORMATION": DATA_TRANSFORMATION_ACTION_SPEC,
    # FLOW specifications
    "FLOW.IF": IF_FLOW_SPEC,
    "FLOW.LOOP": LOOP_FLOW_SPEC,
    "FLOW.MERGE": MERGE_FLOW_SPEC,
    "FLOW.FILTER": FILTER_FLOW_SPEC,
    "FLOW.SORT": SORT_FLOW_SPEC,
    "FLOW.WAIT": WAIT_FLOW_SPEC,
    "FLOW.DELAY": DELAY_FLOW_SPEC,
    # HUMAN_IN_THE_LOOP specifications
    "HUMAN_IN_THE_LOOP.SLACK_INTERACTION": SLACK_INTERACTION_SPEC,
    **(
        {"HUMAN_IN_THE_LOOP.GMAIL_INTERACTION": GMAIL_INTERACTION_HIL_SPEC}
        if GMAIL_INTERACTION_HIL_SPEC
        else {}
    ),
    **(
        {"HUMAN_IN_THE_LOOP.OUTLOOK_INTERACTION": OUTLOOK_INTERACTION_HIL_SPEC}
        if OUTLOOK_INTERACTION_HIL_SPEC
        else {}
    ),
    **(
        {"HUMAN_IN_THE_LOOP.DISCORD_INTERACTION": DISCORD_INTERACTION_HIL_SPEC}
        if DISCORD_INTERACTION_HIL_SPEC
        else {}
    ),
    **(
        {"HUMAN_IN_THE_LOOP.TELEGRAM_INTERACTION": TELEGRAM_INTERACTION_HIL_SPEC}
        if TELEGRAM_INTERACTION_HIL_SPEC
        else {}
    ),
    **(
        {"HUMAN_IN_THE_LOOP.MANUAL_REVIEW": MANUAL_REVIEW_HIL_SPEC}
        if MANUAL_REVIEW_HIL_SPEC
        else {}
    ),
    # TOOL specifications
    "TOOL.NOTION_MCP_TOOL": NOTION_MCP_TOOL_SPEC,
    "TOOL.GOOGLE_CALENDAR_MCP_TOOL": GOOGLE_CALENDAR_MCP_TOOL_SPEC,
    "TOOL.SLACK_MCP_TOOL": SLACK_MCP_TOOL_SPEC,
    "TOOL.FIRECRAWL_MCP_TOOL": FIRECRAWL_MCP_TOOL_SPEC,
    "TOOL.DISCORD_MCP_TOOL": DISCORD_MCP_TOOL_SPEC,
    # MEMORY specifications
    "MEMORY.VECTOR_DATABASE": VECTOR_DATABASE_MEMORY_SPEC,
    "MEMORY.CONVERSATION_BUFFER": CONVERSATION_BUFFER_MEMORY_SPEC,
    "MEMORY.KEY_VALUE_STORE": KEY_VALUE_STORE_MEMORY_SPEC,
}


def get_node_spec(node_type: str, node_subtype: str):
    """Get a node specification by type and subtype."""
    key = f"{node_type}.{node_subtype}"
    return NODE_SPECS_REGISTRY.get(key)


def list_available_specs():
    """List all available node specifications."""
    return list(NODE_SPECS_REGISTRY.keys())


class NodeSpecRegistryWrapper:
    """Wrapper class for the NODE_SPECS_REGISTRY dictionary to provide expected methods."""

    def __init__(self, registry_dict):
        self._registry = registry_dict

    def get_node_types(self):
        """Get all node types and their subtypes."""
        types_dict = {}
        for key, spec in self._registry.items():
            if "." not in key:
                continue
            node_type, subtype = key.split(".", 1)
            if node_type not in types_dict:
                types_dict[node_type] = []
            types_dict[node_type].append(subtype)
        return types_dict

    def get_spec(self, node_type: str, subtype: str):
        """Get a node specification by type and subtype."""
        key = f"{node_type}.{subtype}"
        return self._registry.get(key)

    def list_all_specs(self):
        """List all available node specifications."""
        return list(self._registry.values())


# Create the wrapped registry instance
_wrapped_registry = NodeSpecRegistryWrapper(NODE_SPECS_REGISTRY)


# Version info
__version__ = "2.0.0"
__status__ = "Revamped with provider-based AI agents"

__all__ = [
    # Version info
    "__version__",
    "__status__",
    # Base classes
    "NodeSpec",
    "ParameterDef",
    "ParameterType",
    "InputPortSpec",
    "OutputPortSpec",
    "DataFormat",
    "ConnectionType",
    "ConnectionSpec",
    "BaseNodeSpec",
    "COMMON_CONFIGS",
    "COMMON_PORTS",
    # Specifications
    "MANUAL_TRIGGER_SPEC",
    "WEBHOOK_TRIGGER_SPEC",
    "CRON_TRIGGER_SPEC",
    "GITHUB_TRIGGER_SPEC",
    "SLACK_TRIGGER_SPEC",
    "EMAIL_TRIGGER_SPEC",
    "OPENAI_CHATGPT_SPEC",
    "ANTHROPIC_CLAUDE_SPEC",
    "GOOGLE_GEMINI_SPEC",
    "SLACK_EXTERNAL_ACTION_SPEC",
    "GITHUB_EXTERNAL_ACTION_SPEC",
    "NOTION_EXTERNAL_ACTION_SPEC",
    "GOOGLE_CALENDAR_EXTERNAL_ACTION_SPEC",
    "FIRECRAWL_EXTERNAL_ACTION_SPEC",
    "DISCORD_ACTION_SPEC",
    "TELEGRAM_ACTION_SPEC",
    "HTTP_REQUEST_ACTION_SPEC",
    "DATA_TRANSFORMATION_ACTION_SPEC",
    "IF_FLOW_SPEC",
    "LOOP_FLOW_SPEC",
    "MERGE_FLOW_SPEC",
    "FILTER_FLOW_SPEC",
    "SORT_FLOW_SPEC",
    "WAIT_FLOW_SPEC",
    "DELAY_FLOW_SPEC",
    "SLACK_INTERACTION_SPEC",
    "GMAIL_INTERACTION_HIL_SPEC",
    "OUTLOOK_INTERACTION_HIL_SPEC",
    "DISCORD_INTERACTION_HIL_SPEC",
    "TELEGRAM_INTERACTION_HIL_SPEC",
    "MANUAL_REVIEW_HIL_SPEC",
    "NOTION_MCP_TOOL_SPEC",
    "GOOGLE_CALENDAR_MCP_TOOL_SPEC",
    "SLACK_MCP_TOOL_SPEC",
    "FIRECRAWL_MCP_TOOL_SPEC",
    "DISCORD_MCP_TOOL_SPEC",
    "VECTOR_DATABASE_MEMORY_SPEC",
    "CONVERSATION_BUFFER_MEMORY_SPEC",
    "KEY_VALUE_STORE_MEMORY_SPEC",
    # Registry and utilities
    "NODE_SPECS_REGISTRY",
    "NodeSpecRegistryWrapper",
    "_wrapped_registry",
    "get_node_spec",
    "list_available_specs",
]
