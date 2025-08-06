"""
Node Type Converter
Converts between API Gateway node types and Workflow Engine node types
"""

from typing import Any, Dict, List


# Mapping from API Gateway NodeType enum to Workflow Engine node types
NODE_TYPE_MAPPING = {
    "trigger": "TRIGGER_NODE",
    "action": "ACTION_NODE", 
    "condition": "FLOW_NODE",
    "loop": "FLOW_NODE",
    "webhook": "TRIGGER_NODE",
    "api_call": "ACTION_NODE",
    "email": "ACTION_NODE",
    "delay": "FLOW_NODE"
}

# Subtype mapping based on node type
SUBTYPE_MAPPING = {
    "trigger": {
        "default": "TRIGGER_MANUAL",
        "cron": "TRIGGER_CRON",
        "webhook": "TRIGGER_WEBHOOK"
    },
    "action": {
        "default": "HTTP_REQUEST",
        "http": "HTTP_REQUEST",
        "api_call": "HTTP_REQUEST",
        "email": "SEND_EMAIL"
    },
    "condition": {
        "default": "IF"
    },
    "loop": {
        "default": "FOR_EACH_LOOP"
    },
    "webhook": {
        "default": "TRIGGER_WEBHOOK"
    },
    "delay": {
        "default": "DELAY"
    }
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
    
    # Convert type to Workflow Engine format
    engine_type = NODE_TYPE_MAPPING.get(original_type, "ACTION_NODE")
    
    # Extract parameters from config or use direct parameters
    config = node.get("config", {})
    parameters = node.get("parameters", config)
    
    # Determine subtype - use the one provided or infer from type
    subtype = node.get("subtype")
    if not subtype:
        # Try to infer subtype from config or use default
        if original_type in SUBTYPE_MAPPING:
            subtype = SUBTYPE_MAPPING[original_type].get("default", "")
    
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
    connections: Dict[str, Any], 
    nodes: List[Dict[str, Any]]
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