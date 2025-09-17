import time
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

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
)


def node(
    node_id: str, ntype: str, subtype: str | None = None, parameters: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Create a node definition that matches shared model format."""
    return {
        "id": node_id,
        "name": f"Node {node_id}",
        "type": ntype,
        "subtype": subtype,
        "type_version": 1,
        "position": {"x": 0, "y": 0},
        "parameters": parameters or {},
        "credentials": {},
        "disabled": False,
        "on_error": "continue",
        "retry_policy": None,
        "notes": {},
        "webhooks": [],
    }


def connect(
    source_id: str,
    target_id: str,
    output_field: str = "main",
    input_field: str = "main",
    connection_type: str = "MAIN",
    index: int = 0,
) -> Dict[str, Any]:
    """Create a connection in the new format expected by shared models."""
    return {"node": target_id, "type": connection_type, "index": index}


def single_node_workflow(node_def: Dict[str, Any]) -> Dict[str, Any]:
    now = int(time.time() * 1000)  # Unix timestamp in milliseconds (BIGINT)
    return {
        "id": str(uuid4()),
        "name": "Single Node Workflow",
        "nodes": [node_def],
        "connections": {},
        "created_at": now,
        "updated_at": now,
    }


def linear_workflow(nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a linear workflow with proper database structure."""
    conns: Dict[str, Any] = {}
    for i in range(len(nodes) - 1):
        source_id = nodes[i]["id"]
        target_id = nodes[i + 1]["id"]

        # Create connection in new format
        conns[source_id] = {
            "connection_types": {"main": {"connections": [connect(source_id, target_id)]}}
        }

    # Create workflow structure that matches database expectations
    # The nodes and connections go inside workflow_data JSONB field
    workflow_definition = {
        "nodes": nodes,
        "connections": conns,
        "settings": {
            "timezone": {"name": "UTC"},
            "save_execution_progress": True,
            "save_manual_executions": True,
            "timeout": 3600,
            "error_policy": "continue",
            "caller_policy": "workflow",
        },
        "static_data": {},
        "pin_data": {},
        "version": "1.0",
    }

    # Return the format expected by the database
    now = int(time.time() * 1000)  # Unix timestamp in milliseconds (BIGINT)
    return {
        "id": str(uuid4()),
        "name": "Linear Workflow",
        "description": "A linear workflow for testing",
        "tags": [],
        "active": True,
        "workflow_data": workflow_definition,  # This is the key - store workflow structure in JSONB field
        "created_at": now,
        "updated_at": now,
    }


def branching_workflow(
    trigger_node: Dict[str, Any],
    condition_node: Dict[str, Any],
    true_path_nodes: List[Dict[str, Any]],
    false_path_nodes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Create a branching workflow with conditional paths."""
    all_nodes = [trigger_node, condition_node] + true_path_nodes + false_path_nodes

    connections = {trigger_node["id"]: [connect(trigger_node["id"], condition_node["id"])]}

    # Connect condition to first nodes of each path
    if true_path_nodes:
        connections.setdefault(condition_node["id"], []).append(
            connect(condition_node["id"], true_path_nodes[0]["id"], output_field="true_path")
        )
        # Connect true path nodes linearly
        for i in range(len(true_path_nodes) - 1):
            connections.setdefault(true_path_nodes[i]["id"], []).append(
                connect(true_path_nodes[i]["id"], true_path_nodes[i + 1]["id"])
            )

    if false_path_nodes:
        connections.setdefault(condition_node["id"], []).append(
            connect(condition_node["id"], false_path_nodes[0]["id"], output_field="false_path")
        )
        # Connect false path nodes linearly
        for i in range(len(false_path_nodes) - 1):
            connections.setdefault(false_path_nodes[i]["id"], []).append(
                connect(false_path_nodes[i]["id"], false_path_nodes[i + 1]["id"])
            )

    return {
        "id": str(uuid4()),
        "name": "Branching Workflow",
        "nodes": all_nodes,
        "connections": connections,
    }


def parallel_workflow(
    trigger_node: Dict[str, Any],
    split_node: Dict[str, Any],
    parallel_nodes: List[Dict[str, Any]],
    merge_node: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a parallel processing workflow."""
    all_nodes = [trigger_node, split_node] + parallel_nodes + [merge_node]

    connections = {trigger_node["id"]: [connect(trigger_node["id"], split_node["id"])]}

    # Connect split to all parallel nodes
    for parallel_node in parallel_nodes:
        connections.setdefault(split_node["id"], []).append(
            connect(split_node["id"], parallel_node["id"])
        )
        # Connect each parallel node to merge
        connections.setdefault(parallel_node["id"], []).append(
            connect(parallel_node["id"], merge_node["id"])
        )

    return {
        "id": str(uuid4()),
        "name": "Parallel Processing Workflow",
        "nodes": all_nodes,
        "connections": connections,
    }


def create_ai_workflow(
    system_prompt: str, user_message: str, model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """Create a simple AI agent workflow."""
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )
    ai_node = node(
        "n2",
        NodeType.AI_AGENT.value,
        AIAgentSubtype.OPENAI_CHATGPT.value,
        {
            "provider": "openai",
            "model": model,
            "system_prompt": system_prompt,
            "user_message": user_message,
        },
    )
    return linear_workflow([trigger, ai_node])


def create_data_transformation_workflow(field_mappings: Dict[str, str]) -> Dict[str, Any]:
    """Create a data transformation workflow."""
    trigger = node("n1", "TRIGGER", "MANUAL", {"trigger_type": "manual"})
    transform_node = node(
        "n2",
        "ACTION",
        "TRANSFORM",
        {
            "action_type": "data_transformation",
            "transformation_type": "field_mapping",
            "field_mappings": field_mappings,
        },
    )
    return linear_workflow([trigger, transform_node])


def create_approval_workflow(
    title: str, description: str, timeout_seconds: int = 1800
) -> Dict[str, Any]:
    """Create a human approval workflow."""
    trigger = node("n1", "TRIGGER", "MANUAL", {"trigger_type": "manual"})
    approval_node = node(
        "n2",
        "HUMAN_IN_THE_LOOP",
        "APPROVAL",
        {
            "interaction_type": "approval",
            "title": title,
            "description": description,
            "approval_options": ["Approve", "Reject"],
            "timeout_seconds": timeout_seconds,
        },
    )
    return linear_workflow([trigger, approval_node])


def create_webhook_workflow(
    url: str, method: str = "POST", payload: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Create a webhook posting workflow."""
    trigger = node("n1", "TRIGGER", "MANUAL", {"trigger_type": "manual"})
    webhook_node = node(
        "n2",
        "EXTERNAL_ACTION",
        "WEBHOOK",
        {"action_type": "webhook", "url": url, "method": method, "payload": payload or {}},
    )
    return linear_workflow([trigger, webhook_node])


def create_memory_workflow(memory_type: str, operation: str, **kwargs) -> Dict[str, Any]:
    """Create a memory operation workflow."""
    trigger = node("n1", "TRIGGER", "MANUAL", {"trigger_type": "manual"})
    memory_node = node(
        "n2",
        "MEMORY",
        memory_type.upper(),
        {"memory_type": memory_type, "operation": operation, **kwargs},
    )
    return linear_workflow([trigger, memory_node])


def create_error_handling_workflow(
    failing_url: str = "https://invalid-domain-12345.com",
) -> Dict[str, Any]:
    """Create a workflow designed to test error handling."""
    trigger = node("n1", "TRIGGER", "MANUAL", {"trigger_type": "manual"})
    failing_action = node(
        "n2",
        "ACTION",
        "HTTP",
        {"action_type": "http_request", "url": failing_url, "method": "GET", "timeout": 1},
    )
    recovery_action = node(
        "n3",
        "ACTION",
        "LOG",
        {"action_type": "log", "message": "Error recovery executed", "level": "WARNING"},
    )
    return linear_workflow([trigger, failing_action, recovery_action])


def create_complex_pipeline(stages: List[str]) -> Dict[str, Any]:
    """Create a complex multi-stage processing pipeline."""
    nodes = []
    nodes.append(node("n1", "TRIGGER", "MANUAL", {"trigger_type": "manual"}))

    for i, stage in enumerate(stages, 2):
        if stage == "validate":
            nodes.append(
                node(
                    f"n{i}",
                    "FLOW",
                    "IF",
                    {
                        "flow_type": "if",
                        "condition": "input_data.valid == true",
                        "condition_field": "valid",
                        "condition_operator": "==",
                        "condition_value": True,
                    },
                )
            )
        elif stage == "transform":
            nodes.append(
                node(
                    f"n{i}",
                    "ACTION",
                    "TRANSFORM",
                    {
                        "action_type": "data_transformation",
                        "transformation_type": "field_mapping",
                        "field_mappings": {"input": "transformed_input"},
                    },
                )
            )
        elif stage == "ai_process":
            nodes.append(
                node(
                    f"n{i}",
                    "AI_AGENT",
                    "OPENAI",
                    {
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                        "system_prompt": "Process the data",
                        "user_message": "Process: {{input_data}}",
                    },
                )
            )
        elif stage == "store":
            nodes.append(
                node(
                    f"n{i}",
                    "MEMORY",
                    "KEY_VALUE_STORE",
                    {
                        "memory_type": "key_value_store",
                        "operation": "store",
                        "key": "processed_data",
                        "value": "{{input_data}}",
                    },
                )
            )
        elif stage == "notify":
            nodes.append(
                node(
                    f"n{i}",
                    "EXTERNAL_ACTION",
                    "WEBHOOK",
                    {
                        "action_type": "webhook",
                        "url": "https://httpbin.org/post",
                        "method": "POST",
                        "payload": {"status": "completed"},
                    },
                )
            )
        else:
            # Default to utility tool
            nodes.append(
                node(
                    f"n{i}",
                    "TOOL",
                    "UTILITY",
                    {"tool_type": "utility", "utility_type": "timestamp", "operation": stage},
                )
            )

    return linear_workflow(nodes)
