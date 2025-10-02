"""
HIL Response Classifier for workflow_engine_v2.

Provides AI-powered classification of incoming webhook responses to determine
relevance to pending HIL interactions.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.node_enums import GoogleGeminiModel


@dataclass
class ClassificationResult:
    """Result of AI response classification."""

    relevance_score: float  # 0.0-1.0 confidence score
    reasoning: str  # AI explanation of decision
    is_relevant: bool  # True if score >= threshold
    classification: str  # 'relevant', 'filtered', 'uncertain'


class HILResponseClassifierV2:
    """AI-powered classifier to determine webhook response relevance to HIL requests."""

    def __init__(self, relevance_threshold: float = 0.7):
        """Initialize classifier.

        Args:
            relevance_threshold: Minimum score (0.0-1.0) to consider response relevant
        """
        self.logger = logging.getLogger(__name__)
        self.relevance_threshold = relevance_threshold

        # Initialize Gemini client if API key available
        gemini_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            try:
                # Import Gemini provider for AI-powered classification
                from .ai_providers import GeminiProvider

                self.gemini_client = GeminiProvider(gemini_api_key)
                self.logger.info(
                    "Initialized Gemini client for AI-powered HIL response classification"
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to initialize Gemini client: {str(e)}, falling back to heuristic classification"
                )
                self.gemini_client = None
        else:
            self.gemini_client = None
            self.logger.info("No Gemini API key provided, using heuristic classification only")

        self.logger.info(
            f"Initialized HIL Response Classifier with threshold {relevance_threshold}"
        )

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

            # Use AI classification if available, fallback to heuristics
            if self.gemini_client:
                result = await self._ai_classification(interaction_context, response_context)
            else:
                result = await self._heuristic_classification(interaction_context, response_context)

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
            "node_id": interaction.get("node_id"),
            "execution_id": interaction.get("execution_id"),
            "workflow_id": interaction.get("workflow_id"),
            "user_id": interaction.get("user_id"),
            "request_message": request_data.get("message"),
            "request_title": request_data.get("title"),
            "expected_responses": request_data.get("expected_responses", []),
            "keywords": request_data.get("keywords", []),
        }

        return context

    def _extract_response_context(self, webhook_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant context from webhook response for classification."""
        context = {
            "timestamp": webhook_payload.get("timestamp"),
            "channel": webhook_payload.get("channel"),
            "user_id": webhook_payload.get("user_id"),
            "user_name": webhook_payload.get("user_name"),
            "message_text": webhook_payload.get("text", ""),
            "response_type": webhook_payload.get("type"),
            "event_type": webhook_payload.get("event", {}).get("type"),
            "thread_ts": webhook_payload.get("thread_ts"),
            "reaction": webhook_payload.get("reaction"),
        }

        # Extract Slack-specific context
        if "event" in webhook_payload:
            event = webhook_payload["event"]
            context.update(
                {
                    "event_text": event.get("text", ""),
                    "event_user": event.get("user"),
                    "event_channel": event.get("channel"),
                    "event_ts": event.get("ts"),
                }
            )

        return context

    async def _ai_classification(
        self, interaction_context: Dict[str, Any], response_context: Dict[str, Any]
    ) -> ClassificationResult:
        """AI-powered classification using Gemini."""
        try:
            # Build sophisticated classification prompt
            prompt = self._build_classification_prompt(interaction_context, response_context)

            # Call Gemini API for classification
            result = self.gemini_client.generate(
                prompt,
                {
                    "model": "gemini-1.5-flash",
                    "temperature": 0.1,  # Low temperature for consistent classification
                    "max_tokens": 500,
                },
            )

            response_text = result.get("response", "").strip()

            # Parse AI response as JSON
            import json

            try:
                ai_result = json.loads(response_text)

                relevance_score = float(ai_result.get("relevance_score", 0.5))
                reasoning = ai_result.get("reasoning", "AI classification completed")
                classification = ai_result.get("classification", "uncertain")

                # Validate score bounds
                relevance_score = max(0.0, min(1.0, relevance_score))

                # Validate classification values
                if classification not in ["relevant", "filtered", "uncertain"]:
                    classification = "uncertain"

                return ClassificationResult(
                    relevance_score=relevance_score,
                    reasoning=f"AI: {reasoning}",
                    is_relevant=(relevance_score >= self.relevance_threshold),
                    classification=classification,
                )

            except json.JSONDecodeError:
                self.logger.warning(f"AI returned non-JSON response: {response_text}")
                # Fall back to heuristic classification
                return await self._heuristic_classification(interaction_context, response_context)

        except Exception as e:
            self.logger.error(f"AI classification failed: {str(e)}")
            # Fall back to heuristic classification
            return await self._heuristic_classification(interaction_context, response_context)

    def _build_classification_prompt(
        self, interaction_context: Dict[str, Any], response_context: Dict[str, Any]
    ) -> str:
        """Build sophisticated prompt for AI classification."""
        return f"""You are an AI classifier that determines if webhook responses are relevant to pending human-in-the-loop interactions.

PENDING INTERACTION CONTEXT:
- Type: {interaction_context.get('interaction_type', 'unknown')}
- Channel: {interaction_context.get('channel_type', 'unknown')}
- Title: {interaction_context.get('request_title', 'N/A')}
- Message: {interaction_context.get('request_message', 'N/A')}
- Node ID: {interaction_context.get('node_id', 'N/A')}
- User ID: {interaction_context.get('user_id', 'N/A')}
- Created: {interaction_context.get('created_at', 'N/A')}
- Expected Responses: {interaction_context.get('expected_responses', [])}
- Keywords: {interaction_context.get('keywords', [])}

WEBHOOK RESPONSE CONTEXT:
- Message Text: {response_context.get('message_text', 'N/A')}
- Event Text: {response_context.get('event_text', 'N/A')}
- User Name: {response_context.get('user_name', 'N/A')}
- User ID: {response_context.get('user_id', 'N/A')}
- Channel: {response_context.get('channel', 'N/A')}
- Event Channel: {response_context.get('event_channel', 'N/A')}
- Response Type: {response_context.get('response_type', 'N/A')}
- Event Type: {response_context.get('event_type', 'N/A')}
- Timestamp: {response_context.get('timestamp', 'N/A')}
- Thread TS: {response_context.get('thread_ts', 'N/A')}
- Reaction: {response_context.get('reaction', 'N/A')}

CLASSIFICATION TASK:
Analyze if this webhook response is a relevant reply to the pending human-in-the-loop interaction.

Consider these factors:
1. **Content Relevance**: Does the response content relate to the interaction title/message?
2. **Expected Response Pattern**: Does it match expected approval/rejection/input patterns?
3. **Channel Consistency**: Is it from the expected communication channel?
4. **User Context**: Is the responder appropriate for this interaction?
5. **Timing**: Is the response timing reasonable for human interaction?
6. **Response Quality**: Does it appear to be a meaningful human response vs automated/bot?
7. **Thread Context**: Is it properly threaded or associated with the original request?
8. **Action Keywords**: Does it contain approval keywords (approve, yes, reject, no, etc.)?

RESPONSE FORMAT:
Respond with ONLY a valid JSON object in this exact format:
{{"relevance_score": <float between 0.0 and 1.0>, "reasoning": "<detailed explanation of your analysis>", "classification": "<relevant|filtered|uncertain>"}}

Classification Guidelines:
- "relevant": High confidence this is a direct response (score >= 0.7)
- "filtered": High confidence this is NOT a response (score <= 0.3)
- "uncertain": Unclear or ambiguous response (score 0.3-0.7)

Be thorough in your reasoning and consider all contextual factors."""

    async def _heuristic_classification(
        self, interaction_context: Dict[str, Any], response_context: Dict[str, Any]
    ) -> ClassificationResult:
        """Heuristic-based classification as fallback."""
        score = 0.0
        reasons = []

        # Channel matching
        if self._channels_match(interaction_context, response_context):
            score += 0.3
            reasons.append("channel match")

        # User context matching
        if self._user_context_matches(interaction_context, response_context):
            score += 0.2
            reasons.append("user context")

        # Timing relevance
        timing_score = self._calculate_timing_relevance(interaction_context, response_context)
        score += timing_score * 0.2
        if timing_score > 0.5:
            reasons.append("recent timing")

        # Content relevance
        content_score = self._calculate_content_relevance(interaction_context, response_context)
        score += content_score * 0.3
        if content_score > 0.5:
            reasons.append("content relevance")

        # Ensure score is between 0 and 1
        score = min(1.0, max(0.0, score))

        is_relevant = score >= self.relevance_threshold
        classification = "relevant" if is_relevant else ("uncertain" if score > 0.3 else "filtered")

        reasoning = f"Score: {score:.2f} based on: {', '.join(reasons) if reasons else 'no strong indicators'}"

        return ClassificationResult(
            relevance_score=score,
            reasoning=reasoning,
            is_relevant=is_relevant,
            classification=classification,
        )

    def _channels_match(self, interaction: Dict[str, Any], response: Dict[str, Any]) -> bool:
        """Check if channels match between interaction and response."""
        interaction_channel = interaction.get("channel_type")
        response_channel = response.get("channel")

        if not interaction_channel or not response_channel:
            return False

        # Direct channel ID match
        if interaction_channel == response_channel:
            return True

        # Channel type matching (e.g., 'slack' matches slack channels)
        if interaction_channel.lower() == "slack" and response_channel.startswith("C"):
            return True

        return False

    def _user_context_matches(self, interaction: Dict[str, Any], response: Dict[str, Any]) -> bool:
        """Check if user context suggests relevance."""
        interaction_user = interaction.get("user_id")
        response_user = response.get("user_id") or response.get("event_user")

        # Same user responding
        if interaction_user and response_user and interaction_user == response_user:
            return True

        return False

    def _calculate_timing_relevance(
        self, interaction: Dict[str, Any], response: Dict[str, Any]
    ) -> float:
        """Calculate timing relevance score (0.0-1.0)."""
        try:
            from datetime import datetime, timezone

            interaction_time_str = interaction.get("created_at")
            response_timestamp = response.get("timestamp")

            if not interaction_time_str or not response_timestamp:
                return 0.0

            # Parse timestamps
            if isinstance(interaction_time_str, str):
                interaction_time = datetime.fromisoformat(
                    interaction_time_str.replace("Z", "+00:00")
                )
            else:
                interaction_time = interaction_time_str

            if isinstance(response_timestamp, (int, float)):
                response_time = datetime.fromtimestamp(response_timestamp, tz=timezone.utc)
            else:
                response_time = datetime.fromisoformat(
                    str(response_timestamp).replace("Z", "+00:00")
                )

            # Calculate time difference in seconds
            time_diff = abs((response_time - interaction_time).total_seconds())

            # Score based on recency (higher score for more recent responses)
            if time_diff < 60:  # Within 1 minute
                return 1.0
            elif time_diff < 300:  # Within 5 minutes
                return 0.8
            elif time_diff < 1800:  # Within 30 minutes
                return 0.6
            elif time_diff < 3600:  # Within 1 hour
                return 0.4
            elif time_diff < 21600:  # Within 6 hours
                return 0.2
            else:
                return 0.1

        except Exception:
            return 0.0

    def _calculate_content_relevance(
        self, interaction: Dict[str, Any], response: Dict[str, Any]
    ) -> float:
        """Calculate content relevance score (0.0-1.0)."""
        try:
            # Get text from both contexts
            request_text = (interaction.get("request_message", "") or "").lower()
            response_text = (
                response.get("message_text", "") or response.get("event_text", "") or ""
            ).lower()

            if not request_text or not response_text:
                return 0.0

            # Check for direct keywords
            keywords = interaction.get("keywords", [])
            keyword_matches = 0
            for keyword in keywords:
                if keyword.lower() in response_text:
                    keyword_matches += 1

            keyword_score = min(1.0, keyword_matches / max(1, len(keywords))) if keywords else 0.0

            # Check for expected responses
            expected_responses = interaction.get("expected_responses", [])
            response_matches = 0
            for expected in expected_responses:
                if expected.lower() in response_text:
                    response_matches += 1

            expected_score = (
                min(1.0, response_matches / max(1, len(expected_responses)))
                if expected_responses
                else 0.0
            )

            # Simple word overlap
            request_words = set(request_text.split())
            response_words = set(response_text.split())
            common_words = request_words.intersection(response_words)

            # Filter out common stop words
            stop_words = {
                "the",
                "a",
                "an",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
            }
            meaningful_common = common_words - stop_words

            overlap_score = min(1.0, len(meaningful_common) / max(1, len(request_words)))

            # Combine scores with weights
            final_score = keyword_score * 0.4 + expected_score * 0.4 + overlap_score * 0.2

            return final_score

        except Exception:
            return 0.0

    async def get_classification_stats(self) -> Dict[str, Any]:
        """Get classification statistics (for monitoring)."""
        return {
            "classifier_type": "heuristic",
            "threshold": self.relevance_threshold,
            "features": [
                "channel_matching",
                "user_context",
                "timing_relevance",
                "content_relevance",
            ],
        }


__all__ = ["HILResponseClassifierV2", "ClassificationResult"]
