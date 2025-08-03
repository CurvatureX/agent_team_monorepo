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

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult

try:
    from shared.node_specs import node_spec_registry
    from shared.node_specs.base import NodeSpec
except ImportError:
    node_spec_registry = None
    NodeSpec = None


class ActionNodeExecutor(BaseNodeExecutor):
    """Executor for ACTION_NODE type."""

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for action nodes."""
        if node_spec_registry:
            # Return the HTTP_REQUEST spec as default (most commonly used)
            return node_spec_registry.get_spec("ACTION_NODE", "HTTP_REQUEST")
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported action subtypes."""
        return ["RUN_CODE", "HTTP_REQUEST", "DATA_TRANSFORMATION", "FILE_OPERATION"]

    def validate(self, node: Any) -> List[str]:
        """Validate action node configuration."""
        errors = []

        if not node.subtype:
            errors.append("Action subtype is required")
            return errors

        subtype = node.subtype

        if subtype == "RUN_CODE":
            errors.extend(self._validate_required_parameters(node, ["code", "language"]))
            language = node.parameters.get("language", "")
            if language not in ["python", "javascript", "bash", "sql"]:
                errors.append(f"Unsupported language: {language}")

        elif subtype == "HTTP_REQUEST":
            errors.extend(self._validate_required_parameters(node, ["method", "url"]))
            method = node.parameters.get("method", "").upper()
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                errors.append(f"Invalid HTTP method: {method}")

        elif subtype == "DATA_TRANSFORMATION":
            errors.extend(self._validate_required_parameters(node, ["transformation_type"]))
            transform_type = node.parameters.get("transformation_type", "")
            if transform_type not in ["filter", "map", "reduce", "sort", "group", "join"]:
                errors.append(f"Invalid transformation type: {transform_type}")

        elif subtype == "FILE_OPERATION":
            errors.extend(self._validate_required_parameters(node, ["operation_type"]))
            operation_type = node.parameters.get("operation_type", "")
            if operation_type not in ["read", "write", "copy", "move", "delete", "list"]:
                errors.append(f"Invalid file operation type: {operation_type}")

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute action node."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype
            logs.append(f"Executing action node with subtype: {subtype}")

            if subtype == "RUN_CODE":
                return self._execute_run_code(context, logs, start_time)
            elif subtype == "HTTP_REQUEST":
                return self._execute_http_request(context, logs, start_time)
            elif subtype == "DATA_TRANSFORMATION":
                return self._execute_data_transformation(context, logs, start_time)
            elif subtype == "FILE_OPERATION":
                return self._execute_file_operation(context, logs, start_time)
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
        code = context.get_parameter("code", "")
        language = context.get_parameter("language", "python")
        timeout = context.get_parameter("timeout", 30)

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
        method = context.get_parameter("method", "GET").upper()
        url = context.get_parameter("url", "")
        headers = context.get_parameter("headers", {})
        data = context.get_parameter("data", {})
        timeout = context.get_parameter("timeout", 30)

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
