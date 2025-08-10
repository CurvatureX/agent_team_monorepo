"""
Data Mapping Processor

Core processor for executing data transformations between workflow nodes.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from .context import ExecutionContext
from .engines import FunctionRegistry, JSONPathParser, ScriptEngine, TemplateEngine
from .exceptions import DataMappingError, FieldExtractionError, TransformationError, ValidationError


class MappingType(Enum):
    """Data mapping types."""

    DIRECT = "DIRECT"
    FIELD_MAPPING = "FIELD_MAPPING"
    TEMPLATE = "TEMPLATE"
    TRANSFORM = "TRANSFORM"


class TransformType(Enum):
    """Field transform types."""

    NONE = "NONE"
    STRING_FORMAT = "STRING_FORMAT"
    JSON_PATH = "JSON_PATH"
    REGEX = "REGEX"
    FUNCTION = "FUNCTION"
    CONDITION = "CONDITION"


@dataclass
class FieldTransform:
    """Field-level transformation configuration."""

    type: TransformType
    transform_value: str
    options: Dict[str, str] = None

    def __post_init__(self):
        if self.options is None:
            self.options = {}


@dataclass
class FieldMapping:
    """Field mapping configuration."""

    source_field: str
    target_field: str
    transform: Optional[FieldTransform] = None
    required: bool = False
    default_value: Optional[str] = None


@dataclass
class DataMapping:
    """Data mapping configuration."""

    type: MappingType
    field_mappings: List[FieldMapping] = None
    transform_script: Optional[str] = None
    static_values: Dict[str, str] = None
    description: Optional[str] = None

    def __post_init__(self):
        if self.field_mappings is None:
            self.field_mappings = []
        if self.static_values is None:
            self.static_values = {}


class DataMappingProcessor:
    """Data mapping processor for executing various data transformations."""

    def __init__(self):
        self.template_engine = TemplateEngine()
        self.script_engine = ScriptEngine()
        self.jsonpath_parser = JSONPathParser()
        self.function_registry = FunctionRegistry()
        self.logger = logging.getLogger(__name__)

    def transform_data(
        self,
        source_data: Dict[str, Any],
        mapping: DataMapping,
        context: ExecutionContext,
        source_node=None,
        target_node=None,
        source_port: str = "main",
        target_port: str = "main",
    ) -> Dict[str, Any]:
        """Transform source data according to mapping rules."""

        try:
            self.logger.debug(f"Starting data transformation: {mapping.type.value}")

            # Execute data transformation based on mapping type
            if mapping.type == MappingType.DIRECT:
                transformed_data = self._apply_direct_mapping(source_data)
            elif mapping.type == MappingType.FIELD_MAPPING:
                transformed_data = self._apply_field_mappings(source_data, mapping, context)
            elif mapping.type == MappingType.TEMPLATE:
                transformed_data = self._apply_template_transform(source_data, mapping, context)
            elif mapping.type == MappingType.TRANSFORM:
                transformed_data = self._apply_script_transform(source_data, mapping, context)
            else:
                raise ValueError(f"Unsupported mapping type: {mapping.type}")

            self.logger.debug(f"Data transformation completed successfully")
            return transformed_data

        except Exception as e:
            self._log_mapping_error(mapping, source_data, e)
            raise DataMappingError(f"Data mapping failed: {str(e)}")

    def _apply_direct_mapping(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply direct mapping (pass-through)."""
        return source_data.copy() if isinstance(source_data, dict) else source_data

    def _apply_field_mappings(
        self, source_data: Dict[str, Any], mapping: DataMapping, context: ExecutionContext
    ) -> Dict[str, Any]:
        """Apply field-level mappings."""
        result = {}

        # Process field mappings
        for field_mapping in mapping.field_mappings:
            try:
                # Extract source field value
                source_value = self._extract_field_value(source_data, field_mapping.source_field)

                # Check required fields
                if field_mapping.required and source_value is None:
                    if field_mapping.default_value:
                        source_value = self._resolve_template_value(
                            field_mapping.default_value, context
                        )
                    else:
                        raise ValueError(f"Required field missing: {field_mapping.source_field}")

                # Skip if source value is None and field is not required
                if source_value is None and not field_mapping.required:
                    continue

                # Apply field-level transformation
                if field_mapping.transform:
                    source_value = self._apply_field_transform(
                        source_value, field_mapping.transform, context
                    )

                # Set target field value
                self._set_field_value(result, field_mapping.target_field, source_value)

            except Exception as e:
                self._log_field_mapping_error(field_mapping, source_data, e)
                if field_mapping.required:
                    raise

        # Process static values
        for key, value_template in mapping.static_values.items():
            resolved_value = self._resolve_template_value(value_template, context)
            self._set_field_value(result, key, resolved_value)

        return result

    def _apply_template_transform(
        self, source_data: Dict[str, Any], mapping: DataMapping, context: ExecutionContext
    ) -> Dict[str, Any]:
        """Apply template-based transformation."""
        if not mapping.transform_script:
            raise TransformationError("Template transformation requires transform_script")

        try:
            # Prepare template variables
            template_vars = {**source_data, **context.to_dict()}

            # Render template
            rendered = self.template_engine.render(mapping.transform_script, template_vars)

            # Parse result as JSON
            import json

            try:
                result = json.loads(rendered)
                return result if isinstance(result, dict) else {"result": result}
            except json.JSONDecodeError:
                return {"result": rendered}

        except Exception as e:
            raise TransformationError(f"Template transformation failed: {str(e)}")

    def _apply_script_transform(
        self, source_data: Dict[str, Any], mapping: DataMapping, context: ExecutionContext
    ) -> Dict[str, Any]:
        """Apply script-based transformation."""
        if not mapping.transform_script:
            raise TransformationError("Script transformation requires transform_script")

        try:
            result = self.script_engine.execute_javascript(
                mapping.transform_script, source_data, context.to_dict()
            )
            return result if isinstance(result, dict) else {"result": result}
        except Exception as e:
            raise TransformationError(f"Script transformation failed: {str(e)}")

    def _extract_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Extract field value using JSONPath or simple path."""
        try:
            return self.jsonpath_parser.extract(data, field_path)
        except Exception as e:
            self.logger.warning(f"Field extraction failed for path '{field_path}': {e}")
            return None

    def _apply_field_transform(
        self, value: Any, transform: FieldTransform, context: ExecutionContext
    ) -> Any:
        """Apply field-level transformation."""

        if transform.type == TransformType.NONE:
            return value

        elif transform.type == TransformType.STRING_FORMAT:
            try:
                return transform.transform_value.format(value=value)
            except Exception as e:
                raise TransformationError(f"String format transformation failed: {str(e)}")

        elif transform.type == TransformType.FUNCTION:
            try:
                func = self.function_registry.get_function(transform.transform_value)
                return func(value, **transform.options)
            except Exception as e:
                raise TransformationError(f"Function transformation failed: {str(e)}")

        elif transform.type == TransformType.CONDITION:
            try:
                return self._evaluate_condition(value, transform.transform_value, context)
            except Exception as e:
                raise TransformationError(f"Condition transformation failed: {str(e)}")

        elif transform.type == TransformType.REGEX:
            try:
                import re

                pattern = transform.transform_value
                replacement = transform.options.get("replacement", "")
                return re.sub(pattern, replacement, str(value))
            except Exception as e:
                raise TransformationError(f"Regex transformation failed: {str(e)}")

        else:
            raise ValueError(f"Unsupported transform type: {transform.type}")

    def _evaluate_condition(
        self, value: Any, condition_expr: str, context: ExecutionContext
    ) -> Any:
        """Evaluate conditional expression."""
        # Replace {{value}} with actual value
        expr = condition_expr.replace("{{value}}", str(value))

        # Simple ternary operator evaluation
        if "?" in expr and ":" in expr:
            condition_part, rest = expr.split("?", 1)
            true_part, false_part = rest.split(":", 1)

            condition_part = condition_part.strip()
            true_part = true_part.strip().strip("'\"")
            false_part = false_part.strip().strip("'\"")

            # Evaluate condition
            if self._evaluate_simple_condition(condition_part, value):
                return true_part
            else:
                return false_part

        return value

    def _evaluate_simple_condition(self, condition: str, value: Any) -> bool:
        """Evaluate simple boolean condition."""
        # Replace value placeholder
        condition = condition.replace(str(value), "VALUE")

        try:
            # Parse comparison operators
            for op in [">=", "<=", ">", "<", "==", "!="]:
                if op in condition:
                    left, right = condition.split(op, 1)
                    left_val = float(value) if left.strip() == "VALUE" else float(left.strip())
                    right_val = float(right.strip())

                    if op == ">":
                        return left_val > right_val
                    elif op == "<":
                        return left_val < right_val
                    elif op == ">=":
                        return left_val >= right_val
                    elif op == "<=":
                        return left_val <= right_val
                    elif op == "==":
                        return left_val == right_val
                    elif op == "!=":
                        return left_val != right_val
        except (ValueError, TypeError):
            pass

        return False

    def _set_field_value(self, data: Dict[str, Any], field_path: str, value: Any):
        """Set field value using dot notation path."""
        if not field_path:
            return

        parts = field_path.split(".")
        current = data

        # Navigate to parent of target field
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set final field value
        current[parts[-1]] = value

    def _resolve_template_value(self, template: str, context: ExecutionContext) -> Any:
        """Resolve template variables in a value."""
        if not isinstance(template, str) or "{{" not in template:
            return template

        try:
            return self.template_engine.render(template, context.to_dict())
        except Exception:
            return template

    def _log_mapping_error(
        self, mapping: DataMapping, source_data: Dict[str, Any], error: Exception
    ):
        """Log mapping error for debugging."""
        self.logger.error(
            f"Data mapping error - Type: {mapping.type.value}, "
            f"Error: {str(error)}, "
            f"Source data keys: {list(source_data.keys()) if isinstance(source_data, dict) else 'non-dict'}"
        )

    def _log_field_mapping_error(
        self, field_mapping: FieldMapping, source_data: Dict[str, Any], error: Exception
    ):
        """Log field mapping error for debugging."""
        self.logger.error(
            f"Field mapping error - Source: {field_mapping.source_field}, "
            f"Target: {field_mapping.target_field}, "
            f"Required: {field_mapping.required}, "
            f"Error: {str(error)}"
        )
