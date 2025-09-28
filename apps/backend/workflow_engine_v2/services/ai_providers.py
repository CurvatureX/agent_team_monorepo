"""AI provider registry for v2 engine.

This is an extensible shim; real integrations (OpenAI/Anthropic/Gemini) can be
added here. For now, include EchoProvider and a simple registry.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx


class AIProvider:
    def generate(
        self, prompt: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError


class EchoProvider(AIProvider):
    def generate(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "prompt": prompt,
            "response": prompt,
            "model": params.get("model", "echo"),
            "params": params,
        }


_registry: Dict[str, AIProvider] = {
    "echo": EchoProvider(),
}


def get_ai_provider(name: str) -> AIProvider:
    return _registry.get(name, _registry["echo"])


def register_ai_provider(name: str, provider: AIProvider) -> None:
    _registry[name] = provider


class OpenAIProvider(AIProvider):
    def __init__(
        self, api_key: Optional[str] = None, base_url: str = "https://api.openai.com/v1"
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._base = base_url.rstrip("/")

    def generate(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        api_key = (
            params.get("api_key") or (params.get("auth") or {}).get("api_key") or self._api_key
        )
        if not api_key:
            raise ValueError("OPENAI_API_KEY not provided")
        model = params.get("model") or "gpt-4o-mini"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": params.get("system_prompt", "You are a helpful assistant."),
                },
                {"role": "user", "content": prompt},
            ],
        }
        timeout = float(params.get("timeout_seconds", 30))
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{self._base}/chat/completions", headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            content = ""
            try:
                content = data["choices"][0]["message"]["content"]
            except Exception:
                content = str(data)
            usage = data.get("usage", {})
            return {
                "prompt": prompt,
                "response": content,
                "model": model,
                "provider": "openai",
                "raw": data,
                "usage": usage,
            }


class AnthropicProvider(AIProvider):
    """Real Anthropic Claude API integration."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    def generate(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        api_key = (
            params.get("api_key") or (params.get("auth") or {}).get("api_key") or self._api_key
        )
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not provided")

        model = params.get("model") or "claude-3-5-haiku-20241022"
        max_tokens = int(params.get("max_tokens", 1024))
        temperature = float(params.get("temperature", 0.7))

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        # Handle available functions for tool use
        tools = None
        available_functions = params.get("available_functions")
        if available_functions:
            tools = []
            for func_name, func_info in available_functions.items():
                tool_def = {
                    "name": func_name,
                    "description": func_info.get("description", f"Execute {func_name}"),
                    "input_schema": func_info.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                }
                tools.append(tool_def)

        body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        if tools:
            body["tools"] = tools

        timeout = float(params.get("timeout_seconds", 30))

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(
                    "https://api.anthropic.com/v1/messages", headers=headers, json=body
                )
                resp.raise_for_status()
                data = resp.json()

                # Extract response content
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

                usage = data.get("usage", {})
                result = {
                    "prompt": prompt,
                    "response": content,
                    "model": model,
                    "provider": "anthropic",
                    "raw": data,
                    "usage": {
                        "input_tokens": usage.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                    },
                }

                if tool_calls:
                    result["tool_calls"] = tool_calls

                return result

        except httpx.HTTPStatusError as e:
            raise ValueError(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise ValueError(f"Anthropic API request failed: {str(e)}")


class GeminiProvider(AIProvider):
    """Real Google Gemini API integration."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    def generate(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        api_key = (
            params.get("api_key") or (params.get("auth") or {}).get("api_key") or self._api_key
        )
        if not api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not provided")

        model = params.get("model") or "gemini-1.5-flash"
        temperature = float(params.get("temperature", 0.7))
        max_tokens = int(params.get("max_tokens", 1024))

        # Handle available functions for tool use
        tools = None
        available_functions = params.get("available_functions")
        if available_functions:
            tools = []
            for func_name, func_info in available_functions.items():
                function_declaration = {
                    "name": func_name,
                    "description": func_info.get("description", f"Execute {func_name}"),
                    "parameters": func_info.get("parameters", {"type": "object", "properties": {}}),
                }
                tools.append({"function_declarations": [function_declaration]})

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if tools:
            body["tools"] = tools

        timeout = float(params.get("timeout_seconds", 30))

        try:
            with httpx.Client(timeout=timeout) as client:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                resp = client.post(url, json=body)
                resp.raise_for_status()
                data = resp.json()

                # Extract response content
                content = ""
                tool_calls = []

                if "candidates" in data and data["candidates"]:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        for part in candidate["content"]["parts"]:
                            if "text" in part:
                                content += part["text"]
                            elif "functionCall" in part:
                                tool_calls.append(
                                    {
                                        "name": part["functionCall"].get("name"),
                                        "args": part["functionCall"].get("args", {}),
                                    }
                                )

                # Extract usage information
                usage_metadata = data.get("usageMetadata", {})
                usage = {
                    "input_tokens": usage_metadata.get("promptTokenCount", 0),
                    "output_tokens": usage_metadata.get("candidatesTokenCount", 0),
                }

                result = {
                    "prompt": prompt,
                    "response": content,
                    "model": model,
                    "provider": "gemini",
                    "raw": data,
                    "usage": usage,
                }

                if tool_calls:
                    result["tool_calls"] = tool_calls

                return result

        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                error_message = error_data.get("error", {}).get("message", e.response.text)
            except:
                error_message = e.response.text
            raise ValueError(f"Gemini API error: {e.response.status_code} - {error_message}")
        except Exception as e:
            raise ValueError(f"Gemini API request failed: {str(e)}")


# Register default providers
register_ai_provider("openai", OpenAIProvider())
register_ai_provider("anthropic", AnthropicProvider())
register_ai_provider("gemini", GeminiProvider())


__all__ = [
    "AIProvider",
    "EchoProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "get_ai_provider",
    "register_ai_provider",
]
