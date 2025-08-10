"""
Node Type Converter
Converts between API Gateway node types and unified node types.
Uses shared enums for consistency across all services.
"""

from typing import Any, Dict, List

try:
    from shared.models.node_enums import NodeType, resolve_legacy_api_type
except ImportError:
    # Fallback if shared models not available
    NodeType = None
    resolve_legacy_api_type = lambda x: x


# Legacy mapping from API Gateway NodeType enum to unified node types
# NOTE: This mapping is now redundant as shared.models.node_enums provides
# resolve_legacy_api_type() function with the authoritative mapping.
LEGACY_NODE_TYPE_MAPPING = {
    "trigger": NodeType.TRIGGER.value if NodeType else "TRIGGER",
    "action": NodeType.ACTION.value if NodeType else "ACTION",
    "condition": NodeType.FLOW.value if NodeType else "FLOW",
    "loop": NodeType.FLOW.value if NodeType else "FLOW",
    "webhook": NodeType.TRIGGER.value if NodeType else "TRIGGER",
    "api_call": NodeType.EXTERNAL_ACTION.value if NodeType else "EXTERNAL_ACTION",
    "email": NodeType.EXTERNAL_ACTION.value if NodeType else "EXTERNAL_ACTION",
    "delay": NodeType.FLOW.value if NodeType else "FLOW",
}

# Subtype mapping based on node type - UPDATED TO UNIFIED FORMAT
SUBTYPE_MAPPING = {
    "trigger": {
        "default": "MANUAL",  # Updated to unified format
        "cron": "CRON",  # Updated to unified format
        "manual": "MANUAL",  # Updated to unified format
        "webhook": "WEBHOOK",  # Updated to unified format
    },
    "action": {
        "default": "HTTP_REQUEST",
        "http": "HTTP_REQUEST",
        "api_call": "HTTP_REQUEST",
        "email": "SEND_EMAIL",
    },
    "condition": {"default": "IF"},
    "loop": {"default": "FOR_EACH"},
    "webhook": {"default": "WEBHOOK"},  # Updated to unified format
    "delay": {"default": "WAIT"},
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
    if NodeType and resolve_legacy_api_type and original_type:
        # Use the authoritative conversion from shared.models.node_enums
        result = resolve_legacy_api_type(original_type)
        engine_type = result.value if hasattr(result, "value") else result
    else:
        # Fallback to local mapping
        engine_type = LEGACY_NODE_TYPE_MAPPING.get(
            original_type, NodeType.ACTION.value if NodeType else "ACTION"
        )

    # Extract parameters from config or use direct parameters
    config = node.get("config", {})
    parameters = node.get("parameters", config)

    # Determine subtype - use the one provided or infer from type
    subtype = node.get("subtype")
    if not subtype:
        # Try to infer subtype from config or use default
        if original_type in SUBTYPE_MAPPING:
            subtype = SUBTYPE_MAPPING[original_type].get("default", "")
    elif original_type in SUBTYPE_MAPPING:
        # If subtype is provided, try to match it in the mapping (case-insensitive)
        subtype_lower = subtype.lower()
        type_mapping = SUBTYPE_MAPPING[original_type]

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
