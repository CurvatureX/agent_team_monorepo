"""Google Gemini AI Agent Runner - Dedicated implementation for Gemini models."""

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


class GoogleGeminiRunner(NodeRunner):
    """Dedicated runner for Google Gemini AI agent with full parameter support."""

    def __init__(self) -> None:
        self._memory_runner = MemoryRunner()
        self._tool_runner = ToolRunner()
        self._api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        """Execute Gemini AI agent with Google-specific configuration."""
        ctx = inputs.get("_ctx")

        # Extract user_prompt from main input port
        main_input = inputs.get("result", {})
        user_prompt = self._extract_user_prompt(main_input)

        if not user_prompt:
            # Fallback to trigger data
            user_prompt = self._extract_message_from_trigger(trigger)

        if not user_prompt or not user_prompt.strip():
            logger.error("❌ Google Gemini Agent requires a non-empty user_prompt")
            raise ValueError("Google Gemini Agent requires 'user_prompt' in main input")

        logger.info(f"🤖 Google Gemini Agent executing: {node.name}")
        logger.debug(f"👤 User prompt: {user_prompt[:100]}...")

        # Extract media inputs for multimodal processing
        media_input = inputs.get("media", {})
        images = media_input.get("images", []) or main_input.get("images", [])

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
                provider_guidance = get_tool_invocation_guidance("gemini")
                system_prompt = f"{system_prompt}\n\n{mcp_guidance}\n\n{provider_guidance}".strip()

        # Generate Google Gemini response
        try:
            generation_result = self._generate_gemini_response(
                node=node,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                available_tools=available_tools,
                images=images,
            )

            ai_response = generation_result["content"]
            logger.info(f"✅ Gemini response generated: {len(ai_response)} characters")

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
                "token_usage": generation_result.get("token_usage", {}),
                "function_calls": generation_result.get("function_calls", []),
            }

            return {"result": output}

        except Exception as e:
            logger.error(f"❌ Google Gemini generation failed: {str(e)}")
            raise ValueError(f"Google Gemini generation failed: {str(e)}")

    def _generate_gemini_response(
        self,
        node: Node,
        user_prompt: str,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        available_tools: List[Dict[str, Any]],
        images: List[Any],
    ) -> Dict[str, Any]:
        """Generate response using Google Gemini API with full parameter support."""
        configs = node.configurations

        # Extract Gemini-specific parameters from node spec
        api_key = configs.get("google_api_key") or configs.get("gemini_api_key") or self._api_key
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY or GEMINI_API_KEY not found. Set google_api_key/gemini_api_key in node configuration or environment variable."
            )

        model = configs.get("model", "gemini-2.5-flash")

        # Extract generation_config from node spec
        generation_config = configs.get("generation_config", {})
        max_output_tokens = int(generation_config.get("max_output_tokens", 8192))
        temperature = float(generation_config.get("temperature", 0.7))
        top_p = float(generation_config.get("top_p", 0.95))
        top_k = int(generation_config.get("top_k", 40))
        candidate_count = int(generation_config.get("candidate_count", 1))
        stop_sequences = generation_config.get("stop_sequences", [])

        # Extract safety_settings from node spec
        safety_settings_config = configs.get("safety_settings", {})
        safety_settings = []
        if safety_settings_config:
            harm_categories = {
                "harassment": "HARM_CATEGORY_HARASSMENT",
                "hate_speech": "HARM_CATEGORY_HATE_SPEECH",
                "sexually_explicit": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "dangerous_content": "HARM_CATEGORY_DANGEROUS_CONTENT",
            }
            for key, category in harm_categories.items():
                if key in safety_settings_config:
                    safety_settings.append(
                        {"category": category, "threshold": safety_settings_config[key]}
                    )

        # Build contents array with conversation history
        contents = []

        # Add system instruction if provided (prepended as system content)
        system_instruction = None
        if system_prompt:
            system_instruction = system_prompt

        # Add conversation history
        for msg in conversation_history:
            role = (
                "user" if msg["role"] == "user" else "model"
            )  # Gemini uses "model" not "assistant"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        # Build current user message parts
        user_parts = [{"text": user_prompt}]

        # Add images for multimodal processing if enabled
        multimodal_config = configs.get("multimodal_config", {})
        if multimodal_config.get("enable_vision", True) and images:
            for image in images[:5]:  # Limit to 5 images
                if isinstance(image, str):
                    # Base64 or URL
                    if image.startswith("data:image"):
                        # Extract base64 data
                        parts = image.split(",", 1)
                        if len(parts) == 2:
                            user_parts.append(
                                {"inline_data": {"mime_type": "image/jpeg", "data": parts[1]}}
                            )
                    else:
                        # URL - Note: Gemini may not support direct URLs, might need to fetch and convert
                        logger.warning(f"⚠️ Image URL provided but Gemini requires base64 data")
                elif isinstance(image, dict):
                    if "inline_data" in image:
                        user_parts.append(image)
                    elif "data" in image and "mime_type" in image:
                        user_parts.append(
                            {
                                "inline_data": {
                                    "mime_type": image["mime_type"],
                                    "data": image["data"],
                                }
                            }
                        )

        # Add current user message
        contents.append({"role": "user", "parts": user_parts})

        # Build request body
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "topP": top_p,
                "topK": top_k,
                "candidateCount": candidate_count,
                "maxOutputTokens": max_output_tokens,
            },
        }

        if stop_sequences:
            body["generationConfig"]["stopSequences"] = stop_sequences

        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        if safety_settings:
            body["safetySettings"] = safety_settings

        # Add tools if available (Gemini function calling)
        if available_tools:
            body["tools"] = self._format_tools_for_gemini(available_tools)

        # Performance config
        performance_config = configs.get("performance_config", {})
        timeout_seconds = float(performance_config.get("timeout_seconds", 120))

        logger.debug(f"🔍 Gemini API request: model={model}, max_tokens={max_output_tokens}")

        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                resp = client.post(url, json=body)
                resp.raise_for_status()
                data = resp.json()

                # Extract response content and tool calls
                content = ""
                tool_calls = []

                if "candidates" in data and data["candidates"]:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        for part in candidate["content"]["parts"]:
                            if "text" in part:
                                content += part["text"]
                            elif "functionCall" in part:
                                func_call = part["functionCall"]
                                tool_calls.append(
                                    {
                                        "name": func_call.get("name"),
                                        "args": func_call.get("args", {}),
                                    }
                                )

                # Extract usage information
                usage_metadata = data.get("usageMetadata", {})
                token_usage = {
                    "input_tokens": usage_metadata.get("promptTokenCount", 0),
                    "output_tokens": usage_metadata.get("candidatesTokenCount", 0),
                    "total_tokens": usage_metadata.get("totalTokenCount", 0),
                }

                # Determine format type
                response_format = configs.get("response_format", "text")
                format_type = (
                    response_format if response_format in ["text", "json", "schema"] else "text"
                )

                # Build metadata
                metadata = {
                    "model_version": model,
                    "finish_reason": candidate.get("finishReason")
                    if "candidates" in data
                    else None,
                    "safety_ratings": candidate.get("safetyRatings", [])
                    if "candidates" in data
                    else [],
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
            try:
                error_data = e.response.json()
                error_message = error_data.get("error", {}).get("message", error_text)
            except:
                error_message = error_text
            logger.error(f"❌ Gemini API error: {e.response.status_code} - {error_message}")
            raise ValueError(f"Gemini API error: {e.response.status_code} - {error_message}")
        except Exception as e:
            logger.error(f"❌ Gemini API request failed: {str(e)}")
            raise ValueError(f"Gemini API request failed: {str(e)}")

    def _format_tools_for_gemini(
        self, available_tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format MCP tools into Gemini's function calling format."""
        function_declarations = []

        for tool in available_tools:
            if "name" in tool:
                # Direct MCP tool definition format
                function_declarations.append(
                    {
                        "name": tool["name"],
                        "description": tool.get("description", f"Execute {tool['name']}"),
                        "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                    }
                )

        # Gemini expects tools as an array with functionDeclarations
        return [{"functionDeclarations": function_declarations}] if function_declarations else []

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
        """Load conversation history from memory nodes in Gemini message format."""
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
                "role": "assistant",  # Use "assistant" for consistency, even though Gemini uses "model"
                "metadata": {
                    "ai_model": ai_node.configurations.get("model", "gemini-2.5-flash"),
                    "ai_provider": "gemini",
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
                    "ai_model": ai_node.configurations.get("model", "gemini-2.5-flash"),
                    "ai_provider": "gemini",
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
                "ai_model": ai_node.configurations.get("model", "gemini-2.5-flash"),
                "ai_provider": "gemini",
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


__all__ = ["GoogleGeminiRunner"]
