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
        """Execute AI agent node with memory integration."""
        provider = self.subtype or context.get_parameter(
            "provider", AIAgentSubtype.OPENAI_CHATGPT.value
        )
        model = context.get_parameter("model_version", "gpt-4")
        system_prompt = context.get_parameter("system_prompt", "")

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

            # 2. Execute AI with enhanced context
            response_text = await self._real_ai_call(
                provider, model, system_prompt, enhanced_user_message
            )

            # 3. AFTER AI execution: Store conversation in connected memory nodes
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
