"""Enhanced AI agent runner with intelligent MEMORY and TOOL integration."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import TriggerInfo
from shared.models.node_enums import MemorySubtype, NodeType
from shared.models.workflow import Node
from workflow_engine_v2.runners.base import NodeRunner
from workflow_engine_v2.runners.memory import MemoryRunner
from workflow_engine_v2.runners.tool import ToolRunner
from workflow_engine_v2.services.ai_providers import get_ai_provider

logger = logging.getLogger(__name__)


class AIAgentRunner(NodeRunner):
    """Enhanced AI agent runner with memory-aware conversation and MCP tool integration."""

    def __init__(self) -> None:
        self._memory_runner = MemoryRunner()
        self._tool_runner = ToolRunner()

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        """Execute AI agent with memory-aware conversation and tool integration."""
        ctx = inputs.get("_ctx")

        # Extract user message from inputs, then fallback to trigger data if needed
        main_input = inputs.get("result", {})
        user_message = self._extract_user_message(main_input)
        if (not isinstance(user_message, str)) or (not user_message.strip()):
            user_message = self._extract_message_from_trigger(trigger)

        provider_name = self._determine_provider(node)
        try:
            resolved_model = self._resolve_model_name(node, provider_name)
        except Exception:
            resolved_model = "(unconfigured)"

        # Concise, useful info-level log
        logger.info(
            f"🤖 AI Agent executing: {node.name} | provider={provider_name}, model={resolved_model}"
        )
        # Move noisy diagnostics to debug level
        logger.debug(f"🔍 main_input type={type(main_input)} value={main_input}")
        logger.debug(f"🔍 user_message type={type(user_message)} len={len(user_message)}")
        logger.debug(
            f"👤 User message preview: {user_message[:100]}{'...' if len(user_message) > 100 else ''}"
        )

        # If user_message is empty, fail the node execution (required input)
        if not isinstance(user_message, str) or not user_message.strip():
            logger.error(
                "❌ AI Agent requires a non-empty user message (keys: message/user_message/user_input/input/query/text/content)"
            )
            raise ValueError(
                "AI Agent requires a non-empty user message in 'main' (e.g., main.message or main.user_input)."
            )

        # 1. BEFORE AI execution: Detect and load memory context
        memory_nodes = self._detect_attached_nodes(node, ctx, NodeType.MEMORY)
        enhanced_prompt = node.configurations.get("prompt", "") or node.configurations.get(
            "system_prompt", ""
        )

        logger.debug(f"🔍 system/enhanced_prompt len={len(enhanced_prompt)}")
        conversation_history = ""

        if memory_nodes and user_message:
            logger.info(f"🧠 Found {len(memory_nodes)} memory nodes - loading conversation context")
            conversation_history = asyncio.run(
                self._load_conversation_history(memory_nodes, ctx, trigger)
            )

            if conversation_history:
                # Enhance prompt with conversation history
                enhanced_prompt = self._enhance_prompt_with_memory(
                    enhanced_prompt, conversation_history, user_message
                )
                logger.info(
                    f"🧠 Enhanced prompt with {len(conversation_history)} chars of memory context"
                )

        # 1.5. BEFORE AI execution: Enhance with downstream node guidance (if next node is EXTERNAL_ACTION)
        enhanced_prompt = self._enhance_prompt_with_downstream_guidance(enhanced_prompt, node, ctx)

        # 2. BEFORE AI execution: Detect available MCP tools
        tool_nodes = self._detect_attached_nodes(node, ctx, NodeType.TOOL)
        available_tools = []

        if tool_nodes:
            logger.info(f"🔧 Found {len(tool_nodes)} tool nodes - loading available functions")
            available_tools = asyncio.run(self._discover_mcp_tools(tool_nodes, ctx, trigger))
            logger.info(f"🔧 Discovered {len(available_tools)} MCP functions")

        # 3. EXECUTE AI with enhanced context and tools
        output = self._prepare_base_output(inputs, node)
        ai_response = ""

        if enhanced_prompt and user_message:
            logger.info(f"🚀 Generating AI response with provider: {provider_name}")

            try:
                provider = get_ai_provider(provider_name)
                logger.debug(
                    f"🔍 Got provider: {type(provider).__name__} for provider_name={provider_name}"
                )

                # Use model from node configuration directly - must be a real model string
                api_model_name = self._resolve_model_name(node, provider_name)

                # Prepare generation parameters with tools if available
                generation_params = {"model": api_model_name, **node.configurations}

                if available_tools:
                    generation_params["available_functions"] = available_tools

                # Generate AI response
                gen_result = provider.generate(enhanced_prompt, generation_params)
                ai_response = gen_result.get("response", "")

                # Update output with generation details
                self._update_output_with_generation(
                    output, gen_result, enhanced_prompt, user_message
                )

                logger.info(f"✅ AI response generated: {len(ai_response)} characters")

            except Exception as e:
                logger.error(f"❌ AI generation failed: {str(e)}")
                output["provider_error"] = str(e)
                ai_response = f"I apologize, but I encountered an error: {str(e)}"
        else:
            # If we get here, user_message is non-empty (guarded above). Only handle missing prompt.
            if not enhanced_prompt:
                logger.info("⏭️ No prompt/system prompt configured; skipping AI generation")

        # 4. AFTER AI execution: Store conversation in memory nodes
        if memory_nodes and user_message and ai_response:
            logger.info(f"💾 Storing conversation exchange in {len(memory_nodes)} memory nodes")
            asyncio.run(
                self._store_conversation_in_memory(
                    memory_nodes, ctx, trigger, user_message, ai_response, node
                )
            )

        # All attached nodes (memory and tools) have been handled appropriately:
        # - Memory nodes: Context loaded before AI generation, conversation stored after
        # - Tool nodes: MCP tools discovered and made available to AI provider
        # No additional execution of attached nodes is needed

        # Add standardized output field for conversion functions
        output["output"] = ai_response

        # Parse JSON responses to make structured data available to conversion functions
        if ai_response and isinstance(ai_response, str):
            try:
                import json
                # Try to parse AI response as JSON
                parsed_response = json.loads(ai_response.strip())
                if isinstance(parsed_response, dict):
                    # Merge parsed JSON fields into output for easy access by conversion functions
                    output["parsed_json"] = parsed_response
                    # Also add individual fields to the top level for backward compatibility
                    for key, value in parsed_response.items():
                        if key not in output:  # Don't overwrite existing fields
                            output[key] = value
                    logger.info(f"✅ Parsed AI response as JSON with {len(parsed_response)} fields")
                else:
                    logger.debug("🔍 AI response is valid JSON but not an object")
            except (json.JSONDecodeError, ValueError):
                logger.debug("🔍 AI response is not valid JSON - keeping as string")

        return {"result": output}

    def _extract_user_message(self, main_input: Dict[str, Any]) -> str:
        """Extract user message from various input formats."""
        if isinstance(main_input, str):
            return main_input

        # Try common message field names
        for key in ["message", "user_message", "user_input", "input", "query", "text", "content"]:
            if key in main_input and main_input[key]:
                return str(main_input[key])

        # If no specific field, convert dict to string
        if isinstance(main_input, dict) and main_input:
            return str(main_input)

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
    ) -> str:
        """Load conversation history from memory nodes."""
        conversation_history = ""

        for memory_node in memory_nodes:
            try:
                # Create retrieve operation for memory node
                retrieve_inputs = {"main": {"operation": "retrieve"}, "_ctx": ctx}

                # Configure memory node for retrieve operation
                memory_node_copy = Node(
                    id=memory_node.id,
                    name=memory_node.name,
                    description=memory_node.description,
                    type=memory_node.type,
                    subtype=memory_node.subtype,
                    configurations={
                        **memory_node.configurations,
                        "operation": "get_context",  # Get formatted context for LLM
                        "max_messages": 20,
                        "format": "conversation",
                        "include_metadata": False,
                    },
                )

                # Execute memory retrieval
                memory_result = self._memory_runner.run(memory_node_copy, retrieve_inputs, trigger)

                if memory_result.get("result", {}).get("success"):
                    history_data = memory_result["result"].get("context", "")
                    if history_data:
                        conversation_history += (
                            f"\n--- Memory from {memory_node.name or memory_node.id} ---\n"
                        )
                        conversation_history += str(history_data)
                        logger.debug(
                            f"📖 Loaded {len(str(history_data))} chars from memory node {memory_node.id}"
                        )

            except Exception as e:
                logger.warning(f"⚠️ Failed to load memory from {memory_node.id}: {str(e)}")

        return conversation_history.strip()

    def _enhance_prompt_with_memory(
        self, base_prompt: str, conversation_history: str, user_message: str
    ) -> str:
        """Enhance the prompt with conversation history."""
        if not conversation_history:
            return f"{base_prompt}\n\nUser: {user_message}"

        enhanced_prompt = f"""{base_prompt}

