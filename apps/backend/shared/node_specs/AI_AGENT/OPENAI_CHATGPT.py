"""
OPENAI_CHATGPT AI Agent Node Specification

OpenAI ChatGPT AI agent with customizable behavior via system prompt.
Supports function calling via attached TOOL nodes and memory context via MEMORY nodes.
"""

from typing import Any, Dict, List

from shared.models.node_enums import AIAgentSubtype, NodeType, OpenAIModel
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


class OpenAIChatGPTSpec(BaseNodeSpec):
    """OpenAI ChatGPT AI agent specification aligned with OpenAI API."""

    def __init__(self):
        super().__init__(
            type=NodeType.AI_AGENT,
            subtype=AIAgentSubtype.OPENAI_CHATGPT,
            name="OpenAI_ChatGPT",
            description="OpenAI ChatGPT AI agent with customizable behavior via system prompt.",
            # Configuration parameters (OpenAI-native only)
            configurations={
                "model": {
                    "type": "string",
                    "default": OpenAIModel.GPT_5_NANO.value,
                    "description": "OpenAI model version",
                    "required": True,
                    "options": [model.value for model in OpenAIModel],
                },
                "system_prompt": {
                    "type": "string",
                    "default": "You are a helpful AI assistant. Analyze the input and provide a clear, accurate response.",
                    "description": "System prompt defining AI behavior and role",
                    "required": True,
                    "multiline": True,
                },
                "temperature": {
                    "type": "float",
                    "default": 0.7,
                    "min": 0.0,
                    "max": 2.0,
                    "description": "Controls randomness of outputs",
                    "required": False,
                },
                "max_tokens": {
                    "type": "integer",
                    "default": 8192,
                    "description": "Maximum number of tokens in response",
                    "required": False,
                },
                "top_p": {
                    "type": "float",
                    "default": 1.0,
                    "min": 0.0,
                    "max": 1.0,
                    "description": "Nucleus sampling probability",
                    "required": False,
                },
                "frequency_penalty": {
                    "type": "float",
                    "default": 0.0,
                    "min": -2.0,
                    "max": 2.0,
                    "description": "Penalize repeated tokens",
                    "required": False,
                },
                "presence_penalty": {
                    "type": "float",
                    "default": 0.0,
                    "min": -2.0,
                    "max": 2.0,
                    "description": "Encourage new topics",
                    "required": False,
                },
                "response_format": {
                    "type": "string",
                    "default": "text",
                    "description": "Desired response format",
                    "required": False,
                    "options": ["text", "json", "schema"],
                },
                # Shared configs (timeouts, retries, logging, etc.)
                **COMMON_CONFIGS,
            },
            # Parameter schemas
            input_params={
                "user_prompt": {
                    "type": "string",
                    "default": "",
                    "description": "Primary user message or prompt input",
                    "required": True,
                }
            },
            output_params={
                "content": {
                    "type": "string",
                    "default": "",
                    "description": "Model response content",
                    "required": False,
                },
                "metadata": {
                    "type": "object",
                    "default": {},
                    "description": "Additional metadata returned with the response",
                    "required": False,
                },
                "format_type": {
                    "type": "string",
                    "default": "",
                    "description": "Actual response format for the content",
                    "required": False,
                    "options": ["text", "json", "schema"],
                },
                "source_node": {
                    "type": "string",
                    "default": "",
                    "description": "Source node identifier for tracing",
                    "required": False,
                },
                "timestamp": {
                    "type": "string",
                    "default": "",
                    "description": "ISO-8601 timestamp when the response was generated",
                    "required": False,
                },
                "token_usage": {
                    "type": "object",
                    "default": {},
                    "description": "Token usage statistics (input/output/total)",
                    "required": False,
                },
                "function_calls": {
                    "type": "array",
                    "default": [],
                    "description": "List of function/tool calls invoked by the model",
                    "required": False,
                },
            },
            # Port definitions
            input_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "Input data for AI processing",
                    "required": True,
                    "max_connections": -1,
                }
            ],
            output_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "AI agent response output",
                    "required": True,
                    "max_connections": -1,
                }
            ],
            tags=["ai", "openai", "chatgpt", "language-model", "function-calling"],
            examples=[
                {
                    "name": "Sentiment & Insight Extraction",
                    "description": "Analyze customer feedback for sentiment, key themes, and recommendations.",
                    "configurations": {
                        "model": OpenAIModel.GPT_5_NANO.value,
                        "system_prompt": (
                            "You are a text analysis expert. Analyze the text for sentiment, "
                            "themes, and actionable insights. Output JSON with fields: "
                            "'sentiment', 'score', 'themes', 'recommendations'."
                        ),
                        "temperature": 0.3,
                        "response_format": "json",
                    },
                    "input_example": {
                        "message": "The new UI looks great, but it's still a bit slow to load.",
                        "context": {"product": "mobile_app"},
                    },
                    "expected_output": {
                        "content": '{"sentiment": "mixed", "score": 0.65, "themes": ["UI design", "performance"], "recommendations": ["Optimize loading speed"]}',
                        "metadata": {"model": "gpt-5", "tokens": 124},
                        "format_type": "json",
                        "source_node": "sentiment_analysis_ai",
                        "timestamp": "2025-01-28T12:00:00Z",
                    },
                }
            ],
        )


# Export the specification instance
OPENAI_CHATGPT_SPEC = OpenAIChatGPTSpec()
