"""OpenAI ChatGPT AI Agent Runner - Dedicated implementation for OpenAI models."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

import httpx

from shared.models import TriggerInfo
from shared.models.node_enums import MemorySubtype, NodeType
from shared.models.workflow import Node

from .base import NodeRunner
from .mcp_tool_discovery import (
    discover_mcp_tools_from_nodes,
    generate_mcp_system_guidance,
    get_tool_invocation_guidance,
)
from .memory import MemoryRunner
from .tool import ToolRunner

logger = logging.getLogger(__name__)


class OpenAIChatGPTRunner(NodeRunner):
    """Dedicated runner for OpenAI ChatGPT AI agent with full parameter support."""

    def __init__(self) -> None:
        self._memory_runner = MemoryRunner()
        self._tool_runner = ToolRunner()
        self._api_key = os.getenv("OPENAI_API_KEY")

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        """Execute ChatGPT AI agent with OpenAI-specific configuration."""
        ctx = inputs.get("_ctx")

        # Extract user_prompt from main input port
        main_input = inputs.get("result", {})
        user_prompt = self._extract_user_prompt(main_input)

        if not user_prompt:
            # Fallback to trigger data
            user_prompt = self._extract_message_from_trigger(trigger)

        if not user_prompt or not user_prompt.strip():
            logger.error("❌ OpenAI ChatGPT Agent requires a non-empty user_prompt")
            raise ValueError("OpenAI ChatGPT Agent requires 'user_prompt' in main input")

        logger.info(f"🤖 OpenAI ChatGPT Agent executing: {node.name}")
        logger.debug(f"👤 User prompt: {user_prompt[:100]}...")

        # Load conversation memory if available
        memory_nodes = self._detect_attached_nodes(node, ctx, NodeType.MEMORY)
        system_prompt = node.configurations.get("system_prompt", "You are a helpful AI assistant.")
        conversation_history = []

        if memory_nodes:
            logger.info(f"🧠 Loading conversation history from {len(memory_nodes)} memory nodes")
            conversation_history = asyncio.run(
                self._load_conversation_history(memory_nodes, ctx, trigger)
            )
            logger.info(f"🧠 Loaded {len(conversation_history)} messages from memory")

        # Discover available MCP tools
        tool_nodes = self._detect_attached_nodes(node, ctx, NodeType.TOOL)
        available_tools = []

        if tool_nodes:
            logger.info(f"🔧 Discovering MCP tools from {len(tool_nodes)} tool nodes")
            available_tools = discover_mcp_tools_from_nodes(tool_nodes)
            logger.info(f"🔧 Discovered {len(available_tools)} MCP functions")

            # Enhance system prompt with MCP tool guidance
            if available_tools:
                mcp_guidance = generate_mcp_system_guidance(available_tools)
                provider_guidance = get_tool_invocation_guidance("openai")
                system_prompt = f"{system_prompt}\n\n{mcp_guidance}\n\n{provider_guidance}".strip()

        # Generate OpenAI ChatGPT response
        try:
            generation_result = self._generate_openai_response(
                node=node,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                available_tools=available_tools,
            )

            ai_response = generation_result["content"]
            logger.info(f"✅ OpenAI response generated: {len(ai_response)} characters")

            # Store conversation in memory
            if memory_nodes and ai_response:
                logger.info(f"💾 Storing conversation in {len(memory_nodes)} memory nodes")
                asyncio.run(
                    self._store_conversation_in_memory(
                        memory_nodes, ctx, trigger, user_prompt, ai_response, node
                    )
                )

            # Build output according to node spec output_params
            output = {
                "content": ai_response,
                "metadata": generation_result.get("metadata", {}),
                "format_type": generation_result.get("format_type", "text"),
                "source_node": node.id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "token_usage": generation_result.get("token_usage", {}),
                "function_calls": generation_result.get("function_calls", []),
            }

            return {"result": output}

        except Exception as e:
            logger.error(f"❌ OpenAI ChatGPT generation failed: {str(e)}")
            raise ValueError(f"OpenAI ChatGPT generation failed: {str(e)}")

    def _generate_openai_response(
        self,
        node: Node,
        user_prompt: str,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        available_tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate response using OpenAI ChatGPT API with full parameter support."""
        configs = node.configurations

        # Extract OpenAI-specific parameters from node spec
        api_key = configs.get("openai_api_key") or self._api_key
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. Set openai_api_key in node configuration or OPENAI_API_KEY environment variable."
            )

        model = configs.get("model", "gpt-5-nano")
        max_tokens = int(configs.get("max_tokens", 8192))
        temperature = float(configs.get("temperature", 0.7))
        top_p = float(configs.get("top_p", 1.0))
        frequency_penalty = float(configs.get("frequency_penalty", 0.0))
        presence_penalty = float(configs.get("presence_penalty", 0.0))
        response_format = configs.get("response_format", "text")

        # Build messages array with conversation history
        messages = []

        # Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add conversation history (if any)
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current user message
        messages.append({"role": "user", "content": user_prompt})

        # Build request body
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        }

        # Handle response format
        if response_format == "json":
            body["response_format"] = {"type": "json_object"}
        elif response_format == "schema":
            # OpenAI structured outputs
            output_schema = configs.get("output_schema")
            if output_schema:
                body["response_format"] = {"type": "json_schema", "json_schema": output_schema}

        # Add tools if available (OpenAI function calling)
        if available_tools:
            body["tools"] = self._format_tools_for_openai(available_tools)
            body["tool_choice"] = "auto"

        # Performance config
        performance_config = configs.get("performance_config", {})
        timeout_seconds = float(performance_config.get("timeout_seconds", 120))

        # API request headers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        logger.debug(f"🔍 OpenAI API request: model={model}, max_tokens={max_tokens}")

        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions", headers=headers, json=body
                )
                resp.raise_for_status()
                data = resp.json()

                # Extract response content and tool calls
                content = ""
                tool_calls = []

                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    message = choice.get("message", {})

                    # Extract text content
                    if "content" in message and message["content"]:
                        content = message["content"]

                    # Extract tool calls
                    if "tool_calls" in message and message["tool_calls"]:
                        for tool_call in message["tool_calls"]:
                            tool_calls.append(
                                {
                                    "id": tool_call.get("id"),
                                    "type": tool_call.get("type"),
                                    "function": {
                                        "name": tool_call.get("function", {}).get("name"),
                                        "arguments": tool_call.get("function", {}).get("arguments"),
                                    },
                                }
                            )

                # Extract usage information
                usage = data.get("usage", {})
                token_usage = {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }

                # Determine format type
                format_type = (
                    response_format if response_format in ["text", "json", "schema"] else "text"
                )

                # Build metadata
                metadata = {
                    "model": model,
                    "finish_reason": data.get("choices", [{}])[0].get("finish_reason"),
                    "system_fingerprint": data.get("system_fingerprint"),
                }

                return {
                    "content": content,
                    "metadata": metadata,
                    "format_type": format_type,
                    "token_usage": token_usage,
                    "function_calls": tool_calls,
                }

        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"❌ OpenAI API error: {e.response.status_code} - {error_text}")
            raise ValueError(f"OpenAI API error: {e.response.status_code} - {error_text}")
        except Exception as e:
            logger.error(f"❌ OpenAI API request failed: {str(e)}")
            raise ValueError(f"OpenAI API request failed: {str(e)}")

    def _format_tools_for_openai(
        self, available_tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format MCP tools into OpenAI's function calling format."""
        openai_tools = []

        for tool in available_tools:
            if "name" in tool:
                # Direct MCP tool definition format
                openai_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", f"Execute {tool['name']}"),
                            "parameters": tool.get(
                                "parameters", {"type": "object", "properties": {}}
                            ),
                        },
                    }
                )

        return openai_tools

    def _extract_user_prompt(self, main_input: Dict[str, Any]) -> str:
        """Extract user_prompt from main input according to node spec."""
        if isinstance(main_input, str):
            return main_input

        # Priority: user_prompt (from spec) > common field names
        if "user_prompt" in main_input and main_input["user_prompt"]:
            return str(main_input["user_prompt"])

        # Fallback to common field names
        for key in ["message", "user_message", "user_input", "input", "query", "text", "content"]:
            if key in main_input and main_input[key]:
                return str(main_input[key])

        return ""

    def _extract_message_from_trigger(self, trigger: TriggerInfo) -> str:
        """Extract user message from trigger data."""
        try:
            if not trigger or not getattr(trigger, "trigger_data", None):
                return ""
            data = trigger.trigger_data or {}

            # Common direct fields
            for key in ["message", "user_message", "user_input", "text", "content"]:
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()

            # Slack event structure
            event = data.get("event")
            if isinstance(event, dict):
                text = event.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()

        except Exception:
            pass
        return ""

    def _detect_attached_nodes(self, node: Node, ctx: Any, node_type: NodeType) -> List[Node]:
        """Detect attached nodes of a specific type."""
        if not node.attached_nodes or not ctx or not hasattr(ctx, "workflow"):
            return []

        attached_nodes = []
        wf_nodes = (
            {n.id: n for n in ctx.workflow.nodes}
            if ctx.workflow and hasattr(ctx.workflow, "nodes")
            else {}
        )

        for attached_id in node.attached_nodes:
            attached = wf_nodes.get(attached_id)
            if attached and attached.type == node_type.value:
                attached_nodes.append(attached)

        return attached_nodes

    async def _load_conversation_history(
        self, memory_nodes: List[Node], ctx: Any, trigger: TriggerInfo
    ) -> List[Dict[str, str]]:
        """Load conversation history from memory nodes in OpenAI message format."""
        conversation_messages = []

        for memory_node in memory_nodes:
            try:
                # Create retrieve operation for memory node
                retrieve_inputs = {"main": {"operation": "retrieve"}, "_ctx": ctx}

                memory_node_copy = Node(
                    id=memory_node.id,
                    name=memory_node.name,
                    description=memory_node.description,
                    type=memory_node.type,
                    subtype=memory_node.subtype,
                    configurations={
                        **memory_node.configurations,
                        "operation": "get_messages",  # Get structured messages
                        "max_messages": 20,
                        "format": "structured",  # Return as list of messages
                    },
                )

                memory_result = self._memory_runner.run(memory_node_copy, retrieve_inputs, trigger)

                if memory_result.get("result", {}).get("success"):
                    messages = memory_result["result"].get("messages", [])
                    if messages:
                        conversation_messages.extend(messages)
                        logger.debug(f"📖 Loaded {len(messages)} messages from {memory_node.id}")

            except Exception as e:
                logger.warning(f"⚠️ Failed to load memory from {memory_node.id}: {str(e)}")

        return conversation_messages

    async def _store_conversation_in_memory(
        self,
        memory_nodes: List[Node],
        ctx: Any,
        trigger: TriggerInfo,
        user_message: str,
        ai_response: str,
        ai_node: Node,
    ) -> None:
        """Store conversation exchange in memory nodes."""
        for memory_node in memory_nodes:
            try:
                # Determine storage strategy based on memory type
                if memory_node.subtype == MemorySubtype.CONVERSATION_BUFFER.value:
                    await self._store_conversation_buffer(
                        memory_node, ctx, trigger, user_message, ai_response, ai_node
                    )
                elif memory_node.subtype == MemorySubtype.VECTOR_DATABASE.value:
                    await self._store_vector_conversation(
                        memory_node, ctx, trigger, user_message, ai_response, ai_node
                    )
                else:
                    await self._store_generic_conversation(
                        memory_node, ctx, trigger, user_message, ai_response, ai_node
                    )

                logger.debug(f"💾 Stored conversation in {memory_node.id}")

            except Exception as e:
                logger.warning(f"⚠️ Failed to store conversation in {memory_node.id}: {str(e)}")

    async def _store_conversation_buffer(
        self,
        memory_node: Node,
        ctx: Any,
        trigger: TriggerInfo,
        user_message: str,
        ai_response: str,
        ai_node: Node,
    ) -> None:
        """Store conversation in conversation buffer memory."""
        # Store user message
        user_inputs = {
            "main": {
                "message": user_message,
                "role": "user",
                "metadata": {
                    "timestamp": trigger.timestamp if trigger else None,
                    "trigger_type": trigger.trigger_type if trigger else "unknown",
                },
            },
            "_ctx": ctx,
        }

        memory_node_copy = Node(
            id=memory_node.id,
            name=memory_node.name,
            description=memory_node.description,
            type=memory_node.type,
            subtype=memory_node.subtype,
            configurations={**memory_node.configurations, "operation": "store"},
        )

        self._memory_runner.run(memory_node_copy, user_inputs, trigger)

        # Store AI response
        ai_inputs = {
            "main": {
                "message": ai_response,
                "role": "assistant",
                "metadata": {
                    "ai_model": ai_node.configurations.get("model", "gpt-5-nano"),
                    "ai_provider": "openai",
                    "timestamp": trigger.timestamp if trigger else None,
                },
            },
            "_ctx": ctx,
        }

        self._memory_runner.run(memory_node_copy, ai_inputs, trigger)

    async def _store_vector_conversation(
        self,
        memory_node: Node,
        ctx: Any,
        trigger: TriggerInfo,
        user_message: str,
        ai_response: str,
        ai_node: Node,
    ) -> None:
        """Store conversation in vector database memory."""
        conversation_content = f"User: {user_message}\nAssistant: {ai_response}"

        vector_inputs = {
            "main": {
                "content": conversation_content,
                "document_type": "conversation",
                "metadata": {
                    "user_message": user_message,
                    "ai_response": ai_response,
                    "ai_model": ai_node.configurations.get("model", "gpt-5-nano"),
                    "ai_provider": "openai",
                    "timestamp": trigger.timestamp if trigger else None,
                },
            },
            "_ctx": ctx,
        }

        memory_node_copy = Node(
            id=memory_node.id,
            name=memory_node.name,
            description=memory_node.description,
            type=memory_node.type,
            subtype=memory_node.subtype,
            configurations={**memory_node.configurations, "operation": "store"},
        )

        self._memory_runner.run(memory_node_copy, vector_inputs, trigger)

    async def _store_generic_conversation(
        self,
        memory_node: Node,
        ctx: Any,
        trigger: TriggerInfo,
        user_message: str,
        ai_response: str,
        ai_node: Node,
    ) -> None:
        """Store conversation in generic memory format."""
        conversation_data = {
            "conversation_exchange": {
                "user_message": user_message,
                "ai_response": ai_response,
                "timestamp": trigger.timestamp if trigger else None,
                "ai_model": ai_node.configurations.get("model", "gpt-5-nano"),
                "ai_provider": "openai",
            }
        }

        generic_inputs = {"main": conversation_data, "_ctx": ctx}

        memory_node_copy = Node(
            id=memory_node.id,
            name=memory_node.name,
            description=memory_node.description,
            type=memory_node.type,
            subtype=memory_node.subtype,
            configurations={**memory_node.configurations, "operation": "store"},
        )

        self._memory_runner.run(memory_node_copy, generic_inputs, trigger)


__all__ = ["OpenAIChatGPTRunner"]
