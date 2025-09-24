"""
Expression Parser for Workflow Engine

Provides n8n-style expression parsing for accessing data from previous nodes.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ExpressionParser:
    """
    Parses and evaluates workflow expressions.

    Supported expressions:
    - $json - Current item's JSON data
    - $json.field - Access field in current item
    - $node["NodeName"].json - Access another node's output
    - $node["NodeName"].json.field.subfield - Nested access
    - $input.item.json - Access input from previous node
    - {{ expression }} - Expression wrapped in double braces
    """

    def __init__(self, workflow_data: Dict[str, Any], current_node: str):
        """
        Initialize the expression parser.

        Args:
            workflow_data: Complete workflow execution data
            current_node: Name/ID of the current node
        """
        self.workflow_data = workflow_data
        self.current_node = current_node
        self.node_outputs = workflow_data.get("node_outputs", {})
        self.current_item = workflow_data.get("current_item", {})

    def evaluate(self, expression: str) -> Any:
        """
        Evaluate an expression and return the result.

        Args:
            expression: The expression to evaluate

        Returns:
            The evaluated value or the original expression if not parseable
        """
        # Remove wrapping braces if present
        expression = expression.strip()
        if expression.startswith("{{") and expression.endswith("}}"):
            expression = expression[2:-2].strip()

        # Handle different expression types
        if expression.startswith("$json"):
            return self._evaluate_json_expression(expression)
        elif expression.startswith("$node["):
            return self._evaluate_node_expression(expression)
        elif expression.startswith("$input"):
            return self._evaluate_input_expression(expression)
        else:
            # Try to evaluate as a simple variable reference
            return self._evaluate_simple_expression(expression)

    def _evaluate_json_expression(self, expression: str) -> Any:
        """Evaluate $json expressions."""
        if expression == "$json":
            return self.current_item.get("json", {})

        # Handle $json.field.subfield
        if expression.startswith("$json."):
            path = expression[6:]  # Remove "$json."
            return self._navigate_path(self.current_item.get("json", {}), path)

        return None

    def _evaluate_node_expression(self, expression: str) -> Any:
        """
        Evaluate $node["NodeName"] expressions.

        Examples:
            $node["AI Agent"].json
            $node["AI Agent"].json.text
            $node["Parser"].json.extracted.category
        """
        # Pattern to match $node["NodeName"].path
        pattern = r'\$node\["([^"]+)"\](?:\.(.+))?'
        match = re.match(pattern, expression)

        if not match:
            logger.warning(f"Invalid node expression: {expression}")
            return None

        node_name = match.group(1)
        path = match.group(2)

        # Get node output
        if node_name not in self.node_outputs:
            logger.warning(f"Node '{node_name}' not found in outputs")
            return None

        node_output = self.node_outputs[node_name]

        # If no path, return the whole output
        if not path:
            return node_output

        # Navigate the path
        return self._navigate_path(node_output, path)

    def _evaluate_input_expression(self, expression: str) -> Any:
        """
        Evaluate $input expressions.

        These reference the input from the previous node in the workflow.
        """
        if expression == "$input":
            # Return the input data structure
            return self.workflow_data.get("input", {})

        # Handle $input.item.json etc
        if expression.startswith("$input."):
            path = expression[7:]  # Remove "$input."
            return self._navigate_path(self.workflow_data.get("input", {}), path)

        return None

    def _evaluate_simple_expression(self, expression: str) -> Any:
        """Evaluate simple variable references."""
        # Check if it's a direct reference to workflow data
        if expression in self.workflow_data:
            return self.workflow_data[expression]

        # Check current item
        if expression in self.current_item:
            return self.current_item[expression]

        return expression  # Return as-is if not found

    def _navigate_path(self, data: Any, path: str) -> Any:
        """
        Navigate a dot-separated path through nested data.

        Args:
            data: The data to navigate
            path: Dot-separated path (e.g., "field.subfield.value")

        Returns:
            The value at the path or None if not found
        """
        if not path:
            return data

        parts = path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict):
                # Handle dictionary access
                if part in current:
                    current = current[part]
                else:
                    # Try case-insensitive match
                    for key in current.keys():
                        if key.lower() == part.lower():
                            current = current[key]
                            break
                    else:
                        return None
            elif isinstance(current, list):
                # Handle array access
                if part.isdigit():
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                else:
                    # Try to access a property on all items
                    return [self._navigate_path(item, part) for item in current]
            else:
                return None

        return current

    def evaluate_template(self, template: str) -> str:
        """
        Evaluate a template string with multiple expressions.

        Example:
            "Hello {{ $node["AI"].json.name }}, your category is {{ $node["Classifier"].json.category }}"
        """
        # Find all expressions in the template
        expression_pattern = r"\{\{([^}]+)\}\}"

        def replace_expression(match):
            expression = match.group(1).strip()
            result = self.evaluate(expression)

            # Convert result to string
            if result is None:
                return ""
            elif isinstance(result, (dict, list)):
                return json.dumps(result)
            else:
                return str(result)

        return re.sub(expression_pattern, replace_expression, template)


class WorkflowDataProxy:
    """
    Proxy for accessing workflow data in a safe and convenient way.
    This mimics n8n's workflow data proxy functionality.
    """

    def __init__(self, execution_data: Dict[str, Any]):
        """Initialize with workflow execution data."""
        self.execution_data = execution_data
        self.node_outputs = {}

        # Build node output map
        for node_id, node_data in execution_data.get("node_results", {}).items():
            if "output_data" in node_data:
                self.node_outputs[node_id] = node_data["output_data"]

    def get_node_output(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get output data from a specific node."""
        return self.node_outputs.get(node_id)

    def get_node_parameter(self, node_id: str, parameter: str) -> Any:
        """Get a specific parameter from a node's output."""
        output = self.get_node_output(node_id)
        if not output:
            return None

        # Check common locations
        # First check json field (n8n style)
        if "json" in output and parameter in output["json"]:
            return output["json"][parameter]

        # Then check direct field
        if parameter in output:
            return output[parameter]

        # Check in text field
        if parameter == "text" and "text" in output:
            return output["text"]

        return None

    def resolve_expression_for_node(self, node_id: str, expression: str) -> Any:
        """
        Resolve an expression in the context of a specific node.

        This is what would be called when a node needs to access data
        from previous nodes using expressions in its parameters.
        """
        parser = ExpressionParser(
            workflow_data={"node_outputs": self.node_outputs, "current_node": node_id},
            current_node=node_id,
        )

        return parser.evaluate(expression)
