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
        try:
            if operation == "discover":
                return await self.handle_function_discovery(context)
            elif operation == "execute":
                function_name = context.input_data.get("function_name") or context.get_parameter(
                    "function_name"
                )
                function_args = context.input_data.get("function_args") or context.get_parameter(
                    "function_args", {}
                )

                # Handle case where function_name is "unknown" - look for tool-specific parameters
                if not function_name or function_name == "unknown":
                    # Try to infer function from tool type or node name
                    tool_subtype = context.get_parameter("tool_subtype") or context.get_parameter(
                        "subtype"
                    )
                    if tool_subtype and tool_subtype.lower() in ["notion", "notion_mcp"]:
                        function_name = "notion_search"  # Default Notion function
                        function_args = {
                            "query": context.input_data.get("query", ""),
                            "max_results": context.input_data.get("max_results", 5),
                        }
                        self.log_execution(context, f"🔧 Inferred MCP function: {function_name}")
                    elif tool_subtype and tool_subtype.lower() in ["calendar", "google_calendar"]:
                        function_name = "list_events"  # Default Calendar function
                        function_args = {"max_results": context.input_data.get("max_results", 10)}
                        self.log_execution(context, f"🔧 Inferred MCP function: {function_name}")

                if not function_name or function_name == "unknown":
                    return NodeExecutionResult(
                        status=ExecutionStatus.ERROR,
                        error_message="Missing or invalid function_name for MCP execution",
                        error_details={
                            "operation": operation,
                            "received_function_name": function_name,
                            "available_data": list(context.input_data.keys()),
                            "solution": "Specify 'function_name' parameter or use tool-specific subtype",
                            "examples": {
                                "notion": "notion_search, create_page",
                                "calendar": "list_events, create_event",
                            },
                        },
                    )

                result = await self.handle_function_execution(context, function_name, function_args)

                return NodeExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output_data={
                        "operation": "execute",
                        "function_name": function_name,
                        "result": result,
                        "execution_time": 0.1,  # Placeholder
                    },
                    metadata={
                        "node_type": "tool",
                        "operation": operation,
                        "function_name": function_name,
                    },
                )
            else:
                return NodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error_message=f"Unknown MCP operation: {operation}",
                    error_details={
                        "operation": operation,
                        "supported_operations": ["discover", "execute"],
                    },
                )

        except Exception as e:
            self.log_execution(context, f"MCP tool execution failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"MCP tool execution failed: {str(e)}",
                error_details={"operation": operation},
            )

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

    async def handle_function_discovery(self, context: NodeExecutionContext) -> list:
        """Discover available MCP functions via API Gateway."""
        try:
            import os

            import httpx

            # Get MCP server URL from parameters or use default API Gateway
            mcp_server_url = context.get_parameter("mcp_server_url")
            if not mcp_server_url:
                # Determine API Gateway URL based on environment
                api_gateway_url = os.getenv("API_GATEWAY_URL")
                if api_gateway_url:
                    mcp_server_url = f"{api_gateway_url.rstrip('/')}/api/v1/mcp"
                elif os.getenv("WORKFLOW_ENGINE_URL", "").startswith("http://workflow-engine"):
                    # We're in Docker, use service name
                    mcp_server_url = "http://api-gateway:8000/api/v1/mcp"
                else:
                    # Local development
                    mcp_server_url = "http://localhost:8000/api/v1/mcp"

            # Get API key from parameters or environment
            api_key = context.get_parameter("api_key") or os.getenv("MCP_API_KEY", "dev_default")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            self.log_execution(context, f"🔧 Discovering MCP tools from: {mcp_server_url}")

            # Query API Gateway for available tools
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{mcp_server_url}/tools", headers=headers, timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()

                    # Extract tools from MCP response format
                    if "result" in result and "tools" in result["result"]:
                        tools = result["result"]["tools"]
                    elif "tools" in result:
                        tools = result["tools"]
                    else:
                        tools = []

                    # Apply filtering based on Tool Node parameters (subset exposure)
                    params = tool_context.parameters or {}
                    allowed_tools = set(params.get("allowed_tools", []) or [])
                    allowed_prefixes = list(params.get("allowed_prefixes", []) or [])
                    providers = params.get("providers") or []
                    if isinstance(providers, str):
                        providers = [providers]
                    provider_alias = (
                        params.get("tool_subtype")
                        or params.get("subtype")
                        or params.get("provider")
                    )

                    # Map providers to prefixes
                    provider_prefix = {
                        "notion": "notion_",
                        "notion_mcp": "notion_",
                        "calendar": "google_calendar_",
                        "google_calendar": "google_calendar_",
                        "slack": "slack_",
                        "github": "github_",
                        "gmail": "gmail_",
                        "discord": "discord_",
                        "firecrawl": "firecrawl_",
                    }
                    for p in providers:
                        pref = provider_prefix.get(str(p).lower())
                        if pref and pref not in allowed_prefixes:
                            allowed_prefixes.append(pref)
                    if provider_alias and not allowed_prefixes and not allowed_tools:
                        pref = provider_prefix.get(str(provider_alias).lower())
                        if pref:
                            allowed_prefixes.append(pref)

                    def _allowed_tool(name: str) -> bool:
                        if allowed_tools:
                            return name in allowed_tools
                        if allowed_prefixes:
                            return any(name.startswith(p) for p in allowed_prefixes)
                        # If no filters provided, expose all tools (backward compatible)
                        return True

                    tools = [
                        t
                        for t in tools
                        if isinstance(t, dict) and t.get("name") and _allowed_tool(t["name"])
                    ]

                    # Determine output format for tools list
                    # Supported: openai (default), anthropic (claude), gemini
                    output_format = (
                        context.get_parameter("format")
                        or context.get_parameter("llm_provider")
                        or "openai"
                    )
                    output_format = str(output_format).lower()

                    if output_format in ("anthropic", "claude"):
                        # Convert MCP tools to Anthropic tool schema
                        anthropic_tools = []
                        for tool in tools:
                            if isinstance(tool, dict) and tool.get("name"):
                                anthropic_tools.append(
                                    {
                                        "name": tool["name"],
                                        "description": tool.get("description", ""),
                                        "input_schema": tool.get(
                                            "inputSchema", tool.get("parameters", {})
                                        )
                                        or {"type": "object", "properties": {}},
                                    }
                                )
                        self.log_execution(
                            context, f"🔧 Discovered {len(anthropic_tools)} Anthropic tools"
                        )
                        return anthropic_tools

                    elif output_format in ("gemini", "google"):
                        # Convert MCP tools to Gemini function declarations
                        function_declarations = []
                        for tool in tools:
                            if isinstance(tool, dict) and tool.get("name"):
                                function_declarations.append(
                                    {
                                        "name": tool["name"],
                                        "description": tool.get("description", ""),
                                        "parameters": tool.get(
                                            "inputSchema", tool.get("parameters", {})
                                        )
                                        or {"type": "object", "properties": {}},
                                    }
                                )
                        self.log_execution(
                            context, f"🔧 Discovered {len(function_declarations)} Gemini functions"
                        )
                        return function_declarations

                    else:
                        # Default: Convert MCP tools to OpenAI function calling format
                        openai_functions = []
                        for tool in tools:
                            if isinstance(tool, dict) and "name" in tool:
                                function_def = {
                                    "type": "function",
                                    "function": {
                                        "name": tool["name"],
                                        "description": tool.get("description", ""),
                                        "parameters": tool.get(
                                            "inputSchema", tool.get("parameters", {})
                                        )
                                        or {"type": "object", "properties": {}},
                                    },
                                }
                                openai_functions.append(function_def)

                        self.log_execution(
                            context, f"🔧 Discovered {len(openai_functions)} MCP functions"
                        )
                        return openai_functions
                else:
                    self.log_execution(
                        context,
                        f"🔧 MCP discovery failed: {response.status_code} - {response.text}",
                        "ERROR",
                    )
                    return []

        except Exception as e:
            self.log_execution(context, f"🔧 Error discovering MCP functions: {str(e)}", "ERROR")
            return []

    async def handle_function_execution(
        self, context: NodeExecutionContext, function_name: str, function_args: dict
    ) -> dict:
        """Execute MCP function via API Gateway."""
        try:
            import os

            import httpx

            # Get MCP server URL from parameters or use default API Gateway
            mcp_server_url = context.get_parameter("mcp_server_url")
            if not mcp_server_url:
                # Determine API Gateway URL based on environment
                api_gateway_url = os.getenv("API_GATEWAY_URL")
                if api_gateway_url:
                    mcp_server_url = f"{api_gateway_url.rstrip('/')}/api/v1/mcp"
                elif os.getenv("WORKFLOW_ENGINE_URL", "").startswith("http://workflow-engine"):
                    # We're in Docker, use service name
                    mcp_server_url = "http://api-gateway:8000/api/v1/mcp"
                else:
                    # Local development
                    mcp_server_url = "http://localhost:8000/api/v1/mcp"

            # Get API key from parameters or environment
            api_key = context.get_parameter("api_key") or os.getenv("MCP_API_KEY", "dev_default")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            # Prepare MCP invoke request
            invoke_payload = {"name": function_name, "arguments": function_args}

            self.log_execution(
                context, f"🔧 Executing MCP function: {function_name} with args: {function_args}"
            )

            # Call API Gateway MCP invoke endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{mcp_server_url}/invoke", headers=headers, json=invoke_payload, timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()

                    # Extract result from MCP response format
                    if "result" in result:
                        mcp_result = result["result"]

                        # Handle different result formats
                        if "structuredContent" in mcp_result:
                            return mcp_result["structuredContent"]
                        elif "content" in mcp_result:
                            content = mcp_result["content"]
                            if isinstance(content, list) and content:
                                # Combine text content
                                text_parts = []
                                for item in content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        text_parts.append(item.get("text", ""))
                                return {"result": "\n".join(text_parts)}
                            return {"content": content}
                        else:
                            return mcp_result
                    else:
                        return result

                else:
                    error_msg = (
                        f"MCP function execution failed: {response.status_code} - {response.text}"
                    )
                    self.log_execution(context, f"🔧 {error_msg}", "ERROR")
                    return {"error": error_msg, "status_code": response.status_code}

        except Exception as e:
            error_msg = f"Error executing MCP function '{function_name}': {str(e)}"
            self.log_execution(context, f"🔧 {error_msg}", "ERROR")
            return {"error": error_msg}
