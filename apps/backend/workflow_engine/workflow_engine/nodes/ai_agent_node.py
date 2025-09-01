"""
AI Agent Node Executor - Provider-Based Architecture.

Handles AI agent operations using provider-based nodes (Gemini, OpenAI, Claude)
where functionality is determined by system prompts rather than hardcoded roles.
"""

import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.models import NodeType
from shared.models.node_enums import AIAgentSubtype
from shared.node_specs import node_spec_registry
from shared.node_specs.base import NodeSpec

# Memory implementations
try:
    from workflow_engine.memory_implementations import MemoryContextMerger
except ImportError:
    # Create stub class to prevent import errors
    class MemoryContextMerger:
        def __init__(self, config):
            self.config = config


from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult


class AIAgentNodeExecutor(BaseNodeExecutor):
    """Executor for AI_AGENT_NODE type with provider-based architecture."""

    def __init__(self, subtype: Optional[str] = None):
        super().__init__(subtype=subtype)
        self.ai_clients = {}
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Initializing AIAgentNodeExecutor with subtype: {subtype}"
        )
        self._init_ai_clients()

        # Initialize memory context merger
        self.memory_merger = MemoryContextMerger(
            {"max_total_tokens": 4000, "merge_strategy": "priority", "token_buffer": 0.1}
        )
        self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Memory context merger initialized")

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for AI agent nodes."""
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Getting node spec for subtype: {self._subtype}"
        )

        if node_spec_registry and self._subtype:
            # Return the specific spec for current subtype
            spec = node_spec_registry.get_spec(NodeType.AI_AGENT.value, self._subtype)
            if spec:
                self.logger.info(
                    f"[AIAgent Node]: 🤖 AI AGENT: ✅ Found node spec for {self._subtype}"
                )
            else:
                self.logger.info(
                    f"[AIAgent Node]: 🤖 AI AGENT: ⚠️ No node spec found for {self._subtype}"
                )
            return spec

        self.logger.info("[AIAgent Node]: 🤖 AI AGENT: No registry or subtype available")
        return None

    def _init_ai_clients(self):
        """Initialize AI provider clients."""
        self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Initializing AI provider clients...")

        try:
            # Initialize OpenAI client
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                self.ai_clients["openai"] = {"api_key": openai_key, "client": None}
                self.logger.info("[AIAgent Node]: 🤖 AI AGENT: ✅ OpenAI client configured")
            else:
                self.logger.info("[AIAgent Node]: 🤖 AI AGENT: ⚠️ OpenAI API key not found")

            # Initialize Anthropic client
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if anthropic_key:
                self.ai_clients["anthropic"] = {
                    "api_key": anthropic_key,
                    "client": None,
                }
                self.logger.info("[AIAgent Node]: 🤖 AI AGENT: ✅ Anthropic client configured")
            else:
                self.logger.info("[AIAgent Node]: 🤖 AI AGENT: ⚠️ Anthropic API key not found")

            # Initialize Google client
            google_key = os.getenv("GOOGLE_API_KEY")
            if google_key:
                self.ai_clients["google"] = {"api_key": google_key, "client": None}
                self.logger.info("[AIAgent Node]: 🤖 AI AGENT: ✅ Google/Gemini client configured")
            else:
                self.logger.info("[AIAgent Node]: 🤖 AI AGENT: ⚠️ Google API key not found")

            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: Total configured clients: {len(self.ai_clients)}"
            )

        except Exception as e:
            self.logger.error(f"[AIAgent Node]: 🤖 AI AGENT: ❌ Failed to initialize AI clients: {e}")

    def get_supported_subtypes(self) -> List[str]:
        """Get supported AI agent subtypes (provider-based)."""
        return [subtype.value for subtype in AIAgentSubtype]

    def validate(self, node: Any) -> List[str]:
        """Validate AI agent node configuration using spec-based validation."""
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Starting validation for node: {getattr(node, 'id', 'unknown')}"
        )
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Node subtype: {getattr(node, 'subtype', 'none')}"
        )

        # First use the base class validation which includes spec validation
        errors = super().validate(node)

        if errors:
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: ⚠️ Base validation found {len(errors)} errors"
            )
            for error in errors:
                self.logger.info(f"[AIAgent Node]: 🤖 AI AGENT:   - {error}")

        # If spec validation passed, we can skip manual validation
        if not errors and self.spec:
            self.logger.info("[AIAgent Node]: 🤖 AI AGENT: ✅ Spec-based validation passed")
            return errors

        # Fallback to legacy validation if spec not available
        self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Using legacy validation")

        if not node.subtype:
            error_msg = "AI Agent subtype is required"
            errors.append(error_msg)
            self.logger.error(f"[AIAgent Node]: 🤖 AI AGENT: ❌ {error_msg}")
            return errors

        subtype = node.subtype
        supported_subtypes = self.get_supported_subtypes()

        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Checking if {subtype} is in supported types: {supported_subtypes}"
        )

        if subtype not in supported_subtypes:
            error_msg = f"Unsupported AI agent subtype: {subtype}. Supported types: {', '.join(supported_subtypes)}"
            errors.append(error_msg)
            self.logger.error(f"[AIAgent Node]: 🤖 AI AGENT: ❌ {error_msg}")
        else:
            self.logger.info(f"[AIAgent Node]: 🤖 AI AGENT: ✅ Subtype {subtype} is supported")

        return errors

    def _validate_legacy(self, node: Any) -> List[str]:
        """Legacy validation for backward compatibility."""
        errors = []

        # Validate required parameters
        errors.extend(self._validate_required_parameters(node, ["system_prompt"]))

        # Validate model_version if provided
        if hasattr(node, "parameters"):
            model_version = node.parameters.get("model_version")
            if model_version and hasattr(node, "subtype"):
                valid_models = self._get_valid_models_for_provider(node.subtype)
                if valid_models and model_version not in valid_models:
                    errors.append(
                        f"Invalid model version '{model_version}' for {node.subtype}. Valid models: {', '.join(valid_models)}"
                    )

            # Validate provider-specific parameters
            if hasattr(node, "subtype"):
                errors.extend(self._validate_provider_specific_parameters(node, node.subtype))

        return errors

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute AI agent node with provider-based architecture and memory integration."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype
            node_id = getattr(context.node, "id", "unknown")
            self.logger.info(f"[AIAgent Node]: 🤖 AI AGENT: Starting {subtype} execution")
            self.logger.info(f"[AIAgent Node]: 🤖 AI AGENT: Node ID: {node_id}")
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: Execution ID: {getattr(context, 'execution_id', 'unknown')}"
            )

            # Detect connected memory nodes and load conversation history
            connected_memory_nodes = self._detect_connected_memory_nodes(context)
            if connected_memory_nodes:
                self.logger.info(
                    f"[AIAgent Node]: 🤖 AI AGENT: 🧠 Found {len(connected_memory_nodes)} connected memory nodes"
                )
                # Load conversation history from connected memory nodes
                conversation_history = await self._load_conversation_history_from_memory_nodes(
                    context, connected_memory_nodes
                )
                if conversation_history:
                    # Add conversation history to input data for memory enhancement
                    if not isinstance(context.input_data, dict):
                        context.input_data = {}
                    context.input_data["memory_context"] = conversation_history
                    self.logger.info(
                        f"[AIAgent Node]: 🤖 AI AGENT: 🧠 Loaded conversation history ({len(conversation_history)} chars)"
                    )
            else:
                self.logger.info("[AIAgent Node]: 🤖 AI AGENT: 🧠 No connected memory nodes detected")

            # Log input data analysis
            if hasattr(context, "input_data") and context.input_data:
                self.logger.info(f"[AIAgent Node]: 🤖 AI AGENT: Input data analysis:")
                if isinstance(context.input_data, dict):
                    for key, value in context.input_data.items():
                        if key == "memory_context":
                            self.logger.info(
                                f"[AIAgent Node]: 🤖 AI AGENT:   📥 Found '{key}': {len(str(value))} characters"
                            )
                        elif isinstance(value, str) and len(value) > 100:
                            self.logger.info(
                                f"[AIAgent Node]: 🤖 AI AGENT:   📥 Input '{key}': {value[:100]}... ({len(value)} chars)"
                            )
                        else:
                            self.logger.info(
                                f"[AIAgent Node]: 🤖 AI AGENT:   📥 Input '{key}': {value}"
                            )
                else:
                    self.logger.info(
                        f"[AIAgent Node]: 🤖 AI AGENT:   📥 Input data (non-dict): {str(context.input_data)[:200]}..."
                    )
            else:
                self.logger.info("[AIAgent Node]: 🤖 AI AGENT: No input data provided")

            # Process memory contexts if present
            memory_contexts = self._extract_memory_contexts(context)
            if memory_contexts:
                total_chars = sum(len(str(ctx)) for ctx in memory_contexts)
                self.logger.info(
                    f"[AIAgent Node]: 🧠 AIAgent: Found {len(memory_contexts)} contexts, {total_chars} chars total"
                )

            # Enhanced context with memory integration
            enhanced_context = self._enhance_context_with_memory(context, memory_contexts, logs)

            # Execute the AI provider
            result = None
            if subtype == AIAgentSubtype.GOOGLE_GEMINI.value:
                result = self._execute_gemini_agent(enhanced_context, logs, start_time)
            elif subtype == AIAgentSubtype.OPENAI_CHATGPT.value:
                result = self._execute_openai_agent(enhanced_context, logs, start_time)
            elif subtype == AIAgentSubtype.ANTHROPIC_CLAUDE.value:
                result = self._execute_claude_agent(enhanced_context, logs, start_time)
            else:
                result = self._create_error_result(
                    f"Unsupported AI agent provider: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

            # Store conversation exchange in connected memory nodes after successful AI execution
            if (
                result
                and hasattr(result, "status")
                and result.status.value == "success"
                and connected_memory_nodes
            ):
                try:
                    # Extract user message and AI response for storage
                    user_message = self._prepare_input_for_ai(context.input_data)
                    ai_response = ""

                    if hasattr(result, "output_data") and result.output_data:
                        ai_response = result.output_data.get("content", "")

                    if user_message and ai_response:
                        await self._store_conversation_exchange(
                            context, connected_memory_nodes, user_message, ai_response
                        )
                except Exception as e:
                    self.logger.warning(
                        f"[AIAgent Node]: 🧠 AIAgent: Failed to store conversation: {e}"
                    )

            return result

        except Exception as e:
            return self._create_error_result(
                f"Error executing AI agent: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _extract_memory_contexts(self, context: NodeExecutionContext) -> List[str]:
        """Extract memory contexts from workflow execution data.

        This method looks for memory node connections attached to this AI node
        and retrieves their execution results to use as memory context.
        """
        memory_contexts = []

        try:
            # Check if context has memory data from previous node executions
            if hasattr(context, "input_data") and isinstance(context.input_data, dict):
                # Look for memory context data that was added by memory nodes
                if "memory_context" in context.input_data:
                    memory_contexts.append(context.input_data["memory_context"])

                # Also check for specific memory types
                memory_keys = ["conversation_history", "entity_context", "knowledge_context"]
                for key in memory_keys:
                    if key in context.input_data:
                        memory_contexts.append(f"{key}: {context.input_data[key]}")

            # For now, return empty list as a fallback - the execution engine
            # needs to be updated to properly pass memory node results
            return memory_contexts

        except Exception as e:
            self.logger.warning(f"Error extracting memory contexts: {e}")

        return memory_contexts

    def _extract_memory_context_for_api(
        self, context: NodeExecutionContext
    ) -> Optional[Dict[str, Any]]:
        """Extract memory context specifically formatted for API calls with conversation history."""
        try:
            if not hasattr(context, "input_data") or not isinstance(context.input_data, dict):
                return None

            # Check for memory context that contains conversation messages
            if "memory_context" in context.input_data:
                memory_data = context.input_data["memory_context"]

                # If memory_data is a string, try to parse it as JSON
                if isinstance(memory_data, str):
                    try:
                        import json

                        parsed_data = json.loads(memory_data)
                        if isinstance(parsed_data, dict) and "messages" in parsed_data:
                            self.logger.info(
                                f"[AIAgent Node]: 🧠 AI AGENT: Found {len(parsed_data['messages'])} conversation messages in memory"
                            )
                            return parsed_data
                    except json.JSONDecodeError:
                        pass

                # If memory_data is already a dict with messages
                elif isinstance(memory_data, dict) and "messages" in memory_data:
                    self.logger.info(
                        f"[AIAgent Node]: 🧠 AI AGENT: Found {len(memory_data['messages'])} conversation messages in memory"
                    )
                    return memory_data

            # Check for direct messages format (from memory node output)
            if "messages" in context.input_data:
                messages = context.input_data["messages"]
                if isinstance(messages, list) and len(messages) > 0:
                    # Validate message format
                    valid_messages = []
                    for msg in messages:
                        if isinstance(msg, dict) and "role" in msg and "content" in msg:
                            valid_messages.append({"role": msg["role"], "content": msg["content"]})

                    if valid_messages:
                        self.logger.info(
                            f"[AIAgent Node]: 🧠 AI AGENT: Found {len(valid_messages)} valid conversation messages"
                        )
                        return {"messages": valid_messages}

            return None

        except Exception as e:
            self.logger.warning(f"[AIAgent Node]: ⚠️ Error extracting memory context for API: {e}")
            return None

    def _enhance_context_with_memory(
        self, context: NodeExecutionContext, memory_contexts: List[str], logs: List[str]
    ) -> NodeExecutionContext:
        """Enhance the execution context with memory contexts."""
        try:
            if not memory_contexts:
                return context

            # Merge all memory contexts into a single context string
            merged_memory_context = "\n\n".join(memory_contexts)
            self.logger.info(
                f"[AIAgent Node]: 🧠 AIAgent: Memory merged -> {len(memory_contexts)} contexts, {len(merged_memory_context)} chars"
            )
            logs.append(f"Enhanced context with {len(memory_contexts)} memory contexts")

            # Create enhanced input data
            enhanced_input_data = context.input_data.copy() if context.input_data else {}

            # Add merged memory context to input data
            enhanced_input_data["memory_context"] = merged_memory_context
            enhanced_input_data["has_memory_context"] = True

            # Create new context with enhanced input
            enhanced_context = NodeExecutionContext(
                node=context.node,
                input_data=enhanced_input_data,
                workflow_id=getattr(context, "workflow_id", None),
                execution_id=getattr(context, "execution_id", None),
                static_data=getattr(context, "static_data", {}),
                credentials=getattr(context, "credentials", {}),
                metadata=getattr(context, "metadata", {}),
            )
            return enhanced_context

        except Exception as e:
            self.logger.warning(f"[AIAgent Node]: 🧠 AIAgent: Memory enhancement failed: {e}")

        # Return original context if memory enhancement fails or no memory contexts
        return context

    def _enhance_system_prompt_with_summary(
        self, base_prompt: str, memory_context: Optional[Dict[str, Any]]
    ) -> str:
        """Enhance system prompt with memory summary (but not conversation messages)."""
        try:
            if not memory_context:
                return base_prompt

            # Check for conversation summary data
            memory_type = memory_context.get("memory_type", "")

            # Only enhance with summary for CONVERSATION_SUMMARY memory type
            from shared.models.node_enums import MemorySubtype

            if memory_type == MemorySubtype.CONVERSATION_SUMMARY.value:
                summary = memory_context.get("summary", "")
                key_points = memory_context.get("key_points", [])
                entities = memory_context.get("entities", [])
                topics = memory_context.get("topics", [])

                if summary or key_points or entities or topics:
                    self.logger.info(
                        f"[AIAgent Node]: 💭 AI AGENT: Enhancing system prompt with conversation summary"
                    )

                    enhanced_parts = [base_prompt]

                    if summary:
                        enhanced_parts.append(f"\n## Conversation Summary\n\n{summary}")

                    if key_points:
                        enhanced_parts.append(
                            f"\n## Key Points from Previous Conversations\n\n"
                            + "\n".join(f"• {point}" for point in key_points)
                        )

                    if entities:
                        enhanced_parts.append(f"\n## Relevant Entities\n\n" + ", ".join(entities))

                    if topics:
                        enhanced_parts.append(f"\n## Discussion Topics\n\n" + ", ".join(topics))

                    enhanced_prompt = "".join(enhanced_parts)
                    self.logger.info(
                        f"[AIAgent Node]: 💭 AI AGENT: Enhanced system prompt (+{len(enhanced_prompt) - len(base_prompt)} chars)"
                    )
                    return enhanced_prompt

            return base_prompt

        except Exception as e:
            self.logger.warning(
                f"[AIAgent Node]: ⚠️ Error enhancing system prompt with summary: {e}"
            )
            return base_prompt

    def _detect_connected_memory_nodes(self, context: NodeExecutionContext) -> List[Dict[str, Any]]:
        """Detect memory nodes connected to this AI agent."""
        connected_memory_nodes = []

        # Get workflow connections and nodes from metadata
        workflow_connections = context.metadata.get("workflow_connections", {})
        workflow_nodes = context.metadata.get("workflow_nodes", [])
        current_node_id = context.metadata.get("node_id")

        if not current_node_id or not workflow_connections or not workflow_nodes:
            self.logger.info(
                "[AIAgent Node]: 🤖 AI AGENT: 🧠 Missing workflow connection data for memory node detection"
            )
            return connected_memory_nodes

        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: 🧠 Detecting memory nodes connected to {current_node_id}"
        )

        # Look for outgoing connections from this AI agent node to memory nodes
        if current_node_id in workflow_connections:
            node_connections = workflow_connections[current_node_id]
            connection_types = node_connections.get("connection_types", {})

            for connection_type, connection_array in connection_types.items():
                connections_list = connection_array.get("connections", [])

                for connection in connections_list:
                    target_node_id = connection.get("node")

                    # Find the target node definition
                    for node in workflow_nodes:
                        if node.get("id") == target_node_id:
                            if (
                                node.get("type") == NodeType.MEMORY.value
                            ):  # Use proper enum from shared models
                                connected_memory_nodes.append(
                                    {
                                        "node_id": target_node_id,
                                        "node": node,
                                        "connection_type": connection_type,
                                        "connection": connection,
                                    }
                                )
                                self.logger.info(
                                    f"[AIAgent Node]: 🤖 AI AGENT: 🧠 Found connected memory node: {target_node_id} (subtype: {node.get('subtype', 'unknown')})"
                                )
                            break

        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: 🧠 Total connected memory nodes: {len(connected_memory_nodes)}"
        )
        return connected_memory_nodes

    async def _load_conversation_history_from_memory_nodes(
        self, context: NodeExecutionContext, memory_nodes: List[Dict[str, Any]]
    ) -> str:
        """Load conversation history from connected memory nodes."""
        self.logger.info(
            "[AIAgent Node]: 🤖 AI AGENT: 🧠 Loading conversation history from memory nodes"
        )

        # For now, we'll use the first memory node (could be enhanced to merge multiple)
        if not memory_nodes:
            return ""

        memory_node_info = memory_nodes[0]
        memory_node_def = memory_node_info["node"]
        memory_node_id = memory_node_info["node_id"]

        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: 🧠 Loading from memory node: {memory_node_id}"
        )

        try:
            # Import and create memory node executor
            from .memory_node import MemoryNodeExecutor

            memory_executor = MemoryNodeExecutor(subtype=memory_node_def.get("subtype"))

            # Create context for memory node to load conversation history
            memory_context = NodeExecutionContext(
                node=self._dict_to_node_object(memory_node_def),
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                input_data={
                    "action": "load_conversation_history"
                },  # Special action to load history
                static_data=context.static_data,
                credentials=context.credentials,
                metadata=context.metadata,
            )

            # Execute memory node to get conversation history
            memory_result = memory_executor.execute(memory_context)

            if memory_result.status.value == "success" and memory_result.output_data:
                conversation_history = memory_result.output_data.get("conversation_history", "")
                self.logger.info(
                    f"[AIAgent Node]: 🤖 AI AGENT: 🧠 Loaded conversation history ({len(conversation_history)} chars)"
                )
                return conversation_history
            else:
                self.logger.warning(
                    f"[AIAgent Node]: 🤖 AI AGENT: 🧠 Failed to load conversation history: {memory_result.error_message}"
                )
                return ""

        except Exception as e:
            self.logger.error(
                f"[AIAgent Node]: 🤖 AI AGENT: 🧠 Error loading conversation history: {e}"
            )
            return ""

    async def _store_conversation_exchange(
        self,
        context: NodeExecutionContext,
        memory_nodes: List[Dict[str, Any]],
        user_message: str,
        ai_response: str,
    ):
        """Store conversation exchange in connected memory nodes after AI execution."""
        if not memory_nodes:
            return

        for memory_node_info in memory_nodes:
            memory_node_def = memory_node_info["node"]
            memory_node_id = memory_node_info["node_id"]

            try:
                # Import and create memory node executor
                from .memory_node import MemoryNodeExecutor

                memory_executor = MemoryNodeExecutor(subtype=memory_node_def.get("subtype"))

                # Create context for memory node to store conversation
                memory_context = NodeExecutionContext(
                    node=self._dict_to_node_object(memory_node_def),
                    workflow_id=context.workflow_id,
                    execution_id=context.execution_id,
                    input_data={
                        "user_message": user_message,
                        "ai_response": ai_response,
                        "source_node": getattr(context.node, "id", "ai_agent"),
                        "timestamp": datetime.now().isoformat(),
                    },
                    static_data=context.static_data,
                    credentials=context.credentials,
                    metadata=context.metadata,
                )

                # Execute memory node to store conversation
                memory_result = memory_executor.execute(memory_context)

                if memory_result.status.value == "success":
                    self.logger.info(
                        f"[AIAgent Node]: 🧠 AIAgent: Stored conversation -> node:{memory_node_id}"
                    )
                else:
                    self.logger.warning(
                        f"[AIAgent Node]: 🧠 AIAgent: Store failed -> node:{memory_node_id}, error:{memory_result.error_message}"
                    )

            except Exception as e:
                self.logger.error(
                    f"[AIAgent Node]: 🧠 AIAgent: Store error -> node:{memory_node_id}, {e}"
                )

    def _dict_to_node_object(self, node_def: Dict[str, Any]):
        """Convert node definition dict to node object."""
        from types import SimpleNamespace

        return SimpleNamespace(**node_def)

    def _execute_gemini_agent(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute Gemini AI agent."""
        logs.append("Executing Google Gemini agent")
        # Use spec-based parameter retrieval
        base_system_prompt = self.get_parameter_with_spec(context, "system_prompt")
        model_version = self.get_parameter_with_spec(context, "model_version")
        temperature = self.get_parameter_with_spec(context, "temperature")
        max_tokens = self.get_parameter_with_spec(context, "max_tokens")
        safety_settings = self.get_parameter_with_spec(context, "safety_settings")

        # Extract memory context for conversation history and summary
        memory_context = self._extract_memory_context_for_api(context)

        # Enhance system prompt with summary if available (but not conversation messages)
        system_prompt = self._enhance_system_prompt_with_summary(base_system_prompt, memory_context)

        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Gemini agent: {model_version}, temp: {temperature}"
        )
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: System prompt length: {len(system_prompt)} characters"
        )

        # Prepare input for AI processing
        input_text = self._prepare_input_for_ai(context.input_data)

        try:
            # Call Gemini API (Note: Gemini doesn't support conversation history in the same way,
            # but we keep the parameter for consistency)
            ai_response = self._call_gemini_api(
                system_prompt=system_prompt,
                input_text=input_text,
                model=model_version,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Parse AI response to extract just the content
            content = self._parse_ai_response(ai_response)

            # Store AI response in memory if user message was provided
            self._store_conversation_in_memory(context, input_text, content, logs)

            # Use standard communication format
            output_data = {
                "content": content,
                "metadata": {
                    "provider": "gemini",
                    "model": model_version,
                    "system_prompt": system_prompt,
                    "input_text": input_text,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "safety_settings": safety_settings,
                    "executed_at": datetime.now().isoformat(),
                },
                "format_type": "text",
                "source_node": context.node.id
                if hasattr(context, "node") and context.node
                else None,
                "timestamp": datetime.now().isoformat(),
            }

            logs.append(f"AI agent completed: {context.node.subtype}")
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs,
            )

        except Exception as e:
            return self._create_error_result(
                f"Error in Gemini agent: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_openai_agent(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute OpenAI AI agent."""
        logs.append("Executing OpenAI GPT agent")
        # Use spec-based parameter retrieval
        base_system_prompt = self.get_parameter_with_spec(context, "system_prompt")
        model_version = self.get_parameter_with_spec(context, "model_version")
        temperature = self.get_parameter_with_spec(context, "temperature")
        max_tokens = self.get_parameter_with_spec(context, "max_tokens")
        presence_penalty = self.get_parameter_with_spec(context, "presence_penalty")
        frequency_penalty = self.get_parameter_with_spec(context, "frequency_penalty")

        # Extract memory context for conversation history and summary
        memory_context = self._extract_memory_context_for_api(context)

        # Enhance system prompt with summary if available (but not conversation messages)
        system_prompt = self._enhance_system_prompt_with_summary(base_system_prompt, memory_context)

        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: OpenAI configuration - model: {model_version}, temp: {temperature}"
        )
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: System prompt length: {len(system_prompt)} characters"
        )

        # Prepare input for AI processing
        input_text = self._prepare_input_for_ai(context.input_data)
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: User input prepared: '{input_text[:100]}{'...' if len(input_text) > 100 else ''}' ({len(input_text)} chars)"
        )

        try:
            # Call OpenAI API with conversation history
            ai_response = self._call_openai_api(
                system_prompt=system_prompt,
                input_text=input_text,
                model=model_version,
                temperature=temperature,
                max_tokens=max_tokens,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                memory_context=memory_context,
            )

            # Parse AI response to extract just the content
            content = self._parse_ai_response(ai_response)

            # Store AI response in memory if user message was provided
            self._store_conversation_in_memory(context, input_text, content, logs)

            # Use standard communication format
            output_data = {
                "content": content,
                "metadata": {
                    "provider": "openai",
                    "model": model_version,
                    "system_prompt": system_prompt,
                    "input_text": input_text,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "presence_penalty": presence_penalty,
                    "frequency_penalty": frequency_penalty,
                    "executed_at": datetime.now().isoformat(),
                    "conversation_messages_count": len(memory_context.get("messages", []))
                    if memory_context
                    else 0,
                },
                "format_type": "text",
                "source_node": context.node.id
                if hasattr(context, "node") and context.node
                else None,
                "timestamp": datetime.now().isoformat(),
            }

            logs.append(f"AI agent completed: {context.node.subtype}")
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs,
            )

        except Exception as e:
            return self._create_error_result(
                f"Error in OpenAI agent: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_claude_agent(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute Claude AI agent."""
        logs.append("Executing Anthropic Claude agent")
        # Use spec-based parameter retrieval
        base_system_prompt = self.get_parameter_with_spec(context, "system_prompt")
        model_version = self.get_parameter_with_spec(context, "model_version")
        temperature = self.get_parameter_with_spec(context, "temperature")
        max_tokens = self.get_parameter_with_spec(context, "max_tokens")
        stop_sequences = self.get_parameter_with_spec(context, "stop_sequences")

        # Extract memory context for conversation history and summary
        memory_context = self._extract_memory_context_for_api(context)

        # Enhance system prompt with summary if available (but not conversation messages)
        system_prompt = self._enhance_system_prompt_with_summary(base_system_prompt, memory_context)

        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Claude agent: {model_version}, temp: {temperature}"
        )
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: System prompt length: {len(system_prompt)} characters"
        )

        # Prepare input for AI processing
        input_text = self._prepare_input_for_ai(context.input_data)

        try:
            # Call Claude API with conversation history
            ai_response = self._call_claude_api(
                system_prompt=system_prompt,
                input_text=input_text,
                model=model_version,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
                memory_context=memory_context,
            )

            # Parse AI response to extract just the content
            content = self._parse_ai_response(ai_response)

            # Store AI response in memory if user message was provided
            self._store_conversation_in_memory(context, input_text, content, logs)

            # Use standard communication format
            output_data = {
                "content": content,
                "metadata": {
                    "provider": "claude",
                    "model": model_version,
                    "system_prompt": system_prompt,
                    "input_text": input_text,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stop_sequences": stop_sequences,
                    "executed_at": datetime.now().isoformat(),
                    "conversation_messages_count": len(memory_context.get("messages", []))
                    if memory_context
                    else 0,
                },
                "format_type": "text",
                "source_node": context.node.id
                if hasattr(context, "node") and context.node
                else None,
                "timestamp": datetime.now().isoformat(),
            }

            logs.append(f"AI agent completed: {context.node.subtype}")
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs,
            )

        except Exception as e:
            return self._create_error_result(
                f"Error in Claude agent: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _get_valid_models_for_provider(self, provider: str) -> List[str]:
        """Get valid model versions for a provider using enum definitions."""
        from shared.models.node_enums import VALID_AI_MODELS

        return list(VALID_AI_MODELS.get(provider, set()))

    def _validate_provider_specific_parameters(self, node: Any, provider: str) -> List[str]:
        """Validate provider-specific parameters."""
        errors = []

        if provider == AIAgentSubtype.GOOGLE_GEMINI.value:
            # Validate safety_settings format if provided
            safety_settings = node.parameters.get("safety_settings")
            if safety_settings and not isinstance(safety_settings, dict):
                errors.append("safety_settings must be a dictionary")

        elif provider == AIAgentSubtype.OPENAI_CHATGPT.value:
            # Validate penalty values
            for penalty in ["presence_penalty", "frequency_penalty"]:
                value = node.parameters.get(penalty)
                if value is not None and not (-2.0 <= value <= 2.0):
                    errors.append(f"{penalty} must be between -2.0 and 2.0")

        elif provider == AIAgentSubtype.ANTHROPIC_CLAUDE.value:
            # Validate stop_sequences format if provided
            stop_sequences = node.parameters.get("stop_sequences")
            if stop_sequences and not isinstance(stop_sequences, list):
                errors.append("stop_sequences must be a list")

        return errors

    def _prepare_input_for_ai(self, input_data: Dict[str, Any]) -> str:
        """Prepare input data for AI processing, including memory context integration."""
        if isinstance(input_data, str):
            return input_data

        if isinstance(input_data, dict):
            # Check if this is memory node output (has memory-specific structure)
            if self._is_memory_node_output(input_data):
                self.logger.info(
                    f"[AIAgent Node]: 🧠 Memory node output detected, extracting original user message"
                )
                # Extract the original user message from memory context
                original_message = self._extract_original_message_from_memory_output(input_data)
                if original_message:
                    return original_message
                else:
                    self.logger.warning(
                        f"[AIAgent Node]: ⚠️ Could not extract original message from memory output"
                    )
                    return "Please provide your message."

            # Check if memory context is present (from memory integration)
            if "memory_context" in input_data:
                # Memory context is now handled in system prompt, just return the basic message
                self.logger.info(f"🧠 Memory context detected, will be used in system prompt")

                # Fall through to extract the actual user message

            # First check for standard communication format (from trigger or other nodes)
            if "content" in input_data:
                content = input_data["content"]
                # Skip if content looks like memory node JSON output
                if isinstance(content, str) and content.strip().startswith("{"):
                    try:
                        import json

                        parsed_content = json.loads(content)
                        if self._is_memory_node_output(parsed_content):
                            self.logger.info(
                                f"[AIAgent Node]: 🧠 Content is memory JSON, extracting original message"
                            )
                            original_message = self._extract_original_message_from_memory_output(
                                parsed_content
                            )
                            if original_message:
                                return original_message
                    except (json.JSONDecodeError, ValueError, TypeError):
                        pass  # Not JSON, treat as regular content

                self.logger.info(
                    f"[AIAgent Node]: 🎯 Extracted standard format content: {content[:100]}..."
                )
                return str(content)

            # Legacy support: Check for direct message/text fields
            if "message" in input_data:
                message_content = input_data["message"]
                self.logger.info(
                    f"[AIAgent Node]: 🎯 Extracted legacy message field: {message_content}"
                )
                return str(message_content)

            if "text" in input_data:
                text_content = input_data["text"]
                self.logger.info(f"[AIAgent Node]: 🎯 Extracted legacy text field: {text_content}")
                return str(text_content)

            # Legacy support: Check for trigger payload structures
            if "payload" in input_data:
                payload = input_data["payload"]
                if isinstance(payload, dict):
                    # Slack message event
                    if "event" in payload and "text" in payload["event"]:
                        slack_text = payload["event"]["text"]
                        self.logger.info(
                            f"[AIAgent Node]: 🎯 Extracted legacy Slack message: {slack_text}"
                        )
                        return slack_text

                    # Direct text field in payload
                    elif "text" in payload:
                        text_content = payload["text"]
                        self.logger.info(
                            f"[AIAgent Node]: 🎯 Extracted legacy payload text: {text_content}"
                        )
                        return text_content

            # Log what we received for debugging
            self.logger.warning(
                f"⚠️ No extractable message found in input_data keys: {list(input_data.keys())}"
            )
            self.logger.info(f"🔍 Full input_data: {input_data}")

            # Convert entire dict to structured text as fallback
            import json

            return json.dumps(input_data, indent=2, ensure_ascii=False)

    def _parse_ai_response(self, ai_response: str) -> str:
        """Parse AI response to extract just the content, removing JSON wrapper."""
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Parsing AI response ({len(str(ai_response))} characters)"
        )

        if not ai_response:
            self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Empty response received")
            return ""

        try:
            # Try to parse as JSON
            if isinstance(ai_response, str) and ai_response.strip().startswith("{"):
                self.logger.info(
                    "[AIAgent Node]: 🤖 AI AGENT: Response appears to be JSON, attempting to parse"
                )
                import json

                data = json.loads(ai_response)
                self.logger.info(
                    f"[AIAgent Node]: 🤖 AI AGENT: JSON parsed successfully, keys: {list(data.keys())}"
                )

                # Extract response content from common JSON structures
                if "response" in data:
                    response_content = data["response"]
                    self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Found 'response' key in JSON")
                    # If the response is still JSON, try to extract further
                    if isinstance(response_content, str) and response_content.strip().startswith(
                        "{"
                    ):
                        try:
                            inner_data = json.loads(response_content)
                            if "response" in inner_data:
                                self.logger.info(
                                    "[AIAgent Node]: 🤖 AI AGENT: Found nested 'response' key"
                                )
                                return inner_data["response"]
                        except (json.JSONDecodeError, KeyError, TypeError):
                            pass
                    return response_content
                elif "content" in data:
                    self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Found 'content' key in JSON")
                    return data["content"]
                elif "text" in data:
                    self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Found 'text' key in JSON")
                    return data["text"]
                elif "message" in data:
                    self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Found 'message' key in JSON")
                    return data["message"]
                else:
                    # If no known key, return the first string value found
                    self.logger.info(
                        "[AIAgent Node]: 🤖 AI AGENT: No known keys found, using first string value"
                    )
                    for value in data.values():
                        if isinstance(value, str):
                            return value
        except json.JSONDecodeError:
            self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Response is not valid JSON, using as-is")
            pass
        except Exception as e:
            self.logger.warning(f"[AIAgent Node]: 🤖 AI AGENT: Error parsing response: {e}")
            pass

        # If not JSON or no extractable content, return as-is
        self.logger.info(
            "[AIAgent Node]: 🤖 AI AGENT: Using response as-is (no JSON parsing needed)"
        )
        return str(ai_response)

    def _call_gemini_api(
        self,
        system_prompt: str,
        input_text: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call actual Gemini API."""
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Starting Gemini API call with model: {model}"
        )
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Temperature: {temperature}, Max tokens: {max_tokens}"
        )

        try:
            import google.generativeai as genai

            # Configure with API key (use GEMINI_API_KEY as suggested)
            gemini_key = os.getenv("GEMINI_API_KEY")
            if not gemini_key:
                error_msg = "GEMINI_API_KEY not found in environment - Gemini integration not configured in AWS infrastructure"
                self.logger.error(f"[AIAgent Node]: 🤖 AI AGENT: ❌ {error_msg}")
                raise ValueError(error_msg)

            self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Configuring Gemini API client")
            genai.configure(api_key=gemini_key)

            # Create model instance
            self.logger.info(f"[AIAgent Node]: 🤖 AI AGENT: Creating Gemini model instance: {model}")
            model_instance = genai.GenerativeModel(model)

            # Combine system prompt and input
            full_prompt = f"{system_prompt}\n\nInput: {input_text}"
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: Full prompt prepared ({len(full_prompt)} characters)"
            )

            # Make API call
            self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Making Gemini API call...")
            response = model_instance.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature, max_output_tokens=max_tokens
                ),
            )

            response_text = response.text
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: ✅ Gemini API call successful, response length: {len(response_text)}"
            )
            return response_text

        except Exception as e:
            self.logger.error(f"[AIAgent Node]: 🤖 AI AGENT: ❌ Gemini API call failed: {e}")
            # Return error message that will be handled by external action nodes
            return f"⚠️ Gemini API unavailable: {str(e)}"

    def _call_openai_api(
        self,
        system_prompt: str,
        input_text: str,
        model: str,
        temperature: float,
        max_tokens: int,
        presence_penalty: float,
        frequency_penalty: float,
        memory_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Call actual OpenAI API with conversation history support."""
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Starting OpenAI API call with model: {model}"
        )
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Temperature: {temperature}, Max tokens: {max_tokens}"
        )
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Presence penalty: {presence_penalty}, Frequency penalty: {frequency_penalty}"
        )

        try:
            from openai import OpenAI

            # Get API key
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                error_msg = "OPENAI_API_KEY not found in environment"
                self.logger.error(f"[AIAgent Node]: 🤖 AI AGENT: ❌ {error_msg}")
                raise ValueError(error_msg)

            # Create client
            self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Creating OpenAI client")
            client = OpenAI(api_key=openai_key)

            # Build conversation messages
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history if available
            if memory_context and memory_context.get("messages"):
                history_messages = memory_context["messages"]
                self.logger.info(
                    f"[AIAgent Node]: 🧠 AI AGENT: Adding {len(history_messages)} messages from conversation history"
                )
                messages.extend(history_messages)

            # Add current user message
            messages.append({"role": "user", "content": input_text})

            # Log message count
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: Total messages in conversation: {len(messages)}"
            )

            # Make API call
            self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Making OpenAI API call...")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
            )

            response_content = response.choices[0].message.content
            if response_content is None:
                response_content = ""
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: ✅ OpenAI API call successful, response length: {len(response_content)}"
            )
            return response_content

        except Exception as e:
            self.logger.error(f"[AIAgent Node]: 🤖 AI AGENT: ❌ OpenAI API call failed: {e}")

            # Return user-friendly error message
            if "api key" in str(e).lower():
                return f"⚠️ OpenAI API key is invalid or missing"
            elif "rate limit" in str(e).lower():
                return f"⚠️ OpenAI API rate limit exceeded. Please try again later."
            else:
                return f"⚠️ OpenAI API error: {str(e)}"

    def _call_claude_api(
        self,
        system_prompt: str,
        input_text: str,
        model: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: List[str],
        memory_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Call actual Claude API with conversation history support."""
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Starting Anthropic Claude API call with model: {model}"
        )
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Temperature: {temperature}, Max tokens: {max_tokens}"
        )
        self.logger.info(f"[AIAgent Node]: 🤖 AI AGENT: Stop sequences: {stop_sequences}")

        try:
            import anthropic

            # Get API key
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_key:
                error_msg = "ANTHROPIC_API_KEY not found in environment"
                self.logger.error(f"[AIAgent Node]: 🤖 AI AGENT: ❌ {error_msg}")
                raise ValueError(error_msg)

            # Create client
            self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Creating Anthropic client")
            client = anthropic.Anthropic(api_key=anthropic_key)

            # Build conversation messages
            messages = []

            # Add conversation history if available
            if memory_context and memory_context.get("messages"):
                history_messages = memory_context["messages"]
                self.logger.info(
                    f"[AIAgent Node]: 🧠 AI AGENT: Adding {len(history_messages)} messages from conversation history"
                )
                messages.extend(history_messages)

            # Add current user message
            messages.append({"role": "user", "content": input_text})

            # Log message count
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: Total messages in conversation: {len(messages)}"
            )

            # Make API call
            self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Making Claude API call...")
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=messages,
                stop_sequences=stop_sequences if stop_sequences else None,
            )

            response_text = response.content[0].text
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: ✅ Claude API call successful, response length: {len(response_text)}"
            )
            return response_text

        except Exception as e:
            self.logger.error(f"[AIAgent Node]: 🤖 AI AGENT: ❌ Claude API call failed: {e}")

            # Return user-friendly error message
            if "api key" in str(e).lower():
                return f"⚠️ Anthropic API key is invalid or missing"
            elif "rate limit" in str(e).lower():
                return f"⚠️ Anthropic API rate limit exceeded. Please try again later."
            else:
                return f"⚠️ Anthropic Claude API error: {str(e)}"

    def _store_conversation_in_memory(
        self, context: NodeExecutionContext, user_input: str, ai_response: str, logs: List[str]
    ) -> None:
        """Store the conversation (user input + AI response) in connected memory nodes."""
        try:
            # Only store if we have both user input and AI response
            if not user_input or not ai_response:
                self.logger.info(
                    f"[AIAgent Node]: 🧠 AIAgent: Skipping memory storage - missing input or response"
                )
                return

            # Find connected memory nodes
            memory_nodes = self._get_connected_memory_nodes(context)
            if not memory_nodes:
                self.logger.info(
                    f"[AIAgent Node]: 🧠 AIAgent: No connected memory nodes found, skipping storage"
                )
                return

            # Extract clean user message from input - prevent storing JSON structures
            user_message = user_input

            # Skip storing if user input looks like memory node output (prevent recursion)
            if user_input.strip().startswith("{") and len(user_input) > 200:
                try:
                    import json

                    parsed_input = json.loads(user_input)
                    if self._is_memory_node_output(parsed_input):
                        self.logger.warning(
                            f"[AIAgent Node]: 🧠 AIAgent: Skipping storage - user input is memory JSON structure"
                        )
                        return
                    # If it's JSON but not memory output, try to extract content
                    if isinstance(parsed_input, dict) and "content" in parsed_input:
                        content = str(parsed_input["content"])
                        if not content.strip().startswith(
                            "{"
                        ):  # Make sure content isn't nested JSON
                            user_message = content
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass  # Use original input if JSON parsing fails

            # Final check: don't store if message is too long (likely corrupted/recursive)
            if len(user_message) > 1000:
                self.logger.warning(
                    f"[AIAgent Node]: 🧠 AIAgent: Skipping storage - user message too long ({len(user_message)} chars)"
                )
                return

            # Store in each connected memory node
            for memory_node_info in memory_nodes:
                memory_node_def = memory_node_info["node"]
                memory_node_id = memory_node_info["node_id"]

                # Create memory storage data
                memory_data = {
                    "user_message": user_message,
                    "ai_response": ai_response,
                    "source_node": context.node.id
                    if hasattr(context, "node") and context.node
                    else "ai_agent",
                    "timestamp": datetime.now().isoformat(),
                }

                try:
                    # Import memory node executor
                    from .memory_node import MemoryNodeExecutor

                    # Create memory node instance with correct subtype
                    memory_node = MemoryNodeExecutor(subtype=memory_node_def.get("subtype"))

                    # Create memory context for storage
                    memory_context = NodeExecutionContext(
                        node=self._dict_to_node_object(memory_node_def),
                        workflow_id=context.workflow_id,
                        execution_id=context.execution_id,
                        input_data=memory_data,
                        static_data=context.static_data if hasattr(context, "static_data") else {},
                        credentials=context.credentials if hasattr(context, "credentials") else {},
                        metadata=context.metadata if hasattr(context, "metadata") else {},
                    )

                    # Execute memory storage
                    self.logger.info(
                        f"[AIAgent Node]: 🧠 AIAgent: Storing conversation in memory node {memory_node_id}..."
                    )
                    result = memory_node.execute(memory_context)

                    if hasattr(result, "status") and result.status == ExecutionStatus.SUCCESS:
                        self.logger.info(
                            f"[AIAgent Node]: 🧠 AIAgent: ✅ Conversation stored in memory node {memory_node_id}"
                        )
                        logs.append(f"Conversation stored in memory node {memory_node_id}")
                    else:
                        self.logger.warning(
                            f"[AIAgent Node]: 🧠 AIAgent: ⚠️ Failed to store in memory node {memory_node_id}: {getattr(result, 'error_message', 'Unknown error')}"
                        )
                        logs.append(
                            f"Failed to store in memory node {memory_node_id}: {getattr(result, 'error_message', 'Unknown error')}"
                        )

                except Exception as e:
                    self.logger.error(
                        f"[AIAgent Node]: 🧠 AIAgent: ❌ Error storing in memory node {memory_node_id}: {e}"
                    )
                    logs.append(f"Error storing in memory node {memory_node_id}: {e}")

        except Exception as e:
            self.logger.error(
                f"[AIAgent Node]: 🧠 AIAgent: ❌ Error storing conversation in memory: {e}"
            )
            logs.append(f"Error storing conversation in memory: {e}")

    def _is_memory_node_output(self, data: Dict[str, Any]) -> bool:
        """Check if data looks like memory node output."""
        try:
            # Memory node output has specific structure
            memory_indicators = [
                "memory_type",
                "buffer",
                "summary",
                "message_count",
                "memory_context",
                "formatted_context",
                "last_updated",
            ]
            # If it has several memory-specific fields, it's likely memory output
            indicator_count = sum(1 for key in memory_indicators if key in data)
            return indicator_count >= 3
        except (AttributeError, TypeError):
            return False

    def _extract_original_message_from_memory_output(self, memory_output: Dict[str, Any]) -> str:
        """Extract the original user message from memory node output."""
        try:
            # Look in formatted_context or memory_context for recent messages
            context = memory_output.get("formatted_context") or memory_output.get(
                "memory_context", ""
            )
            if isinstance(context, str) and context:
                # Parse the context to find the most recent user message
                lines = context.split("\n")
                for line in reversed(lines):
                    if line.strip().startswith("User: "):
                        user_message = line.strip()[6:]  # Remove "User: " prefix
                        # Skip if it looks like JSON/structured data
                        if not user_message.strip().startswith("{"):
                            self.logger.info(
                                f"[AIAgent Node]: 🎯 Extracted user message from memory: {user_message[:50]}..."
                            )
                            return user_message

            # Fallback: look in buffer for the most recent user message
            buffer = memory_output.get("buffer", [])
            if isinstance(buffer, list) and buffer:
                for message in reversed(buffer):
                    if isinstance(message, dict) and message.get("role") == "user":
                        content = message.get("content", "")
                        # Skip if it looks like JSON/structured data
                        if not str(content).strip().startswith("{"):
                            self.logger.info(
                                f"[AIAgent Node]: 🎯 Extracted user message from buffer: {content[:50]}..."
                            )
                            return str(content)

            return ""
        except Exception as e:
            self.logger.warning(f"[AIAgent Node]: ⚠️ Error extracting original message: {e}")
            return ""
