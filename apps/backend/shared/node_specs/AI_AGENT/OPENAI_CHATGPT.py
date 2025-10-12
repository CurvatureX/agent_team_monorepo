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
                    "default": """You are a helpful AI assistant. Analyze the input and provide a clear, accurate response.

OUTPUT FORMAT REQUIREMENT:
Return ONLY valid JSON. No explanations, no markdown, no code fences.
The output must start with `{` and end with `}`.

Your JSON response should contain the results of your analysis in a structured format.""",
                    "description": "System prompt defining AI behavior and role. Must enforce JSON output format when connecting to downstream nodes.",
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
                    "type": "object",
                    "default": {},
                    "description": "AI model JSON response containing structured data that matches the input parameters of downstream connected nodes. The AI is instructed to produce a JSON object with fields matching the exact parameter names expected by connected nodes (e.g., {'instruction': '...', 'context': {...}} for Notion append action). This enables direct data flow without complex conversion functions.",
                    "required": True,
                },
                "metadata": {
                    "type": "object",
                    "default": {},
                    "description": "Additional metadata returned with the response (model version, stop reason, etc.)",
                    "required": False,
                },
                "token_usage": {
                    "type": "object",
                    "default": {},
                    "description": "Token usage statistics (input_tokens, output_tokens, total_tokens)",
                    "required": False,
                },
                "function_calls": {
                    "type": "array",
                    "default": [],
                    "description": "List of function/tool calls invoked by the model during execution",
                    "required": False,
                },
            },
            tags=["ai", "openai", "chatgpt", "language-model", "function-calling"],
            examples=[
                {
                    "name": "Sentiment & Insight Extraction",
                    "description": "Analyze customer feedback for sentiment, key themes, and recommendations.",
                    "configurations": {
                        "model": OpenAIModel.GPT_5_NANO.value,
                        "system_prompt": (
                            "You are a text analysis expert. Analyze the text for sentiment, "
                            "themes, and actionable insights.\n\n"
                            "OUTPUT FORMAT REQUIREMENT:\n"
                            "Return ONLY valid JSON. No explanations, no markdown, no code fences.\n"
                            "The output must start with `{` and end with `}`.\n\n"
                            "Required fields:\n"
                            "- sentiment (string): overall sentiment (positive/negative/mixed/neutral)\n"
                            "- score (float): sentiment score between 0 and 1\n"
                            "- themes (array): key themes identified in the text\n"
                            "- recommendations (array): actionable insights based on the analysis"
                        ),
                        "temperature": 0.3,
                    },
                    "input_example": {
                        "message": "The new UI looks great, but it's still a bit slow to load.",
                        "context": {"product": "mobile_app"},
                    },
                    "expected_output": {
                        "content": {
                            "sentiment": "mixed",
                            "score": 0.65,
                            "themes": ["UI design", "performance"],
                            "recommendations": ["Optimize loading speed"],
                        },
                        "metadata": {"model_version": "gpt-5", "stop_reason": "stop"},
                        "token_usage": {
                            "input_tokens": 45,
                            "output_tokens": 79,
                            "total_tokens": 124,
                        },
                        "function_calls": [],
                    },
                }
            ],
        )


# Export the specification instance
OPENAI_CHATGPT_SPEC = OpenAIChatGPTSpec()
