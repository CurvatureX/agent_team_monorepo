"""
Node Communication Protocol

This module defines standardized data formats for communication between different node types.
It ensures smooth data flow by establishing common interfaces and data transformation rules.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import DataFormat


@dataclass
class StandardMessage:
    """Standard message format for node-to-node communication."""

    content: str  # Primary content (text, response, etc.)
    metadata: Optional[Dict[str, Any]] = None  # Additional context
    format_type: str = "text"  # text, json, html, markdown, etc.
    source_node: Optional[str] = None  # Originating node ID
    timestamp: Optional[str] = None  # Processing timestamp


# Standard data formats for different node types
STANDARD_TEXT_OUTPUT = DataFormat(
    mime_type="application/json",
    schema="""{
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Primary text content"},
            "metadata": {"type": "object", "description": "Additional context"},
            "format_type": {"type": "string", "enum": ["text", "json", "html", "markdown"]},
            "source_node": {"type": "string", "description": "Originating node ID"},
            "timestamp": {"type": "string", "description": "Processing timestamp"}
        },
        "required": ["content"]
    }""",
    examples=[
        '{"content": "Hello, this is a response from the AI.", "metadata": {"model": "gpt-4", "temperature": 0.7}, "format_type": "text", "source_node": "ai_agent_1", "timestamp": "2025-01-26T10:30:00Z"}',
        '{"content": "# Analysis Results\\nThe data shows significant improvement.", "format_type": "markdown"}',
    ],
)

SLACK_INPUT_FORMAT = DataFormat(
    mime_type="application/json",
    schema="""{
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Message text content"},
            "blocks": {"type": "array", "description": "Slack Block Kit blocks"},
            "mentions": {"type": "array", "description": "User mentions"},
            "metadata": {"type": "object", "description": "Additional context"}
        },
        "required": ["content"]
    }""",
    examples=[
        '{"content": "Hello team! Here are the results.", "blocks": [], "mentions": ["@channel"], "metadata": {}}',
        '{"content": "Analysis complete", "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "*Analysis Results*\\nThe data shows improvement."}}]}',
    ],
)

EMAIL_INPUT_FORMAT = DataFormat(
    mime_type="application/json",
    schema="""{
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Email body content"},
            "subject": {"type": "string", "description": "Email subject line"},
            "format_type": {"type": "string", "enum": ["text", "html", "markdown"]},
            "metadata": {"type": "object", "description": "Additional context"}
        },
        "required": ["content"]
    }""",
    examples=[
        '{"content": "Dear team, please find the analysis results attached.", "subject": "Weekly Analysis Report", "format_type": "text"}',
        '{"content": "<h1>Report</h1><p>Analysis shows improvement.</p>", "format_type": "html"}',
    ],
)


def transform_ai_to_text(ai_output: Dict[str, Any]) -> Dict[str, Any]:
    """Transform AI agent output to standard text format."""
    return {
        "content": ai_output.get("response", str(ai_output)),
        "metadata": ai_output.get("metadata", {}),
        "format_type": "text",
        "source_node": ai_output.get("source_node"),
        "timestamp": ai_output.get("timestamp"),
    }


def transform_text_to_slack(text_output: Dict[str, Any]) -> Dict[str, Any]:
    """Transform standard text output to Slack input format."""
    content = text_output.get("content", "")
    return {
        "content": content,
        "blocks": [],  # Can be populated by Slack node based on content
        "mentions": [],  # Can be extracted from content if needed
        "metadata": text_output.get("metadata", {}),
    }


def transform_text_to_email(text_output: Dict[str, Any]) -> Dict[str, Any]:
    """Transform standard text output to Email input format."""
    content = text_output.get("content", "")
    metadata = text_output.get("metadata", {})

    return {
        "content": content,
        "subject": metadata.get("subject", "Workflow Notification"),
        "format_type": text_output.get("format_type", "text"),
        "metadata": metadata,
    }


# Registry of transformation functions
TRANSFORMATION_REGISTRY = {
    # From AI_AGENT to other nodes
    ("AI_AGENT", "EXTERNAL_ACTION.SLACK"): transform_text_to_slack,
    ("AI_AGENT", "EXTERNAL_ACTION.EMAIL"): transform_text_to_email,
    # From any text output to action nodes
    ("STANDARD_TEXT", "EXTERNAL_ACTION.SLACK"): transform_text_to_slack,
    ("STANDARD_TEXT", "EXTERNAL_ACTION.EMAIL"): transform_text_to_email,
}


def get_transformation_function(source_type: str, target_type: str):
    """Get transformation function for converting between node types."""
    return TRANSFORMATION_REGISTRY.get((source_type, target_type))


def apply_transformation(
    data: Dict[str, Any], source_type: str, target_type: str
) -> Dict[str, Any]:
    """Apply transformation between node types."""
    transform_fn = get_transformation_function(source_type, target_type)
    if transform_fn:
        return transform_fn(data)
    return data  # No transformation available, return as-is
