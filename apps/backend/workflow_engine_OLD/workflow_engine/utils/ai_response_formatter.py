"""
AI Response Formatter for Workflow Engine

This module provides utilities to format AI responses for better integration
with workflow systems, inspired by n8n's approach.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class AIResponseFormatter:
    """Formats AI responses for workflow integration."""

    @staticmethod
    def format_response(
        raw_response: str,
        provider: str,
        model: str,
        input_text: str,
        system_prompt: str,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format AI response for workflow consumption.

        Returns a standardized structure that includes:
        - Raw text response
        - Parsed structured data (if JSON)
        - Extracted common fields
        - Metadata about the AI execution
        """
        # Parse structured data if possible
        structured_data = AIResponseFormatter._parse_structured_response(raw_response)

        # Extract common fields
        extracted_fields = AIResponseFormatter._extract_common_fields(raw_response, structured_data)

        # Build the formatted response
        formatted_response = {
            # Primary outputs - easily accessible in expressions
            "text": raw_response,  # Always available as plain text
            "json": structured_data,  # Parsed JSON if available, None otherwise
            # Common extractions for easy access
            "extracted": extracted_fields,
            # Execution metadata
            "metadata": {
                "provider": provider,
                "model": model,
                "input": {
                    "text": input_text,
                    "system_prompt": system_prompt,
                },
                "timestamp": datetime.now().isoformat(),
                "response_type": "structured" if structured_data else "text",
                **(execution_metadata or {}),
            },
        }

        # Add convenience fields based on content
        if structured_data:
            # If we have structured data, make common fields directly accessible
            for key in ["action", "category", "priority", "tasks", "items"]:
                if key in structured_data:
                    formatted_response[key] = structured_data[key]

        return formatted_response

    @staticmethod
    def _parse_structured_response(response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response if possible."""
        if not response:
            return None

        response_stripped = response.strip()

        # Try to parse as JSON
        if response_stripped.startswith("{") or response_stripped.startswith("["):
            try:
                return json.loads(response_stripped)
            except json.JSONDecodeError:
                logger.debug("Response looks like JSON but failed to parse")

        # Try to extract JSON from markdown code blocks
        json_pattern = r"```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```"
        matches = re.findall(json_pattern, response, re.MULTILINE)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # Try to find JSON anywhere in the response
        json_obj_pattern = r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})"
        json_matches = re.findall(json_obj_pattern, response)

        for match in json_matches:
            try:
                parsed = json.loads(match)
                # Only return if it's a meaningful object
                if len(parsed) > 0:
                    return parsed
            except json.JSONDecodeError:
                continue

        return None

    @staticmethod
    def _extract_common_fields(
        response: str, structured_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract commonly used fields from AI responses."""
        extracted = {}

        # If we have structured data, extract from there
        if structured_data:
            # Common task/action patterns
            if "tasks" in structured_data:
                extracted["task_count"] = len(structured_data["tasks"])
                extracted["first_task"] = (
                    structured_data["tasks"][0] if structured_data["tasks"] else None
                )

            # Priority/urgency patterns
            for priority_key in ["priority", "urgency", "importance"]:
                if priority_key in structured_data:
                    extracted["priority"] = structured_data[priority_key]
                    break

            # Category/classification patterns
            for category_key in ["category", "type", "classification", "label"]:
                if category_key in structured_data:
                    extracted["category"] = structured_data[category_key]
                    break

            # Action/decision patterns
            for action_key in ["action", "decision", "recommendation", "next_step"]:
                if action_key in structured_data:
                    extracted["action"] = structured_data[action_key]
                    break

        # Extract from text if no structured data
        else:
            # Extract bullet points
            bullet_points = re.findall(r"^[-*•]\s*(.+)$", response, re.MULTILINE)
            if bullet_points:
                extracted["bullet_points"] = bullet_points
                extracted["bullet_count"] = len(bullet_points)

            # Extract numbered lists
            numbered_items = re.findall(r"^\d+\.\s*(.+)$", response, re.MULTILINE)
            if numbered_items:
                extracted["numbered_items"] = numbered_items
                extracted["item_count"] = len(numbered_items)

            # Extract questions (ending with ?)
            questions = re.findall(r"([^.!?\n]+\?)", response)
            if questions:
                extracted["questions"] = [q.strip() for q in questions]
                extracted["question_count"] = len(questions)

            # Extract URLs
            urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', response)
            if urls:
                extracted["urls"] = urls
                extracted["url_count"] = len(urls)

            # Extract email addresses
            emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", response)
            if emails:
                extracted["emails"] = emails

            # Check for common keywords
            response_lower = response.lower()
            extracted["has_urgent"] = any(
                word in response_lower for word in ["urgent", "asap", "immediately"]
            )
            extracted["has_action"] = any(
                word in response_lower for word in ["action", "task", "todo", "must"]
            )
            extracted["sentiment"] = AIResponseFormatter._detect_sentiment(response_lower)

        return extracted

    @staticmethod
    def _detect_sentiment(text: str) -> str:
        """Simple sentiment detection."""
        positive_words = ["good", "great", "excellent", "success", "happy", "positive"]
        negative_words = ["bad", "error", "fail", "problem", "issue", "negative"]

        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"


class WorkflowDataAccessor:
    """
    Provides n8n-style data access patterns for workflow nodes.
    This allows subsequent nodes to access AI output using expressions like:
    - $node["AI Node"].json.text
    - $node["AI Node"].json.extracted.priority
    """

    @staticmethod
    def create_node_output(formatted_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create node output in a format that's easily accessible by subsequent nodes.
        """
        return {
            "json": formatted_response,
            # Add shortcuts for common access patterns
            "text": formatted_response.get("text", ""),
            "structured": formatted_response.get("json"),
            "metadata": formatted_response.get("metadata", {}),
        }

    @staticmethod
    def get_expression_value(node_outputs: Dict[str, Any], expression: str) -> Any:
        """
        Evaluate n8n-style expressions to access node data.

        Examples:
            - $node["AI Node"].json.text
            - $node["Parser"].json.extracted.category
        """
        # This is a simplified version - in production you'd want a proper expression parser
        # For now, we'll handle basic dot notation

        # Extract node name from expression
        node_match = re.match(r'\$node\["([^"]+)"\]\.(.+)', expression)
        if not node_match:
            return None

        node_name = node_match.group(1)
        path = node_match.group(2)

        if node_name not in node_outputs:
            return None

        # Navigate the path
        current = node_outputs[node_name]
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current


# Example usage in AI node execution
def format_ai_node_output(
    response: str, provider: str, model: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Format AI node output for workflow integration.
    This would be called in the AI node executor.
    """
    formatted = AIResponseFormatter.format_response(
        raw_response=response,
        provider=provider,
        model=model,
        input_text=context.get("input_text", ""),
        system_prompt=context.get("system_prompt", ""),
        execution_metadata={
            "temperature": context.get("temperature"),
            "max_tokens": context.get("max_tokens"),
            "execution_time": context.get("execution_time"),
        },
    )

    return WorkflowDataAccessor.create_node_output(formatted)
