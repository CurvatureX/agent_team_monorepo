"""Safe data transformation system for workflow connections."""

import json
import re
from typing import Any, Callable, Dict, List


class DataTransformer:
    """Safe data transformation with predefined operations."""

    def __init__(self):
        self.transformers: Dict[str, Callable] = {
            # AI Agent transformations
            "ai_input": self._transform_ai_input,
            "ai_output": self._transform_ai_output,
            # Slack transformations
            "slack_message": self._transform_slack_message,
            # Generic transformations
            "extract_field": self._extract_field,
            "create_object": self._create_object,
            "pass_through": self._pass_through,
        }

    def transform(self, data: Any, transformation_config: Dict[str, Any]) -> Any:
        """Apply safe transformation based on configuration."""
        transformer_type = transformation_config.get("type", "pass_through")
        transformer_func = self.transformers.get(transformer_type, self._pass_through)

        return transformer_func(data, transformation_config)

    def _transform_ai_input(self, data: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform trigger data into AI agent input."""
        message = config.get("message", "Default prompt")
        context = config.get("context", "general")

        return {"user_input": message, "context": context}

    def _transform_ai_output(self, data: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform AI agent output for consumption."""
        if not isinstance(data, dict):
            return {"text": str(data)}

        # Extract the actual AI response
        response = data.get("output", "")
        if not response and "provider_result" in data:
            response = data["provider_result"].get("response", "")

        return {"text": response}

    def _transform_slack_message(self, data: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data into Slack message format."""
        # Extract text from various possible sources
        text = ""
        if isinstance(data, str):
            text = data
        elif isinstance(data, dict):
            text = data.get("text", data.get("output", data.get("response", "")))

        # Apply formatting if specified
        format_template = config.get("format", "{text}")
        formatted_text = format_template.format(text=text)

        return {
            "text": formatted_text,
            "channel": config.get("channel", "#general"),
            "username": config.get("username", "Bot"),
            "action_type": "send_message",
        }

    def _extract_field(self, data: Any, config: Dict[str, Any]) -> Any:
        """Extract a specific field from data."""
        if not isinstance(data, dict):
            return data

        field_path = config.get("field", "").split(".")
        result = data

        for field in field_path:
            if isinstance(result, dict) and field in result:
                result = result[field]
            else:
                return config.get("default", None)

        return result

    def _create_object(self, data: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create object with specified fields."""
        result = {}
        fields = config.get("fields", {})

        for key, value_config in fields.items():
            if isinstance(value_config, str):
                # Simple string value
                result[key] = value_config
            elif isinstance(value_config, dict) and "from_input" in value_config:
                # Extract from input data
                field_path = value_config["from_input"].split(".")
                value = data
                for field in field_path:
                    if isinstance(value, dict) and field in value:
                        value = value[field]
                    else:
                        value = value_config.get("default", "")
                        break
                result[key] = value
            else:
                result[key] = value_config

        return result

    def _pass_through(self, data: Any, config: Dict[str, Any]) -> Any:
        """Pass data through unchanged."""
        return data


def parse_legacy_conversion_function(conversion_function: str) -> Dict[str, Any]:
    """Parse legacy exec() conversion functions into safe transformation configs."""

    # Check for common patterns and convert to safe configs
    if "Tell me a funny joke" in conversion_function:
        return {"type": "ai_input", "message": "Tell me a funny joke", "context": "joke_generation"}

    # Check for Slack message transformation patterns
    if any(pattern in conversion_function for pattern in ["🎭", "#general", "JokeBot", "Slack"]):
        return {
            "type": "slack_message",
            "format": "🎭 {text} 🎭",
            "channel": "#general",
            "username": "JokeBot",
        }

    # Check for general text extraction patterns
    if any(
        pattern in conversion_function
        for pattern in ["input_data.get('output')", "text", "message"]
    ):
        return {"type": "ai_output"}

    # Default fallback
    return {"type": "pass_through"}


# Global transformer instance
transformer = DataTransformer()
