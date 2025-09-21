"""
HIL Response Classifier using Gemini 2.5 Flash Lite.

Provides AI-powered classification of incoming webhook responses to determine
relevance to pending HIL interactions.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from shared.models.node_enums import GoogleGeminiModel


@dataclass
class ClassificationResult:
    """Result of AI response classification."""

    relevance_score: float  # 0.0-1.0 confidence score
    reasoning: str  # AI explanation of decision
    is_relevant: bool  # True if score >= threshold
    classification: str  # 'relevant', 'filtered', 'uncertain'


class HILResponseClassifier:
    """AI-powered classifier to determine webhook response relevance to HIL requests."""

    def __init__(self, relevance_threshold: float = 0.7):
        """Initialize classifier with Gemini 2.5 Flash Lite.

        Args:
            relevance_threshold: Minimum score (0.0-1.0) to consider response relevant
        """
        self.logger = logging.getLogger(__name__)
        self.model = GoogleGeminiModel.GEMINI_2_5_FLASH_LITE
        self.relevance_threshold = relevance_threshold

        # TODO: Initialize Gemini client when available
        self.gemini_client = None

        self.logger.info(f"Initialized HIL Response Classifier with {self.model.value}")

    async def classify_response_relevance(
        self, interaction: Dict[str, Any], webhook_payload: Dict[str, Any]
    ) -> ClassificationResult:
        """
        Classify webhook response relevance to HIL interaction.

        Args:
            interaction: HIL interaction data from human_interactions table
            webhook_payload: Complete webhook response payload

        Returns:
            ClassificationResult with relevance score and reasoning
        """
        try:
            # Extract key information for classification
            interaction_context = self._extract_interaction_context(interaction)
            response_context = self._extract_response_context(webhook_payload)

            # Generate classification prompt
            classification_prompt = self._build_classification_prompt(
                interaction_context, response_context
            )

            # Get AI classification (mock implementation for now)
            ai_result = await self._call_gemini_api(classification_prompt)

            # Parse AI response
            result = self._parse_classification_response(ai_result)

            self.logger.info(
                f"Classified response relevance: {result.relevance_score:.2f} "
                f"({result.classification}) for interaction {interaction.get('id')}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Error classifying response relevance: {str(e)}")
            # Return uncertain result on error
            return ClassificationResult(
                relevance_score=0.5,
                reasoning=f"Classification error: {str(e)}",
                is_relevant=False,
                classification="uncertain",
            )

    def _extract_interaction_context(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant context from HIL interaction for classification."""
        request_data = interaction.get("request_data", {})

        context = {
            "interaction_type": interaction.get("interaction_type"),
            "channel_type": interaction.get("channel_type"),
            "priority": interaction.get("priority"),
            "created_at": interaction.get("created_at"),
            "correlation_id": interaction.get("correlation_id"),
        }

        # Extract specific request details based on interaction type
        if interaction.get("interaction_type") == "approval":
            approval_request = request_data.get("approval_request", {})
            context.update(
                {
                    "title": approval_request.get("title"),
                    "description": approval_request.get("description"),
                    "approval_options": approval_request.get("approval_options", []),
                }
            )
        elif interaction.get("interaction_type") == "input":
            input_request = request_data.get("input_request", {})
            context.update(
                {
                    "title": input_request.get("title"),
                    "description": input_request.get("description"),
                    "required_fields": [f.get("name") for f in input_request.get("fields", [])],
                }
            )
        elif interaction.get("interaction_type") == "selection":
            selection_request = request_data.get("selection_request", {})
            context.update(
                {
                    "title": selection_request.get("title"),
                    "description": selection_request.get("description"),
                    "options": [opt.get("value") for opt in selection_request.get("options", [])],
                }
            )

        return context

    def _extract_response_context(self, webhook_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant context from webhook response for classification."""
        return {
            "source_channel": webhook_payload.get("channel", webhook_payload.get("source")),
            "message_text": self._extract_message_text(webhook_payload),
            "user_info": self._extract_user_info(webhook_payload),
            "timestamp": webhook_payload.get("timestamp", webhook_payload.get("ts")),
            "message_type": webhook_payload.get("type", webhook_payload.get("event_type")),
            "raw_payload_keys": list(webhook_payload.keys()),
        }

    def _extract_message_text(self, payload: Dict[str, Any]) -> str:
        """Extract message text from various webhook payload formats."""
        # Common message text fields across different platforms
        possible_fields = ["text", "message", "content", "body", "description"]

        for field in possible_fields:
            if field in payload:
                text = payload[field]
                if isinstance(text, str):
                    return text
                elif isinstance(text, dict) and "text" in text:
                    return text["text"]

        # Handle nested event structures (Slack, Discord, etc.)
        if "event" in payload and isinstance(payload["event"], dict):
            return self._extract_message_text(payload["event"])

        return ""

    def _extract_user_info(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Extract user information from webhook payload."""
        user_info = {}

        # Common user fields
        if "user" in payload:
            user = payload["user"]
            if isinstance(user, dict):
                user_info.update(
                    {
                        "user_id": user.get("id", ""),
                        "username": user.get("name", user.get("username", "")),
                        "display_name": user.get("display_name", user.get("real_name", "")),
                    }
                )
            elif isinstance(user, str):
                user_info["user_id"] = user

        # Handle nested event structures
        if "event" in payload and isinstance(payload["event"], dict):
            user_info.update(self._extract_user_info(payload["event"]))

        return user_info

    def _build_classification_prompt(
        self, interaction_context: Dict[str, Any], response_context: Dict[str, Any]
    ) -> str:
        """Build classification prompt for Gemini API."""
        return f"""
You are an AI classifier that determines if webhook responses are relevant to pending human-in-the-loop interactions.

PENDING INTERACTION:
- Type: {interaction_context.get('interaction_type')}
- Channel: {interaction_context.get('channel_type')}
- Title: {interaction_context.get('title', 'N/A')}
- Description: {interaction_context.get('description', 'N/A')}
- Expected Options: {interaction_context.get('approval_options', interaction_context.get('options', 'N/A'))}
- Priority: {interaction_context.get('priority')}
- Created: {interaction_context.get('created_at')}

INCOMING RESPONSE:
- Source: {response_context.get('source_channel')}
- Message: {response_context.get('message_text')}
- User: {response_context.get('user_info', {})}
- Type: {response_context.get('message_type')}
- Timestamp: {response_context.get('timestamp')}

TASK:
Analyze if this webhook response is a relevant reply to the pending interaction.

Consider:
1. Does the message content relate to the interaction title/description?
2. Does it contain expected approval options or requested information?
3. Is it from the expected channel?
4. Is the timing reasonable (not too old/future)?
5. Does it appear to be a human response vs automated/bot message?

Respond with ONLY a JSON object:
{{
    "relevance_score": <float 0.0-1.0>,
    "reasoning": "<brief explanation>",
    "classification": "<relevant|filtered|uncertain>"
}}

Score Guidelines:
- 0.9-1.0: Clearly relevant response (e.g., "Approved", direct answer)
- 0.7-0.8: Likely relevant (e.g., related discussion, partial answer)
- 0.3-0.6: Uncertain (e.g., tangential mention, unclear context)
- 0.0-0.2: Clearly irrelevant (e.g., unrelated chat, automated message)
"""

    async def _call_gemini_api(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini 2.5 Flash Lite API for classification."""
        # TODO: Implement actual Gemini API call
        # For now, return mock response based on simple heuristics

        self.logger.debug("Mock Gemini API call for response classification")

        # Simple mock logic for testing
        if "approv" in prompt.lower() or "reject" in prompt.lower():
            return {
                "relevance_score": 0.85,
                "reasoning": "Contains approval/rejection language relevant to interaction",
                "classification": "relevant",
            }
        elif "yes" in prompt.lower() or "no" in prompt.lower():
            return {
                "relevance_score": 0.75,
                "reasoning": "Contains yes/no response potentially relevant to interaction",
                "classification": "relevant",
            }
        else:
            return {
                "relevance_score": 0.2,
                "reasoning": "No clear relevance indicators found in response",
                "classification": "filtered",
            }

    def _parse_classification_response(self, ai_response: Dict[str, Any]) -> ClassificationResult:
        """Parse AI response into ClassificationResult."""
        try:
            relevance_score = float(ai_response.get("relevance_score", 0.0))
            reasoning = ai_response.get("reasoning", "No reasoning provided")
            classification = ai_response.get("classification", "uncertain")

            # Ensure score is within valid range
            relevance_score = max(0.0, min(1.0, relevance_score))

            # Determine relevance based on threshold
            is_relevant = relevance_score >= self.relevance_threshold

            return ClassificationResult(
                relevance_score=relevance_score,
                reasoning=reasoning,
                is_relevant=is_relevant,
                classification=classification,
            )

        except (ValueError, TypeError) as e:
            self.logger.error(f"Error parsing AI classification response: {str(e)}")
            return ClassificationResult(
                relevance_score=0.0,
                reasoning=f"Parse error: {str(e)}",
                is_relevant=False,
                classification="uncertain",
            )

    def update_threshold(self, new_threshold: float):
        """Update relevance threshold for classification."""
        if 0.0 <= new_threshold <= 1.0:
            old_threshold = self.relevance_threshold
            self.relevance_threshold = new_threshold
            self.logger.info(
                f"Updated relevance threshold: {old_threshold:.2f} → {new_threshold:.2f}"
            )
        else:
            raise ValueError("Threshold must be between 0.0 and 1.0")
