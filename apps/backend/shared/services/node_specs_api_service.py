"""
Node Specs API Service

This service provides API compatibility for the node_templates table
using the new node_specs system. It translates between the old database
format and the new code-based specifications.
"""

import logging
from typing import List, Optional

from shared.models import NodeTemplate
from shared.node_specs.registry import node_spec_registry


class NodeSpecsApiService:
    """Service that provides node templates API using node specs."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def list_all_node_templates(
        self,
        type_filter: Optional[str] = None,
        include_system_templates: bool = True,
    ) -> List[NodeTemplate]:
        """
        List all available node templates from node specs.

        This method replaces database queries with node spec lookups,
        providing the same API interface as the original database method.
        """
        try:
            self.logger.info("Listing node templates from node specs registry")

            if not node_spec_registry:
                self.logger.warning("Node spec registry not available")
                return []

            templates = []

            # Use list_all_specs() method instead of .values()
            for spec in node_spec_registry.list_all_specs():
                # Apply filters
                if type_filter and str(spec.type) != type_filter:
                    continue

                if (
                    not include_system_templates
                    and hasattr(spec, "is_system_template")
                    and spec.is_system_template
                ):
                    continue

                # Convert node spec to NodeTemplate format
                template_data = self._convert_spec_to_template(spec)
                templates.append(NodeTemplate.model_validate(template_data))

            self.logger.info(f"Retrieved {len(templates)} node templates from specs")
            return templates

        except Exception as e:
            self.logger.error(f"Error listing node templates from specs: {str(e)}")
            raise

    def get_node_template_by_id(self, template_id: str) -> Optional[NodeTemplate]:
        """Get a specific node template by template ID from node specs."""
        try:
            if not node_spec_registry:
                return None

            # Use list_all_specs() method instead of .values()
            for spec in node_spec_registry.list_all_specs():
                # Check template_id or generate one to match
                spec_template_id = getattr(spec, "template_id", None)
                if not spec_template_id:
                    node_type_str = (
                        spec.type.value if hasattr(spec.type, "value") else str(spec.type)
                    )
                    spec_template_id = f"{node_type_str.lower()}_{spec.subtype.lower()}"

                if spec_template_id == template_id:
                    template_data = self._convert_spec_to_template(spec)
                    return NodeTemplate.model_validate(template_data)

            return None

        except Exception as e:
            self.logger.error(f"Error getting node template {template_id}: {str(e)}")
            raise

    def _convert_spec_to_template(self, spec) -> dict:
        """Convert a node spec to the NodeTemplate format expected by the API."""

        # Extract required parameters and defaults from configurations
        required_parameters = []
        default_parameters = {}

        configurations = getattr(spec, "configurations", {})
        for param_name, param_config in configurations.items():
            if param_config.get("required", False):
                required_parameters.append(param_name)
            if "default" in param_config:
                default_parameters[param_name] = param_config["default"]

        # Build parameter schema in JSON Schema format
        parameter_schema = {"type": "object", "properties": {}, "required": required_parameters}

        for param_name, param_config in configurations.items():
            prop_def = {
                "type": self._convert_param_type(param_config.get("type", "string")),
                "description": param_config.get("description", ""),
            }

            # Options for dropdowns
            # Note: Node specs should use "options" field (not "enum")
            # We convert to "enum" here for JSON Schema compatibility
            if "options" in param_config:
                prop_def["enum"] = param_config["options"]
            elif "enum" in param_config:
                # Legacy support - prefer "options" in node specs
                prop_def["enum"] = param_config["enum"]

            # Default value
            if "default" in param_config:
                prop_def["default"] = param_config["default"]

            # UI/Behavior properties
            if "sensitive" in param_config:
                prop_def["sensitive"] = param_config["sensitive"]

            if "multiline" in param_config:
                prop_def["multiline"] = param_config["multiline"]

            if "readonly" in param_config:
                prop_def["readonly"] = param_config["readonly"]

            # Validation properties
            if "min" in param_config:
                prop_def["min"] = param_config["min"]

            if "max" in param_config:
                prop_def["max"] = param_config["max"]

            if "validation_pattern" in param_config:
                prop_def["validation_pattern"] = param_config["validation_pattern"]

            # Dynamic dropdown properties
            if "api_endpoint" in param_config:
                prop_def["api_endpoint"] = param_config["api_endpoint"]

            if "multiple" in param_config:
                prop_def["multiple"] = param_config["multiple"]

            # UI enhancement properties
            if "placeholder" in param_config:
                prop_def["placeholder"] = param_config["placeholder"]

            if "help_text" in param_config:
                prop_def["help_text"] = param_config["help_text"]

            parameter_schema["properties"][param_name] = prop_def

        # Handle enum values for node_type and subtype
        node_type_str = spec.type.value if hasattr(spec.type, "value") else str(spec.type)
        subtype_str = spec.subtype

        # Generate template_id if not provided
        template_id = getattr(spec, "template_id", None)
        if not template_id:
            template_id = f"{node_type_str.lower()}_{subtype_str.lower()}"

        # Generate display_name if not provided
        display_name = getattr(spec, "display_name", None)
        if not display_name:
            display_name = spec.name or subtype_str.replace("_", " ").title()

        # Return template data in the expected format
        return {
            "id": template_id,
            "name": display_name,
            "description": spec.description or "No description available",
            "node_type": node_type_str,
            "node_subtype": subtype_str,
            "version": getattr(spec, "version", "1.0"),
            "is_system_template": getattr(spec, "is_system_template", True),
            "default_parameters": default_parameters,
            "required_parameters": required_parameters,
            "parameter_schema": parameter_schema,
        }

    def _convert_param_type(self, spec_type: str) -> str:
        """Convert node spec parameter type to JSON Schema type."""
        type_mapping = {
            "string": "string",
            "integer": "integer",
            "float": "number",
            "boolean": "boolean",
            "object": "object",  # Direct object type mapping
            "array": "array",  # Direct array type mapping
            "json": "object",  # Legacy: json -> object
            "enum": "string",
            "file": "string",
            "url": "string",
            "email": "string",
            "cron": "string",
        }
        return type_mapping.get(spec_type.lower(), "string")

    def get_available_node_types(self) -> List[str]:
        """Get all available node types from node specs."""
        try:
            if not node_spec_registry:
                return []

            node_types = set()
            # Use list_all_specs() method instead of .values()
            for spec in node_spec_registry.list_all_specs():
                node_types.add(str(spec.type))

            return sorted(list(node_types))

        except Exception as e:
            self.logger.error(f"Error getting node types: {str(e)}")
            return []

    def get_stats(self) -> dict:
        """Get statistics about available node templates."""
        try:
            if not node_spec_registry:
                return {"total": 0, "by_type": {}}

            # Use list_all_specs() method instead of .values()
            specs = node_spec_registry.list_all_specs()
            stats = {
                "total": len(specs),
                "by_type": {},
                "system_templates": 0,
                "user_templates": 0,
            }

            for spec in specs:
                # Count by type
                node_type = str(spec.type)
                stats["by_type"][node_type] = stats["by_type"].get(node_type, 0) + 1

                # Count system vs user templates
                if getattr(spec, "is_system_template", True):
                    stats["system_templates"] += 1
                else:
                    stats["user_templates"] += 1

            return stats

        except Exception as e:
            self.logger.error(f"Error getting stats: {str(e)}")
            return {"error": str(e)}


# Global instance for reuse
_node_specs_api_service = None


def get_node_specs_api_service() -> NodeSpecsApiService:
    """Get or create the global NodeSpecsApiService instance."""
    global _node_specs_api_service
    if _node_specs_api_service is None:
        _node_specs_api_service = NodeSpecsApiService()
    return _node_specs_api_service
