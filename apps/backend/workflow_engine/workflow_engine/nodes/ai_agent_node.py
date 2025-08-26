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

# Memory implementations will be integrated later
# For now, use stubs to prevent import errors
try:
    from ...memory_implementations import MemoryContext, MemoryContextMerger, MemoryPriority
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
        self._init_ai_clients()

        # Initialize memory context merger
        self.memory_merger = MemoryContextMerger(
            {"max_total_tokens": 4000, "merge_strategy": "priority", "token_buffer": 0.1}
        )

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for AI agent nodes."""
        if node_spec_registry and self._subtype:
            # Return the specific spec for current subtype
            return node_spec_registry.get_spec(NodeType.AI_AGENT.value, self._subtype)
        return None

    def _init_ai_clients(self):
        """Initialize AI provider clients."""
        try:
            # Initialize OpenAI client
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                self.ai_clients["openai"] = {"api_key": openai_key, "client": None}

            # Initialize Anthropic client
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if anthropic_key:
                self.ai_clients["anthropic"] = {
                    "api_key": anthropic_key,
                    "client": None,
                }

            # Initialize Google client
            google_key = os.getenv("GOOGLE_API_KEY")
            if google_key:
                self.ai_clients["google"] = {"api_key": google_key, "client": None}

        except Exception as e:
            self.logger.warning(f"Failed to initialize AI clients: {e}")

    def get_supported_subtypes(self) -> List[str]:
        """Get supported AI agent subtypes (provider-based)."""
        return [subtype.value for subtype in AIAgentSubtype]

    def validate(self, node: Any) -> List[str]:
        """Validate AI agent node configuration using spec-based validation."""
        # First use the base class validation which includes spec validation
        errors = super().validate(node)

        # If spec validation passed, we can skip manual validation
        if not errors and self.spec:
            return errors

        # Fallback to legacy validation if spec not available
        if not node.subtype:
            errors.append("AI Agent subtype is required")
            return errors

        subtype = node.subtype
        supported_subtypes = self.get_supported_subtypes()

        if subtype not in supported_subtypes:
            errors.append(
                f"Unsupported AI agent subtype: {subtype}. Supported types: {', '.join(supported_subtypes)}"
            )

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

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute AI agent node with provider-based architecture and memory integration."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype
            logs.append(f"🤖 AI AGENT: Starting {subtype} execution")
            logs.append(
                f"🤖 AI AGENT: Node ID: {getattr(context.node, 'id', 'unknown') if hasattr(context, 'node') else 'unknown'}"
            )
            logs.append(f"🤖 AI AGENT: Execution ID: {getattr(context, 'execution_id', 'unknown')}")

            # Log input data analysis
            if hasattr(context, "input_data") and context.input_data:
                logs.append(f"🤖 AI AGENT: Input data analysis:")
                if isinstance(context.input_data, dict):
                    for key, value in context.input_data.items():
                        if key == "memory_context":
                            logs.append(
                                f"🤖 AI AGENT:   📥 Found '{key}': {len(str(value))} characters"
                            )
                        elif isinstance(value, str) and len(value) > 100:
                            logs.append(
                                f"🤖 AI AGENT:   📥 Input '{key}': {value[:100]}... ({len(value)} chars)"
                            )
                        else:
                            logs.append(f"🤖 AI AGENT:   📥 Input '{key}': {value}")
                else:
                    logs.append(
                        f"🤖 AI AGENT:   📥 Input data (non-dict): {str(context.input_data)[:200]}..."
                    )
            else:
                logs.append("🤖 AI AGENT: No input data provided")

            # Process memory contexts if present
            memory_contexts = self._extract_memory_contexts(context)
            if memory_contexts:
                logs.append(
                    f"🤖 AI AGENT: 🧠 Memory integration detected - {len(memory_contexts)} contexts found"
                )
                for i, memory_context in enumerate(memory_contexts):
                    logs.append(
                        f"🤖 AI AGENT:   🧠 Context {i+1}: {len(str(memory_context))} characters"
                    )
                    if len(str(memory_context)) > 0:
                        preview = (
                            str(memory_context)[:150] + "..."
                            if len(str(memory_context)) > 150
                            else str(memory_context)
                        )
                        logs.append(f"🤖 AI AGENT:   🧠 Preview: {preview}")
            else:
                logs.append("🤖 AI AGENT: 🧠 No memory contexts detected")

            # Enhanced context with memory integration
            enhanced_context = self._enhance_context_with_memory(context, memory_contexts, logs)

            if subtype == AIAgentSubtype.GOOGLE_GEMINI.value:
                return self._execute_gemini_agent(enhanced_context, logs, start_time)
            elif subtype == AIAgentSubtype.OPENAI_CHATGPT.value:
                return self._execute_openai_agent(enhanced_context, logs, start_time)
            elif subtype == AIAgentSubtype.ANTHROPIC_CLAUDE.value:
                return self._execute_claude_agent(enhanced_context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported AI agent provider: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

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
                logs.append("🤖 AI AGENT: 🧠 No memory contexts to merge, using original context")
                return context

            logs.append(f"🤖 AI AGENT: 🧠 Starting memory context enhancement...")

            # Merge all memory contexts into a single context string
            merged_memory_context = "\n\n".join(memory_contexts)
            logs.append(
                f"🤖 AI AGENT: 🧠 Merged {len(memory_contexts)} contexts into {len(merged_memory_context)} characters"
            )

            # Create enhanced input data
            enhanced_input_data = context.input_data.copy() if context.input_data else {}
            original_keys = list(enhanced_input_data.keys()) if enhanced_input_data else []

            # Add merged memory context to input data
            enhanced_input_data["memory_context"] = merged_memory_context
            enhanced_input_data["has_memory_context"] = True

            logs.append(f"🤖 AI AGENT: 🧠 Enhanced input data:")
            logs.append(f"🤖 AI AGENT: 🧠   Original keys: {original_keys}")
            logs.append(
                f"🤖 AI AGENT: 🧠   Added 'memory_context' ({len(merged_memory_context)} chars)"
            )
            logs.append(f"🤖 AI AGENT: 🧠   Added 'has_memory_context': True")

            # Create new context with enhanced input
            enhanced_context = NodeExecutionContext(
                node=context.node,
                input_data=enhanced_input_data,
                workflow_id=getattr(context, "workflow_id", None),
                execution_id=getattr(context, "execution_id", None),
                credentials=getattr(context, "credentials", None),
            )

            logs.append("🤖 AI AGENT: 🧠 ✅ Context enhanced with memory data")
            return enhanced_context

        except Exception as e:
            logs.append(f"🤖 AI AGENT: 🧠 ❌ Memory enhancement failed: {e}")
            self.logger.warning(f"Memory enhancement error: {e}")

        # Return original context if memory enhancement fails or no memory contexts
        return context

    def _enhance_system_prompt_with_memory(
        self, base_prompt: str, input_data: Dict[str, Any], logs: List[str]
    ) -> str:
        """Enhance the system prompt with memory context using memory-type-specific injection logic."""
        try:
            logs.append("🤖 AI AGENT: 💭 Checking for memory context to inject into system prompt")

            if not input_data or not isinstance(input_data, dict):
                logs.append("🤖 AI AGENT: 💭 No input data available, using original system prompt")
                return base_prompt

            # Check if memory context is available
            if "memory_context" not in input_data:
                logs.append(
                    "🤖 AI AGENT: 💭 No 'memory_context' key found, using original system prompt"
                )
                return base_prompt

            memory_context = input_data["memory_context"]
            memory_type = input_data.get(
                "memory_type", "UNKNOWN"
            )  # Keep "UNKNOWN" as fallback for missing types

            if not memory_context:
                logs.append("🤖 AI AGENT: 💭 Memory context is empty, using original system prompt")
                return base_prompt

            logs.append(f"🤖 AI AGENT: 💭 ✅ Memory context found! Type: {memory_type}")
            logs.append(f"🤖 AI AGENT: 💭   Original prompt length: {len(base_prompt)} characters")
            logs.append(f"🤖 AI AGENT: 💭   Memory context length: {len(memory_context)} characters")

            # Show preview of memory context being injected
            memory_preview = (
                memory_context[:200] + "..." if len(memory_context) > 200 else memory_context
            )
            logs.append(f"🤖 AI AGENT: 💭   Memory context preview: {memory_preview}")

            # Memory-type-specific context injection
            enhanced_prompt = self._inject_memory_by_type(
                base_prompt, memory_context, memory_type, logs
            )

            logs.append(
                f"🤖 AI AGENT: 💭   Enhanced prompt length: {len(enhanced_prompt)} characters"
            )
            logs.append(
                f"🤖 AI AGENT: 💭   Added {len(enhanced_prompt) - len(base_prompt)} characters from memory"
            )
            logs.append("🤖 AI AGENT: 💭 🎯 System prompt successfully enhanced with memory context!")

            return enhanced_prompt

        except Exception as e:
            logs.append(f"🤖 AI AGENT: 💭 ❌ System prompt enhancement failed: {e}")
            self.logger.warning(f"System prompt enhancement error: {e}")
            return base_prompt

    def _inject_memory_by_type(
        self, base_prompt: str, memory_context: str, memory_type: str, logs: List[str]
    ) -> str:
        """Inject memory context using type-specific formatting and instructions."""
        from shared.models.node_enums import MemorySubtype

        logs.append(f"🤖 AI AGENT: 💭 🎯 Using {memory_type}-specific context injection")

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
            logs.append(
                f"🤖 AI AGENT: 💭 ⚠️ Unknown memory type '{memory_type}', using generic injection"
            )
            return f"""{base_prompt}

