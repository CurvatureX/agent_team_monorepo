"""Tool Node Executor."""
from datetime import datetime
from typing import Any, Dict

from shared.models.node_enums import NodeType

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult
from .factory import NodeExecutorFactory


@NodeExecutorFactory.register(NodeType.TOOL.value)
class ToolNodeExecutor(BaseNodeExecutor):
    """Executor for tool nodes (MCP tools, utilities, etc.)."""

    def __init__(self, node_type: str = NodeType.TOOL.value, subtype: str = None):
        super().__init__(node_type, subtype)

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute tool node."""
        tool_type = self.subtype or context.get_parameter("tool_type", "utility")
        operation = context.get_parameter("operation", "execute")

        self.log_execution(context, f"Executing tool node: {tool_type}/{operation}")

        try:
            # Handle different tool types
            if tool_type.lower() in ["mcp", "mcp_tool"]:
                return await self._handle_mcp_tool(context, operation)
            elif tool_type.lower() in ["utility", "system"]:
                return await self._handle_utility_tool(context, operation)
            elif tool_type.lower() in ["file", "file_system"]:
                return await self._handle_file_tool(context, operation)
            elif tool_type.lower() in ["api", "http"]:
                return await self._handle_api_tool(context, operation)
            else:
                # Handle unknown tool types with basic execution
                return await self._handle_generic_tool(context, tool_type, operation)

        except Exception as e:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Tool execution failed: {str(e)}",
                error_details={"tool_type": tool_type, "operation": operation},
            )

    async def _handle_mcp_tool(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle MCP (Model Context Protocol) tools."""
        tool_name = context.get_parameter("tool_name", "unknown")
        tool_params = context.get_parameter("tool_parameters", {})

        try:
            # In a real implementation, this would:
            # 1. Connect to MCP server
            # 2. List available tools
            # 3. Execute the specified tool with parameters
            # 4. Return the tool execution result

            self.log_execution(context, f"Executing MCP tool: {tool_name}")

            # For now, simulate tool execution with meaningful output
            if tool_name == "file_read":
                file_path = tool_params.get("path", "unknown")
                mock_content = f"Mock file content from {file_path}"
                output_data = {
                    "tool_name": tool_name,
                    "operation": operation,
                    "file_path": file_path,
                    "content": mock_content,
                    "size": len(mock_content),
                    "success": True,
                }
            elif tool_name == "file_write":
                file_path = tool_params.get("path", "unknown")
                content = tool_params.get("content", "")
                output_data = {
                    "tool_name": tool_name,
                    "operation": operation,
                    "file_path": file_path,
                    "bytes_written": len(content),
                    "success": True,
                }
            else:
                output_data = {
                    "tool_name": tool_name,
                    "operation": operation,
                    "parameters": tool_params,
                    "result": f"Tool {tool_name} executed successfully",
                    "success": True,
                }

            output_data.update(
                {
                    "tool_type": "mcp",
                    "timestamp": datetime.now().isoformat(),
                    "execution_time_ms": 150,  # Simulated execution time
                }
            )

            return NodeExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output_data=output_data,
                metadata={"node_type": "tool", "tool_type": "mcp", "tool_name": tool_name},
            )

        except Exception as e:
            self.log_execution(context, f"MCP tool execution failed: {str(e)}", "ERROR")
            raise

    async def _handle_utility_tool(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle utility/system tools."""
        import hashlib
        import time
        import uuid

        utility_type = context.get_parameter("utility_type", "timestamp")
        input_data = context.input_data

        self.log_execution(context, f"Executing utility tool: {utility_type}")

        if utility_type == "timestamp":
            output_data = {
                "timestamp": datetime.now().isoformat(),
                "unix_timestamp": int(time.time()),
                "timezone": "UTC",
            }
        elif utility_type == "uuid":
            output_data = {"uuid": str(uuid.uuid4()), "uuid_version": 4}
        elif utility_type == "hash":
            text_to_hash = context.get_parameter("text", str(input_data))
            hash_type = context.get_parameter("hash_type", "sha256")

            if hash_type == "md5":
                hash_value = hashlib.md5(text_to_hash.encode()).hexdigest()
            elif hash_type == "sha1":
                hash_value = hashlib.sha1(text_to_hash.encode()).hexdigest()
            else:  # default to sha256
                hash_value = hashlib.sha256(text_to_hash.encode()).hexdigest()

            output_data = {
                "hash_value": hash_value,
                "hash_type": hash_type,
                "input_text": text_to_hash[:100] + "..."
                if len(text_to_hash) > 100
                else text_to_hash,
            }
        elif utility_type == "format":
            format_type = context.get_parameter("format_type", "json")

            if format_type == "json":
                import json

                formatted_data = json.dumps(input_data, indent=2)
            elif format_type == "yaml":
                try:
                    import yaml

                    formatted_data = yaml.dump(input_data, default_flow_style=False)
                except ImportError:
                    formatted_data = str(input_data)  # Fallback
            else:
                formatted_data = str(input_data)

            output_data = {
                "formatted_data": formatted_data,
                "format_type": format_type,
                "original_data": input_data,
            }
        else:
            output_data = {
                "utility_type": utility_type,
                "result": f"Utility {utility_type} executed",
                "input_data": input_data,
            }

        output_data.update(
            {
                "tool_type": "utility",
                "operation": operation,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={"node_type": "tool", "tool_type": "utility", "utility_type": utility_type},
        )

    async def _handle_file_tool(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle file system tools."""
        import os
        import tempfile

        file_path = context.get_parameter("file_path", "")

        self.log_execution(context, f"Executing file tool: {operation} on {file_path}")

        try:
            if operation == "read":
                if file_path and os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    output_data = {
                        "file_path": file_path,
                        "content": content,
                        "size": len(content),
                        "exists": True,
                    }
                else:
                    output_data = {
                        "file_path": file_path,
                        "content": None,
                        "exists": False,
                        "error": "File not found or path not provided",
                    }

            elif operation == "write":
                content = context.get_parameter("content", "")

                if not file_path:
                    # Create temp file if no path provided
                    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
                        f.write(content)
                        file_path = f.name
                else:
                    # Write to specified path (in real implementation, add security checks)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)

                output_data = {
                    "file_path": file_path,
                    "bytes_written": len(content),
                    "success": True,
                }

            elif operation == "list":
                directory = file_path or "."
                if os.path.isdir(directory):
                    files = os.listdir(directory)
                    output_data = {"directory": directory, "files": files, "file_count": len(files)}
                else:
                    output_data = {
                        "directory": directory,
                        "files": [],
                        "error": "Directory not found",
                    }

            else:
                output_data = {
                    "operation": operation,
                    "file_path": file_path,
                    "result": f"File operation {operation} completed",
                }

            output_data.update(
                {
                    "tool_type": "file",
                    "operation": operation,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return NodeExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output_data=output_data,
                metadata={"node_type": "tool", "tool_type": "file", "operation": operation},
            )

        except Exception as e:
            self.log_execution(context, f"File tool execution failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"File operation failed: {str(e)}",
                error_details={"file_path": file_path, "operation": operation},
            )

    async def _handle_api_tool(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle API/HTTP tools."""
        import httpx

        url = context.get_parameter("url", "")
        method = context.get_parameter("method", "GET").upper()
        headers = context.get_parameter("headers", {})
        payload = context.get_parameter("payload", {})

        if not url:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR, error_message="URL is required for API tool"
            )

        self.log_execution(context, f"Executing API tool: {method} {url}")

        try:
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, timeout=30.0)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=payload, timeout=30.0)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers, timeout=30.0)
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

            output_data = {
                "tool_type": "api",
                "operation": operation,
                "method": method,
                "url": url,
                "status_code": response.status_code,
                "response_data": response_data,
                "headers": dict(response.headers),
                "timestamp": datetime.now().isoformat(),
                "success": 200 <= response.status_code < 300,
            }

            return NodeExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output_data=output_data,
                metadata={
                    "node_type": "tool",
                    "tool_type": "api",
                    "status_code": response.status_code,
                },
            )

        except Exception as e:
            self.log_execution(context, f"API tool execution failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"API request failed: {str(e)}",
                error_details={"url": url, "method": method},
            )

    async def _handle_generic_tool(
        self, context: NodeExecutionContext, tool_type: str, operation: str
    ) -> NodeExecutionResult:
        """Handle generic/unknown tool types."""
        import asyncio

        self.log_execution(context, f"Executing generic tool: {tool_type}")

        # Simulate some processing time
        await asyncio.sleep(0.1)

        output_data = {
            "tool_type": tool_type,
            "operation": operation,
            "result": f"Generic tool {tool_type} executed successfully",
            "input_data": context.input_data,
            "parameters": dict(context.parameters) if context.parameters else {},
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={"node_type": "tool", "tool_type": tool_type, "operation": operation},
        )

    def validate_parameters(self, context: NodeExecutionContext) -> tuple[bool, str]:
        """Validate tool node parameters."""
        tool_type = self.subtype or context.get_parameter("tool_type", "utility")

        # Basic validation - most tools are permissive
        if tool_type in ["api", "http"]:
            url = context.get_parameter("url")
            if not url:
                return False, "API tools require 'url' parameter"

        return True, ""
