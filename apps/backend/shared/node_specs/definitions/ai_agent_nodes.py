"""
AI Agent node specifications.

This module defines specifications for AI_AGENT_NODE subtypes based on AI providers.
Each node represents a different AI model provider (Gemini, OpenAI, Claude) where
the specific functionality is determined by the system prompt rather than predefined roles.
"""

from ...models.node_enums import AIAgentSubtype, NodeType
from ..base import (
    ConnectionType,
    DataFormat,
    InputPortSpec,
    NodeSpec,
    OutputPortSpec,
    ParameterDef,
    ParameterType,
)


# Base AI Agent specification with common parameters
def _create_ai_agent_spec(provider: str, provider_description: str) -> NodeSpec:
    """Create a standardized AI agent specification for a provider."""
    return NodeSpec(
        node_type=NodeType.AI_AGENT,
        subtype=provider,
        description=f"{provider_description} AI agent with customizable behavior via system prompt",
        parameters=[
            ParameterDef(
                name="system_prompt",
                type=ParameterType.STRING,
                required=True,
                description="System prompt that defines the AI agent's role, behavior, and instructions",
            ),
            ParameterDef(
                name="temperature",
                type=ParameterType.FLOAT,
                required=False,
                default_value=0.7,
                description="Controls randomness in AI responses (0.0 = deterministic, 1.0 = creative)",
                validation_pattern=r"^(0(\.\d+)?|1(\.0+)?)$",
            ),
            ParameterDef(
                name="max_tokens",
                type=ParameterType.INTEGER,
                required=False,
                default_value=2048,
                description="Maximum number of tokens in the AI response",
            ),
            ParameterDef(
                name="top_p",
                type=ParameterType.FLOAT,
                required=False,
                default_value=0.9,
                description="Nucleus sampling parameter (0.1 = focused, 1.0 = diverse)",
                validation_pattern=r"^(0(\.\d+)?|1(\.0+)?)$",
            ),
            ParameterDef(
                name="response_format",
                type=ParameterType.ENUM,
                required=False,
                default_value="text",
                enum_values=["text", "json", "structured"],
                description="Expected format of the AI response",
            ),
            ParameterDef(
                name="timeout_seconds",
                type=ParameterType.INTEGER,
                required=False,
                default_value=30,
                description="Request timeout in seconds",
            ),
            ParameterDef(
                name="retry_attempts",
                type=ParameterType.INTEGER,
                required=False,
                default_value=3,
                description="Number of retry attempts on failure",
            ),
        ],
        input_ports=[
            InputPortSpec(
                name="main",
                type=ConnectionType.MAIN,
                required=True,
                description="Input data and context for the AI agent",
                data_format=DataFormat(
                    mime_type="application/json",
                    schema='{"message": "string", "context": "object", "variables": "object"}',
                    examples=[
                        '{"message": "Analyze this data", "context": {"user_id": "123"}, "variables": {"data": [1,2,3]}}',
                        '{"message": "Generate a report", "context": {"format": "markdown"}, "variables": {"metrics": {"sales": 100}}}',
                    ],
                ),
                validation_schema='{"type": "object", "properties": {"message": {"type": "string"}, "context": {"type": "object"}, "variables": {"type": "object"}}, "required": ["message"]}',
            )
        ],
        output_ports=[
            OutputPortSpec(
                name="main",
                type=ConnectionType.MAIN,
                description="AI agent response and metadata",
                data_format=DataFormat(
                    mime_type="application/json",
                    schema='{"response": "string", "metadata": "object", "usage": "object", "processing_time": "number"}',
                    examples=[
                        '{"response": "Analysis complete: The data shows...", "metadata": {"model": "gpt-4", "temperature": 0.7}, "usage": {"prompt_tokens": 50, "completion_tokens": 100}, "processing_time": 2.5}'
                    ],
                ),
                validation_schema='{"type": "object", "properties": {"response": {"type": "string"}, "metadata": {"type": "object"}, "usage": {"type": "object"}, "processing_time": {"type": "number"}}, "required": ["response"]}',
            ),
            OutputPortSpec(
                name="error",
                type=ConnectionType.ERROR,
                description="Error output when AI processing fails",
                data_format=DataFormat(
                    mime_type="application/json",
                    schema='{"error_type": "string", "error_message": "string", "retry_count": "number", "timestamp": "string"}',
                    examples=[
                        '{"error_type": "rate_limit", "error_message": "API rate limit exceeded", "retry_count": 2, "timestamp": "2025-01-28T10:30:00Z"}'
                    ],
                ),
            ),
        ],
        examples=[
            {
                "name": "Text Analysis Agent",
                "description": "Analyze sentiment and extract key insights from text",
                "system_prompt": "You are a text analysis expert. Analyze the given text for sentiment, key themes, and actionable insights. Provide a structured response with sentiment score, main topics, and recommendations.",
                "input_example": {
                    "message": "Customer feedback about our new product features",
                    "context": {"product": "mobile_app"},
                },
                "expected_output": "Structured analysis with sentiment, themes, and recommendations",
            },
            {
                "name": "Data Summarizer Agent",
                "description": "Summarize complex data into digestible insights",
                "system_prompt": "You are a data analyst. Take the provided data and create a concise, executive-level summary highlighting the most important trends, anomalies, and actionable insights.",
                "input_example": {
                    "message": "Summarize monthly sales data",
                    "variables": {"sales_data": [{"month": "Jan", "revenue": 100000}]},
                },
                "expected_output": "Executive summary with key metrics and trends",
            },
        ],
    )


