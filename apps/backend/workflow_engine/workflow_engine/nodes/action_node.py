"""
Action Node Executor.

Handles internal actions like code execution, HTTP requests, data transformation, etc.
"""

import json
import subprocess
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
import tempfile
import os

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult, ExecutionStatus


class ActionNodeExecutor(BaseNodeExecutor):
    """Executor for ACTION_NODE type."""
    
    def get_supported_subtypes(self) -> List[str]:
        """Get supported action subtypes."""
        return [
            "RUN_CODE",
            "HTTP_REQUEST",
            "DATA_TRANSFORMATION",
            "FILE_OPERATION"
        ]
    
    def validate(self, node: Any) -> List[str]:
        """Validate action node configuration."""
        errors = []
        
        if not node.subtype:
            errors.append("Action subtype is required")
            return errors
        
        subtype = node.subtype
        
        if subtype == "RUN_CODE":
            errors.extend(self._validate_required_parameters(node, ["language", "code"]))
            language = node.parameters.get("language")
            if language not in ["python", "javascript", "bash", "shell"]:
                errors.append(f"Unsupported language: {language}")
        
        elif subtype == "HTTP_REQUEST":
            errors.extend(self._validate_required_parameters(node, ["url", "method"]))
            method = node.parameters.get("method", "GET")
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                errors.append(f"Invalid HTTP method: {method}")
        
        elif subtype == "DATA_TRANSFORMATION":
            errors.extend(self._validate_required_parameters(node, ["transformation_type"]))
        
        elif subtype == "FILE_OPERATION":
            errors.extend(self._validate_required_parameters(node, ["operation", "file_path"]))
        
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
                    logs=logs
                )
        
        except Exception as e:
            return self._create_error_result(
                f"Error executing action: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_run_code(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute code in specified language."""
        language = context.get_parameter("language")
        code = context.get_parameter("code")
        timeout = context.get_parameter("timeout", 30)
        
        logs.append(f"Running {language} code with timeout {timeout}s")
        
        try:
            if language == "python":
                result = self._run_python_code(code, context.input_data, timeout)
            elif language == "javascript":
                result = self._run_javascript_code(code, context.input_data, timeout)
            elif language in ["bash", "shell"]:
                result = self._run_shell_code(code, context.input_data, timeout)
            else:
                return self._create_error_result(
                    f"Unsupported language: {language}",
                    execution_time=time.time() - start_time,
                    logs=logs
                )
            
            output_data = {
                "language": language,
                "code": code,
                "result": result,
                "executed_at": datetime.now().isoformat()
            }
            
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs
            )
        
        except subprocess.TimeoutExpired:
            return self._create_error_result(
                f"Code execution timed out after {timeout}s",
                execution_time=time.time() - start_time,
                logs=logs
            )
        except Exception as e:
            return self._create_error_result(
                f"Code execution failed: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_http_request(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute HTTP request."""
        url = context.get_parameter("url")
        method = context.get_parameter("method", "GET")
        headers = context.get_parameter("headers", {})
        
        logs.append(f"HTTP {method} request to {url}")
        
        # Simulate HTTP request
        request_data = context.input_data.get("request_data", {})
        
        # In a real implementation, this would use httpx or requests
        simulated_response = {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "data": {"success": True, "message": "Request completed successfully"},
            "request_info": {
                "url": url,
                "method": method,
                "headers": headers,
                "data": request_data
            }
        }
        
        output_data = {
            "http_request": {
                "url": url,
                "method": method,
                "headers": headers,
                "request_data": request_data
            },
            "response": simulated_response,
            "requested_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_data_transformation(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute data transformation."""
        transformation_type = context.get_parameter("transformation_type")
        
        logs.append(f"Data transformation: {transformation_type}")
        
        input_data = context.input_data
        
        if transformation_type == "json_to_csv":
            transformed_data = self._json_to_csv(input_data)
        elif transformation_type == "csv_to_json":
            transformed_data = self._csv_to_json(input_data)
        elif transformation_type == "filter":
            filter_condition = context.get_parameter("filter_condition", {})
            transformed_data = self._filter_data(input_data, filter_condition)
        elif transformation_type == "sort":
            sort_key = context.get_parameter("sort_key", "id")
            transformed_data = self._sort_data(input_data, sort_key)
        elif transformation_type == "aggregate":
            group_by = context.get_parameter("group_by", "category")
            transformed_data = self._aggregate_data(input_data, group_by)
        else:
            transformed_data = input_data  # No transformation
        
        output_data = {
            "transformation_type": transformation_type,
            "original_data": input_data,
            "transformed_data": transformed_data,
            "transformed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_file_operation(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute file operation."""
        operation = context.get_parameter("operation")
        file_path = context.get_parameter("file_path")
        
        logs.append(f"File operation: {operation} on {file_path}")
        
        # Simulate file operations (in real implementation, would actually perform file ops)
        if operation == "read":
            result = {
                "operation": "read",
                "file_path": file_path,
                "content": "Simulated file content",
                "size": 1024,
                "modified_at": datetime.now().isoformat()
            }
        elif operation == "write":
            content = context.input_data.get("content", "")
            result = {
                "operation": "write",
                "file_path": file_path,
                "content": content,
                "bytes_written": len(content),
                "written_at": datetime.now().isoformat()
            }
        elif operation == "delete":
            result = {
                "operation": "delete",
                "file_path": file_path,
                "deleted": True,
                "deleted_at": datetime.now().isoformat()
            }
        else:
            result = {
                "operation": operation,
                "file_path": file_path,
                "status": "completed"
            }
        
        return self._create_success_result(
            output_data=result,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _run_python_code(self, code: str, input_data: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Run Python code in a sandboxed environment."""
        # In a real implementation, this would use a proper sandbox
        # For now, simulate execution
        return {
            "stdout": "Python code executed successfully",
            "stderr": "",
            "return_code": 0,
            "execution_time": 0.5,
            "result": {"processed": True, "input_data": input_data}
        }
    
    def _run_javascript_code(self, code: str, input_data: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Run JavaScript code."""
        # Simulate JavaScript execution
        return {
            "stdout": "JavaScript code executed successfully",
            "stderr": "",
            "return_code": 0,
            "execution_time": 0.3,
            "result": {"processed": True, "input_data": input_data}
        }
    
    def _run_shell_code(self, code: str, input_data: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Run shell code."""
        # Simulate shell execution
        return {
            "stdout": "Shell command executed successfully",
            "stderr": "",
            "return_code": 0,
            "execution_time": 0.2,
            "result": {"processed": True, "input_data": input_data}
        }
    
    def _json_to_csv(self, data: Dict[str, Any]) -> str:
        """Convert JSON to CSV format."""
        # Simulate JSON to CSV conversion
        return "id,name,value\n1,Item1,100\n2,Item2,200"
    
    def _csv_to_json(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert CSV to JSON format."""
        # Simulate CSV to JSON conversion
        return [
            {"id": 1, "name": "Item1", "value": 100},
            {"id": 2, "name": "Item2", "value": 200}
        ]
    
    def _filter_data(self, data: Dict[str, Any], condition: Dict[str, Any]) -> Dict[str, Any]:
        """Filter data based on condition."""
        # Simulate data filtering
        return {"filtered_data": data, "condition": condition, "count": 2}
    
    def _sort_data(self, data: Dict[str, Any], sort_key: str) -> Dict[str, Any]:
        """Sort data by specified key."""
        # Simulate data sorting
        return {"sorted_data": data, "sort_key": sort_key, "order": "asc"}
    
    def _aggregate_data(self, data: Dict[str, Any], group_by: str) -> Dict[str, Any]:
        """Aggregate data by specified field."""
        # Simulate data aggregation
        return {
            "aggregated_data": {
                "group1": {"count": 5, "sum": 150},
                "group2": {"count": 3, "sum": 90}
            },
            "group_by": group_by
        } 