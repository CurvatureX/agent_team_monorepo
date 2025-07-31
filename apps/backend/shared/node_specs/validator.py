"""
Node specification validation system.

This module provides validation logic for node parameters, ports, and data formats
according to their specifications.
"""

import json
import re
from typing import Any, Dict, List, Union

from .base import InputPortSpec, NodeSpec, OutputPortSpec, ParameterDef, ParameterType


class NodeSpecValidator:
    """Validator for node specifications and configurations."""

    @staticmethod
    def validate_parameters(node, spec: NodeSpec) -> List[str]:
        """Validate node parameters against specification."""
        errors = []

        # Get node parameters safely
        node_parameters = getattr(node, "parameters", {})
        if not isinstance(node_parameters, dict):
            node_parameters = {}

        # Check required parameters
        for param_def in spec.parameters:
            if param_def.required and param_def.name not in node_parameters:
                errors.append(f"Missing required parameter: {param_def.name}")
                continue

            # Validate parameter type and format if present
            if param_def.name in node_parameters:
                value = node_parameters[param_def.name]
                param_errors = NodeSpecValidator._validate_parameter_value(value, param_def)
                errors.extend(param_errors)

        return errors

    @staticmethod
    def validate_ports(node, spec: NodeSpec) -> List[str]:
        """Validate node port configuration."""
        errors = []

        # Validate input ports
        required_inputs = {p.name for p in spec.input_ports if p.required}
        actual_inputs = set()

        # Get actual input ports from node
        if hasattr(node, "input_ports"):
            actual_inputs = {p.name for p in getattr(node, "input_ports", [])}

        missing_inputs = required_inputs - actual_inputs
        for missing in missing_inputs:
            errors.append(f"Missing required input port: {missing}")

        # Validate output ports (less strict - they're usually generated)
        expected_outputs = {p.name for p in spec.output_ports}
        actual_outputs = set()

        if hasattr(node, "output_ports"):
            actual_outputs = {p.name for p in getattr(node, "output_ports", [])}

        # Only warn about missing expected outputs if the node has any output ports defined
        if actual_outputs:
            missing_outputs = expected_outputs - actual_outputs
            for missing in missing_outputs:
                errors.append(f"Missing expected output port: {missing}")

        return errors

    @staticmethod
    def validate_port_data(
        port_spec: Union[InputPortSpec, OutputPortSpec], data: Dict[str, Any]
    ) -> List[str]:
        """Validate port data format against specification."""
        errors = []

        if port_spec.validation_schema:
            try:
                import jsonschema

                schema = json.loads(port_spec.validation_schema)
                jsonschema.validate(data, schema)
            except ImportError:
                errors.append("jsonschema library not available for validation")
            except jsonschema.ValidationError as e:
                errors.append(f"Data format validation failed: {e.message}")
            except json.JSONDecodeError:
                errors.append("Invalid JSON schema in port specification")
            except Exception as e:
                errors.append(f"Schema validation error: {str(e)}")

        return errors

    @staticmethod
    def _validate_parameter_value(value: str, param_def: ParameterDef) -> List[str]:
        """Validate individual parameter value."""
        errors = []

        if param_def.type == ParameterType.INTEGER:
            try:
                int(value)
            except (ValueError, TypeError):
                errors.append(f"Parameter {param_def.name} must be an integer")

        elif param_def.type == ParameterType.FLOAT:
            try:
                float(value)
            except (ValueError, TypeError):
                errors.append(f"Parameter {param_def.name} must be a float")

        elif param_def.type == ParameterType.BOOLEAN:
            if str(value).lower() not in ["true", "false", "1", "0", "yes", "no"]:
                errors.append(f"Parameter {param_def.name} must be a boolean value")

        elif param_def.type == ParameterType.ENUM:
            if param_def.enum_values and str(value) not in param_def.enum_values:
                errors.append(f"Parameter {param_def.name} must be one of: {param_def.enum_values}")

        elif param_def.type == ParameterType.JSON:
            try:
                json.loads(str(value))
            except (json.JSONDecodeError, TypeError):
                errors.append(f"Parameter {param_def.name} must be valid JSON")

        elif param_def.type == ParameterType.URL:
            # Basic URL validation
            url_pattern = r"^https?://.+"
            if not re.match(url_pattern, str(value)):
                errors.append(f"Parameter {param_def.name} must be a valid URL")

        elif param_def.type == ParameterType.EMAIL:
            # Basic email validation
            email_pattern = r"^[^@]+@[^@]+\.[^@]+$"
            if not re.match(email_pattern, str(value)):
                errors.append(f"Parameter {param_def.name} must be a valid email address")

        elif param_def.type == ParameterType.CRON_EXPRESSION:
            # Basic cron expression validation (5 or 6 parts)
            cron_pattern = r"^(\*|[0-9,\-/]+)\s+(\*|[0-9,\-/]+)\s+(\*|[0-9,\-/]+)\s+(\*|[0-9,\-/]+)\s+(\*|[0-9,\-/]+)(\s+(\*|[0-9,\-/]+))?$"
            if not re.match(cron_pattern, str(value)):
                errors.append(f"Parameter {param_def.name} must be a valid cron expression")

        # Validate custom regex pattern if provided
        if param_def.validation_pattern:
            try:
                if not re.match(param_def.validation_pattern, str(value)):
                    errors.append(f"Parameter {param_def.name} format is incorrect")
            except re.error:
                errors.append(f"Invalid validation pattern for parameter {param_def.name}")

        return errors

    @staticmethod
    def validate_spec_definition(spec: NodeSpec) -> List[str]:
        """Validate that a node specification itself is well-formed."""
        errors = []

        # Basic validation
        if not spec.node_type:
            errors.append("NodeSpec must have a node_type")

        if not spec.subtype:
            errors.append("NodeSpec must have a subtype")

        # Validate parameter definitions
        param_names = set()
        for param in spec.parameters:
            if param.name in param_names:
                errors.append(f"Duplicate parameter name: {param.name}")
            param_names.add(param.name)

            # Validate enum parameters have enum_values
            if param.type == ParameterType.ENUM and not param.enum_values:
                errors.append(f"Enum parameter {param.name} must have enum_values")

            # Validate parameter naming conventions
            if not param.name.replace("_", "").isalnum():
                errors.append(
                    f"Parameter name {param.name} should only contain letters, numbers, and underscores"
                )

        # Validate port definitions
        input_port_names = set()
        for port in spec.input_ports:
            if port.name in input_port_names:
                errors.append(f"Duplicate input port name: {port.name}")
            input_port_names.add(port.name)

            # Validate port naming
            if not port.name.replace("_", "").isalnum():
                errors.append(
                    f"Input port name {port.name} should only contain letters, numbers, and underscores"
                )

        output_port_names = set()
        for port in spec.output_ports:
            if port.name in output_port_names:
                errors.append(f"Duplicate output port name: {port.name}")
            output_port_names.add(port.name)

            # Validate port naming
            if not port.name.replace("_", "").isalnum():
                errors.append(
                    f"Output port name {port.name} should only contain letters, numbers, and underscores"
                )

        # Validate JSON schemas if present
        for port in spec.input_ports + spec.output_ports:
            if port.validation_schema:
                try:
                    json.loads(port.validation_schema)
                except json.JSONDecodeError:
                    errors.append(f"Invalid JSON schema for port {port.name}")

        # Validate examples if present
        if spec.examples:
            for i, example in enumerate(spec.examples):
                if not isinstance(example, dict):
                    errors.append(f"Example {i} must be a dictionary")
                elif "name" not in example:
                    errors.append(f"Example {i} must have a 'name' field")

        return errors

    @staticmethod
    def validate_parameter_value_advanced(value: str, param_def: ParameterDef) -> List[str]:
        """Advanced parameter validation with better error messages."""
        errors = []

        # Basic type validation
        basic_errors = NodeSpecValidator._validate_parameter_value(value, param_def)
        errors.extend(basic_errors)

        # Additional validations for specific parameter types
        if param_def.type == ParameterType.JSON and not basic_errors:
            try:
                parsed_json = json.loads(str(value))
                # For AI agents, validate common JSON structures
                if param_def.name in ["safety_settings", "stop_sequences"] and not isinstance(
                    parsed_json, (dict, list)
                ):
                    errors.append(f"Parameter {param_def.name} JSON must be an object or array")
            except:
                pass  # Already caught by basic validation

        return errors
