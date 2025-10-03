"""
Validation service for workflow_engine_v2.

Provides comprehensive workflow and node validation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.node_enums import (
    ActionSubtype,
    AIAgentSubtype,
    ExternalActionSubtype,
    FlowSubtype,
    MemorySubtype,
    NodeType,
)
from shared.models.workflow import Connection, Node, Workflow


class ValidationServiceV2:
    """Service for validating workflows and nodes."""

    def __init__(self):
        """Initialize validation service."""
        self.errors = []
        self.warnings = []

    def validate_workflow(self, workflow: Workflow) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a complete workflow.

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        try:
            # Basic workflow structure validation
            self._validate_workflow_structure(workflow)

            # Node validation
            self._validate_nodes(workflow.nodes)

            # Connection validation
            self._validate_connections(workflow.connections, workflow.nodes)

            # Trigger validation
            self._validate_triggers(workflow.triggers, workflow.nodes)

            # Workflow logic validation
            self._validate_workflow_logic(workflow)

            is_valid = len(self.errors) == 0
            return is_valid, self.errors.copy(), self.warnings.copy()

        except Exception as e:
            self.errors.append(f"Validation error: {str(e)}")
            return False, self.errors.copy(), self.warnings.copy()

    def _validate_workflow_structure(self, workflow: Workflow) -> None:
        """Validate basic workflow structure."""
        if not workflow.metadata:
            self.errors.append("Workflow metadata is required")
            return

        if not workflow.metadata.id:
            self.errors.append("Workflow ID is required")

        if not workflow.metadata.name:
            self.errors.append("Workflow name is required")

        if not workflow.nodes:
            self.errors.append("Workflow must have at least one node")

        if not workflow.triggers:
            self.warnings.append("Workflow has no trigger nodes defined")

    def _validate_nodes(self, nodes: List[Node]) -> None:
        """Validate all nodes in the workflow."""
        node_ids = set()

        for node in nodes:
            # Check for duplicate IDs
            if node.id in node_ids:
                self.errors.append(f"Duplicate node ID: {node.id}")
            node_ids.add(node.id)

            # Validate individual node
            self._validate_node(node)

    def _validate_node(self, node: Node) -> None:
        """Validate an individual node."""
        if not node.id:
            self.errors.append("Node ID is required")

        if not node.type:
            self.errors.append(f"Node type is required for node {node.id}")

        # Validate node type and subtype combination
        try:
            node_type = NodeType(node.type)
            self._validate_node_subtype(node, node_type)
        except ValueError:
            self.errors.append(f"Invalid node type '{node.type}' for node {node.id}")

        # Validate node configurations
        self._validate_node_configurations(node)

    def _validate_node_subtype(self, node: Node, node_type: NodeType) -> None:
        """Validate node subtype based on node type."""
        try:
            if node_type == NodeType.ACTION:
                ActionSubtype(node.subtype)
            elif node_type == NodeType.EXTERNAL_ACTION:
                ExternalActionSubtype(node.subtype)
                # External actions require action_type parameter
                if not node.configurations.get("action_type"):
                    self.errors.append(
                        f"EXTERNAL_ACTION node {node.id} requires 'action_type' configuration"
                    )
            elif node_type == NodeType.FLOW:
                FlowSubtype(node.subtype)
            elif node_type == NodeType.MEMORY:
                MemorySubtype(node.subtype)
        except ValueError:
            self.errors.append(
                f"Invalid subtype '{node.subtype}' for node type '{node.type}' in node {node.id}"
            )

    def _validate_node_configurations(self, node: Node) -> None:
        """Validate node-specific configurations."""
        if not node.configurations:
            node.configurations = {}

        # Node-type specific validation
        if node.type == NodeType.AI_AGENT.value:
            self._validate_ai_agent_config(node)
        elif node.type == NodeType.EXTERNAL_ACTION.value:
            self._validate_external_action_config(node)
        elif node.type == NodeType.FLOW.value:
            self._validate_flow_config(node)
        elif node.type == NodeType.MEMORY.value:
            self._validate_memory_config(node)

    def _validate_ai_agent_config(self, node: Node) -> None:
        """Validate AI agent node configurations."""
        # Check for required AI provider subtype
        try:
            ai_subtype = AIAgentSubtype(node.subtype)
        except ValueError:
            valid_subtypes = [subtype.value for subtype in AIAgentSubtype]
            self.errors.append(
                f"AI_AGENT node {node.id} has invalid subtype '{node.subtype}'. Valid subtypes: {valid_subtypes}"
            )
            return

        # Check for model specification
        model = node.configurations.get("model")
        if not model:
            self.warnings.append(f"AI_AGENT node {node.id} should specify a 'model' configuration")

        # Validate model names
        if (
            ai_subtype == AIAgentSubtype.OPENAI_CHATGPT
            and model
            and not model.startswith(("gpt-", "text-"))
        ):
            self.warnings.append(
                f"AI_AGENT node {node.id} has unexpected OpenAI model name: {model}"
            )
        elif (
            ai_subtype == AIAgentSubtype.ANTHROPIC_CLAUDE
            and model
            and not model.startswith("claude-")
        ):
            self.warnings.append(
                f"AI_AGENT node {node.id} has unexpected Claude model name: {model}"
            )

    def _validate_external_action_config(self, node: Node) -> None:
        """Validate external action node configurations."""
        action_type = node.configurations.get("action_type")
        if not action_type:
            self.errors.append(
                f"EXTERNAL_ACTION node {node.id} requires 'action_type' configuration"
            )

        # Subtype-specific validation
        try:
            ext_subtype = ExternalActionSubtype(node.subtype)
            if ext_subtype == ExternalActionSubtype.SLACK:
                if action_type and action_type not in [
                    "send_message",
                    "list_channels",
                    "list_users",
                ]:
                    self.warnings.append(
                        f"EXTERNAL_ACTION Slack node {node.id} has unrecognized action_type: {action_type}"
                    )
            elif ext_subtype == ExternalActionSubtype.GITHUB:
                if action_type and action_type not in [
                    "create_issue",
                    "create_pr",
                    "get_repo",
                    "list_issues",
                ]:
                    self.warnings.append(
                        f"EXTERNAL_ACTION GitHub node {node.id} has unrecognized action_type: {action_type}"
                    )
        except ValueError:
            # Already validated in _validate_node_subtype, so just continue
            pass

    def _validate_flow_config(self, node: Node) -> None:
        """Validate flow node configurations."""
        try:
            flow_subtype = FlowSubtype(node.subtype)
            if flow_subtype == FlowSubtype.IF:
                condition = node.configurations.get(
                    "condition_expression"
                ) or node.configurations.get("expression")
                if not condition:
                    self.errors.append(
                        f"FLOW IF node {node.id} requires 'condition_expression' configuration"
                    )

            elif flow_subtype == FlowSubtype.FOR_EACH:
                items_source = node.configurations.get("items_source")
                if not items_source:
                    self.errors.append(
                        f"FLOW FOR_EACH node {node.id} requires 'items_source' configuration"
                    )
        except ValueError:
            # Already validated in _validate_node_subtype, so just continue
            pass

    def _validate_memory_config(self, node: Node) -> None:
        """Validate memory node configurations."""
        try:
            memory_subtype = MemorySubtype(node.subtype)
            if memory_subtype == MemorySubtype.KEY_VALUE_STORE:
                operation = node.configurations.get("operation", "get")
                if operation == "set" and not node.configurations.get("key"):
                    self.warnings.append(
                        f"MEMORY KEY_VALUE_STORE node {node.id} with 'set' operation should specify a 'key'"
                    )
        except ValueError:
            # Already validated in _validate_node_subtype, so just continue
            pass

    def _validate_connections(self, connections: List[Connection], nodes: List[Node]) -> None:
        """Validate workflow connections."""
        node_ids = {node.id for node in nodes}

        for connection in connections:
            if not connection.id:
                self.errors.append("Connection ID is required")

            if not connection.from_node:
                self.errors.append(f"Connection {connection.id} missing from_node")
            elif connection.from_node not in node_ids:
                self.errors.append(
                    f"Connection {connection.id} references non-existent from_node: {connection.from_node}"
                )

            if not connection.to_node:
                self.errors.append(f"Connection {connection.id} missing to_node")
            elif connection.to_node not in node_ids:
                self.errors.append(
                    f"Connection {connection.id} references non-existent to_node: {connection.to_node}"
                )

            # Check for self-connections
            if connection.from_node == connection.to_node:
                self.warnings.append(f"Connection {connection.id} is a self-connection")

    def _validate_triggers(self, triggers: List[str], nodes: List[Node]) -> None:
        """Validate trigger node references."""
        node_ids = {node.id for node in nodes}
        trigger_nodes = [node for node in nodes if node.type == NodeType.TRIGGER.value]

        for trigger_id in triggers:
            if trigger_id not in node_ids:
                self.errors.append(f"Trigger references non-existent node: {trigger_id}")

        for trigger_node in trigger_nodes:
            if trigger_node.id not in triggers:
                self.warnings.append(
                    f"TRIGGER node {trigger_node.id} is not listed in workflow triggers"
                )

    def _validate_workflow_logic(self, workflow: Workflow) -> None:
        """Validate workflow logic and flow."""
        # Check for disconnected nodes
        self._check_disconnected_nodes(workflow)

        # Check for cycles
        self._check_for_cycles(workflow)

    def _check_disconnected_nodes(self, workflow: Workflow) -> None:
        """Check for nodes that are not connected to the workflow."""
        connected_nodes = set()

        # Add trigger nodes as starting points
        for trigger_id in workflow.triggers:
            connected_nodes.add(trigger_id)

        # Follow connections to find all reachable nodes
        for connection in workflow.connections:
            connected_nodes.add(connection.from_node)
            connected_nodes.add(connection.to_node)

        # Find disconnected nodes
        all_node_ids = {node.id for node in workflow.nodes}
        disconnected = all_node_ids - connected_nodes

        for node_id in disconnected:
            self.warnings.append(f"Node {node_id} appears to be disconnected from the workflow")

    def _check_for_cycles(self, workflow: Workflow) -> None:
        """Check for circular dependencies in the workflow."""
        # Build adjacency list
        graph = {}
        for node in workflow.nodes:
            graph[node.id] = []

        for connection in workflow.connections:
            if connection.from_node in graph:
                graph[connection.from_node].append(connection.to_node)

        # DFS cycle detection
        visited = set()
        rec_stack = set()

        def has_cycle(node_id):
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in graph.get(node_id, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in graph:
            if node_id not in visited:
                if has_cycle(node_id):
                    self.warnings.append(f"Cycle detected in workflow involving node {node_id}")
                    break

    def validate_node_standalone(self, node: Node) -> Tuple[bool, List[str], List[str]]:
        """Validate a single node in isolation."""
        self.errors = []
        self.warnings = []

        self._validate_node(node)

        is_valid = len(self.errors) == 0
        return is_valid, self.errors.copy(), self.warnings.copy()


__all__ = ["ValidationServiceV2"]
