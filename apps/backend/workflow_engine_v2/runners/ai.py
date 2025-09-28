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
from shared.models.workflow_new import Node

from ..services.ai_providers import get_ai_provider
from .base import NodeRunner
from .memory import MemoryRunner
from .tool import ToolRunner

logger = logging.getLogger(__name__)


class AIAgentRunner(NodeRunner):
    """Enhanced AI agent runner with memory-aware conversation and MCP tool integration."""

    def __init__(self) -> None:
        self._memory_runner = MemoryRunner()
        self._tool_runner = ToolRunner()

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        """Execute AI agent with memory-aware conversation and tool integration."""
        ctx = inputs.get("_ctx")

        # Extract user message from inputs
        main_input = inputs.get("main", {})
        user_message = self._extract_user_message(main_input)

        logger.info(
            f"🤖 AI Agent executing: {node.name} (model: {node.configurations.get('model', node.subtype)})"
        )
        logger.info(f"🔍 DEBUG main_input type: {type(main_input)}, value: {main_input}")
        logger.info(f"🔍 DEBUG user_message type: {type(user_message)}, value: {user_message}")
        logger.info(
            f"👤 User message: {user_message[:100]}{'...' if len(user_message) > 100 else ''}"
        )

        # 1. BEFORE AI execution: Detect and load memory context
        memory_nodes = self._detect_attached_nodes(node, ctx, NodeType.MEMORY)
        enhanced_prompt = node.configurations.get("prompt", "") or node.configurations.get(
            "system_prompt", ""
        )

        logger.info(f"🔍 DEBUG enhanced_prompt: '{enhanced_prompt}'")
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

        provider_name = self._determine_provider(node)

        if enhanced_prompt and user_message:
            logger.info(f"🚀 Generating AI response with provider: {provider_name}")

            try:
                provider = get_ai_provider(provider_name)

                # Prepare generation parameters with tools if available
                generation_params = {"model": output["model"], **node.configurations}

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
        return {"main": output}

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

                if memory_result.get("main", {}).get("success"):
                    history_data = memory_result["main"].get("context", "")
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

    async def _discover_mcp_tools(
        self, tool_nodes: List[Node], ctx: Any, trigger: TriggerInfo
    ) -> List[Dict[str, Any]]:
        """Discover available MCP tools from attached tool nodes."""
        available_tools = []

        for tool_node in tool_nodes:
            try:
                # Create tool discovery operation
                tool_inputs = {"main": {"operation": "list_functions"}, "_ctx": ctx}

                # Execute tool discovery
                tool_result = self._tool_runner.run(tool_node, tool_inputs, trigger)

                if tool_result.get("main"):
                    tools_data = tool_result["main"]

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
                else:
                    # Store as generic conversation data
                    await self._store_generic_conversation(
                        memory_node, ctx, trigger, user_message, ai_response, ai_node
                    )

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
                    "ai_model": ai_node.configurations.get("model", ai_node.subtype),
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
                "ai_model": ai_node.configurations.get("model", ai_node.subtype),
                "ai_provider": self._determine_provider(ai_node),
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

    def _prepare_base_output(self, inputs: Dict[str, Any], node: Node) -> Dict[str, Any]:
        """Prepare base output structure."""
        return {
            "input": inputs.get("main", inputs),
            "model": node.configurations.get("model") or node.subtype,
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


__all__ = ["AIAgentRunner"]
