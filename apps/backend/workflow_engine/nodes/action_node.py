"""
Action Node Executor.

Handles HTTP requests, code execution, and data transformations.
"""

import json
from datetime import datetime
from typing import Any, Dict

from shared.models.node_enums import ActionSubtype, NodeType

from utils.unicode_utils import clean_unicode_string, safe_json_loads

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult
from .factory import NodeExecutorFactory


@NodeExecutorFactory.register(NodeType.ACTION.value)
class ActionNodeExecutor(BaseNodeExecutor):
    """Executor for action nodes."""

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute action node."""
        action_type = self.subtype or context.get_parameter(
            "action_type", ActionSubtype.HTTP_REQUEST.value
        )

        self.log_execution(
            context,
            f"🔍 DEBUG: ActionNode execute - subtype='{self.subtype}', action_type='{action_type}', parameters={context.parameters}",
        )
        self.log_execution(context, f"Executing action node: {action_type}")

        if action_type == ActionSubtype.HTTP_REQUEST.value:
            return await self._execute_http_request(context)
        elif action_type == ActionSubtype.DATA_TRANSFORMATION.value:
            return await self._execute_data_transform(context)
        else:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Unsupported action type: {action_type}",
                error_details={
                    "action_type": action_type,
                    "supported_actions": [
                        ActionSubtype.HTTP_REQUEST.value,
                        ActionSubtype.DATA_TRANSFORMATION.value,
                    ],
                    "solution": "Use one of the supported action types",
                },
            )

    async def _execute_http_request(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute HTTP request."""
        import httpx

        url = context.get_parameter("url", "")
        method = context.get_parameter("method", "GET").upper()
        headers = context.get_parameter("headers", {})
        payload = context.get_parameter("payload", {})
        timeout = context.get_parameter("timeout", 30.0)

        if not url:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR, error_message="URL is required for HTTP request"
            )

        self.log_execution(context, f"Executing HTTP request: {method} {url}")

        try:
            # Set default headers
            if "Content-Type" not in headers and method in ["POST", "PUT", "PATCH"]:
                headers["Content-Type"] = "application/json"

            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, timeout=timeout)
                elif method == "POST":
                    response = await client.post(
                        url, headers=headers, json=payload, timeout=timeout
                    )
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=payload, timeout=timeout)
                elif method == "PATCH":
                    response = await client.patch(
                        url, headers=headers, json=payload, timeout=timeout
                    )
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers, timeout=timeout)
                else:
                    return NodeExecutionResult(
                        status=ExecutionStatus.ERROR,
                        error_message=f"Unsupported HTTP method: {method}",
                    )

            # Try to parse JSON response
            try:
                response_data = response.json()
            except:
                response_data = response.text

            self.log_execution(context, f"✅ HTTP request completed: {response.status_code}")

            return NodeExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output_data={
                    "response": {
                        "status_code": response.status_code,
                        "data": response_data,
                        "headers": dict(response.headers),
                    },
                    "request": {
                        "url": url,
                        "method": method,
                        "headers": headers,
                        "payload": payload,
                    },
                    "success": 200 <= response.status_code < 300,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            self.log_execution(context, f"HTTP request failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"HTTP request failed: {str(e)}",
                error_details={"url": url, "method": method},
            )

    async def _execute_data_transform(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute data transformation."""
        # Support both transform_type and transformation_type parameters
        transform_type = context.get_parameter("transform_type") or context.get_parameter(
            "transformation_type", "jq"
        )
        transform_script = (
            context.get_parameter("transform_script")
            or context.get_parameter("transformation_rule")
            or ""  # Official spec parameter
        )
        mapping_rules = context.get_parameter("mapping_rules", {})

        # Support field_mappings parameter (common in tests)
        field_mappings = context.get_parameter("field_mappings", {})
        if field_mappings and not mapping_rules:
            # field_mappings might be a JSON string, parse it safely
            if isinstance(field_mappings, str):
                try:
                    # Clean Unicode before parsing JSON
                    cleaned_mappings = clean_unicode_string(field_mappings)
                    mapping_rules = safe_json_loads(cleaned_mappings)
                except (json.JSONDecodeError, TypeError) as e:
                    self.log_execution(
                        context, f"Failed to parse field_mappings JSON: {e}", "ERROR"
                    )
                    mapping_rules = {}
            else:
                mapping_rules = field_mappings

        # Handle field_mapping transformation type
        if transform_type == "field_mapping":
            transform_type = "mapping"

        self.log_execution(context, f"Executing data transformation: {transform_type}")

        try:
            if transform_type == "jq":
                # JQ-style transformations
                transformed_data = await self._apply_jq_transform(
                    context.input_data, transform_script
                )
            elif transform_type == "mapping":
                # Field mapping transformations
                transformed_data = await self._apply_field_mapping(
                    context.input_data, mapping_rules
                )
            elif transform_type == "python":
                # Python expression transformations (limited for security)
                transformed_data = await self._apply_python_transform(
                    context.input_data, transform_script
                )
            elif transform_type == "jsonpath" or transform_type == "custom":
                # JSONPath transformations (also handle "custom" type for spec compliance)
                self.log_execution(
                    context,
                    f"🔍 DEBUG: Applying JSONPath '{transform_script}' to data: {context.input_data}",
                )
                transformed_data = await self._apply_jsonpath_transform(
                    context.input_data, transform_script
                )
                self.log_execution(context, f"🔍 DEBUG: JSONPath result: {transformed_data}")
            else:
                # Default: pass-through with basic transformations
                transformed_data = context.input_data

            self.log_execution(context, f"✅ Data transformation completed")

            return NodeExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output_data={
                    "transformed_data": transformed_data,
                    "original_data": context.input_data,
                    "transform_type": transform_type,
                    "transform_script": transform_script,
                    "mapping_rules": mapping_rules,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            self.log_execution(context, f"Data transformation failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Data transformation failed: {str(e)}",
                error_details={
                    "transform_type": transform_type,
                    "transform_script": transform_script,
                },
            )

    async def _apply_jq_transform(self, data: Any, script: str) -> Any:
        """Apply JQ-style transformation (simplified implementation)."""
        if not script:
            return data

        # Basic JQ-like operations (in real implementation, use actual jq library)
        if script == ".":
            return data
        elif script.startswith(".") and "|" not in script:
            # Simple field access like ".field" or ".field.subfield"
            field_path = script[1:]  # Remove leading dot
            return self._get_nested_value(data, field_path)
        elif script == "keys":
            return list(data.keys()) if isinstance(data, dict) else []
        elif script == "values":
            return list(data.values()) if isinstance(data, dict) else []
        elif script == "length":
            return len(data) if hasattr(data, "__len__") else 0
        else:
            # For complex scripts, return original data (in real implementation, use jq library)
            return data

    async def _apply_field_mapping(self, data: Any, mapping_rules: Dict[str, str]) -> Any:
        """Apply field mapping transformations."""
        if not mapping_rules or not isinstance(data, dict):
            return data

        transformed = {}
        for target_field, source_path in mapping_rules.items():
            value = self._get_nested_value(data, source_path)
            if value is not None:
                transformed[target_field] = value

        return transformed

    async def _apply_python_transform(self, data: Any, script: str) -> Any:
        """Apply Python expression transformation (limited for security)."""
        if not script:
            return data

        # Very limited Python transformations for security
        # In real implementation, use a sandboxed environment or AST parsing
        safe_operations = {
            "upper": lambda x: x.upper() if isinstance(x, str) else x,
            "lower": lambda x: x.lower() if isinstance(x, str) else x,
            "strip": lambda x: x.strip() if isinstance(x, str) else x,
            "len": lambda x: len(x) if hasattr(x, "__len__") else 0,
            "str": lambda x: str(x),
            "int": lambda x: int(x) if str(x).isdigit() else x,
            "float": lambda x: float(x) if isinstance(x, (int, float, str)) else x,
        }

        if script in safe_operations:
            return safe_operations[script](data)
        elif script.startswith("data.") and len(script.split(".")) == 2:
            field = script.split(".")[1]
            return data.get(field) if isinstance(data, dict) else data
        else:
            # Return original data for unsupported operations
            return data

    async def _apply_jsonpath_transform(self, data: Any, script: str) -> Any:
        """Apply JSONPath transformation (simplified implementation)."""
        if not script:
            return data

        # Basic JSONPath-like operations
        if script == "$":
            return data
        elif script.startswith("$."):
            field_path = script[2:]  # Remove "$."
            return self._get_nested_value(data, field_path)
        elif script == "$..*":
            # Get all values (flattened)
            return self._flatten_values(data)
        else:
            return data

    def _get_nested_value(self, data: Any, path: str) -> Any:
        """Get nested value from data using dot notation."""
        if not path:
            return data

        try:
            keys = path.split(".")
            value = data
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                elif isinstance(value, list) and key.isdigit():
                    index = int(key)
                    value = value[index] if 0 <= index < len(value) else None
                else:
                    return None
            return value
        except:
            return None

    def _flatten_values(self, data: Any) -> list:
        """Flatten all values from nested data structure."""
        values = []
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, (dict, list)):
                    values.extend(self._flatten_values(value))
                else:
                    values.append(value)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    values.extend(self._flatten_values(item))
                else:
                    values.append(item)
        else:
            values.append(data)
        return values

    def validate_parameters(self, context: NodeExecutionContext) -> tuple[bool, str]:
        """Validate action node parameters."""
        action_type = self.subtype or context.get_parameter(
            "action_type", ActionSubtype.HTTP_REQUEST.value
        )

        if action_type == ActionSubtype.HTTP_REQUEST.value:
            url = context.get_parameter("url")
            if not url:
                return False, "HTTP request action requires 'url' parameter"

        elif action_type == ActionSubtype.DATA_TRANSFORMATION.value:
            # Support both transform_type and transformation_type for compatibility
            transform_type = context.get_parameter("transform_type") or context.get_parameter(
                "transformation_type", "jq"
            )
            transform_script = context.get_parameter("transform_script", "")

            # Accept mapping_rules or field_mappings (string or dict)
            mapping_rules = context.get_parameter("mapping_rules", {})
            if not mapping_rules:
                field_mappings = context.get_parameter("field_mappings", {})
                if isinstance(field_mappings, str):
                    try:
                        cleaned = clean_unicode_string(field_mappings)
                        mapping_rules = safe_json_loads(cleaned)
                    except Exception:
                        # If it exists but cannot be parsed, consider it provided to avoid false negatives
                        mapping_rules = field_mappings or {}
                else:
                    mapping_rules = field_mappings or {}

            # Normalize alias
            if transform_type == "field_mapping":
                transform_type = "mapping"

            if transform_type in ["jq", "python", "jsonpath"] and not transform_script:
                return (
                    False,
                    f"{transform_type} transformation requires 'transform_script' parameter",
                )
            elif transform_type == "mapping" and not mapping_rules:
                return (
                    False,
                    "Mapping transformation requires 'mapping_rules' or 'field_mappings' parameter",
                )

        return True, ""
