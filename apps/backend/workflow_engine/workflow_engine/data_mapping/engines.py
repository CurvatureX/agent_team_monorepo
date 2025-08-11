"""
Data Mapping Engines

Core engines for template processing, script execution, JSONPath parsing, and function registry.
"""

from shared.logging_config import get_logger

import json
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .exceptions import (
    FunctionNotFoundError,
    JSONPathError,
    ScriptExecutionError,
    TemplateRenderError,
)


class TemplateEngine:
    """Template engine for processing Handlebars-like templates."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def compile(self, template: str) -> "CompiledTemplate":
        """Compile a template string."""
        return CompiledTemplate(template)

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """Render a template with variables."""
        try:
            compiled = self.compile(template)
            return compiled.render(variables)
        except Exception as e:
            raise TemplateRenderError(f"Template rendering failed: {str(e)}")


class CompiledTemplate:
    """Compiled template for efficient rendering."""

    def __init__(self, template: str):
        self.template = template
        self.variables = self._extract_variables(template)

    def _extract_variables(self, template: str) -> List[str]:
        """Extract variable names from template."""
        pattern = r"\{\{([^}]+)\}\}"
        matches = re.findall(pattern, template)
        return [match.strip() for match in matches]

    def render(self, variables: Dict[str, Any]) -> str:
        """Render template with provided variables."""
        result = self.template

        # Replace variables
        for var_expr in self.variables:
            placeholder = "{{" + var_expr + "}}"

            # Handle simple variables
            if "." not in var_expr and not any(op in var_expr for op in [">", "<", "?", ":"]):
                if var_expr in variables:
                    value = variables[var_expr]
                    result = result.replace(placeholder, str(value))
            else:
                # Handle complex expressions (simplified evaluation)
                try:
                    value = self._evaluate_expression(var_expr, variables)
                    result = result.replace(placeholder, str(value))
                except Exception:
                    # Keep placeholder if evaluation fails
                    pass

        return result

    def _evaluate_expression(self, expr: str, variables: Dict[str, Any]) -> Any:
        """Evaluate complex template expressions."""
        # Handle dot notation (e.g., "context.user_id")
        if "." in expr and not any(op in expr for op in [">", "<", "?", ":"]):
            parts = expr.split(".")
            value = variables
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value

        # Handle ternary expressions (e.g., "value > 0.8 ? 'high' : 'normal'")
        if "?" in expr and ":" in expr:
            condition, rest = expr.split("?", 1)
            true_val, false_val = rest.split(":", 1)

            condition = condition.strip()
            true_val = true_val.strip().strip("'\"")
            false_val = false_val.strip().strip("'\"")

            if self._evaluate_condition(condition, variables):
                return true_val
            else:
                return false_val

        return expr

    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """Evaluate boolean conditions."""
        # Simple condition evaluation (e.g., "value > 0.8")
        for op in [">=", "<=", ">", "<", "==", "!="]:
            if op in condition:
                left, right = condition.split(op, 1)
                left_val = self._get_variable_value(left.strip(), variables)
                right_val = self._parse_value(right.strip())

                if op == ">":
                    return float(left_val) > float(right_val)
                elif op == "<":
                    return float(left_val) < float(right_val)
                elif op == ">=":
                    return float(left_val) >= float(right_val)
                elif op == "<=":
                    return float(left_val) <= float(right_val)
                elif op == "==":
                    return left_val == right_val
                elif op == "!=":
                    return left_val != right_val

        return False

    def _get_variable_value(self, var_name: str, variables: Dict[str, Any]) -> Any:
        """Get variable value, supporting dot notation."""
        if "." in var_name:
            parts = var_name.split(".")
            value = variables
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        return variables.get(var_name)

    def _parse_value(self, value_str: str) -> Any:
        """Parse string value to appropriate type."""
        value_str = value_str.strip()

        # Remove quotes
        if (
            value_str.startswith('"')
            and value_str.endswith('"')
            or value_str.startswith("'")
            and value_str.endswith("'")
        ):
            return value_str[1:-1]

        # Try to parse as number
        try:
            if "." in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass

        # Return as string
        return value_str


class ScriptEngine:
    """Script engine for executing transformation scripts."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def execute_javascript(
        self, script: str, input_data: Dict[str, Any], context: Dict[str, Any]
    ) -> Any:
        """Execute JavaScript transformation script."""
        # For now, implement a basic JavaScript-like interpreter
        # In production, you might want to use a proper JS engine like PyV8 or Node.js
        try:
            return self._execute_basic_script(script, input_data, context)
        except Exception as e:
            raise ScriptExecutionError(f"JavaScript execution failed: {str(e)}")

    def _execute_basic_script(
        self, script: str, input_data: Dict[str, Any], context: Dict[str, Any]
    ) -> Any:
        """Basic script execution (simplified interpreter)."""
        # This is a simplified implementation
        # In a real system, you'd want to use a proper JavaScript engine

        # Create execution environment
        env = {
            "input": input_data,
            "context": context,
            "current_time": context.get("current_time", datetime.now().isoformat()),
            "workflow_id": context.get("workflow_id"),
            "execution_id": context.get("execution_id"),
            "node_id": context.get("node_id"),
        }

        # For demo purposes, if script contains 'return', extract the return value
        if "return" in script:
            # Extract return statement (very simplified)
            lines = script.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("return "):
                    return_expr = line[7:].rstrip(";")
                    return self._evaluate_return_expression(return_expr, env)

        return {}

    def _evaluate_return_expression(self, expr: str, env: Dict[str, Any]) -> Any:
        """Evaluate return expression."""
        # Very simplified expression evaluation
        expr = expr.strip()

        if expr.startswith("{") and expr.endswith("}"):
            # Try to parse as JSON-like object
            try:
                # Replace JavaScript variables with values
                for var_name, var_value in env.items():
                    if var_name in expr:
                        if isinstance(var_value, str):
                            expr = expr.replace(var_name, f'"{var_value}"')
                        else:
                            expr = expr.replace(var_name, str(var_value))

                return json.loads(expr)
            except json.JSONDecodeError:
                pass

        return {}


