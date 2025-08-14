"""
Action Node Executor.

Handles action operations like running code, HTTP requests, data transformations, etc.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from shared.models.node_enums import ActionSubtype
from shared.node_specs import node_spec_registry
from shared.node_specs.base import NodeSpec

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult


class ActionNodeExecutor(BaseNodeExecutor):
    """Executor for ACTION_NODE type."""

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for action nodes."""
        if node_spec_registry and self._subtype:
            # Return the specific spec for current subtype
            return node_spec_registry.get_spec(NodeType.ACTION.value, self._subtype)
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported action subtypes."""
        return [subtype.value for subtype in ActionSubtype]

    def validate(self, node: Any) -> List[str]:
        """Validate action node configuration using spec-based validation."""
        # First use the base class validation which includes spec validation
        errors = super().validate(node)

        # If spec validation passed, we're done
        if not errors and self.spec:
            return errors

        # Fallback to basic validation if spec not available
        if not node.subtype:
            errors.append("Action subtype is required")
            return errors

        if node.subtype not in self.get_supported_subtypes():
            errors.append(f"Unsupported action subtype: {node.subtype}")

        return errors

    def _validate_legacy(self, node: Any) -> List[str]:
        """Legacy validation for backward compatibility."""
        errors = []

        if not hasattr(node, "subtype"):
            return errors

        subtype = node.subtype

        if subtype == ActionSubtype.RUN_CODE.value:
            errors.extend(self._validate_required_parameters(node, ["code", "language"]))
            if hasattr(node, "parameters"):
                language = node.parameters.get("language", "")
                if language not in ["python", "javascript", "bash", "sql", "r", "julia"]:
                    errors.append(f"Unsupported language: {language}")

        elif subtype == ActionSubtype.HTTP_REQUEST.value:
            errors.extend(self._validate_required_parameters(node, ["method", "url"]))
            if hasattr(node, "parameters"):
                method = node.parameters.get("method", "").upper()
                if method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
                    errors.append(f"Invalid HTTP method: {method}")

        elif subtype == ActionSubtype.DATA_TRANSFORMATION.value:
            errors.extend(
                self._validate_required_parameters(
                    node, ["transformation_type", "transformation_rule"]
                )
            )
            if hasattr(node, "parameters"):
                transform_type = node.parameters.get("transformation_type", "")
                if transform_type not in [
                    "filter",
                    "map",
                    "reduce",
                    "sort",
                    "group",
                    "join",
                    "aggregate",
                    "custom",
                ]:
                    errors.append(f"Invalid transformation type: {transform_type}")

        elif subtype == ActionSubtype.FILE_OPERATION.value:
            errors.extend(self._validate_required_parameters(node, ["operation", "file_path"]))
            if hasattr(node, "parameters"):
                operation = node.parameters.get("operation", "")
                if operation not in ["read", "write", "copy", "move", "delete", "list"]:
                    errors.append(f"Invalid file operation: {operation}")

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute action node."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype
            logs.append(f"Executing action node with subtype: {subtype}")

            if subtype == ActionSubtype.RUN_CODE.value:
                return self._execute_run_code(context, logs, start_time)
            elif subtype == ActionSubtype.HTTP_REQUEST.value:
                return self._execute_http_request(context, logs, start_time)
            elif subtype == ActionSubtype.DATA_TRANSFORMATION.value:
                return self._execute_data_transformation(context, logs, start_time)
            elif subtype == ActionSubtype.FILE_OPERATION.value:
                return self._execute_file_operation(context, logs, start_time)
            elif subtype == ActionSubtype.DATABASE_QUERY.value:
                return self._execute_database_query(context, logs, start_time)
            elif subtype == ActionSubtype.WEB_SEARCH.value:
                return self._execute_web_search(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported action subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

        except Exception as e:
            return self._create_error_result(
                f"Error executing action: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_run_code(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute code in specified language."""
        # Use spec-based parameter retrieval
        code = self.get_parameter_with_spec(context, "code")
        language = self.get_parameter_with_spec(context, "language")
        timeout = self.get_parameter_with_spec(context, "timeout")
        environment = self.get_parameter_with_spec(context, "environment")
        capture_output = self.get_parameter_with_spec(context, "capture_output")

        logs.append(f"Running {language} code with timeout: {timeout}s")

        try:
            if language == "python":
                result = self._run_python_code(code, context.input_data, timeout)
            elif language == "javascript":
                result = self._run_javascript_code(code, context.input_data, timeout)
            elif language == "bash":
                result = self._run_bash_code(code, context.input_data, timeout)
            elif language == "sql":
                result = self._run_sql_code(code, context.input_data, timeout)
            else:
                return self._create_error_result(
                    f"Unsupported language: {language}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

            output_data = {
                "action_type": "run_code",
                "language": language,
                "code": code,
                "result": result,
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "return_code": result.get("return_code", 0),
                "execution_time": result.get("execution_time", 0),
                "executed_at": datetime.now().isoformat(),
            }

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
            )

        except Exception as e:
            return self._create_error_result(
                f"Error running {language} code: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_http_request(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute HTTP request."""
        # Use spec-based parameter retrieval
        method = self.get_parameter_with_spec(context, "method")
        url = self.get_parameter_with_spec(context, "url")
        headers = self.get_parameter_with_spec(context, "headers")
        data = self.get_parameter_with_spec(context, "data")
        timeout = self.get_parameter_with_spec(context, "timeout")
        authentication = self.get_parameter_with_spec(context, "authentication")
        retry_attempts = self.get_parameter_with_spec(context, "retry_attempts")

        # Convert method to uppercase
        if method:
            method = method.upper()

        # Debug logging
        logs.append(f"Parameters: {context.node.parameters}")
        logs.append(f"Headers type: {type(headers)}, value: {headers}")
        logs.append(f"Making {method} request to {url}")

        try:
            # Ensure headers is a dictionary
            if isinstance(headers, str):
                headers = {}
                logs.append("WARNING: headers was a string, using empty dict")

            # Also ensure data is a dictionary
            if isinstance(data, str):
                data = {}
                logs.append("WARNING: data was a string, using empty dict")

            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if method in ["POST", "PUT", "PATCH"] else None,
                params=data if method == "GET" else None,
                timeout=timeout,
            )

            output_data = {
                "action_type": "http_request",
                "method": method,
                "url": url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "response_text": response.text,
                "response_json": self._safe_json_parse(response.text),
                "execution_time": time.time() - start_time,
                "executed_at": datetime.now().isoformat(),
            }

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
            )

        except Exception as e:
            return self._create_error_result(
                f"Error making HTTP request: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_data_transformation(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute data transformation."""
        transformation_type = context.get_parameter("transformation_type", "filter")
        transformation_config = context.get_parameter("transformation_config", {})

        logs.append(f"Transforming data using {transformation_type}")

        try:
            input_data = context.input_data.get("data", [])

            if transformation_type == "filter":
                result = self._filter_data(input_data, transformation_config)
            elif transformation_type == "map":
                result = self._map_data(input_data, transformation_config)
            elif transformation_type == "reduce":
                result = self._reduce_data(input_data, transformation_config)
            elif transformation_type == "sort":
                result = self._sort_data(input_data, transformation_config)
            elif transformation_type == "group":
                result = self._group_data(input_data, transformation_config)
            elif transformation_type == "join":
                result = self._join_data(input_data, transformation_config)
            else:
                return self._create_error_result(
                    f"Unsupported transformation type: {transformation_type}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

            output_data = {
                "action_type": "data_transformation",
                "transformation_type": transformation_type,
                "input_data": input_data,
                "transformed_data": result,
                "input_count": len(input_data) if isinstance(input_data, list) else 1,
                "output_count": len(result) if isinstance(result, list) else 1,
                "executed_at": datetime.now().isoformat(),
            }

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
            )

        except Exception as e:
            return self._create_error_result(
                f"Error transforming data: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_file_operation(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute file operation."""
        operation_type = context.get_parameter("operation_type", "read")
        file_path = context.get_parameter("file_path", "")
        content = context.get_parameter("content", "")

        logs.append(f"Performing {operation_type} operation on {file_path}")

        try:
            if operation_type == "read":
                result = self._read_file(file_path)
            elif operation_type == "write":
                result = self._write_file(file_path, content)
            elif operation_type == "copy":
                target_path = context.get_parameter("target_path", "")
                result = self._copy_file(file_path, target_path)
            elif operation_type == "move":
                target_path = context.get_parameter("target_path", "")
                result = self._move_file(file_path, target_path)
            elif operation_type == "delete":
                result = self._delete_file(file_path)
            elif operation_type == "list":
                result = self._list_files(file_path)
            else:
                return self._create_error_result(
                    f"Unsupported file operation type: {operation_type}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

            output_data = {
                "action_type": "file_operation",
                "operation_type": operation_type,
                "file_path": file_path,
                "result": result,
                "success": result.get("success", False),
                "executed_at": datetime.now().isoformat(),
            }

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
            )

        except Exception as e:
            return self._create_error_result(
                f"Error performing file operation: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _run_python_code(
        self, code: str, input_data: Dict[str, Any], timeout: int
    ) -> Dict[str, Any]:
        """Run Python code safely."""
        exec_start = time.time()

        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Execute the code
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "INPUT_DATA": json.dumps(input_data)},
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "execution_time": time.time() - exec_start,
            }
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def _run_javascript_code(
        self, code: str, input_data: Dict[str, Any], timeout: int
    ) -> Dict[str, Any]:
        """Run JavaScript code safely."""
        exec_start = time.time()

        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(f"const inputData = {json.dumps(input_data)};\n{code}")
            temp_file = f.name

        try:
            # Execute the code using node
            result = subprocess.run(
                ["node", temp_file], capture_output=True, text=True, timeout=timeout
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "execution_time": time.time() - exec_start,
            }
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def _run_bash_code(self, code: str, input_data: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Run bash code safely."""
        exec_start = time.time()

        try:
            # Execute the code
            result = subprocess.run(
                ["bash", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "INPUT_DATA": json.dumps(input_data)},
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "execution_time": time.time() - exec_start,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": 1,
                "execution_time": time.time() - exec_start,
            }

    def _run_sql_code(self, code: str, input_data: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Run SQL code (mock implementation)."""
        exec_start = time.time()

        # Mock SQL execution
        return {
            "stdout": f"SQL executed: {code}",
            "stderr": "",
            "return_code": 0,
            "execution_time": time.time() - exec_start,
            "rows_affected": 1,
        }

    def _safe_json_parse(self, text: str) -> Any:
        """Safely parse JSON text."""
        try:
            return json.loads(text)
        except:
            return None

    def _filter_data(self, data: List[Any], config: Dict[str, Any]) -> List[Any]:
        """Filter data based on condition."""
        condition = config.get("condition", lambda x: True)
        if isinstance(condition, str):
            # Simple string-based filtering
            return [item for item in data if condition in str(item)]
        return data

    def _map_data(self, data: List[Any], config: Dict[str, Any]) -> List[Any]:
        """Map data using transformation."""
        transform = config.get("transform", lambda x: x)
        return [transform(item) for item in data]

    def _reduce_data(self, data: List[Any], config: Dict[str, Any]) -> Any:
        """Reduce data using function."""
        func = config.get("function", lambda x, y: x + y)
        initial = config.get("initial", 0)
        result = initial
        for item in data:
            result = func(result, item)
        return result

    def _sort_data(self, data: List[Any], config: Dict[str, Any]) -> List[Any]:
        """Sort data."""
        key = config.get("key", None)
        reverse = config.get("reverse", False)
        return sorted(data, key=key, reverse=reverse)

    def _group_data(self, data: List[Any], config: Dict[str, Any]) -> Dict[str, List[Any]]:
        """Group data by key."""
        key_func = config.get("key", lambda x: str(x))
        groups = {}
        for item in data:
            group_key = key_func(item)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)
        return groups

    def _join_data(self, data: List[Any], config: Dict[str, Any]) -> List[Any]:
        """Join data from multiple sources."""
        # Mock implementation
        return data

    def _read_file(self, file_path: str) -> Dict[str, Any]:
        """Read file content."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"success": True, "content": content, "size": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Write content to file."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "size": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _copy_file(self, source_path: str, target_path: str) -> Dict[str, Any]:
        """Copy file."""
        try:
            import shutil

            shutil.copy2(source_path, target_path)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _move_file(self, source_path: str, target_path: str) -> Dict[str, Any]:
        """Move file."""
        try:
            import shutil

            shutil.move(source_path, target_path)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _delete_file(self, file_path: str) -> Dict[str, Any]:
        """Delete file."""
        try:
            os.remove(file_path)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_files(self, directory_path: str) -> Dict[str, Any]:
        """List files in directory."""
        try:
            files = os.listdir(directory_path)
            return {"success": True, "files": files, "count": len(files)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_database_query(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute database query (mock implementation)."""
        query = self.get_parameter_with_spec(context, "query")
        database_url = self.get_parameter_with_spec(context, "database_url")

        logs.append(f"Executing database query: {query[:50]}...")

        # Mock implementation - would connect to actual database in production
        output_data = {
            "action_type": "database_query",
            "query": query,
            "database_url": database_url,
            "rows_affected": 1,
            "result": [{"id": 1, "status": "success"}],
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_web_search(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute web search (mock implementation)."""
        query = self.get_parameter_with_spec(context, "search_query")
        max_results = self.get_parameter_with_spec(context, "max_results")

        logs.append(f"Searching web for: {query}")

        # Mock implementation - would use actual search API in production
        output_data = {
            "action_type": "web_search",
            "query": query,
            "max_results": max_results,
            "results": [
                {
                    "title": "Search Result 1",
                    "url": "https://example.com/1",
                    "snippet": "Mock result 1",
                },
                {
                    "title": "Search Result 2",
                    "url": "https://example.com/2",
                    "snippet": "Mock result 2",
                },
            ],
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )
