"""
AI Agent Node Executor - Provider-Based Architecture.

Handles AI agent operations using provider-based nodes (Gemini, OpenAI, Claude)
where functionality is determined by system prompts rather than hardcoded roles.
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.models import NodeType
from shared.models.node_enums import AIAgentSubtype
from shared.node_specs import node_spec_registry
from shared.node_specs.base import ConnectionType, NodeSpec

# Memory implementations
try:
    from workflow_engine.memory_implementations import (
        MemoryContext,
        MemoryContextMerger,
        MemoryPriority,
    )
except ImportError:
    # Create stub classes to prevent import errors
    class MemoryContext:
        def __init__(self, **kwargs):
            pass

    class MemoryPriority:
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

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
            self.logger.warning(f"Failed to initialize AI clients: {e}")

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
                credentials=getattr(context, "credentials", None),
            )
            return enhanced_context

        except Exception as e:
            self.logger.warning(f"[AIAgent Node]: 🧠 AIAgent: Memory enhancement failed: {e}")

        # Return original context if memory enhancement fails or no memory contexts
        return context

    def _enhance_system_prompt_with_memory(
        self, base_prompt: str, input_data: Dict[str, Any], logs: List[str]
    ) -> str:
        """Enhance the system prompt with memory context using memory-type-specific injection logic."""
        try:
            # Check for memory context to inject
            if not input_data or not isinstance(input_data, dict):
                return base_prompt

            # Check if memory context is available
            if "memory_context" not in input_data:
                return base_prompt

            memory_context = input_data["memory_context"]
            memory_type = input_data.get("memory_type", "UNKNOWN")

            if not memory_context:
                return base_prompt

            # Show detailed breakdown of memory content being injected
            self.logger.info(
                f"[AIAgent Node]: 💭 AIAgent: SystemPrompt enhanced -> type:{memory_type}, context:{len(memory_context)} chars"
            )

            # Show more detailed preview of memory content
            lines = memory_context.split("\n")
            self.logger.info(
                f"[AIAgent Node]: 💭 AIAgent: 📝 Memory sections: {len([l for l in lines if l.startswith('##')])} sections"
            )

            # Show first few lines of memory context
            preview_lines = lines[:3] if len(lines) >= 3 else lines
            for i, line in enumerate(preview_lines):
                if line.strip():
                    line_preview = line[:80] + "..." if len(line) > 80 else line
                    self.logger.info(f"[AIAgent Node]: 💭 AIAgent: 📋 Line {i+1}: {line_preview}")

            if len(lines) > 3:
                self.logger.info(
                    f"[AIAgent Node]: 💭 AIAgent: 📋 ... and {len(lines) - 3} more lines"
                )

            # Memory-type-specific context injection
            enhanced_prompt = self._inject_memory_by_type(
                base_prompt, memory_context, memory_type, logs
            )

            return enhanced_prompt

        except Exception as e:
            self.logger.warning(f"[AIAgent Node]: 💭 AIAgent: SystemPrompt enhancement failed: {e}")
            return base_prompt

    def _inject_memory_by_type(
        self, base_prompt: str, memory_context: str, memory_type: str, logs: List[str]
    ) -> str:
        """Inject memory context using type-specific formatting and instructions."""
        from shared.models.node_enums import MemorySubtype

        if memory_type == MemorySubtype.CONVERSATION_BUFFER.value:
            return f"""{base_prompt}

## Recent Conversation History

You have access to recent conversation history to maintain context and continuity:

{memory_context}

Use this conversation history to:
- Maintain context across the conversation
- Reference previous topics and decisions
- Provide consistent responses based on earlier interactions"""

        elif memory_type == MemorySubtype.CONVERSATION_SUMMARY.value:
            return f"""{base_prompt}

## Conversation Summary

You have access to a summary of past conversations:

{memory_context}

Use this summary to:
- Understand the broader context and relationship
- Avoid repeating previously covered topics unnecessarily
- Build upon previous discussions and agreements"""

        elif memory_type == MemorySubtype.VECTOR_DATABASE.value:
            return f"""{base_prompt}

## Relevant Knowledge Retrieved

Based on the current conversation, these relevant pieces of information have been retrieved:

{memory_context}

Use this retrieved knowledge to:
- Provide accurate, fact-based responses
- Reference specific information when relevant
- Supplement your knowledge with retrieved context"""

        elif memory_type == MemorySubtype.ENTITY_MEMORY.value:
            return f"""{base_prompt}

## Known Entities and Relationships

You have access to information about known entities and their relationships:

{memory_context}

Use this entity information to:
- Recognize and properly reference people, places, and things
- Understand relationships and connections
- Provide personalized and contextually aware responses"""

        elif memory_type == MemorySubtype.EPISODIC_MEMORY.value:
            return f"""{base_prompt}

## Past Events and Episodes

You have access to relevant past events and episodes:

{memory_context}

Use this episodic memory to:
- Reference past events and their outcomes
- Learn from previous interactions and experiences
- Provide responses informed by historical context"""

        elif memory_type == MemorySubtype.KNOWLEDGE_BASE.value:
            return f"""{base_prompt}

## Structured Knowledge Base

You have access to structured facts and knowledge:

{memory_context}

Use this knowledge base to:
- Provide accurate factual information
- Apply relevant rules and guidelines
- Make informed decisions based on structured knowledge"""

        elif memory_type == MemorySubtype.GRAPH_MEMORY.value:
            return f"""{base_prompt}

## Entity Relationship Graph

You have access to an entity relationship network:

{memory_context}

Use this graph information to:
- Understand complex relationships and connections
- Navigate through related concepts and entities
- Provide responses that consider network effects and indirect relationships"""

        elif memory_type == MemorySubtype.DOCUMENT_STORE.value:
            return f"""{base_prompt}

## Relevant Documents

You have access to relevant documents and content:

{memory_context}

Use these documents to:
- Reference specific information and details
- Provide comprehensive, document-based responses
- Cite or summarize relevant content when appropriate"""

        else:
            # Fallback for unknown memory types or legacy support
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: 💭 ⚠️ Unknown memory type '{memory_type}', using generic injection"
            )
            return f"""{base_prompt}

## Memory Context

You have access to relevant memory context that should inform your responses:

{memory_context}

Please use this context appropriately when responding. Reference relevant information from your memory when it's helpful, but don't force it into every response."""

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

        # Log original system prompt before memory enhancement
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Original system prompt ({len(base_system_prompt)} chars): {base_system_prompt}"
        )

        # Enhance system prompt with memory context if available
        system_prompt = self._enhance_system_prompt_with_memory(
            base_system_prompt, context.input_data, logs
        )

        # Log if system prompt was enhanced with memory
        if len(system_prompt) > len(base_system_prompt):
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: ✅ System prompt enhanced with memory (+{len(system_prompt) - len(base_system_prompt)} chars)"
            )

        self.logger.info(f"Gemini agent: {model_version}, temp: {temperature}")

        # Always show the complete system prompt for debugging
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: ===== COMPLETE SYSTEM PROMPT =====\n{system_prompt}\n===== END SYSTEM PROMPT ====="
        )

        # Prepare input for AI processing
        input_text = self._prepare_input_for_ai(context.input_data)

        try:
            # For now, use mock response (replace with actual Gemini API call)
            ai_response = self._call_gemini_api(
                system_prompt=system_prompt,
                input_text=input_text,
                model=model_version,
                temperature=temperature,
                max_tokens=max_tokens,
                safety_settings=safety_settings,
            )

            # Parse AI response to extract just the content
            content = self._parse_ai_response(ai_response)

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

        # Log original system prompt before memory enhancement
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Original system prompt ({len(base_system_prompt)} chars): {base_system_prompt}"
        )

        # Enhance system prompt with memory context if available
        system_prompt = self._enhance_system_prompt_with_memory(
            base_system_prompt, context.input_data, logs
        )

        # Log if system prompt was enhanced with memory
        if len(system_prompt) > len(base_system_prompt):
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: ✅ System prompt enhanced with memory (+{len(system_prompt) - len(base_system_prompt)} chars)"
            )

        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: OpenAI configuration - model: {model_version}, temp: {temperature}"
        )
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Final system prompt length: {len(system_prompt)} characters"
        )

        # Always show the complete system prompt for debugging
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: ===== COMPLETE SYSTEM PROMPT =====\n{system_prompt}\n===== END SYSTEM PROMPT ====="
        )

        # Prepare input for AI processing
        input_text = self._prepare_input_for_ai(context.input_data)
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: User input prepared: '{input_text[:100]}{'...' if len(input_text) > 100 else ''}' ({len(input_text)} chars)"
        )

        try:
            # For now, use mock response (replace with actual OpenAI API call)
            ai_response = self._call_openai_api(
                system_prompt=system_prompt,
                input_text=input_text,
                model=model_version,
                temperature=temperature,
                max_tokens=max_tokens,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
            )

            # Parse AI response to extract just the content
            content = self._parse_ai_response(ai_response)

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

        # Log original system prompt before memory enhancement
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: Original system prompt ({len(base_system_prompt)} chars): {base_system_prompt}"
        )

        # Enhance system prompt with memory context if available
        system_prompt = self._enhance_system_prompt_with_memory(
            base_system_prompt, context.input_data, logs
        )

        # Log if system prompt was enhanced with memory
        if len(system_prompt) > len(base_system_prompt):
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: ✅ System prompt enhanced with memory (+{len(system_prompt) - len(base_system_prompt)} chars)"
            )

        self.logger.info(f"Claude agent: {model_version}, temp: {temperature}")

        # Always show the complete system prompt for debugging
        self.logger.info(
            f"[AIAgent Node]: 🤖 AI AGENT: ===== COMPLETE SYSTEM PROMPT =====\n{system_prompt}\n===== END SYSTEM PROMPT ====="
        )

        # Prepare input for AI processing
        input_text = self._prepare_input_for_ai(context.input_data)

        try:
            # For now, use mock response (replace with actual Claude API call)
            ai_response = self._call_claude_api(
                system_prompt=system_prompt,
                input_text=input_text,
                model=model_version,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
            )

            # Parse AI response to extract just the content
            content = self._parse_ai_response(ai_response)

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
        """Get valid model versions for a provider."""
        models = {
            AIAgentSubtype.GOOGLE_GEMINI.value: [
                "gemini-pro",
                "gemini-pro-vision",
                "gemini-ultra",
            ],
            AIAgentSubtype.OPENAI_CHATGPT.value: [
                "gpt-4",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
                "gpt-4-vision-preview",
            ],
            AIAgentSubtype.ANTHROPIC_CLAUDE.value: [
                "claude-3-opus",
                "claude-3-sonnet",
                "claude-3-haiku",
                "claude-2.1",
            ],
        }
        return models.get(provider, [])

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
            # Check if memory context is present (from memory integration)
            if "memory_context" in input_data:
                # Memory context is now handled in system prompt, just return the basic message
                self.logger.info(f"🧠 Memory context detected, will be used in system prompt")

                # Fall through to extract the actual user message

            # First check for standard communication format (from trigger or other nodes)
            if "content" in input_data:
                content = input_data["content"]
                self.logger.info(f"[AIAgent Node]: 🎯 Extracted standard format content: {content}")
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
            return json.dumps(input_data, indent=2, ensure_ascii=False)

        return str(input_data)

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
                        except:
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
        safety_settings: Dict,
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
            self.logger.error(f"Gemini API call failed: {e}")
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
    ) -> str:
        """Call actual OpenAI API."""
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

            # Make API call
            self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Making OpenAI API call...")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_text},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
            )

            response_content = response.choices[0].message.content
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: ✅ OpenAI API call successful, response length: {len(response_content)}"
            )
            return response_content

        except Exception as e:
            self.logger.error(f"[AIAgent Node]: 🤖 AI AGENT: ❌ OpenAI API call failed: {e}")
            self.logger.error(f"OpenAI API call failed: {e}")

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
    ) -> str:
        """Call actual Claude API."""
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

            # Make API call
            self.logger.info("[AIAgent Node]: 🤖 AI AGENT: Making Claude API call...")
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": input_text}],
                stop_sequences=stop_sequences if stop_sequences else None,
            )

            response_text = response.content[0].text
            self.logger.info(
                f"[AIAgent Node]: 🤖 AI AGENT: ✅ Claude API call successful, response length: {len(response_text)}"
            )
            return response_text

        except Exception as e:
            self.logger.error(f"[AIAgent Node]: 🤖 AI AGENT: ❌ Claude API call failed: {e}")
            self.logger.error(f"Claude API call failed: {e}")

            # Return user-friendly error message
            if "api key" in str(e).lower():
                return f"⚠️ Anthropic API key is invalid or missing"
            elif "rate limit" in str(e).lower():
                return f"⚠️ Anthropic API rate limit exceeded. Please try again later."
            else:
                return f"⚠️ Anthropic Claude API error: {str(e)}"
