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
from workflow_engine.memory_implementations import (
    MemoryContext,
    MemoryContextMerger,
    MemoryPriority,
)

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
            logs.append(f"Executing AI agent node with provider: {subtype}")

            # Process memory contexts if present
            memory_contexts = self._extract_memory_contexts(context)
            if memory_contexts:
                logs.append(f"Found {len(memory_contexts)} memory contexts")
                for memory_context in memory_contexts:
                    logs.append(
                        f"  - {memory_context.memory_type}: {memory_context.estimated_tokens} tokens (priority: {memory_context.priority})"
                    )

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

    def _extract_memory_contexts(self, context: NodeExecutionContext) -> List[MemoryContext]:
        """Extract memory contexts from input connections."""
        memory_contexts = []

        try:
            # Check if there are memory input connections
            if hasattr(context, "input_connections") and context.input_connections:
                for connection in context.input_connections:
                    # Look for MEMORY connection type
                    if (
                        hasattr(connection, "connection_type")
                        and connection.connection_type == ConnectionType.MEMORY
                    ):
                        # Extract memory context data
                        connection_data = getattr(connection, "data", {})

                        if isinstance(connection_data, dict):
                            memory_type = connection_data.get("memory_type", "unknown")
                            context_data = connection_data.get("context", {})
                            priority = connection_data.get("priority", 0.5)
                            estimated_tokens = connection_data.get("estimated_tokens", 0)
                            source_node_id = connection_data.get("source_node_id")

                            memory_context = MemoryContext(
                                memory_type=memory_type,
                                context=context_data,
                                priority=priority,
                                estimated_tokens=estimated_tokens,
                                source_node_id=source_node_id,
                            )
                            memory_contexts.append(memory_context)

            # Also check context.input_data for memory contexts (fallback)
            elif hasattr(context, "input_data") and isinstance(context.input_data, dict):
                memory_data = context.input_data.get("memory_contexts", [])
                if isinstance(memory_data, list):
                    for mem_data in memory_data:
                        if isinstance(mem_data, dict):
                            memory_context = self.memory_merger.create_memory_context(
                                memory_type=mem_data.get("memory_type", "unknown"),
                                context_data=mem_data.get("context", {}),
                                priority=mem_data.get("priority"),
                                source_node_id=mem_data.get("source_node_id"),
                            )
                            memory_contexts.append(memory_context)

        except Exception as e:
            self.logger.warning(f"Error extracting memory contexts: {e}")

        return memory_contexts

    def _enhance_context_with_memory(
        self, context: NodeExecutionContext, memory_contexts: List[MemoryContext], logs: List[str]
    ) -> NodeExecutionContext:
        """Enhance the execution context with merged memory contexts."""
        try:
            # Extract the user message from input data
            user_message = self._prepare_input_for_ai(context.input_data)

            # Merge memory contexts if available
            if memory_contexts:
                merge_result = self.memory_merger.merge_contexts(memory_contexts, user_message)

                logs.append(
                    f"Memory merge: {merge_result['contexts_included']} included, "
                    f"{merge_result['contexts_dropped']} dropped"
                )
                logs.append(f"Total tokens: {merge_result['total_estimated_tokens']}")

                # Create enhanced input data
                enhanced_input_data = context.input_data.copy() if context.input_data else {}

                # Add merged memory context to input data
                enhanced_input_data["memory_context"] = merge_result["merged_context"]
                enhanced_input_data["memory_summary"] = merge_result["memory_summary"]
                enhanced_input_data["original_message"] = user_message

                # Create new context with enhanced input
                enhanced_context = NodeExecutionContext(
                    node=context.node,
                    input_data=enhanced_input_data,
                    workflow_id=getattr(context, "workflow_id", None),
                    execution_id=getattr(context, "execution_id", None),
                    credentials=getattr(context, "credentials", None),
                    input_connections=getattr(context, "input_connections", None),
                )

                return enhanced_context

        except Exception as e:
            logs.append(f"Warning: Memory enhancement failed: {e}")
            self.logger.warning(f"Memory enhancement error: {e}")

        # Return original context if memory enhancement fails or no memory contexts
        return context

    def _execute_gemini_agent(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute Gemini AI agent."""
        # Use spec-based parameter retrieval
        system_prompt = self.get_parameter_with_spec(context, "system_prompt")
        model_version = self.get_parameter_with_spec(context, "model_version")
        temperature = self.get_parameter_with_spec(context, "temperature")
        max_tokens = self.get_parameter_with_spec(context, "max_tokens")
        safety_settings = self.get_parameter_with_spec(context, "safety_settings")

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
        system_prompt = self.get_parameter_with_spec(context, "system_prompt")
        model_version = self.get_parameter_with_spec(context, "model_version")
        temperature = self.get_parameter_with_spec(context, "temperature")
        max_tokens = self.get_parameter_with_spec(context, "max_tokens")
        presence_penalty = self.get_parameter_with_spec(context, "presence_penalty")
        frequency_penalty = self.get_parameter_with_spec(context, "frequency_penalty")

        logs.append(f"OpenAI agent: {model_version}, temp: {temperature}")

        # Prepare input for AI processing
        input_text = self._prepare_input_for_ai(context.input_data)

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
        system_prompt = self.get_parameter_with_spec(context, "system_prompt")
        model_version = self.get_parameter_with_spec(context, "model_version")
        temperature = self.get_parameter_with_spec(context, "temperature")
        max_tokens = self.get_parameter_with_spec(context, "max_tokens")
        stop_sequences = self.get_parameter_with_spec(context, "stop_sequences")

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
            if "memory_context" in input_data and "original_message" in input_data:
                memory_context = input_data["memory_context"]
                original_message = input_data["original_message"]

                # Combine memory context with user message
                enhanced_input = f"""Context from memory:
{memory_context}

Current user message:
{original_message}"""

                self.logger.info(
                    f"🧠 Enhanced input with memory context (memory: {len(memory_context)} chars)"
                )
                return enhanced_input

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
