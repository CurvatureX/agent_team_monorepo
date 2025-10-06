"""
ANTHROPIC_CLAUDE AI Agent Node Specification

Anthropic Claude AI agent node for performing advanced AI operations including
text generation, analysis, reasoning, code generation, and multi-modal processing.
"""

from typing import Any, Dict, List

from shared.models.node_enums import AIAgentSubtype, AnthropicModel, NodeType
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


class AnthropicClaudeSpec(BaseNodeSpec):
    """Anthropic Claude AI agent specification for advanced AI processing."""

    def __init__(self):
        super().__init__(
            type=NodeType.AI_AGENT,
            subtype=AIAgentSubtype.ANTHROPIC_CLAUDE,
            name="Anthropic_Claude",
            description="Anthropic Claude AI agent for advanced reasoning, analysis, code generation, and multi-modal processing",
            # Configuration parameters
            configurations={
                "model": {
                    "type": "string",
                    "default": AnthropicModel.CLAUDE_SONNET_4.value,
                    "description": "Claude model version",
                    "required": True,
                    "options": [model.value for model in AnthropicModel],
                },
                "system_prompt": {
                    "type": "string",
                    "default": "",
                    "description": "系统提示词（发送时需包装为system角色消息）",
                    "required": False,
                    "multiline": True,
                },
                "max_tokens": {
                    "type": "integer",
                    "default": 8192,
                    "description": "最大输出令牌数（Claude默认约4096，部分模型可至约8192）",
                    "required": False,
                },
                "temperature": {
                    "type": "number",
                    "default": 0.7,
                    "min": 0.0,
                    "max": 1.0,
                    "description": "创造性温度参数",
                    "required": False,
                },
                "top_p": {
                    "type": "number",
                    "default": 0.9,
                    "min": 0.0,
                    "max": 1.0,
                    "description": "Top-p采样参数",
                    "required": False,
                },
                "response_format": {
                    "type": "string",
                    "default": "text",
                    "description": "响应格式（仅支持 'text' 与 'json'；'markdown'/'structured'/'code' 属于封装层后处理）",
                    "required": False,
                    "options": ["text", "json"],
                },
                "multimodal_config": {
                    "type": "object",
                    "default": {
                        "enable_vision": False,
                        "max_images": 5,
                        "image_detail": "auto",
                        "supported_formats": ["jpeg", "png", "gif", "webp"],
                    },
                    "description": "多模态配置（Claude支持视觉，但该配置为封装层，非API参数）",
                    "required": False,
                },
                "function_calling": {
                    "type": "object",
                    "default": {"enabled": False, "functions": [], "function_choice": "auto"},
                    "description": "函数调用配置（Claude无原生OpenAI风格函数调用，需通过提示或外部框架解析/实现）",
                    "required": False,
                },
                "context_management": {
                    "type": "object",
                    "default": {
                        "enable_memory": False,
                        "memory_type": "conversation",
                        "max_context_length": 100000,
                        "context_compression": False,
                    },
                    "description": "上下文管理（Claude不管理对话记忆；截断/压缩/存储需由调用方封装实现）",
                    "required": False,
                },
                "output_processing": {
                    "type": "object",
                    "default": {
                        "enable_streaming": False,
                        "parse_json": False,
                        "extract_code": False,
                        "validate_output": False,
                        "output_schema": {},
                    },
                    "description": "输出处理配置（提取代码/校验/输出schema均为后处理逻辑，非API参数）",
                    "required": False,
                },
                "safety_config": {
                    "type": "object",
                    "default": {
                        "content_filtering": True,
                        "harmful_content_detection": True,
                        "pii_detection": False,
                        "custom_safety_guidelines": "",
                    },
                    "description": "安全配置（Anthropic内置安全策略；此处为额外封装层控制，非API参数）",
                    "required": False,
                },
                "performance_config": {
                    "type": "object",
                    "default": {
                        "timeout_seconds": 120,
                        "retry_attempts": 3,
                        "retry_delay": 1.0,
                        "exponential_backoff": True,
                        "cache_responses": False,
                    },
                    "description": "性能配置（超时/重试/回退/缓存等均为基础设施层，非API参数）",
                    "required": False,
                },
                "cost_optimization": {
                    "type": "object",
                    "default": {
                        "enable_caching": False,
                        "cache_ttl": 3600,
                        "prompt_compression": False,
                        "output_length_limit": -1,
                    },
                    "description": "成本优化配置（提示压缩/缓存/TTL为封装或基础设施层，非API参数）",
                    "required": False,
                },
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
            },
            output_params={
                "content": {
                    "type": "object",
                    "default": "",
                    "description": "The model response content includes fields that match the input parameters of connected nodes. When passing values to connected nodes, use these matching fields so the values are delivered correctly.",
                    "required": True,
                },
                "metadata": {
                    "type": "object",
                    "default": {},
                    "description": "Additional metadata returned with the response",
                    "required": False,
                },
                "token_usage": {
                    "type": "object",
                    "default": {},
                    "description": "Token usage statistics (input/output/total)",
                    "required": True,
                },
                "function_calls": {
                    "type": "array",
                    "default": [],
                    "description": "List of function/tool calls invoked by the model",
                    "required": False,
                },
            },  # Examples
            examples=[
                {
                    "name": "Advanced Code Analysis and Review",
                    "description": "Perform comprehensive code analysis with security, performance, and best practices review",
                    "configurations": {
                        "anthropic_api_key": "sk-ant-your_api_key_here",
                        "model": "claude-sonnet-4-20250514",
                        "system_prompt": "You are an expert software engineer and security analyst. Perform comprehensive code reviews focusing on:\n1. Code quality and best practices\n2. Security vulnerabilities\n3. Performance optimizations\n4. Maintainability improvements\n5. Testing recommendations\n\nProvide specific, actionable feedback with code examples.",
                        "max_tokens": 8192,
                        "temperature": 0.3,
                        "response_format": "json",
                        "output_processing": {
                            "parse_json": True,
                            "validate_output": True,
                            "output_schema": {
                                "type": "object",
                                "properties": {
                                    "overall_rating": {"type": "string"},
                                    "security_issues": {"type": "array"},
                                    "performance_issues": {"type": "array"},
                                    "best_practice_violations": {"type": "array"},
                                    "improvement_suggestions": {"type": "array"},
                                    "positive_aspects": {"type": "array"},
                                },
                            },
                        },
                    },
                    "input_example": {
                        "user_input": {
                            "language": "python",
                            "code_context": "FastAPI authentication middleware for a financial services API",
                            "code_content": 'def authenticate_user(token: str):\n    if not token:\n        return None\n    try:\n        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])\n        user_id = payload.get("user_id")\n        user = get_user_by_id(user_id)\n        return user\n    except:\n        return None',
                        },
                        "context": {
                            "project_type": "financial_api",
                            "security_level": "high",
                            "compliance_requirements": ["PCI-DSS", "SOX"],
                        },
                    },
                    "expected_outputs": {
                        "content": "# Code Analysis Results\n\n## Overall Assessment\n**Rating:** Needs Significant Improvement\n\n## Critical Security Issues\n1. **Broad Exception Handling**: The bare `except:` clause masks all exceptions...",
                        "metadata": {
                            "model_version": "claude-sonnet-4-20250514",
                            "processing_time": 3.2,
                        },
                        "format_type": "json",
                        "token_usage": {
                            "input_tokens": 245,
                            "output_tokens": 1580,
                            "total_tokens": 1825,
                            "cost_usd": 0.0234,
                        },
                        "function_calls": [],
                    },
                },
                {
                    "name": "Multi-Modal Document Analysis",
                    "description": "Analyze documents with both text and images for comprehensive insights",
                    "configurations": {
                        "anthropic_api_key": "sk-ant-your_api_key_here",
                        "model": "claude-sonnet-4-20250514",
                        "system_prompt": "You are an expert document analyst specializing in multi-modal content analysis...",
                        "max_tokens": 6144,
                        "temperature": 0.4,
                        "multimodal_config": {
                            "enable_vision": True,
                            "max_images": 3,
                            "image_detail": "high",
                        },
                        "output_processing": {"parse_json": True, "extract_code": False},
                    },
                    "input_example": {
                        "user_input": {
                            "document_type": "Financial Report",
                            "analysis_purpose": "Investment due diligence",
                            "text_content": "Q4 2024 Financial Results - Revenue increased 23% YoY to $156M...",
                        },
                        "images": [
                            {
                                "url": "data:image/png;base64,...",
                                "description": "Revenue growth chart",
                            },
                            {
                                "url": "data:image/png;base64,...",
                                "description": "Balance sheet summary",
                            },
                        ],
                    },
                    "expected_outputs": {
                        "content": "# Financial Document Analysis\n\n## Executive Summary\nThis Q4 2024 financial report demonstrates strong performance...",
                        "metadata": {
                            "model_version": "claude-sonnet-4-20250514",
                            "processing_time": 4.7,
                        },
                        "format_type": "text",
                        "token_usage": {
                            "input_tokens": 1850,
                            "output_tokens": 2240,
                            "total_tokens": 4090,
                            "cost_usd": 0.0891,
                        },
                        "function_calls": [],
                    },
                },
            ],
        )


# Export the specification instance
ANTHROPIC_CLAUDE_SPEC = AnthropicClaudeSpec()
