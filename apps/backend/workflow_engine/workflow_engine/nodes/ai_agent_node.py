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

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult


class AIAgentNodeExecutor(BaseNodeExecutor):
    """Executor for AI_AGENT_NODE type with provider-based architecture."""

    def __init__(self):
        super().__init__()
        self.ai_clients = {}
        self._init_ai_clients()

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
                self.ai_clients["anthropic"] = {"api_key": anthropic_key, "client": None}

            # Initialize Google client
            google_key = os.getenv("GOOGLE_API_KEY")
            if google_key:
                self.ai_clients["google"] = {"api_key": google_key, "client": None}

        except Exception as e:
            self.logger.warning(f"Failed to initialize AI clients: {e}")

    def get_supported_subtypes(self) -> List[str]:
        """Get supported AI agent subtypes (provider-based)."""
        return [
            "GEMINI_NODE",  # Google Gemini
            "OPENAI_NODE",  # OpenAI GPT
            "CLAUDE_NODE",  # Anthropic Claude
        ]

    def validate(self, node: Any) -> List[str]:
        """Validate AI agent node configuration for provider-based architecture."""
        errors = []

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

        # Validate required parameters for all provider-based nodes
        errors.extend(self._validate_required_parameters(node, ["system_prompt"]))

        # Validate model_version if provided
        model_version = node.parameters.get("model_version")
        if model_version:
            valid_models = self._get_valid_models_for_provider(subtype)
            if valid_models and model_version not in valid_models:
                errors.append(
                    f"Invalid model version '{model_version}' for {subtype}. Valid models: {', '.join(valid_models)}"
                )

        # Validate provider-specific parameters
        errors.extend(self._validate_provider_specific_parameters(node, subtype))

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute AI agent node with provider-based architecture."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype
            logs.append(f"Executing AI agent node with provider: {subtype}")

            if subtype == "GEMINI_NODE":
                return self._execute_gemini_agent(context, logs, start_time)
            elif subtype == "OPENAI_NODE":
                return self._execute_openai_agent(context, logs, start_time)
            elif subtype == "CLAUDE_NODE":
                return self._execute_claude_agent(context, logs, start_time)
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

    def _execute_gemini_agent(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute Gemini AI agent."""
        system_prompt = context.get_parameter("system_prompt")
        model_version = context.get_parameter("model_version", "gemini-pro")
        temperature = context.get_parameter("temperature", 0.7)
        max_tokens = context.get_parameter("max_tokens", 1000)
        safety_settings = context.get_parameter("safety_settings", {})

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

            output_data = {
                "provider": "gemini",
                "model": model_version,
                "system_prompt": system_prompt,
                "input_text": input_text,
                "ai_response": ai_response,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "safety_settings": safety_settings,
                "executed_at": datetime.now().isoformat(),
            }

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
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
        system_prompt = context.get_parameter("system_prompt")
        model_version = context.get_parameter("model_version", "gpt-4")
        temperature = context.get_parameter("temperature", 0.7)
        max_tokens = context.get_parameter("max_tokens", 1000)
        presence_penalty = context.get_parameter("presence_penalty", 0.0)
        frequency_penalty = context.get_parameter("frequency_penalty", 0.0)

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

            output_data = {
                "provider": "openai",
                "model": model_version,
                "system_prompt": system_prompt,
                "input_text": input_text,
                "ai_response": ai_response,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "presence_penalty": presence_penalty,
                "frequency_penalty": frequency_penalty,
                "executed_at": datetime.now().isoformat(),
            }

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
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
        system_prompt = context.get_parameter("system_prompt")
        model_version = context.get_parameter("model_version", "claude-3-sonnet")
        temperature = context.get_parameter("temperature", 0.7)
        max_tokens = context.get_parameter("max_tokens", 1000)
        stop_sequences = context.get_parameter("stop_sequences", [])

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

            output_data = {
                "provider": "claude",
                "model": model_version,
                "system_prompt": system_prompt,
                "input_text": input_text,
                "ai_response": ai_response,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stop_sequences": stop_sequences,
                "executed_at": datetime.now().isoformat(),
            }

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
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
            "GEMINI_NODE": ["gemini-pro", "gemini-pro-vision", "gemini-ultra"],
            "OPENAI_NODE": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4-vision-preview"],
            "CLAUDE_NODE": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku", "claude-2.1"],
        }
        return models.get(provider, [])

    def _validate_provider_specific_parameters(self, node: Any, provider: str) -> List[str]:
        """Validate provider-specific parameters."""
        errors = []

        if provider == "GEMINI_NODE":
            # Validate safety_settings format if provided
            safety_settings = node.parameters.get("safety_settings")
            if safety_settings and not isinstance(safety_settings, dict):
                errors.append("safety_settings must be a dictionary")

        elif provider == "OPENAI_NODE":
            # Validate penalty values
            for penalty in ["presence_penalty", "frequency_penalty"]:
                value = node.parameters.get(penalty)
                if value is not None and not (-2.0 <= value <= 2.0):
                    errors.append(f"{penalty} must be between -2.0 and 2.0")

        elif provider == "CLAUDE_NODE":
            # Validate stop_sequences format if provided
            stop_sequences = node.parameters.get("stop_sequences")
            if stop_sequences and not isinstance(stop_sequences, list):
                errors.append("stop_sequences must be a list")

        return errors

    def _prepare_input_for_ai(self, input_data: Dict[str, Any]) -> str:
        """Prepare input data for AI processing."""
        if isinstance(input_data, str):
            return input_data

        # Convert dict to structured text
        if isinstance(input_data, dict):
            return json.dumps(input_data, indent=2, ensure_ascii=False)

        return str(input_data)

    def _call_gemini_api(
        self,
        system_prompt: str,
        input_text: str,
        model: str,
        temperature: float,
        max_tokens: int,
        safety_settings: Dict,
    ) -> str:
        """Call Gemini API (mock implementation)."""
        # TODO: Replace with actual Gemini API call
        return (
            f'{{"response": "Mock Gemini response for: {input_text[:50]}...", "model": "{model}"}}'
        )

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
        """Call OpenAI API (mock implementation)."""
        # TODO: Replace with actual OpenAI API call
        return (
            f'{{"response": "Mock OpenAI response for: {input_text[:50]}...", "model": "{model}"}}'
        )

    def _call_claude_api(
        self,
        system_prompt: str,
        input_text: str,
        model: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: List[str],
    ) -> str:
        """Call Claude API (mock implementation)."""
        # TODO: Replace with actual Claude API call
        return (
            f'{{"response": "Mock Claude response for: {input_text[:50]}...", "model": "{model}"}}'
        )
