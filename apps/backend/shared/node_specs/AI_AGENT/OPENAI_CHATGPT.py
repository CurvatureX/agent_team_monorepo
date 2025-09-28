"""
OPENAI_CHATGPT AI Agent Node Specification

OpenAI ChatGPT AI agent with customizable behavior via system prompt.
Supports function calling via attached TOOL nodes and memory context via MEMORY nodes.
"""

from typing import Any, Dict, List

from shared.models.node_enums import AIAgentSubtype, NodeType, OpenAIModel
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec, create_port


class OpenAIChatGPTSpec(BaseNodeSpec):
    """OpenAI ChatGPT AI agent specification following the new workflow architecture."""

    def __init__(self):
        super().__init__(
            type=NodeType.AI_AGENT,
            subtype=AIAgentSubtype.OPENAI_CHATGPT,
            name="OpenAI_ChatGPT",
            description="OpenAI ChatGPT AI agent with customizable behavior via system prompt",
            # Configuration parameters
            configurations={
                "model": {
                    "type": "string",
                    "default": OpenAIModel.GPT_5.value,
                    "description": "OpenAI模型版本",
                    "required": True,
                    "options": [model.value for model in OpenAIModel],
                },
                "system_prompt": {
                    "type": "string",
                    "default": "You are a helpful AI assistant. Analyze the input and provide a clear, accurate response.",
                    "description": "系统提示词，定义AI的行为和角色",
                    "required": True,
                    "multiline": True,
                },
                "temperature": {
                    "type": "float",
                    "default": 0.7,
                    "min": 0.0,
                    "max": 2.0,
                    "description": "控制输出随机性（0-2）",
                    "required": False,
                },
                "max_tokens": {
                    "type": "integer",
                    "default": 2048,
                    "min": 1,
                    "max": 8192,
                    "description": "最大输出token数",
                    "required": False,
                },
                "top_p": {
                    "type": "float",
                    "default": 1.0,
                    "min": 0.0,
                    "max": 1.0,
                    "description": "核采样参数",
                    "required": False,
                },
                "frequency_penalty": {
                    "type": "float",
                    "default": 0.0,
                    "min": -2.0,
                    "max": 2.0,
                    "description": "频率惩罚参数",
                    "required": False,
                },
                "presence_penalty": {
                    "type": "float",
                    "default": 0.0,
                    "min": -2.0,
                    "max": 2.0,
                    "description": "存在惩罚参数",
                    "required": False,
                },
                "response_format": {
                    "type": "string",
                    "default": "text",
                    "description": "期望的响应格式",
                    "required": False,
                    "options": ["text", "json", "structured"],
                },
                "enable_function_calling": {
                    "type": "boolean",
                    "default": True,
                    "description": "启用通过连接的TOOL节点进行MCP函数调用",
                    "required": False,
                },
                "max_function_calls": {
                    "type": "integer",
                    "default": 5,
                    "min": 1,
                    "max": 20,
                    "description": "每次AI执行的最大函数调用次数",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"message": "", "context": {}, "variables": {}},
            default_output_params={
                "content": "",
                "metadata": {},
                "format_type": "",
                "source_node": "",
                "timestamp": "",
                "token_usage": {},
                "function_calls": [],
            },
            # Port definitions with comprehensive schemas
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="dict",
                    description="Input data for AI processing",
                    required=True,
                    max_connections=1,
                )
            ],
            output_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="dict",
                    description="AI agent response output",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="error",
                    name="error",
                    data_type="dict",
                    description="Error output for failed operations",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Attached nodes - TOOL and MEMORY nodes are attached, not connected via ports
            attached_nodes=[],  # Will be populated when creating node instances
            # Metadata
            tags=["ai", "openai", "chatgpt", "language-model", "function-calling"],
            # Examples
            examples=[
                {
                    "name": "Text Analysis Agent",
                    "description": "Analyze sentiment and extract key insights from text",
                    "configurations": {
                        "model": OpenAIModel.GPT_5.value,
                        "system_prompt": "You are a text analysis expert. Analyze the given text for sentiment, key themes, and actionable insights. Provide a structured response with sentiment score, main topics, and recommendations.",
                        "temperature": 0.3,
                        "response_format": "json",
                    },
                    "input_example": {
                        "message": "Customer feedback about our new product features",
                        "context": {"product": "mobile_app"},
                        "variables": {
                            "feedback_text": "The new UI is confusing but the performance improvements are great!"
                        },
                    },
                    "expected_output": {
                        "content": '{"sentiment": "mixed", "score": 0.6, "themes": ["UI design", "performance"], "recommendations": ["Improve UI clarity", "Highlight performance gains"]}',
                        "metadata": {"model": "gpt-5", "tokens": 156},
                        "format_type": "json",
                        "source_node": "text_analysis_ai",
                        "timestamp": "2025-01-28T10:30:00Z",
                    },
                },
                {
                    "name": "Code Review Assistant",
                    "description": "Review code changes and provide feedback",
                    "configurations": {
                        "model": OpenAIModel.GPT_5.value,
                        "system_prompt": "You are a senior software engineer conducting code reviews. Focus on code quality, security, performance, and best practices. Provide constructive feedback.",
                        "temperature": 0.2,
                        "enable_function_calling": True,
                    },
                    "input_example": {
                        "message": "Please review this Python function",
                        "context": {"language": "python", "project": "api_service"},
                        "variables": {
                            "code": "def process_data(data):\\n    return [x*2 for x in data if x > 0]"
                        },
                    },
                    "expected_output": {
                        "content": "The function looks good overall. Consider adding type hints and docstring for better maintainability. The list comprehension is efficient.",
                        "metadata": {"model": "gpt-5", "tokens": 89},
                        "format_type": "text",
                        "source_node": "code_review_ai",
                        "timestamp": "2025-01-28T11:15:00Z",
                    },
                },
            ],
        )


# Export the specification instance
OPENAI_CHATGPT_SPEC = OpenAIChatGPTSpec()
