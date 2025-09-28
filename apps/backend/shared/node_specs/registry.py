"""
Node Specifications Registry - Backward Compatibility Module

This module provides backward compatibility for the old registry interface.
The actual registry is now in __init__.py as NODE_SPECS_REGISTRY.
"""

from . import NODE_SPECS_REGISTRY, _wrapped_registry, get_node_spec, list_available_specs

# Backward compatibility aliases
node_spec_registry = _wrapped_registry
NodeSpecRegistry = _wrapped_registry

# Export the registry and utility functions
__all__ = [
    "node_spec_registry",
    "NodeSpecRegistry",
    "NODE_SPECS_REGISTRY",
    "get_node_spec",
    "list_available_specs",
]
