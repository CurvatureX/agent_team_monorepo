"""
GOOGLE_GEMINI AI Agent Node Specification

Google Gemini AI agent node for performing advanced AI operations including
multi-modal processing, reasoning, analysis, and creative tasks.
"""

from typing import Any, Dict, List

from shared.models.node_enums import AIAgentSubtype, GoogleGeminiModel, NodeType
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


class GoogleGeminiSpec(BaseNodeSpec):
    """Google Gemini AI agent specification aligned with Gemini API."""

    def __init__(self):
        super().__init__(
            type=NodeType.AI_AGENT,
            subtype=AIAgentSubtype.GOOGLE_GEMINI,
            name="Google_Gemini",
            description=(
                "Google Gemini AI agent for advanced multi-modal processing, reasoning, "
                "code generation, and creative tasks"
            ),
            # Configuration parameters (Gemini-native only)
            configurations={
                "model": {
                    "type": "string",
                    "default": GoogleGeminiModel.GEMINI_2_5_FLASH.value,
                    "description": "Gemini model version",
                    "required": True,
                    "options": [model.value for model in GoogleGeminiModel],
                },
                "system_prompt": {
                    "type": "string",
                    "default": "",
                    "description": "System prompt (prepended as system content)",
                    "required": False,
                    "multiline": True,
                },
                "user_prompt": {
                    "type": "string",
                    "default": "",
                    "description": "User prompt template",
                    "required": True,
                    "multiline": True,
                },
                "generation_config": {
                    "type": "object",
                    "default": {
                        "max_output_tokens": 8192,
                        "temperature": 0.7,
                        "top_p": 0.95,
                        "top_k": 40,
                        "candidate_count": 1,
                        "stop_sequences": [],
                    },
                    "description": "Gemini generation configuration",
                    "required": False,
                },
                "safety_settings": {
                    "type": "object",
                    "default": {
                        "harassment": "BLOCK_MEDIUM_AND_ABOVE",
                        "hate_speech": "BLOCK_MEDIUM_AND_ABOVE",
                        "sexually_explicit": "BLOCK_MEDIUM_AND_ABOVE",
                        "dangerous_content": "BLOCK_MEDIUM_AND_ABOVE",
                    },
                    "description": "Gemini safety configuration",
                    "required": False,
                },
                "multimodal_config": {
                    "type": "object",
                    "default": {
                        "enable_vision": True,
                        "enable_audio": False,
                        "enable_video": False,
                    },
                    "description": "Enable multimodal inputs (image/audio/video if model supports)",
                    "required": False,
                },
                "function_calling": {
                    "type": "object",
                    "default": {"enabled": False, "functions": [], "function_calling_mode": "AUTO"},
                    "description": "Gemini function calling (tools API)",
                    "required": False,
                },
                # Add shared/common configs (timeouts, retries, etc.)
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "user_prompt": {
                    "type": "string",
                    "default": "",
                    "description": "User input text or prompt variables",
                    "required": True,
                },
                "images": {
                    "type": "array",
                    "default": [],
                    "description": "Optional image inputs for multi-modal processing",
                    "required": False,
                },
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
            tags=[
                "ai-agent",
                "google",
                "gemini",
                "llm",
                "multimodal",
                "reasoning",
            ],
            examples=[
                {
                    "name": "Generate Product Description",
                    "description": (
                        "Use Gemini to generate a concise, engaging product description "
                        "for an e-commerce listing that highlights features and appeals to the target audience."
                    ),
                    "configurations": {
                        "model": "gemini-2.5-flash",
                        "system_prompt": "You are an expert e-commerce copywriter.",
                        "user_prompt": (
                            "Write a compelling product description for {{product_name}}. "
                            "Emphasize its {{key_features}} and tailor the tone to attract {{target_audience}}."
                        ),
                        "generation_config": {
                            "max_output_tokens": 512,
                            "temperature": 0.7,
                            "top_p": 0.9,
                        },
                        "safety_settings": {
                            "harassment": "BLOCK_MEDIUM_AND_ABOVE",
                            "hate_speech": "BLOCK_MEDIUM_AND_ABOVE",
                            "sexually_explicit": "BLOCK_MEDIUM_AND_ABOVE",
                            "dangerous_content": "BLOCK_MEDIUM_AND_ABOVE",
                        },
                    },
                    "input_example": {
                        "user_input": {
                            "product_name": "Aurora Smart Lamp",
                            "key_features": ["voice control", "16M colors", "adaptive brightness"],
                            "target_audience": "tech-savvy young professionals",
                        }
                    },
                    "expected_outputs": {
                        "content": {
                            "product_description": "Meet the Aurora Smart Lamp — a stylish and intelligent addition to any space. With effortless voice control, a spectrum of over 16 million colors, and adaptive brightness, it transforms your environment with ease. Whether you're working late or relaxing, Aurora adapts seamlessly to your lifestyle.",
                            "key_benefits": [
                                "Voice-controlled convenience",
                                "Personalized ambiance with 16M colors",
                                "Intelligent auto-adjustment",
                                "Modern aesthetic",
                            ],
                            "target_appeal": "Perfect for tech-savvy young professionals seeking smart home integration",
                        },
                        "metadata": {"model_version": "gemini-2.5-flash", "stop_reason": "STOP"},
                        "token_usage": {
                            "input_tokens": 55,
                            "output_tokens": 94,
                            "total_tokens": 149,
                        },
                        "function_calls": [],
                    },
                }
            ],
        )


# Export the specification instance
GOOGLE_GEMINI_SPEC = GoogleGeminiSpec()
