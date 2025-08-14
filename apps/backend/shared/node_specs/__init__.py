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

from .base import (
    ConnectionSpec,
    ConnectionType,
    DataFormat,
    InputPortSpec,
    NodeSpec,
    OutputPortSpec,
    ParameterDef,
    ParameterType,
)
from .registry import NodeSpecRegistry, node_spec_registry
from .validator import NodeSpecValidator

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
    # Registry
    "NodeSpecRegistry",
    "node_spec_registry",
    # Validator
    "NodeSpecValidator",
]
