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
        category_filter: Optional[str] = None,
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

            for spec in node_spec_registry.list_all_specs():
                # Apply filters
                if (
                    category_filter
                    and hasattr(spec, "category")
                    and spec.category != category_filter
                ):
                    continue

                if type_filter and spec.node_type != type_filter:
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

            for spec in node_spec_registry.list_all_specs():
                if hasattr(spec, "template_id") and spec.template_id == template_id:
                    template_data = self._convert_spec_to_template(spec)
                    return NodeTemplate.model_validate(template_data)

            return None

        except Exception as e:
            self.logger.error(f"Error getting node template {template_id}: {str(e)}")
            raise

    def _convert_spec_to_template(self, spec) -> dict:
        """Convert a node spec to the NodeTemplate format expected by the API."""

        # Extract required parameters
        required_parameters = []
        default_parameters = {}

        for param in spec.parameters:
            if param.required:
                required_parameters.append(param.name)
            if param.default_value is not None:
                default_parameters[param.name] = param.default_value

        # Build parameter schema in JSON Schema format
        parameter_schema = {"type": "object", "properties": {}, "required": required_parameters}

        for param in spec.parameters:
            prop_def = {
                "type": self._convert_param_type(param.type.value),
                "description": param.description,
            }

            if param.enum_values:
                prop_def["enum"] = param.enum_values

            if param.default_value is not None:
                prop_def["default"] = param.default_value

            parameter_schema["properties"][param.name] = prop_def

        # Handle enum values for node_type and subtype
        node_type_str = (
            spec.node_type.value if hasattr(spec.node_type, "value") else str(spec.node_type)
        )
        subtype_str = spec.subtype.value if hasattr(spec.subtype, "value") else str(spec.subtype)

        # Generate template_id if not provided
        template_id = getattr(spec, "template_id", None)
        if not template_id:
            template_id = f"{node_type_str.lower()}_{subtype_str.lower()}"

        # Generate display_name if not provided
        display_name = getattr(spec, "display_name", None)
        if not display_name:
            display_name = subtype_str.replace("_", " ").title()

        # Return template data in the expected format
        return {
            "id": template_id,
            "name": display_name,
            "description": spec.description or "No description available",
            "category": getattr(spec, "category", "general"),
            "node_type": node_type_str,
            "node_subtype": subtype_str,
            "version": spec.version,
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
            "json": "object",
            "enum": "string",
            "file": "string",
            "url": "string",
            "email": "string",
            "cron": "string",
        }
        return type_mapping.get(spec_type.lower(), "string")

    def get_available_categories(self) -> List[str]:
        """Get all available categories from node specs."""
        try:
            if not node_spec_registry:
                return []

            categories = set()
            for spec in node_spec_registry.list_all_specs():
                if hasattr(spec, "category") and spec.category:
                    categories.add(spec.category)

            return sorted(list(categories))

        except Exception as e:
            self.logger.error(f"Error getting categories: {str(e)}")
            return []

    def get_available_node_types(self) -> List[str]:
        """Get all available node types from node specs."""
        try:
            if not node_spec_registry:
                return []

            node_types = set()
            for spec in node_spec_registry.list_all_specs():
                node_types.add(spec.node_type)

            return sorted(list(node_types))

        except Exception as e:
            self.logger.error(f"Error getting node types: {str(e)}")
            return []

    def get_stats(self) -> dict:
        """Get statistics about available node templates."""
        try:
            if not node_spec_registry:
                return {"total": 0, "by_category": {}, "by_type": {}}

            specs = node_spec_registry.list_all_specs()
            stats = {
                "total": len(specs),
                "by_category": {},
                "by_type": {},
                "system_templates": 0,
                "user_templates": 0,
            }

            for spec in specs:
                # Count by category
                category = getattr(spec, "category", "uncategorized")
                stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

                # Count by type
                node_type = spec.node_type
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
