"""Anthropic Claude AI Agent Runner - Dedicated implementation for Claude models."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
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


class AnthropicClaudeRunner(NodeRunner):
    """Dedicated runner for Anthropic Claude AI agent with full parameter support."""

    def __init__(self) -> None:
        self._memory_runner = MemoryRunner()
        self._tool_runner = ToolRunner()
        self._api_key = os.getenv("ANTHROPIC_API_KEY")

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        """Execute Claude AI agent with Anthropic-specific configuration."""
        ctx = inputs.get("_ctx")

        # Extract user_prompt from main input port
        main_input = inputs.get("result", {})
        user_prompt = self._extract_user_prompt(main_input)

        if not user_prompt:
            # Fallback to trigger data
            user_prompt = self._extract_message_from_trigger(trigger)

        if not user_prompt or not user_prompt.strip():
            logger.error("❌ Claude AI Agent requires a non-empty user_prompt")
            raise ValueError("Claude AI Agent requires 'user_prompt' in main input")

        logger.info(f"🤖 Claude AI Agent executing: {node.name}")
        logger.debug(f"👤 User prompt: {user_prompt[:100]}...")

        # Load conversation memory if available
        memory_nodes = self._detect_attached_nodes(node, ctx, NodeType.MEMORY)
        system_prompt = node.configurations.get("system_prompt", "")
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
                provider_guidance = get_tool_invocation_guidance("anthropic")
                system_prompt = f"{system_prompt}\n\n{mcp_guidance}\n\n{provider_guidance}".strip()

        # Log the final enhanced system prompt for debugging
        logger.info("=" * 80)
        logger.info("📝 FINAL ENHANCED SYSTEM PROMPT:")
        logger.info("=" * 80)
        logger.info(system_prompt)
        logger.info("=" * 80)

        # Generate Claude AI response with tool execution loop
        try:
            generation_result = self._generate_claude_response_with_tools(
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
                logger.info(f"✅ Claude response generated: {len(ai_response)} characters")
            else:
                logger.info(
                    f"✅ Claude response generated: {type(ai_response).__name__} with {len(str(ai_response))} chars"
                )

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
                "token_usage": generation_result.get("token_usage", {}),
                "function_calls": generation_result.get("function_calls", []),
            }

            logger.info(f"📦 Built output before return: {output}")
            return {"result": output}

        except Exception as e:
            logger.error(f"❌ Claude AI generation failed: {str(e)}")
            raise ValueError(f"Claude AI generation failed: {str(e)}")

    def _generate_claude_response(
        self,
        node: Node,
        user_prompt: str,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        available_tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate response using Anthropic Claude API with full parameter support."""
        configs = node.configurations

        # Extract Anthropic-specific parameters from node spec
        api_key = configs.get("anthropic_api_key") or self._api_key
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. Set anthropic_api_key in node configuration or ANTHROPIC_API_KEY environment variable."
            )

        model = configs.get("model", "claude-sonnet-4-20250514")
        # Guard against misconfigured OpenAI model names on Anthropic runner
        try:
            if isinstance(model, str) and (
                model.lower().startswith("gpt") or "gpt-" in model.lower()
            ):
                logger.warning(
                    f"⚠️ Anthropic runner received OpenAI model '{model}'. Falling back to Claude default."
                )
                model = "claude-sonnet-4-20250514"
        except Exception:
            # If any issue occurs, just proceed with default
            model = "claude-sonnet-4-20250514"
        max_tokens = int(configs.get("max_tokens", 8192))
        temperature = float(configs.get("temperature", 0.7))
        top_p = float(configs.get("top_p", 0.9))

        # Build messages array with conversation history
        messages = []

        # Add conversation history (if any)
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current user message
        messages.append({"role": "user", "content": user_prompt})

        # Build request body
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        # Only add top_p for non-4.5 models (Claude 4.5 doesn't allow both temperature and top_p)
        if "4-5" not in model and "sonnet-4-5" not in model.lower():
            body["top_p"] = top_p

        # Add system prompt if provided
        if system_prompt:
            body["system"] = system_prompt

        # Add tools if available
        if available_tools:
            body["tools"] = self._format_tools_for_anthropic(available_tools)

        # Performance config
        performance_config = configs.get("performance_config", {})
        timeout_seconds = float(performance_config.get("timeout_seconds", 120))

        # API request headers
        headers = {
            "x-api-key": api_key,
            "anthropic-version": configs.get(
                "anthropic_version", os.getenv("ANTHROPIC_VERSION", "2023-06-01")
            ),
            "Content-Type": "application/json",
        }

        logger.debug(f"🔍 Claude API request: model={model}, max_tokens={max_tokens}")

        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                resp = client.post(
                    "https://api.anthropic.com/v1/messages", headers=headers, json=body
                )
                resp.raise_for_status()
                data = resp.json()

                # Extract response content and tool calls
                content = ""
                tool_calls = []

                if "content" in data:
                    for content_block in data["content"]:
                        if content_block.get("type") == "text":
                            content += content_block.get("text", "")
                        elif content_block.get("type") == "tool_use":
                            tool_calls.append(
                                {
                                    "id": content_block.get("id"),
                                    "name": content_block.get("name"),
                                    "input": content_block.get("input", {}),
                                }
                            )

                # Extract usage information
                usage = data.get("usage", {})
                token_usage = {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                }

                # Always attempt to parse JSON responses
                parsed_content = content
                if isinstance(content, str) and content.strip():
                    try:
                        import json

                        parsed_content = json.loads(content)
                        logger.debug(f"✅ Parsed JSON response: {type(parsed_content)}")
                    except json.JSONDecodeError:
                        # Not JSON, keep as string
                        parsed_content = content

                # Build metadata
                metadata = {
                    "model_version": model,
                    "stop_reason": data.get("stop_reason"),
                    "stop_sequence": data.get("stop_sequence"),
                }

                return {
                    "content": parsed_content,
                    "metadata": metadata,
                    "token_usage": token_usage,
                    "function_calls": tool_calls,
                }

        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"❌ Anthropic API error: {e.response.status_code} - {error_text}")
            raise ValueError(f"Anthropic API error: {e.response.status_code} - {error_text}")
        except Exception as e:
            logger.error(f"❌ Anthropic API request failed: {str(e)}")
            raise ValueError(f"Anthropic API request failed: {str(e)}")

    def _generate_claude_response_with_tools(
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
        """Generate Claude response with multi-turn tool execution support.

        This implements the proper tool calling pattern:
        1. Send user message to Claude
        2. If Claude calls tools, execute them
        3. Send tool results back to Claude
        4. Claude generates final text response
        5. Return the final text response
        """
        configs = node.configurations
        api_key = configs.get("anthropic_api_key") or self._api_key
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")

        model = configs.get("model", "claude-sonnet-4-20250514")
        max_tokens = int(configs.get("max_tokens", 8192))
        temperature = float(configs.get("temperature", 0.7))
        top_p = float(configs.get("top_p", 0.9))
        timeout_seconds = float(configs.get("performance_config", {}).get("timeout_seconds", 120))

        headers = {
            "x-api-key": api_key,
            "anthropic-version": configs.get(
                "anthropic_version", os.getenv("ANTHROPIC_VERSION", "2023-06-01")
            ),
            "Content-Type": "application/json",
        }

        # Build initial messages
        messages = []
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_prompt})

        total_input_tokens = 0
        total_output_tokens = 0
        all_tool_calls = []
        max_iterations = 5
        iteration = 0

        # Map tool name to its providing node (when discoverer provides metadata)
        tool_source_map = {}
        try:
            tool_source_map = {
                t["name"]: t.get("_source_node_id")
                for t in (available_tools or [])
                if isinstance(t, dict) and t.get("name") and t.get("_source_node_id")
            }
        except Exception:
            tool_source_map = {}

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"🔄 Claude conversation turn {iteration}/{max_iterations}")

            # Build request body
            body = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            # Only add top_p for non-4.5 models (Claude 4.5 doesn't allow both temperature and top_p)
            if "4-5" not in model and "sonnet-4-5" not in model.lower():
                body["top_p"] = top_p

            if system_prompt:
                body["system"] = system_prompt

            if available_tools:
                body["tools"] = self._format_tools_for_anthropic(available_tools)

            # Call Anthropic API
            try:
                with httpx.Client(timeout=timeout_seconds) as client:
                    resp = client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers=headers,
                        json=body,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                # Extract response content and tool calls
                content_text = ""
                tool_calls = []

                if "content" in data:
                    for content_block in data["content"]:
                        if content_block.get("type") == "text":
                            content_text += content_block.get("text", "")
                        elif content_block.get("type") == "tool_use":
                            tool_calls.append(
                                {
                                    "id": content_block.get("id"),
                                    "name": content_block.get("name"),
                                    "input": content_block.get("input", {}),
                                }
                            )

                # Track token usage
                usage = data.get("usage", {})
                total_input_tokens += usage.get("input_tokens", 0)
                total_output_tokens += usage.get("output_tokens", 0)
                all_tool_calls.extend(tool_calls)

                # If no tool calls, we're done
                if not tool_calls:
                    logger.info(f"✅ Claude generated final response ({len(content_text)} chars)")

                    # Always attempt to parse JSON responses
                    parsed_content = content_text
                    if isinstance(content_text, str) and content_text.strip():
                        try:
                            import json

                            parsed_content = json.loads(content_text)
                            logger.debug(f"✅ Parsed JSON response: {type(parsed_content)}")
                        except json.JSONDecodeError:
                            # Not JSON, keep as string
                            parsed_content = content_text

                    return {
                        "content": parsed_content,
                        "metadata": {
                            "model_version": model,
                            "stop_reason": data.get("stop_reason"),
                            "stop_sequence": data.get("stop_sequence"),
                        },
                        "token_usage": {
                            "input_tokens": total_input_tokens,
                            "output_tokens": total_output_tokens,
                            "total_tokens": total_input_tokens + total_output_tokens,
                        },
                        "function_calls": all_tool_calls,
                    }

                # Execute tool calls
                logger.info(f"🔧 Executing {len(tool_calls)} tool call(s)")
                tool_results = []

                for tool_call in tool_calls:
                    tool_name = tool_call.get("name")
                    tool_input = tool_call.get("input", {})
                    tool_id = tool_call.get("id")

                    logger.info(f"🔨 Executing tool: {tool_name}")

                    try:
                        tool_result = self._execute_mcp_tool(
                            tool_name=tool_name,
                            tool_input=tool_input,
                            tool_nodes=tool_nodes,
                            tool_source_map=tool_source_map,
                            trigger=trigger,
                            ctx=ctx,
                        )

                        # Format tool result for Claude - use JSON for better parsing
                        import json

                        result_content = tool_result.get("result", {})

                        # Log tool result for debugging
                        logger.info(f"📥 Tool '{tool_name}' returned: {str(tool_result)[:300]}...")
                        logger.info(
                            f"📊 Result content type: {type(result_content)}, has data: {bool(result_content)}"
                        )

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

                        logger.info(
                            f"📤 Sending to Claude ({len(result_str)} chars): {result_str[:200]}..."
                        )

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result_str,
                            }
                        )

                        logger.info(f"✅ Tool {tool_name} executed successfully")

                    except Exception as e:
                        logger.error(f"❌ Tool {tool_name} execution failed: {str(e)}")
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": f"Error: {str(e)}",
                                "is_error": True,
                            }
                        )

                # Build assistant message with tool uses
                assistant_content = []
                if content_text:
                    assistant_content.append({"type": "text", "text": content_text})

                for tc in tool_calls:
                    assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["name"],
                            "input": tc["input"],
                        }
                    )

                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_content,
                    }
                )

                # Add tool results as user message
                messages.append(
                    {
                        "role": "user",
                        "content": tool_results,
                    }
                )

            except httpx.HTTPStatusError as e:
                error_text = e.response.text
                logger.error(f"❌ Anthropic API error: {e.response.status_code} - {error_text}")
                raise ValueError(f"Anthropic API error: {e.response.status_code} - {error_text}")
            except Exception as e:
                logger.error(f"❌ Anthropic API request failed: {str(e)}")
                raise ValueError(f"Anthropic API request failed: {str(e)}")

        # Max iterations reached
        logger.warning(f"⚠️ Max iterations ({max_iterations}) reached")

        # Always attempt to parse JSON responses
        parsed_content = content_text
        if isinstance(content_text, str) and content_text.strip():
            try:
                import json

                parsed_content = json.loads(content_text)
                logger.debug(f"✅ Parsed JSON response: {type(parsed_content)}")
            except json.JSONDecodeError:
                # Not JSON, keep as string
                parsed_content = content_text

        return {
            "content": parsed_content,
            "metadata": {"model_version": model, "stop_reason": "max_iterations"},
            "token_usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
            },
            "function_calls": all_tool_calls,
        }

    def _execute_mcp_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_nodes: List[Node],
        tool_source_map: Optional[Dict[str, str]],
        trigger: TriggerInfo,
        ctx: Any,
    ) -> Dict[str, Any]:
        """Execute an MCP tool call through the appropriate tool node."""
        # Prefer the specific tool node that declared this tool (if known)
        preferred_node_id = None
        try:
            preferred_node_id = (tool_source_map or {}).get(tool_name)
        except Exception:
            preferred_node_id = None

        # Build an ordered list: preferred node first (if any), then the rest
        ordered_tool_nodes: List[Node] = []
        if preferred_node_id:
            ordered_tool_nodes = [n for n in tool_nodes if n.id == preferred_node_id] + [
                n for n in tool_nodes if n.id != preferred_node_id
            ]
        else:
            ordered_tool_nodes = list(tool_nodes)

        # Find the tool node that provides this tool
        for tool_node in ordered_tool_nodes:
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

    def _format_tools_for_anthropic(
        self, available_tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format MCP tools into Anthropic's tool format."""
        anthropic_tools = []

        for tool in available_tools:
            if "name" in tool:
                # Direct MCP tool definition format
                anthropic_tools.append(
                    {
                        "name": tool["name"],
                        "description": tool.get("description", f"Execute {tool['name']}"),
                        "input_schema": tool.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    }
                )

        return anthropic_tools

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
        """Load conversation history from memory nodes in Claude message format."""
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
        import json

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
                    "ai_model": ai_node.configurations.get("model", "claude-sonnet-4-20250514"),
                    "ai_provider": "anthropic",
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
                    "ai_model": ai_node.configurations.get("model", "claude-sonnet-4-20250514"),
                    "ai_provider": "anthropic",
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
                "ai_model": ai_node.configurations.get("model", "claude-sonnet-4-20250514"),
                "ai_provider": "anthropic",
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

    def _extract_config_context(self, node: Node, spec: Any) -> str:
        """Extract human-readable configuration context from downstream node.

        This provides the AI with visibility into what's already configured in the
        downstream node, so it can make intelligent decisions about what to include
        in its output.

        Note: All configurations are exposed to AI context, including tokens/keys,
        as the AI needs this information to generate correct instructions.
        """
        config_lines = []

        # Get all configurations from the node
        for key, value in node.configurations.items():
            if value is not None:
                # Handle schema-style configuration (dict with default/value)
                if isinstance(value, dict):
                    # Check if it's a schema definition
                    if "default" in value or "value" in value:
                        actual_value = value.get("default") or value.get("value")
                    else:
                        # It's a configuration object, show it
                        actual_value = value
                else:
                    actual_value = value

                # Format for readability
                if actual_value or actual_value == "":
                    # Truncate very long values
                    value_str = str(actual_value)
                    if len(value_str) > 300:
                        value_str = value_str[:300] + "... (truncated)"

                    if actual_value == "":
                        config_lines.append(f"- `{key}`: (empty string)")
                    else:
                        config_lines.append(f"- `{key}`: {value_str}")

        if config_lines:
            return (
                "\n".join(config_lines)
                + "\n\n**Note:** You can override any of these configured values by including them in your output. If not specified, the configured values above will be used."
            )
        else:
            return "(No pre-configured values - all parameters must come from your output)"


__all__ = ["AnthropicClaudeRunner"]