{conversation_history}

Current user message: {user_message}

Please respond based on the conversation history above and the current user message. Maintain context and reference previous interactions when relevant."""

        return enhanced_prompt

    def _enhance_prompt_with_downstream_guidance(
        self, base_prompt: str, node: Node, ctx: Any
    ) -> str:
        """Enhance system prompt with downstream EXTERNAL_ACTION node usage instructions.

        This method detects if the current AI_AGENT node's output flows into an
        EXTERNAL_ACTION node, and if so, appends that node's system_prompt_appendix
        to guide the AI on how to structure its output for proper consumption.
        """
        if not ctx or not hasattr(ctx, "graph"):
            return base_prompt

        try:
            # Import here to avoid circular dependencies
            from workflow_engine_v2.core.spec import get_spec

            graph = ctx.graph  # WorkflowGraph instance

            # Get successor nodes (nodes that receive output from this AI node)
            downstream_nodes = graph.successors(node.id)

            if not downstream_nodes:
                return base_prompt

            appendices = []

            for next_node_id, output_key, _ in downstream_nodes:
                next_node = graph.nodes.get(next_node_id)

                # Only enhance for EXTERNAL_ACTION nodes
                if next_node and next_node.type == NodeType.EXTERNAL_ACTION:
                    # Load node spec to get system_prompt_appendix
                    try:
                        spec = get_spec(next_node.type, next_node.subtype)

                        if (
                            spec
                            and hasattr(spec, "system_prompt_appendix")
                            and spec.system_prompt_appendix
                        ):
                            logger.info(
                                f"📋 Enhancing prompt with guidance for downstream node: {next_node.name} ({next_node.subtype})"
                            )
                            appendices.append(
                                f"\n\n## Downstream Node Output Guidance: {next_node.name}\n"
                                f"Your output will be consumed by a {next_node.subtype} external action node.\n"
                                f"{spec.system_prompt_appendix}"
                            )
                    except Exception as e:
                        logger.debug(f"⚠️ Could not load spec for {next_node.subtype}: {str(e)}")

            if appendices:
                enhanced = base_prompt + "\n".join(appendices)
                logger.info(
                    f"✨ Enhanced system prompt with {len(appendices)} downstream node guidance(s)"
                )
                return enhanced

        except Exception as e:
            logger.warning(f"⚠️ Failed to enhance prompt with downstream guidance: {str(e)}")

        return base_prompt

    async def _discover_mcp_tools(
        self, tool_nodes: List[Node], ctx: Any, trigger: TriggerInfo
    ) -> List[Dict[str, Any]]:
        """Discover available MCP tools from attached tool nodes."""
        available_tools = []

        for tool_node in tool_nodes:
            try:
                # Create tool discovery operation
                tool_inputs = {"result": {"operation": "list_functions"}, "_ctx": ctx}

                # Execute tool discovery
                tool_result = self._tool_runner.run(tool_node, tool_inputs, trigger)

                if tool_result.get("result"):
                    tools_data = tool_result["result"]

                    # Extract function definitions
                    if "functions" in tools_data:
                        functions = tools_data["functions"]
                        if isinstance(functions, list):
                            available_tools.extend(functions)
                    elif "available_functions" in tools_data:
                        functions = tools_data["available_functions"]
                        if isinstance(functions, list):
                            available_tools.extend(functions)

                    logger.debug(f"🔧 Discovered functions from tool node {tool_node.id}")

            except Exception as e:
                logger.warning(f"⚠️ Failed to discover tools from {tool_node.id}: {str(e)}")

        return available_tools

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
                # Determine how to store based on memory type
                if memory_node.subtype == MemorySubtype.CONVERSATION_BUFFER.value:
                    # Store as separate user and assistant messages
                    await self._store_conversation_buffer(
                        memory_node, ctx, trigger, user_message, ai_response, ai_node
                    )
                elif memory_node.subtype == MemorySubtype.VECTOR_DATABASE.value:
                    # Store conversation as searchable content
                    await self._store_vector_conversation(
                        memory_node, ctx, trigger, user_message, ai_response, ai_node
                    )
                # Note: WORKING_MEMORY requires explicit key-value pairs and is not suitable
                # for automatic conversation storage. Skip other memory types.

                logger.debug(f"💾 Stored conversation in memory node {memory_node.id}")

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
                    "ai_model": ai_node.configurations.get("model", ai_node.subtype),
                    "ai_provider": self._determine_provider(ai_node),
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
        # Create conversation content for vector storage
        conversation_content = f"User: {user_message}\nAssistant: {ai_response}"

        vector_inputs = {
            "main": {
                "content": conversation_content,
                "document_type": "conversation",
                "metadata": {
                    "user_message": user_message,
                    "ai_response": ai_response,
                    "ai_model": self._resolve_model_name(
                        ai_node, self._determine_provider(ai_node)
                    ),
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

    def _prepare_base_output(self, inputs: Dict[str, Any], node: Node) -> Dict[str, Any]:
        """Prepare base output structure."""
        try:
            model_for_output = self._resolve_model_name(node, self._determine_provider(node))
        except Exception:
            model_for_output = "(unconfigured)"

        return {
            "input": inputs.get("result", inputs),
            "model": model_for_output,
            "attached": {},
            "memory_enhanced": False,
            "tools_available": False,
        }

    def _determine_provider(self, node: Node) -> str:
        """Determine AI provider from node configuration."""
        provider_name = node.configurations.get("provider")
        if not provider_name:
            sub = str(node.subtype).upper() if node.subtype else ""
            if "OPENAI" in sub:
                provider_name = "openai"
            elif "ANTHROPIC" in sub:
                provider_name = "anthropic"
            elif "GEMINI" in sub or "GOOGLE" in sub:
                provider_name = "gemini"
            else:
                provider_name = "echo"
        return str(provider_name)

    def _update_output_with_generation(
        self,
        output: Dict[str, Any],
        gen_result: Dict[str, Any],
        enhanced_prompt: str,
        user_message: str,
    ) -> None:
        """Update output with AI generation results."""
        output["provider_result"] = gen_result
        output["response"] = gen_result.get("response", "")
        output["enhanced_prompt"] = enhanced_prompt
        output["original_user_message"] = user_message

        usage = gen_result.get("usage") or {}
        details = {
            "ai_model": output.get("model"),
            "prompt_tokens": usage.get("prompt_tokens") or usage.get("input_tokens"),
            "completion_tokens": usage.get("completion_tokens") or usage.get("output_tokens"),
            "model_response": gen_result.get("response"),
        }
        output["_details"] = {k: v for k, v in details.items() if v is not None}

        if usage:
            output["_tokens"] = {
                "input": usage.get("prompt_tokens") or usage.get("input_tokens") or 0,
                "output": usage.get("completion_tokens") or usage.get("output_tokens") or 0,
            }

        # Handle streaming if configured
        if output.get("stream", False) and isinstance(gen_result.get("response"), str):
            resp = gen_result.get("response")
            chunk_size = int(output.get("stream_chunk_size", 64) or 64)
            chunks = [resp[i : i + chunk_size] for i in range(0, len(resp), chunk_size)]
            output["_stream_chunks"] = chunks

    def _resolve_model_name(self, node: Node, provider_name: str) -> str:
        """Resolve the actual model string from node configuration or spec.

        - Accepts string values directly (preferred).
        - If configuration contains a schema dict, prefer 'value', then 'default',
          then single-item 'options'.
        - If not present in configuration, falls back to the node spec's 'model'
          default or first option.
        - Does not fall back to provider defaults; raises if unresolved.
        """
        raw = node.configurations.get("model")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        if isinstance(raw, dict):
            # Prefer an explicit selection if present
            if isinstance(raw.get("value"), str) and raw.get("value").strip():
                return raw.get("value").strip()
            # Fallback to schema default
            if isinstance(raw.get("default"), str) and raw.get("default").strip():
                return raw.get("default").strip()
            # If options exist and exactly one, use it
            opts = raw.get("options")
            if isinstance(opts, list) and len(opts) == 1 and isinstance(opts[0], str):
                return opts[0]
        # Try to read default from node spec (the real node template)
        try:
            from ..core.spec import get_spec

            spec = get_spec(node.type, node.subtype)
            if spec and isinstance(spec.configurations, dict):
                spec_model = spec.configurations.get("model")
                if isinstance(spec_model, dict):
                    if (
                        isinstance(spec_model.get("default"), str)
                        and spec_model.get("default").strip()
                    ):
                        return spec_model.get("default").strip()
                    spec_opts = spec_model.get("options")
                    if isinstance(spec_opts, list) and spec_opts and isinstance(spec_opts[0], str):
                        return spec_opts[0]
        except Exception:
            pass

        # No provider fallback: enforce explicit or spec-based model
        raise ValueError(
            f"Model not specified for node '{node.name}'. Set configurations['model'] to a valid model."
        )

    def _extract_message_from_trigger(self, trigger: TriggerInfo) -> str:
        """Fallback: extract user message from TriggerInfo.trigger_data (e.g., Slack event)."""
        try:
            if not trigger or not getattr(trigger, "trigger_data", None):
                return ""
            data = trigger.trigger_data or {}

            # Common direct fields
            for key in [
                "message",
                "user_message",
                "user_input",
                "input",
                "query",
                "text",
                "content",
            ]:
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()

            # Slack Events: possibly nested under event
            event = data.get("event")
            if isinstance(event, dict):
                text = event.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()

            # Sometimes 'event_data' may be a serialized dict string
            event_raw = data.get("event_data")
            if isinstance(event_raw, dict):
                text = (
                    event_raw.get("event", {}).get("text")
                    if isinstance(event_raw.get("event"), dict)
                    else None
                )
                if isinstance(text, str) and text.strip():
                    return text.strip()
            elif isinstance(event_raw, str) and event_raw:
                try:
                    import ast

                    parsed = ast.literal_eval(event_raw)
                    if isinstance(parsed, dict):
                        ev = parsed.get("event")
                        if isinstance(ev, dict):
                            text = ev.get("text")
                            if isinstance(text, str) and text.strip():
                                return text.strip()
                except Exception:
                    pass
        except Exception:
            pass
        return ""


__all__ = ["AIAgentRunner"]
