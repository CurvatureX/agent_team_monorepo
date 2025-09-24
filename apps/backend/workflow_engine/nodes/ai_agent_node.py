"""
AI Agent Node Executor.

Handles OpenAI, Anthropic, and other AI provider integrations.
"""

import asyncio
import socket
from datetime import datetime
from typing import Any, Dict, Optional

from utils.unicode_utils import clean_unicode_string, safe_json_dumps

from shared.models.node_enums import AIAgentSubtype, NodeType

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult
from .factory import NodeExecutorFactory


@NodeExecutorFactory.register(NodeType.AI_AGENT.value)
class AIAgentNodeExecutor(BaseNodeExecutor):
    """Executor for AI agent nodes."""

    def __init__(self, node_type: str = NodeType.AI_AGENT.value, subtype: str = None):
        super().__init__(node_type, subtype)

    async def _make_resilient_request(
        self,
        method: str,
        url: str,
        headers: dict,
        content: str = None,
        context: NodeExecutionContext = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> "httpx.Response":
        """Make HTTP request with retry logic for DNS and connection failures."""
        import httpx

        last_exception = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    if method.upper() == "POST":
                        response = await client.post(
                            url, headers=headers, content=content, timeout=30.0
                        )
                    else:
                        response = await client.get(url, headers=headers, timeout=30.0)
                    return response

            except (socket.gaierror, httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)  # Exponential backoff
                    if context:
                        self.log_execution(
                            context,
                            f"⚠️ AI API request failed (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying in {delay}s...",
                            "WARNING",
                        )
                    await asyncio.sleep(delay)
                else:
                    if context:
                        self.log_execution(
                            context,
                            f"❌ All {max_retries} AI API retry attempts failed. Last error: {str(e)}",
                            "ERROR",
                        )
                    raise e
            except Exception as e:
                # For non-network errors, don't retry
                if context:
                    self.log_execution(context, f"❌ Non-retryable AI API error: {str(e)}", "ERROR")
                raise e

        # This should never be reached, but just in case
        raise last_exception if last_exception else Exception(
            "Unknown error in resilient AI API request"
        )

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute AI agent node with memory integration and MCP function calling."""
        provider = self.subtype or context.get_parameter(
            "provider", AIAgentSubtype.OPENAI_CHATGPT.value
        )
        model = context.get_parameter("model_version", "gpt-4")
        system_prompt = context.get_parameter("system_prompt", "")
        enable_function_calling = context.get_parameter("enable_function_calling", True)

        # Try to get user_message from parameters first, then from input_data with common field names
        user_message = (
            context.get_parameter("user_message")
            or context.input_data.get("message")
            or context.input_data.get("user_message")
            or context.input_data.get("text")
            or ""
        )

        self.log_execution(context, f"Executing AI agent node: {provider}/{model}")

        try:
            # 1. BEFORE AI execution: Load memory from connected memory nodes
            connected_memory_nodes = self._detect_connected_memory_nodes(context)
            enhanced_user_message = user_message

            if connected_memory_nodes:
                self.log_execution(
                    context, f"🧠 Found {len(connected_memory_nodes)} connected memory nodes"
                )
                conversation_history = await self._load_conversation_history_from_memory_nodes(
                    context, connected_memory_nodes
                )
                if conversation_history:
                    # Enhance user message with conversation history
                    enhanced_user_message = (
                        f"{conversation_history}\n\nCurrent message: {user_message}"
                    )
                    self.log_execution(
                        context,
                        f"🧠 Enhanced user message with {len(conversation_history)} chars of memory",
                    )

            # 2. DISCOVER MCP FUNCTIONS: Get available functions from connected TOOL nodes
            available_functions = []
            function_provider_map = {}
            if enable_function_calling:
                connected_tool_nodes = self._detect_connected_tool_nodes(context)
                if connected_tool_nodes:
                    self.log_execution(
                        context, f"🔧 Found {len(connected_tool_nodes)} connected TOOL nodes"
                    )
                    available_functions, function_provider_map = await self._discover_mcp_functions(
                        context, connected_tool_nodes
                    )
                    if available_functions:
                        self.log_execution(
                            context, f"🔧 Discovered {len(available_functions)} MCP functions"
                        )

            # 3. Execute AI with enhanced context and function calling
            if available_functions:
                response_text = await self._real_ai_call_with_functions(
                    provider,
                    model,
                    system_prompt,
                    enhanced_user_message,
                    available_functions,
                    context,
                    connected_tool_nodes,
                    function_provider_map,
                )
            else:
                response_text = await self._real_ai_call(
                    provider, model, system_prompt, enhanced_user_message
                )

            # 4. AFTER AI execution: Store conversation in connected memory nodes
            if connected_memory_nodes and user_message and response_text:
                await self._store_conversation_in_memory_nodes(
                    context, connected_memory_nodes, user_message, response_text
                )

            output_data = {
                "response": response_text,
                "provider": provider,
                "model": model,
                "token_usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
                "finished_reason": "stop",
                "generated_at": datetime.now().isoformat(),
            }

            return NodeExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output_data=output_data,
                metadata={"node_type": "ai_agent", "provider": provider, "model": model},
            )

        except Exception as e:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"AI agent execution failed: {str(e)}",
                error_details={"provider": provider, "model": model},
            )

    async def _real_ai_call(
        self, provider: str, model: str, system_prompt: str, user_message: str
    ) -> str:
        """Real AI API call implementation."""
        import os

        import httpx

        try:
            if provider in [AIAgentSubtype.OPENAI_CHATGPT.value]:
                return await self._call_openai(model, system_prompt, user_message)
            elif provider in [AIAgentSubtype.ANTHROPIC_CLAUDE.value]:
                return await self._call_anthropic(model, system_prompt, user_message)
            elif provider in [AIAgentSubtype.GOOGLE_GEMINI.value]:
                return await self._call_google_gemini(model, system_prompt, user_message)
            else:
                # Return error for unsupported AI providers
                supported_providers = [e.value for e in AIAgentSubtype]
                raise ValueError(
                    f"Unsupported AI provider: {provider}. Supported providers: {supported_providers}"
                )

        except Exception as e:
            # Re-raise the exception instead of returning mock response
            raise Exception(f"AI provider {provider} call failed: {str(e)}")

    async def _call_openai_with_functions(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        available_functions: list,
        context: NodeExecutionContext,
        tool_nodes: list,
        function_provider_map: dict,
    ) -> str:
        """Call OpenAI API with function calling support."""
        import json
        import os

        import httpx

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Please set OPENAI_API_KEY environment variable."
            )

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # Map model names
        if model in ["gpt-4.1-mini", "gpt-4-mini"]:
            model = "gpt-4o-mini"
        elif model in ["gpt-4", "gpt-4.0"]:
            model = "gpt-4o"

        # Clean and validate input strings
        system_prompt_clean = clean_unicode_string(system_prompt)
        user_message_clean = clean_unicode_string(user_message)

        # Build conversation with function calling support
        messages = [
            {"role": "system", "content": system_prompt_clean},
            {"role": "user", "content": user_message_clean},
        ]

        max_function_calls = context.get_parameter("max_function_calls", 5)
        function_call_count = 0

        while function_call_count < max_function_calls:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000,
            }

            # Add tools only if functions are available
            if available_functions:
                payload["tools"] = available_functions
                payload["tool_choice"] = "auto"

            # Serialize JSON with proper Unicode handling
            try:
                json_data = safe_json_dumps(payload, separators=(",", ":"))
            except (UnicodeEncodeError, TypeError, ValueError) as e:
                self.log_execution(context, f"JSON encoding error in OpenAI payload: {e}", "ERROR")
                return f"[OpenAI Encoding Error] Could not encode message properly."

            response = await self._make_resilient_request(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers,
                json_data,
                context=context,
            )

            result = response.json()

            if response.status_code != 200:
                error = result.get("error", {}).get("message", "Unknown error")
                return f"[OpenAI Error] {error}"

            message = result["choices"][0]["message"]
            messages.append(message)

            # Check if AI wants to call functions
            if message.get("tool_calls"):
                function_call_count += 1
                self.log_execution(
                    context, f"🔧 OpenAI requesting {len(message['tool_calls'])} function calls"
                )

                # Execute each function call
                for tool_call in message["tool_calls"]:
                    function_name = tool_call["function"]["name"]
                    try:
                        function_args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        function_args = {}

                    # Execute function via connected TOOL node
                    function_result = await self._execute_function_call(
                        context, function_name, function_args, tool_nodes, function_provider_map
                    )

                    # Add function result to conversation
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": function_name,
                            "content": json.dumps(function_result),
                        }
                    )

                # Continue conversation with function results
                continue
            else:
                # No more function calls, return the response
                return message.get("content", "")

        # If we hit the max function calls, return the last response
        return messages[-1].get("content", "Maximum function calls reached")

    async def _call_openai(self, model: str, system_prompt: str, user_message: str) -> str:
        """Call OpenAI API."""
        import json
        import os

        import httpx

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Please set OPENAI_API_KEY environment variable."
            )

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # Map model names
        if model in ["gpt-4.1-mini", "gpt-4-mini"]:
            model = "gpt-4o-mini"
        elif model in ["gpt-4", "gpt-4.0"]:
            model = "gpt-4o"

        # Clean and validate input strings to prevent Unicode issues
        system_prompt_clean = clean_unicode_string(system_prompt)
        user_message_clean = clean_unicode_string(user_message)

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt_clean},
                {"role": "user", "content": user_message_clean},
            ],
            "temperature": 0.7,
            "max_tokens": 500,
        }

        # Serialize JSON with proper Unicode handling to avoid surrogate issues
        try:
            json_data = safe_json_dumps(payload, separators=(",", ":"))
        except (UnicodeEncodeError, TypeError, ValueError) as e:
            self.log_execution(None, f"JSON encoding error in OpenAI payload: {e}", "ERROR")
            # Clean the payload more aggressively and try again
            try:
                cleaned_payload = {
                    "model": payload["model"],
                    "messages": [
                        {
                            "role": "system",
                            "content": clean_unicode_string(payload["messages"][0]["content"]),
                        },
                        {
                            "role": "user",
                            "content": clean_unicode_string(payload["messages"][1]["content"]),
                        },
                    ],
                    "temperature": payload["temperature"],
                    "max_tokens": payload["max_tokens"],
                }
                json_data = safe_json_dumps(cleaned_payload, separators=(",", ":"))
                self.log_execution(
                    None, f"Successfully cleaned and re-encoded OpenAI payload", "INFO"
                )
            except Exception as fallback_error:
                self.log_execution(
                    None, f"Failed to clean OpenAI payload: {fallback_error}", "ERROR"
                )
                return f"[OpenAI Encoding Error] Could not encode message properly. Fallback: Processing message with cleaned content."

        response = await self._make_resilient_request(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers,
            json_data,
            context=None,  # We don't have context in this method, but it's optional
        )

        result = response.json()

        if response.status_code == 200:
            return result["choices"][0]["message"]["content"]
        else:
            error = result.get("error", {}).get("message", "Unknown error")
            return f"[OpenAI Error] {error} | Fallback: Processing '{user_message}'"

    async def _call_anthropic_with_functions(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        available_functions: list,
        context: NodeExecutionContext,
        tool_nodes: list,
        function_provider_map: dict,
    ) -> str:
        """Call Anthropic Claude API with function calling support."""
        import json
        import os

        import httpx

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Anthropic API key not found. Please set ANTHROPIC_API_KEY environment variable."
            )

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        # Map model names
        if model in ["claude-3", "claude"]:
            model = "claude-3-sonnet-20240229"

        # Clean and validate input strings
        system_prompt_clean = clean_unicode_string(system_prompt)
        user_message_clean = clean_unicode_string(user_message)

        # Build conversation with function calling support
        messages = [{"role": "user", "content": user_message_clean}]

        max_function_calls = context.get_parameter("max_function_calls", 5)
        function_call_count = 0

        while function_call_count < max_function_calls:
            payload = {
                "model": model,
                "max_tokens": 1000,
                "system": system_prompt_clean,
                "messages": messages,
            }

            # Add tools only if functions are available (convert OpenAI format to Anthropic format)
            if available_functions:
                anthropic_tools = []
                for func in available_functions:
                    # Convert OpenAI function format to Anthropic tool format
                    if func.get("type") == "function" and "function" in func:
                        tool_def = {
                            "name": func["function"]["name"],
                            "description": func["function"]["description"],
                            "input_schema": func["function"]["parameters"],
                        }
                        anthropic_tools.append(tool_def)

                if anthropic_tools:
                    payload["tools"] = anthropic_tools

            # Serialize JSON with proper Unicode handling
            try:
                json_data = safe_json_dumps(payload, separators=(",", ":"))
            except (UnicodeEncodeError, TypeError, ValueError) as e:
                self.log_execution(
                    context, f"JSON encoding error in Anthropic payload: {e}", "ERROR"
                )
                return f"[Anthropic Encoding Error] Could not encode message properly."

            response = await self._make_resilient_request(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers,
                json_data,
                context=context,
            )

            result = response.json()

            if response.status_code != 200:
                error = result.get("error", {}).get("message", "Unknown error")
                return f"[Anthropic Error] {error}"

            # Check if Claude wants to call functions
            content = result.get("content", [])
            text_content = ""
            has_tool_calls = False

            for content_block in content:
                if content_block.get("type") == "text":
                    text_content += content_block.get("text", "")
                elif content_block.get("type") == "tool_use":
                    has_tool_calls = True
                    function_call_count += 1

                    tool_name = content_block.get("name")
                    tool_input = content_block.get("input", {})
                    tool_use_id = content_block.get("id")

                    self.log_execution(context, f"🔧 Claude requesting function call: {tool_name}")

                    # Execute function via connected TOOL node
                    function_result = await self._execute_function_call(
                        context, tool_name, tool_input, tool_nodes, function_provider_map
                    )

                    # Add Claude's message with tool use
                    messages.append({"role": "assistant", "content": [content_block]})

                    # Add function result as tool result
                    messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": json.dumps(function_result),
                                }
                            ],
                        }
                    )

            if has_tool_calls:
                # Continue conversation with function results
                continue
            else:
                # No more function calls, return the text response
                return text_content

        # If we hit the max function calls, return the last text content
        return text_content or "Maximum function calls reached"

    async def _call_anthropic(self, model: str, system_prompt: str, user_message: str) -> str:
        """Call Anthropic Claude API."""
        import json
        import os

        import httpx

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Anthropic API key not found. Please set ANTHROPIC_API_KEY environment variable."
            )

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        # Map model names
        if model in ["claude-3", "claude"]:
            model = "claude-3-sonnet-20240229"

        # Clean and validate input strings to prevent Unicode issues
        system_prompt_clean = clean_unicode_string(system_prompt)
        user_message_clean = clean_unicode_string(user_message)

        payload = {
            "model": model,
            "max_tokens": 500,
            "system": system_prompt_clean,
            "messages": [{"role": "user", "content": user_message_clean}],
        }

        # Serialize JSON with proper Unicode handling to avoid surrogate issues
        try:
            json_data = safe_json_dumps(payload, separators=(",", ":"))
        except (UnicodeEncodeError, TypeError, ValueError) as e:
            self.log_execution(None, f"JSON encoding error in Anthropic payload: {e}", "ERROR")
            # Clean the payload more aggressively and try again
            try:
                cleaned_payload = {
                    "model": payload["model"],
                    "max_tokens": payload["max_tokens"],
                    "system": clean_unicode_string(payload["system"]),
                    "messages": [
                        {
                            "role": "user",
                            "content": clean_unicode_string(payload["messages"][0]["content"]),
                        }
                    ],
                }
                json_data = safe_json_dumps(cleaned_payload, separators=(",", ":"))
                self.log_execution(
                    None, f"Successfully cleaned and re-encoded Anthropic payload", "INFO"
                )
            except Exception as fallback_error:
                self.log_execution(
                    None, f"Failed to clean Anthropic payload: {fallback_error}", "ERROR"
                )
                return f"[Anthropic Encoding Error] Could not encode message properly. Fallback: Processing message with cleaned content."

        response = await self._make_resilient_request(
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers,
            json_data,
            context=None,  # We don't have context in this method, but it's optional
        )

        result = response.json()

        if response.status_code == 200:
            return result["content"][0]["text"]
        else:
            error = result.get("error", {}).get("message", "Unknown error")
            return f"[Anthropic Error] {error} | Fallback: Processing '{user_message}'"

    def validate_parameters(self, context: NodeExecutionContext) -> tuple[bool, str]:
        """Validate AI agent node parameters. Returns (is_valid, error_message)."""
        missing_params = []

        # Check system_prompt (required from parameters)
        if not context.get_parameter("system_prompt"):
            missing_params.append("system_prompt")

        # Check user_message (can come from parameters or input_data)
        user_message = (
            context.get_parameter("user_message")
            or context.input_data.get("message")
            or context.input_data.get("user_message")
            or context.input_data.get("text")
        )
        if not user_message:
            missing_params.append("user_message (or message/text in input_data)")

        if missing_params:
            if len(missing_params) == 1:
                error_msg = f"Missing required parameter: {missing_params[0]}"
            else:
                error_msg = f"Missing required parameters: {', '.join(missing_params)}"

            # Log detailed parameter and input_data information
            all_params = list(context.parameters.keys()) if context.parameters else []
            all_input_keys = list(context.input_data.keys()) if context.input_data else []
            error_msg += (
                f" (Available parameters: {', '.join(all_params) if all_params else 'none'}, "
            )
            error_msg += f"Available input_data keys: {', '.join(all_input_keys) if all_input_keys else 'none'})"

            self.log_execution(context, error_msg, "ERROR")
            return False, error_msg

        return True, ""

    def _detect_connected_memory_nodes(self, context: NodeExecutionContext) -> list:
        """Detect memory nodes connected to this AI agent via memory connections."""
        connected_memory_nodes = []

        try:
            # Get workflow metadata containing connections and nodes
            if not hasattr(context, "metadata") or not context.metadata:
                self.log_execution(context, "🧠 No metadata available for memory node detection")
                return []

            workflow_connections = context.metadata.get("workflow_connections", {})
            workflow_nodes = context.metadata.get("workflow_nodes", [])
            current_node_id = context.metadata.get("node_id")

            if not current_node_id or not workflow_connections or not workflow_nodes:
                self.log_execution(
                    context,
                    f"🧠 Missing required data - node_id: {current_node_id}, connections: {bool(workflow_connections)}, nodes: {len(workflow_nodes)}",
                )
                return []

            # Find outgoing memory connections from this AI agent node
            if current_node_id in workflow_connections:
                node_connections = workflow_connections[current_node_id]
                connection_types = node_connections.get("connection_types", {})

                # Look specifically for memory connections
                memory_connections = connection_types.get("memory", {})
                if memory_connections and "connections" in memory_connections:
                    for connection in memory_connections["connections"]:
                        target_node_id = connection.get("node")
                        if target_node_id:
                            # Find the target node definition
                            for node in workflow_nodes:
                                if (
                                    node.get("id") == target_node_id
                                    and node.get("type") == "MEMORY"
                                ):
                                    connected_memory_nodes.append(
                                        {
                                            "node_id": target_node_id,
                                            "node": node,
                                            "connection": connection,
                                        }
                                    )
                                    self.log_execution(
                                        context,
                                        f"🧠 Found connected memory node: {target_node_id} ({node.get('name', 'unnamed')})",
                                    )

            return connected_memory_nodes

        except Exception as e:
            self.log_execution(context, f"🧠 Error detecting memory nodes: {str(e)}", "ERROR")
            return []

    async def _load_conversation_history_from_memory_nodes(
        self, context: NodeExecutionContext, memory_nodes: list
    ) -> str:
        """Load conversation history from connected memory nodes."""
        conversation_history = ""

        try:
            from .memory_node import MemoryNodeExecutor

            for memory_info in memory_nodes:
                memory_node = memory_info["node"]
                memory_node_id = memory_info["node_id"]

                # Create execution context for memory node (retrieve operation)
                memory_context = NodeExecutionContext(
                    workflow_id=context.workflow_id,
                    execution_id=context.execution_id,
                    node_id=memory_node_id,
                    parameters={
                        **memory_node.get("parameters", {}),
                        "operation": "retrieve",  # Set operation to retrieve
                    },
                    input_data=context.input_data.copy(),
                    metadata=context.metadata,
                )

                # Execute memory node to retrieve conversation history
                memory_executor = MemoryNodeExecutor()
                memory_result = await memory_executor.execute(memory_context)

                if memory_result.status == ExecutionStatus.SUCCESS and memory_result.output_data:
                    history_data = memory_result.output_data.get("conversation_history", "")
                    if history_data:
                        conversation_history += (
                            f"\n--- Memory from {memory_node.get('name', memory_node_id)} ---\n"
                        )
                        conversation_history += str(history_data)
                        self.log_execution(
                            context,
                            f"🧠 Loaded {len(str(history_data))} chars from memory node {memory_node_id}",
                        )

        except Exception as e:
            self.log_execution(context, f"🧠 Error loading conversation history: {str(e)}", "ERROR")

        return conversation_history.strip()

    async def _store_conversation_in_memory_nodes(
        self, context: NodeExecutionContext, memory_nodes: list, user_message: str, ai_response: str
    ):
        """Store conversation exchange in connected memory nodes."""
        try:
            from .memory_node import MemoryNodeExecutor

            for memory_info in memory_nodes:
                memory_node = memory_info["node"]
                memory_node_id = memory_info["node_id"]

                # Create conversation exchange data
                conversation_data = {
                    "user_message": user_message,
                    "ai_response": ai_response,
                    "timestamp": datetime.now().isoformat(),
                    "ai_provider": self.subtype,
                }

                # Create execution context for memory node (store operation)
                memory_context = NodeExecutionContext(
                    workflow_id=context.workflow_id,
                    execution_id=context.execution_id,
                    node_id=memory_node_id,
                    parameters={
                        **memory_node.get("parameters", {}),
                        "operation": "store",  # Set operation to store
                        "conversation_data": conversation_data,
                    },
                    input_data=conversation_data,
                    metadata=context.metadata,
                )

                # Execute memory node to store conversation
                memory_executor = MemoryNodeExecutor()
                memory_result = await memory_executor.execute(memory_context)

                if memory_result.status == ExecutionStatus.SUCCESS:
                    self.log_execution(
                        context, f"🧠 Stored conversation in memory node {memory_node_id}"
                    )
                else:
                    self.log_execution(
                        context,
                        f"🧠 Failed to store in memory node {memory_node_id}: {memory_result.error_message}",
                        "ERROR",
                    )

        except Exception as e:
            self.log_execution(
                context, f"🧠 Error storing conversation in memory: {str(e)}", "ERROR"
            )

    def _detect_connected_tool_nodes(self, context: NodeExecutionContext) -> list:
        """Detect TOOL nodes connected via MCP_TOOLS connections."""
        connected_tool_nodes = []

        try:
            # Get workflow metadata containing connections and nodes
            if not hasattr(context, "metadata") or not context.metadata:
                self.log_execution(context, "🔧 No metadata available for TOOL node detection")
                return []

            workflow_connections = context.metadata.get("workflow_connections", {})
            workflow_nodes = context.metadata.get("workflow_nodes", [])
            current_node_id = context.metadata.get("node_id")

            if not current_node_id or not workflow_connections or not workflow_nodes:
                self.log_execution(
                    context,
                    f"🔧 Missing required data - node_id: {current_node_id}, connections: {bool(workflow_connections)}, nodes: {len(workflow_nodes)}",
                )
                return []

            # Find outgoing MCP_TOOLS connections from this AI agent node
            if current_node_id in workflow_connections:
                node_connections = workflow_connections[current_node_id]
                connection_types = node_connections.get("connection_types", {})

                # Look specifically for MCP_TOOLS connections
                mcp_connections = connection_types.get("mcp_tools", {})
                if mcp_connections and "connections" in mcp_connections:
                    for connection in mcp_connections["connections"]:
                        target_node_id = connection.get("node")
                        if target_node_id:
                            # Find the target node definition
                            for node in workflow_nodes:
                                if node.get("id") == target_node_id and node.get("type") == "TOOL":
                                    connected_tool_nodes.append(
                                        {
                                            "node_id": target_node_id,
                                            "node": node,
                                            "connection": connection,
                                        }
                                    )
                                    self.log_execution(
                                        context,
                                        f"🔧 Found connected TOOL node: {target_node_id} ({node.get('name', 'unnamed')})",
                                    )

            return connected_tool_nodes

        except Exception as e:
            self.log_execution(context, f"🔧 Error detecting TOOL nodes: {str(e)}", "ERROR")
            return []

    async def _discover_mcp_functions(
        self, context: NodeExecutionContext, tool_nodes: list
    ) -> tuple[list, dict]:
        """Discover available MCP functions from connected TOOL nodes.

        Returns a tuple of (available_functions, function_provider_map) where
        function_provider_map maps function name -> tool node_id that provides it.
        """
        available_functions = []
        function_provider_map: dict[str, str] = {}

        try:
            from .tool_node import ToolNodeExecutor

            for tool_info in tool_nodes:
                tool_node = tool_info["node"]
                tool_node_id = tool_info["node_id"]

                # Create execution context for TOOL node (discovery operation)
                tool_context = NodeExecutionContext(
                    workflow_id=context.workflow_id,
                    execution_id=context.execution_id,
                    node_id=tool_node_id,
                    parameters={
                        **tool_node.get("parameters", {}),
                        "operation": "discover",  # Set operation to discover
                    },
                    input_data={"operation": "discover"},
                    metadata=context.metadata,
                )

                # Execute TOOL node to discover available functions
                tool_executor = ToolNodeExecutor()
                tool_result = await tool_executor.handle_function_discovery(tool_context)

                if tool_result and isinstance(tool_result, list):
                    # Record which tool node provided which functions
                    for entry in tool_result:
                        func_name = None
                        if isinstance(entry, dict):
                            if entry.get("type") == "function" and "function" in entry:
                                func_name = entry["function"].get("name")
                            elif "name" in entry:
                                func_name = entry.get("name")
                        if func_name:
                            function_provider_map.setdefault(func_name, tool_node_id)
                            available_functions.append(entry)
                    self.log_execution(
                        context,
                        f"🔧 Discovered {len(tool_result)} functions from TOOL node {tool_node_id}",
                    )

        except Exception as e:
            self.log_execution(context, f"🔧 Error discovering MCP functions: {str(e)}", "ERROR")

        return available_functions, function_provider_map

    async def _real_ai_call_with_functions(
        self,
        provider: str,
        model: str,
        system_prompt: str,
        user_message: str,
        available_functions: list,
        context: NodeExecutionContext,
        tool_nodes: list,
        function_provider_map: dict,
    ) -> str:
        """AI call with function calling support."""
        try:
            if provider in [AIAgentSubtype.OPENAI_CHATGPT.value]:
                return await self._call_openai_with_functions(
                    model,
                    system_prompt,
                    user_message,
                    available_functions,
                    context,
                    tool_nodes,
                    function_provider_map,
                )
            elif provider in [AIAgentSubtype.ANTHROPIC_CLAUDE.value]:
                return await self._call_anthropic_with_functions(
                    model,
                    system_prompt,
                    user_message,
                    available_functions,
                    context,
                    tool_nodes,
                    function_provider_map,
                )
            elif provider in [AIAgentSubtype.GOOGLE_GEMINI.value]:
                return await self._call_google_gemini_with_functions(
                    model,
                    system_prompt,
                    user_message,
                    available_functions,
                    context,
                    tool_nodes,
                    function_provider_map,
                )
            else:
                # Fallback to regular AI call without functions
                return await self._real_ai_call(provider, model, system_prompt, user_message)

        except Exception as e:
            self.log_execution(
                context,
                f"🔧 Function calling failed, falling back to regular AI call: {str(e)}",
                "WARNING",
            )
            # Fallback to regular AI call
            return await self._real_ai_call(provider, model, system_prompt, user_message)

    async def _execute_function_call(
        self,
        context: NodeExecutionContext,
        function_name: str,
        function_args: dict,
        tool_nodes: list,
        function_provider_map: dict | None = None,
    ) -> dict:
        """Execute function call via appropriate connected TOOL node."""
        try:
            from .tool_node import ToolNodeExecutor

            # Find the TOOL node that provides this function
            if not tool_nodes:
                raise ValueError("No TOOL nodes available for function execution")
            # If mapping present, route to the provider that exposed this function
            tool_info = None
            if function_provider_map and function_name in function_provider_map:
                node_id = function_provider_map.get(function_name)
                for info in tool_nodes:
                    if info.get("node_id") == node_id:
                        tool_info = info
                        break
            if tool_info is None:
                # Fallback to the first tool node
                tool_info = tool_nodes[0]
            tool_node = tool_info["node"]
            tool_node_id = tool_info["node_id"]

            # Create execution context for TOOL node (execute operation)
            tool_context = NodeExecutionContext(
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                node_id=tool_node_id,
                parameters={
                    **tool_node.get("parameters", {}),
                    "operation": "execute",
                },
                input_data={
                    "operation": "execute",
                    "function_name": function_name,
                    "function_args": function_args,
                },
                metadata=context.metadata,
            )

            # Execute TOOL node to run the function
            tool_executor = ToolNodeExecutor()
            tool_result = await tool_executor.handle_function_execution(
                tool_context, function_name, function_args
            )

            self.log_execution(
                context, f"🔧 Executed function '{function_name}' via TOOL node {tool_node_id}"
            )

            return tool_result if tool_result else {}

        except Exception as e:
            self.log_execution(
                context, f"🔧 Error executing function '{function_name}': {str(e)}", "ERROR"
            )
            return {"error": str(e)}

    async def _call_google_gemini_with_functions(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        available_functions: list,
        context: NodeExecutionContext,
        tool_nodes: list,
        function_provider_map: dict,
    ) -> str:
        """Call Google Gemini API with function calling support."""
        import json
        import os

        import httpx

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "Google API key not found. Set GOOGLE_API_KEY environment variable. "
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )

        # Map model names for Gemini
        if model in ["gemini-1.5-pro", "gemini-pro"]:
            model = "gemini-1.5-pro-latest"
        elif model in ["gemini-1.5-flash", "gemini-flash"]:
            model = "gemini-1.5-flash-latest"

        # For now, Google Gemini function calling implementation is a placeholder
        # The actual implementation would require proper Gemini API integration
        self.log_execution(
            context,
            "🔧 Google Gemini function calling not fully implemented, falling back to regular call",
            "WARNING",
        )

        # Fallback to regular Gemini call (which currently returns an error)
        return await self._call_google_gemini(model, system_prompt, user_message)

    async def _call_google_gemini(self, model: str, system_prompt: str, user_message: str) -> str:
        """Call Google Gemini API."""
        import os

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "Google API key not found. Set GOOGLE_API_KEY environment variable. "
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )

        # For now, return a clear error that Google Gemini integration needs to be implemented
        raise ValueError(
            "Google Gemini integration not yet implemented. "
            "Please use OPENAI_CHATGPT or ANTHROPIC_CLAUDE providers instead."
        )
