"""
Validation Service using Pydantic models for FastAPI endpoints.
Handles workflow and node validation operations.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Set

from workflow_engine.workflow_engine.core.config import get_settings
from workflow_engine.workflow_engine.models.requests import TestNodeRequest, ValidateWorkflowRequest
from workflow_engine.workflow_engine.models.responses import (
    TestNodeResponse,
    ValidateWorkflowResponse,
    ValidationResult,
)
from workflow_engine.workflow_engine.models.workflow import NodeData, NodeType, WorkflowData
from workflow_engine.workflow_engine.utils.converters import ValidationHelper

logger = logging.getLogger(__name__)
settings = get_settings()


class ValidationService:
    """Service for workflow and node validation operations."""

    def __init__(self):
        self.logger = logger

        # Define valid node types and their required parameters
        self.node_type_requirements = {
            NodeType.TRIGGER: {
                "required_params": ["trigger_type"],
                "optional_params": ["schedule", "conditions"],
            },
            NodeType.ACTION: {
                "required_params": ["action_type"],
                "optional_params": ["parameters", "timeout"],
            },
            NodeType.CONDITION: {
                "required_params": ["condition_expression"],
                "optional_params": ["true_path", "false_path"],
            },
            NodeType.AI_AGENT: {
                "required_params": ["agent_type", "prompt"],
                "optional_params": ["model", "temperature", "max_tokens"],
            },
            NodeType.TOOL: {
                "required_params": ["tool_name"],
                "optional_params": ["tool_parameters"],
            },
            NodeType.FLOW: {"required_params": ["flow_type"], "optional_params": ["conditions"]},
            NodeType.MEMORY: {
                "required_params": ["memory_type"],
                "optional_params": ["key", "value"],
            },
            NodeType.HUMAN_LOOP: {
                "required_params": ["approval_type"],
                "optional_params": ["timeout", "approvers"],
            },
            NodeType.EXTERNAL_ACTION: {
                "required_params": ["endpoint_url", "method"],
                "optional_params": ["headers", "body", "timeout"],
            },
        }

    async def validate_workflow(self, request: ValidateWorkflowRequest) -> ValidateWorkflowResponse:
        """Validate a workflow definition."""
        try:
            self.logger.info("Validating workflow definition")

            workflow = request.workflow
            strict_mode = request.strict_mode

            errors = []
            warnings = []
            suggestions = []

            # Basic workflow validation
            basic_errors = self._validate_basic_workflow_structure(workflow)
            errors.extend(basic_errors)

            # Node validation
            node_errors, node_warnings, node_suggestions = self._validate_nodes(
                workflow.nodes, strict_mode
            )
            errors.extend(node_errors)
            warnings.extend(node_warnings)
            suggestions.extend(node_suggestions)

            # Connection validation
            connection_errors, connection_warnings = self._validate_connections(
                workflow.nodes, workflow.connections.connections
            )
            errors.extend(connection_errors)
            warnings.extend(connection_warnings)

            # Workflow settings validation
            settings_errors, settings_warnings = self._validate_workflow_settings(workflow.settings)
            errors.extend(settings_errors)
            warnings.extend(settings_warnings)

            # Advanced validation in strict mode
            if strict_mode:
                (
                    advanced_errors,
                    advanced_warnings,
                    advanced_suggestions,
                ) = self._validate_advanced_workflow_logic(workflow)
                errors.extend(advanced_errors)
                warnings.extend(advanced_warnings)
                suggestions.extend(advanced_suggestions)

            # Determine if workflow is valid
            is_valid = len(errors) == 0

            validation_result = ValidationResult(
                valid=is_valid, errors=errors, warnings=warnings, suggestions=suggestions
            )

            self.logger.info(
                f"Workflow validation completed: valid={is_valid}, errors={len(errors)}, warnings={len(warnings)}"
            )

            return ValidateWorkflowResponse(
                validation_result=validation_result,
                success=True,
                message=f"Workflow validation completed with {len(errors)} errors and {len(warnings)} warnings",
            )

        except Exception as e:
            self.logger.error(f"Error validating workflow: {str(e)}")
            raise Exception(f"Failed to validate workflow: {str(e)}")

    async def test_node(self, request: TestNodeRequest) -> TestNodeResponse:
        """Test a single workflow node."""
        try:
            self.logger.info(f"Testing node: {request.node.id} for user: {request.user_id}")

            node = request.node
            input_data = request.input_data

            start_time = datetime.now()

            # Validate node configuration
            node_errors = self._validate_single_node(node)
            if node_errors:
                return TestNodeResponse(
                    node_id=node.id,
                    success=False,
                    output_data={},
                    execution_time_ms=0,
                    errors=node_errors,
                    message="Node configuration is invalid",
                )

            # Simulate node execution
            output_data, errors = await self._simulate_node_execution(node, input_data)

            end_time = datetime.now()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            success = len(errors) == 0

            self.logger.info(f"Node test completed: {node.id}, success={success}")

            return TestNodeResponse(
                node_id=node.id,
                success=success,
                output_data=output_data,
                execution_time_ms=execution_time_ms,
                errors=errors,
                message="Node test completed successfully" if success else "Node test failed",
            )

        except Exception as e:
            self.logger.error(f"Error testing node: {str(e)}")
            raise Exception(f"Failed to test node: {str(e)}")

    def _validate_basic_workflow_structure(self, workflow: WorkflowData) -> List[str]:
        """Validate basic workflow structure."""
        errors = []

        # Name validation
        if not workflow.name or not workflow.name.strip():
            errors.append("Workflow name is required")
        elif len(workflow.name) > 255:
            errors.append("Workflow name cannot exceed 255 characters")

        # Nodes validation
        if not workflow.nodes:
            errors.append("Workflow must have at least one node")
        elif len(workflow.nodes) > 100:
            errors.append("Workflow cannot have more than 100 nodes")

        # Check for duplicate node IDs
        node_ids = [node.id for node in workflow.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("All node IDs must be unique")

        return errors

    def _validate_nodes(
        self, nodes: List[NodeData], strict_mode: bool
    ) -> tuple[List[str], List[str], List[str]]:
        """Validate all nodes in the workflow."""
        errors = []
        warnings = []
        suggestions = []

        trigger_nodes = []

        for i, node in enumerate(nodes):
            # Basic node validation
            node_errors = self._validate_single_node(node)
            errors.extend([f"Node {node.id}: {error}" for error in node_errors])

            # Collect trigger nodes
            if node.type == NodeType.TRIGGER:
                trigger_nodes.append(node)

            # Node position validation
            if node.position.x < 0 or node.position.y < 0:
                warnings.append(f"Node {node.id}: Position coordinates should be non-negative")

            # Parameter validation based on node type
            if strict_mode:
                param_errors, param_warnings = self._validate_node_parameters(node)
                errors.extend([f"Node {node.id}: {error}" for error in param_errors])
                warnings.extend([f"Node {node.id}: {warning}" for warning in param_warnings])

        # Workflow-level node validation
        if not trigger_nodes:
            warnings.append("Workflow has no trigger nodes - it cannot be started automatically")
        elif len(trigger_nodes) > 1:
            suggestions.append(
                "Consider consolidating multiple trigger nodes for simpler workflow management"
            )

        return errors, warnings, suggestions

    def _validate_single_node(self, node: NodeData) -> List[str]:
        """Validate a single node."""
        errors = []

        # Basic node properties
        if not node.id or not node.id.strip():
            errors.append("Node ID is required")

        if not node.name or not node.name.strip():
            errors.append("Node name is required")

        if not node.type or not node.type.strip():
            errors.append("Node type is required")

        # Validate node type
        try:
            node_type = NodeType(node.type)
        except ValueError:
            errors.append(f"Invalid node type: {node.type}")
            return errors

        # Validate required parameters for node type
        if node_type in self.node_type_requirements:
            requirements = self.node_type_requirements[node_type]
            required_params = requirements.get("required_params", [])

            for param in required_params:
                if param not in node.parameters:
                    errors.append(f"Required parameter '{param}' is missing")

        return errors

    def _validate_node_parameters(self, node: NodeData) -> tuple[List[str], List[str]]:
        """Validate node-specific parameters."""
        errors = []
        warnings = []

        node_type = node.type
        parameters = node.parameters

        # Type-specific parameter validation
        if node_type == NodeType.TRIGGER:
            trigger_type = parameters.get("trigger_type")
            if trigger_type == "schedule" and "schedule" not in parameters:
                errors.append("Schedule trigger requires 'schedule' parameter")
            elif trigger_type == "webhook" and "webhook_url" not in parameters:
                warnings.append("Webhook trigger should specify 'webhook_url' parameter")

        elif node_type == NodeType.AI_AGENT:
            model = parameters.get("model", "gpt-3.5-turbo")
            if model not in ["gpt-3.5-turbo", "gpt-4", "claude-3-sonnet", "claude-3-opus"]:
                warnings.append(f"Unsupported AI model: {model}")

            temperature = parameters.get("temperature")
            if temperature and (float(temperature) < 0 or float(temperature) > 2):
                errors.append("Temperature must be between 0 and 2")

        elif node_type == NodeType.EXTERNAL_ACTION:
            endpoint_url = parameters.get("endpoint_url")
            if endpoint_url and not endpoint_url.startswith(("http://", "https://")):
                errors.append("Endpoint URL must start with http:// or https://")

            method = parameters.get("method", "GET")
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                errors.append(f"Invalid HTTP method: {method}")

        return errors, warnings

    def _validate_connections(
        self, nodes: List[NodeData], connections: Dict[str, List[str]]
    ) -> tuple[List[str], List[str]]:
        """Validate node connections."""
        errors = []
        warnings = []

        node_ids = {node.id for node in nodes}

        # Validate connection references
        for source_id, targets in connections.items():
            if source_id not in node_ids:
                errors.append(f"Connection source node '{source_id}' does not exist")
                continue

            for target_id in targets:
                if target_id not in node_ids:
                    errors.append(f"Connection target node '{target_id}' does not exist")

        # Check for circular dependencies
        if self._has_circular_dependencies(connections):
            errors.append("Workflow contains circular dependencies")

        # Check for unreachable nodes
        reachable_nodes = self._find_reachable_nodes(connections)
        unreachable_nodes = node_ids - reachable_nodes

        if unreachable_nodes:
            warnings.append(f"Unreachable nodes detected: {', '.join(unreachable_nodes)}")

        return errors, warnings

    def _validate_workflow_settings(self, settings) -> tuple[List[str], List[str]]:
        """Validate workflow settings."""
        errors = []
        warnings = []

        if settings.timeout <= 0:
            errors.append("Workflow timeout must be positive")
        elif settings.timeout > 86400:  # 24 hours
            warnings.append("Workflow timeout is very long (>24 hours)")

        if settings.max_retries < 0:
            errors.append("Max retries cannot be negative")
        elif settings.max_retries > 10:
            warnings.append("High number of max retries may cause long execution times")

        if settings.retry_delay < 0:
            errors.append("Retry delay cannot be negative")

        return errors, warnings

    def _validate_advanced_workflow_logic(
        self, workflow: WorkflowData
    ) -> tuple[List[str], List[str], List[str]]:
        """Perform advanced workflow logic validation."""
        errors = []
        warnings = []
        suggestions = []

        nodes = workflow.nodes
        connections = workflow.connections.connections

        # Check for dead ends (nodes with no outgoing connections except final nodes)
        dead_end_nodes = []
        for node in nodes:
            if node.id not in connections and node.type not in [
                NodeType.EXTERNAL_ACTION,
                NodeType.HUMAN_LOOP,
            ]:
                dead_end_nodes.append(node.id)

        if dead_end_nodes:
            warnings.append(f"Nodes with no outgoing connections: {', '.join(dead_end_nodes)}")

        # Check for complex branching patterns
        complex_nodes = [node_id for node_id, targets in connections.items() if len(targets) > 3]
        if complex_nodes:
            suggestions.append(
                f"Consider simplifying complex branching in nodes: {', '.join(complex_nodes)}"
            )

        # Estimate execution complexity
        total_nodes = len(nodes)
        total_connections = sum(len(targets) for targets in connections.values())

        if total_nodes > 50 or total_connections > 100:
            suggestions.append(
                "Large workflow detected - consider breaking into smaller sub-workflows"
            )

        return errors, warnings, suggestions

    def _has_circular_dependencies(self, connections: Dict[str, List[str]]) -> bool:
        """Check for circular dependencies using DFS."""
        visited = set()
        rec_stack = set()

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in connections.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in connections.keys():
            if node not in visited:
                if dfs(node):
                    return True

        return False

    def _find_reachable_nodes(self, connections: Dict[str, List[str]]) -> Set[str]:
        """Find all reachable nodes from trigger nodes."""
        # For now, assume all connected nodes are reachable
        # In a full implementation, we'd start from trigger nodes
        reachable = set(connections.keys())

        for targets in connections.values():
            reachable.update(targets)

        return reachable

    async def _simulate_node_execution(
        self, node: NodeData, input_data: Dict[str, Any]
    ) -> tuple[Dict[str, Any], List[str]]:
        """Simulate node execution for testing."""
        try:
            # Simulate execution time
            await asyncio.sleep(0.1)

            # Mock successful execution based on node type
            if node.type == NodeType.TRIGGER:
                output_data = {
                    "triggered": True,
                    "timestamp": datetime.now().isoformat(),
                    "trigger_data": input_data,
                }
            elif node.type == NodeType.AI_AGENT:
                output_data = {
                    "response": f"Mock AI response for prompt: {node.parameters.get('prompt', 'No prompt')}",
                    "model": node.parameters.get("model", "gpt-3.5-turbo"),
                    "tokens_used": 150,
                }
            elif node.type == NodeType.EXTERNAL_ACTION:
                output_data = {
                    "status_code": 200,
                    "response": {"message": "Mock external API response"},
                    "endpoint": node.parameters.get("endpoint_url", "mock://api"),
                }
            else:
                output_data = {
                    "status": "success",
                    "message": f"Mock execution of {node.type} node",
                    "input_processed": len(input_data) > 0,
                }

            return output_data, []

        except Exception as e:
            return {}, [f"Simulation error: {str(e)}"]