# Gemini AI Agent - Google's Gemini models
GEMINI_NODE_SPEC = _create_ai_agent_spec(AIAgentSubtype.GOOGLE_GEMINI, "Google Gemini")

# Add Gemini-specific parameters
GEMINI_NODE_SPEC.parameters.extend(
    [
        ParameterDef(
            name="model_version",
            type=ParameterType.ENUM,
            required=False,
            default_value="gemini-pro",
            enum_values=["gemini-pro", "gemini-pro-vision", "gemini-ultra"],
            description="Specific Gemini model version to use",
        ),
        ParameterDef(
            name="safety_settings",
            type=ParameterType.JSON,
            required=False,
            description="Safety filter settings for harmful content categories",
        ),
    ]
)


# OpenAI AI Agent - OpenAI GPT models
OPENAI_NODE_SPEC = _create_ai_agent_spec(AIAgentSubtype.OPENAI_CHATGPT, "OpenAI GPT")

# Add OpenAI-specific parameters
OPENAI_NODE_SPEC.parameters.extend(
    [
        ParameterDef(
            name="model_version",
            type=ParameterType.ENUM,
            required=False,
            default_value="gpt-4",
            enum_values=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o"],
            description="Specific OpenAI model version to use",
        ),
        ParameterDef(
            name="presence_penalty",
            type=ParameterType.FLOAT,
            required=False,
            default_value=0.0,
            description="Penalty for new topics (−2.0 to 2.0)",
            validation_pattern=r"^-?([01](\.\d+)?|2(\.0+)?)$",
        ),
        ParameterDef(
            name="frequency_penalty",
            type=ParameterType.FLOAT,
            required=False,
            default_value=0.0,
            description="Penalty for repeated content (−2.0 to 2.0)",
            validation_pattern=r"^-?([01](\.\d+)?|2(\.0+)?)$",
        ),
    ]
)


# Claude AI Agent - Anthropic Claude models
CLAUDE_NODE_SPEC = _create_ai_agent_spec(AIAgentSubtype.ANTHROPIC_CLAUDE, "Anthropic Claude")

# Add Claude-specific parameters
CLAUDE_NODE_SPEC.parameters.extend(
    [
        ParameterDef(
            name="model_version",
            type=ParameterType.ENUM,
            required=False,
            default_value="claude-3-sonnet",
            enum_values=["claude-3-haiku", "claude-3-sonnet", "claude-3-opus", "claude-3.5-sonnet"],
            description="Specific Claude model version to use",
        ),
        ParameterDef(
            name="stop_sequences",
            type=ParameterType.JSON,
            required=False,
            description="Custom stop sequences to halt generation (array of strings)",
        ),
    ]
)