class JSONPathParser:
    """JSONPath parser for field extraction."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def extract(self, data: Dict[str, Any], path: str) -> Any:
        """Extract value using JSONPath expression."""
        try:
            if path.startswith("$"):
                return self._extract_jsonpath(data, path)
            else:
                return self._extract_simple_path(data, path)
        except Exception as e:
            raise JSONPathError(f"JSONPath extraction failed: {str(e)}")

    def compile(self, path: str) -> "CompiledJSONPath":
        """Compile JSONPath for efficient reuse."""
        return CompiledJSONPath(path)

    def _extract_jsonpath(self, data: Dict[str, Any], path: str) -> Any:
        """Extract using JSONPath expression."""
        # Simplified JSONPath implementation
        # In production, use a proper JSONPath library like jsonpath-ng

        path = path[1:]  # Remove leading $
        if not path or path == ".":
            return data

        if path.startswith("."):
            path = path[1:]

        return self._extract_simple_path(data, path)

    def _extract_simple_path(self, data: Any, path: str) -> Any:
        """Extract using simple dot notation path."""
        if not path:
            return data

        parts = path.split(".")
        current = data

        for part in parts:
            if current is None:
                return None

            # Handle array access
            if "[" in part and part.endswith("]"):
                field_name, array_part = part.split("[", 1)
                array_index = array_part[:-1]  # Remove closing ]

                if field_name:
                    current = current.get(field_name) if isinstance(current, dict) else None

                if current is None:
                    return None

                if array_index == "*":
                    # Return all array elements
                    return current if isinstance(current, list) else []
                else:
                    try:
                        index = int(array_index)
                        current = (
                            current[index]
                            if isinstance(current, list) and 0 <= index < len(current)
                            else None
                        )
                    except (ValueError, IndexError):
                        return None
            else:
                # Simple field access
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None

        return current


class CompiledJSONPath:
    """Compiled JSONPath for efficient extraction."""

    def __init__(self, path: str):
        self.path = path
        self.parser = JSONPathParser()

    def extract(self, data: Dict[str, Any]) -> Any:
        """Extract value from data."""
        return self.parser.extract(data, self.path)


class FunctionRegistry:
    """Registry for built-in transformation functions."""

    def __init__(self):
        self.functions: Dict[str, Callable] = {}
        self.logger = get_logger(__name__)
        self._register_builtin_functions()

    def _register_builtin_functions(self):
        """Register built-in transformation functions."""
        self.functions.update(
            {
                "date_format": self._date_format,
                "string_upper": self._string_upper,
                "string_lower": self._string_lower,
                "json_stringify": self._json_stringify,
                "json_parse": self._json_parse,
                "array_join": self._array_join,
                "array_length": self._array_length,
                "math_round": self._math_round,
            }
        )

    def register_function(self, name: str, func: Callable):
        """Register a custom transformation function."""
        self.functions[name] = func

    def get_function(self, name: str) -> Callable:
        """Get a transformation function by name."""
        if name not in self.functions:
            raise FunctionNotFoundError(f"Function '{name}' not found")
        return self.functions[name]

    def list_functions(self) -> List[str]:
        """List all available function names."""
        return list(self.functions.keys())

    # Built-in functions
    def _date_format(
        self, value: Any, format: str = "%Y-%m-%d %H:%M:%S", timezone: str = None
    ) -> str:
        """Format date value."""
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt.strftime(format)
            except ValueError:
                return str(value)
        return str(value)

    def _string_upper(self, value: Any) -> str:
        """Convert string to uppercase."""
        return str(value).upper()

    def _string_lower(self, value: Any) -> str:
        """Convert string to lowercase."""
        return str(value).lower()

    def _json_stringify(self, value: Any, indent: int = None) -> str:
        """Convert value to JSON string."""
        return json.dumps(value, indent=indent, ensure_ascii=False)

    def _json_parse(self, value: str) -> Any:
        """Parse JSON string to value."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def _array_join(self, value: List[Any], separator: str = ",") -> str:
        """Join array elements into string."""
        if not isinstance(value, list):
            return str(value)
        return separator.join(str(item) for item in value)

    def _array_length(self, value: List[Any]) -> int:
        """Get array length."""
        if isinstance(value, list):
            return len(value)
        return 0

    def _math_round(self, value: Any, digits: int = 0) -> float:
        """Round numeric value."""
        try:
            return round(float(value), digits)
        except (ValueError, TypeError):
            return 0.0
