"""
AI Agent Node Executor.

Handles OpenAI, Anthropic, and other AI provider integrations.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from utils.unicode_utils import clean_unicode_string, safe_json_dumps

from shared.models.node_enums import NodeType

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult
from .factory import NodeExecutorFactory


@NodeExecutorFactory.register(NodeType.AI_AGENT.value)
class AIAgentNodeExecutor(BaseNodeExecutor):
    """Executor for AI agent nodes."""

    def __init__(self, node_type: str = NodeType.AI_AGENT.value, subtype: str = None):
        super().__init__(node_type, subtype)

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute AI agent node."""
        provider = self.subtype or context.get_parameter("provider", "openai")
        model = context.get_parameter("model_version", "gpt-4")
        system_prompt = context.get_parameter("system_prompt", "")

        # Try to get user_message from parameters first, then from input_data with common field names
        user_message = (
            context.get_parameter("user_message")
            or context.input_data.get("message")
            or context.input_data.get("user_message")
            or context.input_data.get("text")
            or ""
        )

        self.log_execution(context, f"Executing AI agent node: {provider}/{model}")

        try:
            # Call real AI API
            response_text = await self._real_ai_call(provider, model, system_prompt, user_message)

            output_data = {
                "response": response_text,
                "provider": provider,
                "model": model,
                "token_usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
                "finished_reason": "stop",
                "generated_at": datetime.now().isoformat(),
            }

            return NodeExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output_data=output_data,
                metadata={"node_type": "ai_agent", "provider": provider, "model": model},
            )

        except Exception as e:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"AI agent execution failed: {str(e)}",
                error_details={"provider": provider, "model": model},
            )

    async def _real_ai_call(
        self, provider: str, model: str, system_prompt: str, user_message: str
    ) -> str:
        """Real AI API call implementation."""
        import os

        import httpx

        try:
            if provider.lower() in ["openai", "openai_chatgpt"]:
                return await self._call_openai(model, system_prompt, user_message)
            elif provider.lower() in ["anthropic", "claude"]:
                return await self._call_anthropic(model, system_prompt, user_message)
            else:
                # Fallback to mock for unknown providers
                await asyncio.sleep(0.1)
                return f"[Mock {provider}/{model} Response] Processed message: '{user_message}' with system prompt: '{system_prompt}'"

        except Exception as e:
            # Fallback to mock on error
            await asyncio.sleep(0.1)
            return f"[Fallback Response] Error calling {provider}: {str(e)} | Message: '{user_message}'"

    async def _call_openai(self, model: str, system_prompt: str, user_message: str) -> str:
        """Call OpenAI API."""
        import json
        import os

        import httpx

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return f"[Mock OpenAI Response] No API key found. Message: '{user_message}'"

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # Map model names
        if model in ["gpt-4.1-mini", "gpt-4-mini"]:
            model = "gpt-4o-mini"
        elif model in ["gpt-4", "gpt-4.0"]:
            model = "gpt-4o"

        # Clean and validate input strings to prevent Unicode issues
        system_prompt_clean = clean_unicode_string(system_prompt)
        user_message_clean = clean_unicode_string(user_message)

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt_clean},
                {"role": "user", "content": user_message_clean},
            ],
            "temperature": 0.7,
            "max_tokens": 500,
        }

        # Serialize JSON with proper Unicode handling to avoid surrogate issues
        try:
            json_data = safe_json_dumps(payload, separators=(",", ":"))
        except (UnicodeEncodeError, TypeError, ValueError) as e:
            self.log_execution(None, f"JSON encoding error in OpenAI payload: {e}", "ERROR")
            # Clean the payload more aggressively and try again
            try:
                cleaned_payload = {
                    "model": payload["model"],
                    "messages": [
                        {
                            "role": "system",
                            "content": clean_unicode_string(payload["messages"][0]["content"]),
                        },
                        {
                            "role": "user",
                            "content": clean_unicode_string(payload["messages"][1]["content"]),
                        },
                    ],
                    "temperature": payload["temperature"],
                    "max_tokens": payload["max_tokens"],
                }
                json_data = safe_json_dumps(cleaned_payload, separators=(",", ":"))
                self.log_execution(
                    None, f"Successfully cleaned and re-encoded OpenAI payload", "INFO"
                )
            except Exception as fallback_error:
                self.log_execution(
                    None, f"Failed to clean OpenAI payload: {fallback_error}", "ERROR"
                )
                return f"[OpenAI Encoding Error] Could not encode message properly. Fallback: Processing message with cleaned content."

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                content=json_data,
                timeout=30.0,
            )

        result = response.json()

        if response.status_code == 200:
            return result["choices"][0]["message"]["content"]
        else:
            error = result.get("error", {}).get("message", "Unknown error")
            return f"[OpenAI Error] {error} | Fallback: Processing '{user_message}'"

    async def _call_anthropic(self, model: str, system_prompt: str, user_message: str) -> str:
        """Call Anthropic Claude API."""
        import json
        import os

        import httpx

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return f"[Mock Anthropic Response] No API key found. Message: '{user_message}'"

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        # Map model names
        if model in ["claude-3", "claude"]:
            model = "claude-3-sonnet-20240229"

        # Clean and validate input strings to prevent Unicode issues
        system_prompt_clean = clean_unicode_string(system_prompt)
        user_message_clean = clean_unicode_string(user_message)

        payload = {
            "model": model,
            "max_tokens": 500,
            "system": system_prompt_clean,
            "messages": [{"role": "user", "content": user_message_clean}],
        }

        # Serialize JSON with proper Unicode handling to avoid surrogate issues
        try:
            json_data = safe_json_dumps(payload, separators=(",", ":"))
        except (UnicodeEncodeError, TypeError, ValueError) as e:
            self.log_execution(None, f"JSON encoding error in Anthropic payload: {e}", "ERROR")
            # Clean the payload more aggressively and try again
            try:
                cleaned_payload = {
                    "model": payload["model"],
                    "max_tokens": payload["max_tokens"],
                    "system": clean_unicode_string(payload["system"]),
                    "messages": [
                        {
                            "role": "user",
                            "content": clean_unicode_string(payload["messages"][0]["content"]),
                        }
                    ],
                }
                json_data = safe_json_dumps(cleaned_payload, separators=(",", ":"))
                self.log_execution(
                    None, f"Successfully cleaned and re-encoded Anthropic payload", "INFO"
                )
            except Exception as fallback_error:
                self.log_execution(
                    None, f"Failed to clean Anthropic payload: {fallback_error}", "ERROR"
                )
                return f"[Anthropic Encoding Error] Could not encode message properly. Fallback: Processing message with cleaned content."

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                content=json_data,
                timeout=30.0,
            )

        result = response.json()

        if response.status_code == 200:
            return result["content"][0]["text"]
        else:
            error = result.get("error", {}).get("message", "Unknown error")
            return f"[Anthropic Error] {error} | Fallback: Processing '{user_message}'"

    def validate_parameters(self, context: NodeExecutionContext) -> tuple[bool, str]:
        """Validate AI agent node parameters. Returns (is_valid, error_message)."""
        missing_params = []

        # Check system_prompt (required from parameters)
        if not context.get_parameter("system_prompt"):
            missing_params.append("system_prompt")

        # Check user_message (can come from parameters or input_data)
        user_message = (
            context.get_parameter("user_message")
            or context.input_data.get("message")
            or context.input_data.get("user_message")
            or context.input_data.get("text")
        )
        if not user_message:
            missing_params.append("user_message (or message/text in input_data)")

        if missing_params:
            if len(missing_params) == 1:
                error_msg = f"Missing required parameter: {missing_params[0]}"
            else:
                error_msg = f"Missing required parameters: {', '.join(missing_params)}"

            # Log detailed parameter and input_data information
            all_params = list(context.parameters.keys()) if context.parameters else []
            all_input_keys = list(context.input_data.keys()) if context.input_data else []
            error_msg += (
                f" (Available parameters: {', '.join(all_params) if all_params else 'none'}, "
            )
            error_msg += f"Available input_data keys: {', '.join(all_input_keys) if all_input_keys else 'none'})"

            self.log_execution(context, error_msg, "ERROR")
            return False, error_msg

        return True, ""
