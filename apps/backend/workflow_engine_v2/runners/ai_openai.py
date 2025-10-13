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
                tool_nodes=tool_nodes,
                trigger=trigger,
                ctx=ctx,
            )

            ai_response = generation_result["content"]
            # Handle both string and dict responses for logging
            if isinstance(ai_response, str):
                logger.info(f"✅ OpenAI response generated: {len(ai_response)} characters")
            else:
                logger.info(
                    f"✅ OpenAI response generated: {type(ai_response).__name__} with {len(str(ai_response))} chars"
                )

            # Store conversation in memory
            if memory_nodes and ai_response:
                logger.info(f"💾 Storing conversation in {len(memory_nodes)} memory nodes")
                try:
                    asyncio.run(
                        self._store_conversation_in_memory(
                            memory_nodes, ctx, trigger, user_prompt, ai_response, node
                        )
                    )
                    logger.info(f"✅ Successfully stored conversation in memory")
                except Exception as mem_err:
                    logger.error(f"❌ Failed to store conversation in memory: {str(mem_err)}")
                    logger.error(f"❌ Memory error type: {type(mem_err).__name__}")
                    import traceback

                    logger.error(f"❌ Traceback: {traceback.format_exc()}")
                    # Don't fail the node just because memory storage failed
                    # The AI response was generated successfully
                    logger.warning("⚠️ Continuing execution despite memory storage failure")

            # Build output according to node spec output_params
            output = {
                "content": ai_response,
                "metadata": generation_result.get("metadata", {}),
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
        tool_nodes: List[Node],
        trigger: TriggerInfo,
        ctx: Any,
    ) -> Dict[str, Any]:
        """Generate response using OpenAI ChatGPT API with full parameter support and iterative tool calling."""
        configs = node.configurations

        # Extract OpenAI-specific parameters from node spec
        api_key = configs.get("openai_api_key") or self._api_key
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. Set openai_api_key in node configuration or OPENAI_API_KEY environment variable."
            )

        model = configs.get("model", "gpt-5-nano")
        max_tokens_config = configs.get("max_tokens")
        max_completion_config = configs.get("max_completion_tokens")
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

        # Iterative tool calling configuration
        max_iterations = int(configs.get("max_tool_iterations", 5))  # Prevent infinite loops
        all_tool_calls = []  # Track all tool calls made across iterations

        # Build request body
        def _model_requires_completion_tokens(model_name: str) -> bool:
            normalized = (model_name or "").lower()
            return normalized.startswith(("gpt-5", "gpt-4.1", "gpt-4o"))

        if _model_requires_completion_tokens(model):
            if temperature != 1.0:
                logger.warning(
                    "⚠️ OpenAI model %s only supports default temperature=1.0; overriding %.3f",
                    model,
                    temperature,
                )
                temperature = 1.0
            if top_p != 1.0:
                logger.warning(
                    "⚠️ OpenAI model %s only supports default top_p=1.0; overriding %.3f",
                    model,
                    top_p,
                )
                top_p = 1.0
            if frequency_penalty != 0.0:
                logger.warning(
                    "⚠️ OpenAI model %s only supports default frequency_penalty=0.0; overriding %.3f",
                    model,
                    frequency_penalty,
                )
                frequency_penalty = 0.0
            if presence_penalty != 0.0:
                logger.warning(
                    "⚠️ OpenAI model %s only supports default presence_penalty=0.0; overriding %.3f",
                    model,
                    presence_penalty,
                )
                presence_penalty = 0.0

        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        }

        if _model_requires_completion_tokens(model):
            max_completion_tokens = (
                int(max_completion_config)
                if max_completion_config is not None
                else int(max_tokens_config)
                if max_tokens_config is not None
                else 8192
            )
            body["max_completion_tokens"] = max_completion_tokens
            effective_max_tokens = max_completion_tokens
            max_param_used = "max_completion_tokens"
        else:
            max_tokens = (
                int(max_tokens_config)
                if max_tokens_config is not None
                else int(max_completion_config)
                if max_completion_config is not None
                else 8192
            )
            body["max_tokens"] = max_tokens
            effective_max_tokens = max_tokens
            max_param_used = "max_tokens"

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

        logger.debug(
            f"🔍 OpenAI API request: model={model}, {max_param_used}={effective_max_tokens}"
        )

        # Iterative tool calling loop
        iteration = 0
        final_content = ""
        cumulative_token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                while iteration < max_iterations:
                    iteration += 1
                    logger.info(f"🔄 OpenAI API call iteration {iteration}/{max_iterations}")

                    # Make API request
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
                                            "arguments": tool_call.get("function", {}).get(
                                                "arguments"
                                            ),
                                        },
                                    }
                                )

                    # Accumulate token usage
                    usage = data.get("usage", {})
                    cumulative_token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    cumulative_token_usage["completion_tokens"] += usage.get("completion_tokens", 0)
                    cumulative_token_usage["total_tokens"] += usage.get("total_tokens", 0)

                    # Check if we have tool calls to execute
                    if tool_calls:
                        logger.info(f"🔧 OpenAI requested {len(tool_calls)} tool call(s)")

                        # Add assistant's message with tool calls to conversation
                        assistant_message = {"role": "assistant", "content": content or None}
                        assistant_message["tool_calls"] = [
                            {
                                "id": tc["id"],
                                "type": tc["type"],
                                "function": {
                                    "name": tc["function"]["name"],
                                    "arguments": tc["function"]["arguments"],
                                },
                            }
                            for tc in tool_calls
                        ]
                        messages.append(assistant_message)

                        # Execute each tool and add results to conversation
                        for tool_call in tool_calls:
                            tool_name = tool_call["function"]["name"]
                            tool_args_str = tool_call["function"]["arguments"]
                            tool_id = tool_call["id"]

                            try:
                                # Parse tool arguments
                                tool_args = (
                                    json.loads(tool_args_str)
                                    if isinstance(tool_args_str, str)
                                    else tool_args_str
                                )
                                logger.info(f"🔧 Executing tool: {tool_name}")

                                # Execute tool using internal MCP tool execution
                                tool_result = self._execute_mcp_tool(
                                    tool_name=tool_name,
                                    tool_input=tool_args,
                                    tool_nodes=tool_nodes,
                                    trigger=trigger,
                                    ctx=ctx,
                                )

                                # Track tool call
                                all_tool_calls.append(
                                    {
                                        "id": tool_id,
                                        "name": tool_name,
                                        "arguments": tool_args,
                                        "result": tool_result,
                                    }
                                )

                                # Format tool result for OpenAI - extract the actual result content
                                result_content = tool_result.get("result", {})

                                # Format as JSON if it's a dict/list, otherwise as string
                                if isinstance(result_content, (dict, list)):
                                    try:
                                        result_str = json.dumps(
                                            result_content, ensure_ascii=False, indent=2
                                        )
                                    except:
                                        result_str = str(result_content)
                                else:
                                    result_str = (
                                        str(result_content)
                                        if result_content
                                        else "Tool executed successfully"
                                    )

                                # Add tool result to messages
                                messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": tool_id,
                                        "content": result_str,
                                    }
                                )

                                logger.info(f"✅ Tool {tool_name} executed successfully")

                            except Exception as e:
                                logger.error(f"❌ Tool {tool_name} execution failed: {str(e)}")
                                # Add error result to conversation
                                messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": tool_id,
                                        "content": json.dumps({"error": str(e), "success": False}),
                                    }
                                )

                        # Update body with new messages for next iteration
                        body["messages"] = messages
                        continue  # Continue to next iteration to get final response

                    else:
                        # No more tool calls - we have the final response
                        final_content = content
                        logger.info(f"✅ Final response received after {iteration} iteration(s)")

                        # Parse JSON if applicable
                        parsed_content = final_content
                        if isinstance(final_content, str) and final_content.strip():
                            try:
                                parsed_content = json.loads(final_content)
                                logger.debug(f"✅ Parsed JSON response: {type(parsed_content)}")
                            except json.JSONDecodeError:
                                # Not JSON, keep as string
                                parsed_content = final_content

                        # Build metadata
                        metadata = {
                            "model": model,
                            "finish_reason": data.get("choices", [{}])[0].get("finish_reason"),
                            "system_fingerprint": data.get("system_fingerprint"),
                            "iterations": iteration,
                        }

                        return {
                            "content": parsed_content,
                            "metadata": metadata,
                            "token_usage": cumulative_token_usage,
                            "function_calls": all_tool_calls,
                        }

                # If we exit loop without returning, we hit max iterations
                logger.warning(
                    f"⚠️ Reached max iterations ({max_iterations}) without final response"
                )
                return {
                    "content": final_content or "Max iterations reached without final response",
                    "metadata": {
                        "model": model,
                        "finish_reason": "max_iterations",
                        "iterations": iteration,
                    },
                    "token_usage": cumulative_token_usage,
                    "function_calls": all_tool_calls,
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

    def _execute_mcp_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_nodes: List[Node],
        trigger: TriggerInfo,
        ctx: Any,
    ) -> Dict[str, Any]:
        """Execute an MCP tool call through the appropriate tool node."""
        # Find the tool node that provides this tool (use first available tool node)
        for tool_node in tool_nodes:
            # Execute the tool via the tool runner
            tool_runner_inputs = {
                "main": {
                    "tool_name": tool_name,
                    "args": tool_input,
                },
                "_ctx": ctx,
            }

            try:
                result = self._tool_runner.run(tool_node, tool_runner_inputs, trigger)
                return result
            except Exception as e:
                logger.error(f"❌ Tool execution error: {str(e)}")
                raise

        raise ValueError(f"No tool node found that can execute {tool_name}")

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

        # Store AI response (convert dict to JSON string if needed)
        ai_message = (
            ai_response
            if isinstance(ai_response, str)
            else json.dumps(ai_response, ensure_ascii=False)
        )

        ai_inputs = {
            "main": {
                "message": ai_message,
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
