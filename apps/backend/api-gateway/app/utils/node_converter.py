"""
Node Type Converter
Converts between API Gateway node types and unified node types.
Uses shared enums for type safety and consistency across all services.

This module provides a legacy compatibility layer that:
1. Maps old frontend/API names to new enum values (e.g., "http" → "HTTP_REQUEST")
2. Provides default subtypes when none specified (e.g., "trigger" defaults to "MANUAL")
3. Handles case-insensitive conversion from legacy API formats
4. Uses enums exclusively - no fallback scenarios or hardcoded strings
"""

from typing import Any, Dict, List

from shared.models.node_enums import (
    ActionSubtype,
    AIAgentSubtype,
    ExternalActionSubtype,
    FlowSubtype,
    HumanLoopSubtype,
    MemorySubtype,
    NodeType,
    ToolSubtype,
    TriggerSubtype,
    resolve_legacy_api_type,
)

# Legacy mapping from API Gateway NodeType enum to unified node types
# Using enums for type safety and consistency
LEGACY_NODE_TYPE_MAPPING = {
    "trigger": NodeType.TRIGGER.value,
    "action": NodeType.ACTION.value,
    "condition": NodeType.FLOW.value,
    "loop": NodeType.FLOW.value,
    "webhook": NodeType.TRIGGER.value,
    "api_call": NodeType.EXTERNAL_ACTION.value,
    "email": NodeType.EXTERNAL_ACTION.value,
    "delay": NodeType.FLOW.value,
}

# Legacy subtype mapping using enums for type safety
LEGACY_SUBTYPE_MAPPING = {
    "trigger": {
        "default": TriggerSubtype.MANUAL.value,
        "cron": TriggerSubtype.CRON.value,
        "manual": TriggerSubtype.MANUAL.value,
        "webhook": TriggerSubtype.WEBHOOK.value,
    },
    "action": {
        "default": ActionSubtype.HTTP_REQUEST.value,
        "http": ActionSubtype.HTTP_REQUEST.value,
        "api_call": ActionSubtype.HTTP_REQUEST.value,
    },
    "email": {
        "default": ExternalActionSubtype.EMAIL.value,
    },
    "api_call": {
        "default": ActionSubtype.HTTP_REQUEST.value,
    },
    "condition": {"default": FlowSubtype.IF.value},
    "loop": {"default": FlowSubtype.FOR_EACH.value},
    "webhook": {"default": TriggerSubtype.WEBHOOK.value},
    "delay": {"default": FlowSubtype.WAIT.value},
}


def convert_node_for_workflow_engine(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a node from API Gateway format to Workflow Engine format

    Args:
        node: Node in API Gateway format (with NodeType enum)

    Returns:
        Node in Workflow Engine format (with type and subtype strings)
    """
    # Get the original type (lowercase enum value)
    original_type = node.get("type", "").lower()

    # Convert type to unified format using authoritative shared model function
    if resolve_legacy_api_type and original_type:
        # Use the authoritative conversion from shared.models.node_enums
        result = resolve_legacy_api_type(original_type)
        engine_type = result.value if hasattr(result, "value") else result
    else:
        # Fallback to local mapping
        engine_type = LEGACY_NODE_TYPE_MAPPING.get(original_type, NodeType.ACTION.value)

    # Extract parameters from config or use direct parameters
    config = node.get("config", {})
    parameters = node.get("parameters", config)

    # Determine subtype - use the one provided or infer from type
    subtype = node.get("subtype")

    if not subtype:
        # Try to infer subtype from config or use default
        if original_type in LEGACY_SUBTYPE_MAPPING:
            subtype = LEGACY_SUBTYPE_MAPPING[original_type].get("default", "")
    elif original_type in LEGACY_SUBTYPE_MAPPING:
        # If subtype is provided, try to match it in the mapping (case-insensitive)
        subtype_lower = subtype.lower()
        type_mapping = LEGACY_SUBTYPE_MAPPING[original_type]

        # Check if the provided subtype is already in the correct unified format
        if subtype in type_mapping.values():
            # Already in unified format, keep as-is
            pass
        elif subtype_lower in type_mapping:
            # Found in mapping (case-insensitive), use mapped value
            subtype = type_mapping[subtype_lower]
        else:
            # Not found in mapping, assume it's already in unified format
            # (This handles cases like direct "CRON", "WEBHOOK", etc.)
            pass

    # Build the converted node
    converted_node = {
        "name": node.get("name", ""),
        "type": engine_type,
        "subtype": subtype or "",
        "parameters": parameters,
        "position": node.get("position", {"x": 0, "y": 0}),
        "disabled": not node.get("enabled", True),
    }

    # Only include id if it exists
    if node.get("id"):
        converted_node["id"] = node["id"]

    return converted_node


def convert_nodes_for_workflow_engine(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert a list of nodes from API Gateway format to Workflow Engine format

    Args:
        nodes: List of nodes in API Gateway format

    Returns:
        List of nodes in Workflow Engine format
    """
    return [convert_node_for_workflow_engine(node) for node in nodes]


def convert_connections_for_workflow_engine(
    connections: Dict[str, Any], nodes: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Convert connections format from API Gateway to Workflow Engine

    The API Gateway uses node IDs in connections, while Workflow Engine
    can use either node IDs or names. This function ensures compatibility.

    Args:
        connections: Connections in API Gateway format
        nodes: List of nodes (to map IDs to names if needed)

    Returns:
        Connections in Workflow Engine format
    """
    # Create ID to name mapping
    id_to_name = {}
    for node in nodes:
        if node.get("id") and node.get("name"):
            id_to_name[node["id"]] = node["name"]

    # If connections are already using names, return as-is
    # Otherwise, convert IDs to names for better readability
    converted_connections = {}

    for source_key, targets in connections.items():
        # Use name if source_key is an ID, otherwise keep as-is
        source_name = id_to_name.get(source_key, source_key)
        converted_connections[source_name] = targets

    return converted_connections
