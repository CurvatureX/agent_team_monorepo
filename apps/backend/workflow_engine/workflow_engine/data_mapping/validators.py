"""
Data Mapping Validators

Validation logic for data mapping configurations and compatibility.
"""

from shared.logging_config import get_logger

from typing import Any, Dict, List, Optional

from .exceptions import ValidationError
from .processor import DataMapping, FieldMapping, MappingType, TransformType


class DataMappingValidator:
    """Validator for data mapping configurations."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def validate_mapping_configuration(
        self, source_node: Any, target_node: Any, connection
    ) -> List[str]:
        """Validate data mapping configuration for a connection."""
        errors = []

        try:
            # 1. Validate basic connection structure
            if not hasattr(connection, "node") or not connection.node:
                errors.append("Connection missing target node")

            # 2. Validate data mapping rules if present
            if hasattr(connection, "data_mapping") and connection.data_mapping:
                mapping_errors = self._validate_data_mapping_rules(
                    source_node, target_node, connection.data_mapping
                )
                errors.extend(mapping_errors)

            # 3. Validate port compatibility (if port specifications are available)
            if hasattr(connection, "source_port") and hasattr(connection, "target_port"):
                port_errors = self._validate_port_compatibility(
                    source_node,
                    target_node,
                    connection.source_port or "main",
                    connection.target_port or "main",
                )
                errors.extend(port_errors)

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            errors.append(f"Validation failed: {str(e)}")

        return errors

    def _validate_data_mapping_rules(
        self, source_node: Any, target_node: Any, mapping: DataMapping
    ) -> List[str]:
        """Validate data mapping rules syntax and logic."""
        errors = []

        try:
            if mapping.type == MappingType.DIRECT:
                # No additional validation needed for direct mapping
                pass

            elif mapping.type == MappingType.FIELD_MAPPING:
                errors.extend(self._validate_field_mappings(mapping.field_mappings))

            elif mapping.type == MappingType.TEMPLATE:
                errors.extend(self._validate_template_mapping(mapping))

            elif mapping.type == MappingType.TRANSFORM:
                errors.extend(self._validate_transform_mapping(mapping))

            else:
                errors.append(f"Unknown mapping type: {mapping.type}")

        except Exception as e:
            errors.append(f"Mapping rule validation failed: {str(e)}")

        return errors

    def _validate_field_mappings(self, field_mappings: List[FieldMapping]) -> List[str]:
        """Validate field mapping configurations."""
        errors = []

        if not field_mappings:
            return errors

        seen_targets = set()

        for i, field_mapping in enumerate(field_mappings):
            # Check required fields
            if not field_mapping.source_field:
                errors.append(f"Field mapping {i}: missing source_field")

            if not field_mapping.target_field:
                errors.append(f"Field mapping {i}: missing target_field")

            # Check for duplicate target fields
            if field_mapping.target_field in seen_targets:
                errors.append(
                    f"Field mapping {i}: duplicate target_field '{field_mapping.target_field}'"
                )
            else:
                seen_targets.add(field_mapping.target_field)

            # Validate field path syntax
            if field_mapping.source_field:
                path_errors = self._validate_field_path(field_mapping.source_field)
                if path_errors:
                    errors.extend(
                        [f"Field mapping {i} source_field: {error}" for error in path_errors]
                    )

            if field_mapping.target_field:
                path_errors = self._validate_field_path(field_mapping.target_field)
                if path_errors:
                    errors.extend(
                        [f"Field mapping {i} target_field: {error}" for error in path_errors]
                    )

            # Validate transforms
            if field_mapping.transform:
                transform_errors = self._validate_field_transform(field_mapping.transform)
                if transform_errors:
                    errors.extend(
                        [f"Field mapping {i} transform: {error}" for error in transform_errors]
                    )

        return errors

    def _validate_field_path(self, path: str) -> List[str]:
        """Validate field path syntax."""
        errors = []

        if not path:
            errors.append("Empty field path")
            return errors

        # Check for invalid characters
        invalid_chars = ["{{", "}}"]  # Template syntax not allowed in field paths
        for char in invalid_chars:
            if char in path:
                errors.append(f"Invalid character sequence '{char}' in field path")

        # Validate array access syntax
        if "[" in path:
            # Basic validation for array syntax
            open_brackets = path.count("[")
            close_brackets = path.count("]")
            if open_brackets != close_brackets:
                errors.append("Mismatched brackets in field path")

        return errors

    def _validate_field_transform(self, transform) -> List[str]:
        """Validate field transformation configuration."""
        errors = []

        if not hasattr(transform, "type"):
            errors.append("Transform missing type")
            return errors

        if transform.type == TransformType.NONE:
            pass  # No validation needed

        elif transform.type == TransformType.STRING_FORMAT:
            if not hasattr(transform, "transform_value") or not transform.transform_value:
                errors.append("STRING_FORMAT transform missing transform_value")
            else:
                # Validate format string
                try:
                    transform.transform_value.format(value="test")
                except (KeyError, ValueError) as e:
                    errors.append(f"Invalid format string: {str(e)}")

        elif transform.type == TransformType.FUNCTION:
            if not hasattr(transform, "transform_value") or not transform.transform_value:
                errors.append("FUNCTION transform missing function name")

        elif transform.type == TransformType.CONDITION:
            if not hasattr(transform, "transform_value") or not transform.transform_value:
                errors.append("CONDITION transform missing condition expression")
            else:
                # Basic condition syntax validation
                condition = transform.transform_value
                if "?" not in condition or ":" not in condition:
                    errors.append(
                        "CONDITION transform must use ternary operator syntax (condition ? true_value : false_value)"
                    )

        elif transform.type == TransformType.REGEX:
            if not hasattr(transform, "transform_value") or not transform.transform_value:
                errors.append("REGEX transform missing pattern")
            else:
                # Validate regex pattern
                try:
                    import re

                    re.compile(transform.transform_value)
                except re.error as e:
                    errors.append(f"Invalid regex pattern: {str(e)}")

        else:
            errors.append(f"Unknown transform type: {transform.type}")

        return errors

    def _validate_template_mapping(self, mapping: DataMapping) -> List[str]:
        """Validate template mapping configuration."""
        errors = []

        if not mapping.transform_script:
            errors.append("Template mapping missing transform_script")
            return errors

        # Basic template syntax validation
        script = mapping.transform_script

        # Check for balanced template brackets
        open_count = script.count("{{")
        close_count = script.count("}}")
        if open_count != close_count:
            errors.append("Unbalanced template brackets in transform_script")

        # Try to parse as JSON structure
        try:
            # Remove template variables for JSON validation
            import re

            cleaned_script = re.sub(r"\{\{[^}]+\}\}", '"template_var"', script)
            import json

            json.loads(cleaned_script)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON structure in template: {str(e)}")
        except Exception:
            # If we can't validate JSON structure, that's okay - might be plain text template
            pass

        return errors

    def _validate_transform_mapping(self, mapping: DataMapping) -> List[str]:
        """Validate transform script mapping configuration."""
        errors = []

        if not mapping.transform_script:
            errors.append("Transform mapping missing transform_script")
            return errors

        script = mapping.transform_script

        # Basic JavaScript-like syntax validation
        if "function transform" not in script:
            errors.append("Transform script must contain a 'function transform' definition")

        # Check for balanced braces
        open_braces = script.count("{")
        close_braces = script.count("}")
        if open_braces != close_braces:
            errors.append("Unbalanced braces in transform script")

        # Check for return statement
        if "return " not in script:
            errors.append("Transform script must contain a return statement")

        return errors

    def _validate_port_compatibility(
        self, source_node: Any, target_node: Any, source_port: str, target_port: str
    ) -> List[str]:
        """Validate port compatibility between nodes."""
        errors = []

        # This would typically integrate with the node specification system
        # For now, we'll do basic validation

        # Check port names are not empty
        if not source_port:
            errors.append("Source port cannot be empty")

        if not target_port:
            errors.append("Target port cannot be empty")

        # Additional port compatibility checks would go here
        # This would integrate with the node specs system to validate:
        # - Port exists on the node
        # - Data types are compatible
        # - Connection limits are respected

        return errors

    def validate_static_values(self, static_values: Dict[str, str]) -> List[str]:
        """Validate static value configurations."""
        errors = []

        for key, value in static_values.items():
            # Validate field path
            path_errors = self._validate_field_path(key)
            if path_errors:
                errors.extend([f"Static value key '{key}': {error}" for error in path_errors])

            # Validate template value
            if isinstance(value, str) and "{{" in value:
                template_errors = self._validate_template_value(value)
                if template_errors:
                    errors.extend([f"Static value '{key}': {error}" for error in template_errors])

        return errors

    def _validate_template_value(self, template_value: str) -> List[str]:
        """Validate template variable syntax."""
        errors = []

        # Check for balanced brackets
        open_count = template_value.count("{{")
        close_count = template_value.count("}}")
        if open_count != close_count:
            errors.append(f"Unbalanced template brackets in '{template_value}'")

        return errors

    def validate_complete_workflow_mappings(self, workflow_definition: Dict[str, Any]) -> List[str]:
        """Validate all data mappings in a complete workflow."""
        errors = []

        if "connections" not in workflow_definition:
            return errors

        connections = workflow_definition["connections"]
        nodes = {node["id"]: node for node in workflow_definition.get("nodes", [])}

        # Validate each connection's data mapping
        for source_node_id, node_connections in connections.get("connections", {}).items():
            if source_node_id not in nodes:
                errors.append(f"Source node not found: {source_node_id}")
                continue

            source_node = nodes[source_node_id]

            for conn_type, conn_array in node_connections.get("connection_types", {}).items():
                for connection in conn_array.get("connections", []):
                    target_node_id = connection.get("node")
                    if target_node_id not in nodes:
                        errors.append(f"Target node not found: {target_node_id}")
                        continue

                    target_node = nodes[target_node_id]

                    # Convert dict to connection object for validation
                    conn_obj = type("Connection", (), connection)()

                    conn_errors = self.validate_mapping_configuration(
                        source_node, target_node, conn_obj
                    )

                    if conn_errors:
                        errors.extend(
                            [
                                f"Connection {source_node_id}->{target_node_id}: {error}"
                                for error in conn_errors
                            ]
                        )

        return errors