## Memory Context

You have access to relevant memory context that should inform your responses:

{memory_context}

Please use this context appropriately when responding. Reference relevant information from your memory when it's helpful, but don't force it into every response."""

    def _execute_gemini_agent(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute Gemini AI agent."""
        # Use spec-based parameter retrieval
        base_system_prompt = self.get_parameter_with_spec(context, "system_prompt")
        model_version = self.get_parameter_with_spec(context, "model_version")
        temperature = self.get_parameter_with_spec(context, "temperature")
        max_tokens = self.get_parameter_with_spec(context, "max_tokens")
        safety_settings = self.get_parameter_with_spec(context, "safety_settings")

        # Enhance system prompt with memory context if available
        system_prompt = self._enhance_system_prompt_with_memory(
            base_system_prompt, context.input_data, logs
        )

        logs.append(f"Gemini agent: {model_version}, temp: {temperature}")

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
        # Use spec-based parameter retrieval
        base_system_prompt = self.get_parameter_with_spec(context, "system_prompt")
        model_version = self.get_parameter_with_spec(context, "model_version")
        temperature = self.get_parameter_with_spec(context, "temperature")
        max_tokens = self.get_parameter_with_spec(context, "max_tokens")
        presence_penalty = self.get_parameter_with_spec(context, "presence_penalty")
        frequency_penalty = self.get_parameter_with_spec(context, "frequency_penalty")

        # Enhance system prompt with memory context if available
        system_prompt = self._enhance_system_prompt_with_memory(
            base_system_prompt, context.input_data, logs
        )

        logs.append(
            f"🤖 AI AGENT: OpenAI configuration - model: {model_version}, temp: {temperature}"
        )
        logs.append(f"🤖 AI AGENT: Final system prompt length: {len(system_prompt)} characters")

        # Show system prompt preview (first and last parts)
        if len(system_prompt) > 300:
            logs.append(
                f"🤖 AI AGENT: System prompt preview (first 150 chars): {system_prompt[:150]}..."
            )
            logs.append(
                f"🤖 AI AGENT: System prompt preview (last 150 chars): ...{system_prompt[-150:]}"
            )
        else:
            logs.append(f"🤖 AI AGENT: Full system prompt: {system_prompt}")

        # Prepare input for AI processing
        input_text = self._prepare_input_for_ai(context.input_data)
        logs.append(
            f"🤖 AI AGENT: User input prepared: '{input_text[:100]}{'...' if len(input_text) > 100 else ''}' ({len(input_text)} chars)"
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
        # Use spec-based parameter retrieval
        base_system_prompt = self.get_parameter_with_spec(context, "system_prompt")
        model_version = self.get_parameter_with_spec(context, "model_version")
        temperature = self.get_parameter_with_spec(context, "temperature")
        max_tokens = self.get_parameter_with_spec(context, "max_tokens")
        stop_sequences = self.get_parameter_with_spec(context, "stop_sequences")

        # Enhance system prompt with memory context if available
        system_prompt = self._enhance_system_prompt_with_memory(
            base_system_prompt, context.input_data, logs
        )

        logs.append(f"Claude agent: {model_version}, temp: {temperature}")

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
                self.logger.info(f"🎯 Extracted standard format content: {content}")
                return str(content)

            # Legacy support: Check for direct message/text fields
            if "message" in input_data:
                message_content = input_data["message"]
                self.logger.info(f"🎯 Extracted legacy message field: {message_content}")
                return str(message_content)

            if "text" in input_data:
                text_content = input_data["text"]
                self.logger.info(f"🎯 Extracted legacy text field: {text_content}")
                return str(text_content)

            # Legacy support: Check for trigger payload structures
            if "payload" in input_data:
                payload = input_data["payload"]
                if isinstance(payload, dict):
                    # Slack message event
                    if "event" in payload and "text" in payload["event"]:
                        slack_text = payload["event"]["text"]
                        self.logger.info(f"🎯 Extracted legacy Slack message: {slack_text}")
                        return slack_text

                    # Direct text field in payload
                    elif "text" in payload:
                        text_content = payload["text"]
                        self.logger.info(f"🎯 Extracted legacy payload text: {text_content}")
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
        if not ai_response:
            return ""

        try:
            # Try to parse as JSON
            if isinstance(ai_response, str) and ai_response.strip().startswith("{"):
                import json

                data = json.loads(ai_response)

                # Extract response content from common JSON structures
                if "response" in data:
                    response_content = data["response"]
                    # If the response is still JSON, try to extract further
                    if isinstance(response_content, str) and response_content.strip().startswith(
                        "{"
                    ):
                        try:
                            inner_data = json.loads(response_content)
                            if "response" in inner_data:
                                return inner_data["response"]
                        except:
                            pass
                    return response_content
                elif "content" in data:
                    return data["content"]
                elif "text" in data:
                    return data["text"]
                elif "message" in data:
                    return data["message"]
                else:
                    # If no known key, return the first string value found
                    for value in data.values():
                        if isinstance(value, str):
                            return value
        except json.JSONDecodeError:
            pass
        except Exception:
            pass

        # If not JSON or no extractable content, return as-is
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
        try:
            import google.generativeai as genai

            # Configure with API key (use GEMINI_API_KEY as suggested)
            gemini_key = os.getenv("GEMINI_API_KEY")
            if not gemini_key:
                raise ValueError(
                    "GEMINI_API_KEY not found in environment - Gemini integration not configured in AWS infrastructure"
                )

            genai.configure(api_key=gemini_key)

            # Create model instance
            model_instance = genai.GenerativeModel(model)

            # Combine system prompt and input
            full_prompt = f"{system_prompt}\n\nInput: {input_text}"

            # Make API call
            response = model_instance.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature, max_output_tokens=max_tokens
                ),
            )

            return response.text

        except Exception as e:
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
        try:
            from openai import OpenAI

            # Get API key
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                raise ValueError("OPENAI_API_KEY not found in environment")

            # Create client
            client = OpenAI(api_key=openai_key)

            # Make API call
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

            return response.choices[0].message.content

        except Exception as e:
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
        try:
            import anthropic

            # Get API key
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")

            # Create client
            client = anthropic.Anthropic(api_key=anthropic_key)

            # Make API call
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": input_text}],
                stop_sequences=stop_sequences if stop_sequences else None,
            )

            return response.content[0].text

        except Exception as e:
            self.logger.error(f"Claude API call failed: {e}")
            # Return user-friendly error message
            if "api key" in str(e).lower():
                return f"⚠️ Anthropic API key is invalid or missing"
            elif "rate limit" in str(e).lower():
                return f"⚠️ Anthropic API rate limit exceeded. Please try again later."
            else:
                return f"⚠️ Anthropic Claude API error: {str(e)}"
