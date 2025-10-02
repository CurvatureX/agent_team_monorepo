"""
Test HIL (Human-in-the-Loop) services for workflow_engine_v2.
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus
from workflow_engine_v2.services.hil_response_classifier import (
    ClassificationResult,
    HILResponseClassifier,
)
from workflow_engine_v2.services.hil_service import HILServiceV2


class TestHILResponseClassifier:
    """Test HIL response classifier functionality."""

    @pytest.fixture
    def classifier(self):
        return HILResponseClassifier()

    @pytest.mark.asyncio
    async def test_classify_relevant_response(self, classifier):
        """Test classification of relevant response."""
        interaction = {
            "execution_id": "exec_123",
            "node_id": "hil_node_1",
            "channel": "slack",
            "request_time": datetime.utcnow().isoformat(),
            "context": {"question": "Do you approve this change?"},
        }

        webhook_payload = {
            "user_id": "user123",
            "channel_id": "C123456",
            "text": "Yes, I approve this change",
            "timestamp": (datetime.utcnow() + timedelta(minutes=2)).isoformat(),
        }

        result = await classifier.classify_response_relevance(interaction, webhook_payload)

        assert isinstance(result, ClassificationResult)
        assert result.is_relevant is True
        assert result.confidence > 0.7  # Should be high confidence
        assert "timing" in result.reasoning_factors
        assert "content_match" in result.reasoning_factors

    @pytest.mark.asyncio
    async def test_classify_irrelevant_response(self, classifier):
        """Test classification of irrelevant response."""
        interaction = {
            "execution_id": "exec_123",
            "node_id": "hil_node_1",
            "channel": "slack",
            "request_time": datetime.utcnow().isoformat(),
            "context": {"question": "Do you approve the budget?"},
        }

        webhook_payload = {
            "user_id": "different_user",
            "channel_id": "different_channel",
            "text": "What's for lunch today?",
            "timestamp": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        }

        result = await classifier.classify_response_relevance(interaction, webhook_payload)

        assert result.is_relevant is False
        assert result.confidence > 0.7  # Should be confident it's not relevant
        assert "timing" in result.reasoning_factors
        assert "content_mismatch" in result.reasoning_factors

    @pytest.mark.asyncio
    async def test_timing_factor_analysis(self, classifier):
        """Test timing factor in classification."""
        base_time = datetime.utcnow()
        interaction = {
            "execution_id": "exec_123",
            "node_id": "hil_node_1",
            "request_time": base_time.isoformat(),
            "context": {"question": "Approve?"},
        }

        # Test immediate response (high timing score)
        immediate_payload = {
            "text": "approved",
            "timestamp": (base_time + timedelta(seconds=30)).isoformat(),
        }

        result = await classifier.classify_response_relevance(interaction, immediate_payload)
        timing_score = result.classification_details["timing_score"]
        assert timing_score > 0.8

        # Test delayed response (lower timing score)
        delayed_payload = {
            "text": "approved",
            "timestamp": (base_time + timedelta(hours=6)).isoformat(),
        }

        result = await classifier.classify_response_relevance(interaction, delayed_payload)
        timing_score = result.classification_details["timing_score"]
        assert timing_score < 0.5

    @pytest.mark.asyncio
    async def test_content_similarity_analysis(self, classifier):
        """Test content similarity analysis."""
        interaction = {
            "execution_id": "exec_123",
            "node_id": "hil_node_1",
            "request_time": datetime.utcnow().isoformat(),
            "context": {"question": "Do you approve the deployment to production?"},
        }

        # Test high content similarity
        similar_payload = {
            "text": "Yes, I approve the production deployment",
            "timestamp": datetime.utcnow().isoformat(),
        }

        result = await classifier.classify_response_relevance(interaction, similar_payload)
        content_score = result.classification_details["content_similarity_score"]
        assert content_score > 0.7

        # Test low content similarity
        dissimilar_payload = {
            "text": "The weather is nice today",
            "timestamp": datetime.utcnow().isoformat(),
        }

        result = await classifier.classify_response_relevance(interaction, dissimilar_payload)
        content_score = result.classification_details["content_similarity_score"]
        assert content_score < 0.3

    @pytest.mark.asyncio
    async def test_context_matching(self, classifier):
        """Test context-based matching."""
        interaction = {
            "execution_id": "exec_123",
            "node_id": "hil_node_1",
            "channel": "slack",
            "user_id": "user123",
            "request_time": datetime.utcnow().isoformat(),
            "context": {"expected_response_type": "approval"},
        }

        # Test matching context
        matching_payload = {
            "user_id": "user123",
            "channel_id": "slack_channel",
            "text": "approved",
            "timestamp": datetime.utcnow().isoformat(),
        }

        result = await classifier.classify_response_relevance(interaction, matching_payload)
        context_score = result.classification_details["context_match_score"]
        assert context_score > 0.5

    def test_keyword_extraction(self, classifier):
        """Test keyword extraction from text."""
        text = "Please approve the deployment to production environment for version 2.1"
        keywords = classifier._extract_keywords(text)

        expected_keywords = {"approve", "deployment", "production", "environment", "version"}
        assert expected_keywords.issubset(set(keywords))

    def test_calculate_text_similarity(self, classifier):
        """Test text similarity calculation."""
        text1 = "approve the deployment"
        text2 = "I approve the deployment to production"
        text3 = "reject the request"

        similarity_high = classifier._calculate_text_similarity(text1, text2)
        similarity_low = classifier._calculate_text_similarity(text1, text3)

        assert similarity_high > similarity_low
        assert 0 <= similarity_high <= 1
        assert 0 <= similarity_low <= 1


class TestHILServiceV2:
    """Test HIL service functionality."""

    @pytest.fixture
    def hil_service(self):
        return HILServiceV2()

    @pytest.fixture
    def mock_classifier(self):
        classifier = MagicMock()
        classifier.classify_response_relevance = AsyncMock()
        return classifier

    @pytest.mark.asyncio
    async def test_create_interaction(self, hil_service):
        """Test creating a new HIL interaction."""
        interaction_data = {
            "execution_id": "exec_123",
            "node_id": "hil_node_1",
            "workflow_id": "workflow_456",
            "user_id": "user789",
            "channel": "slack",
            "message": "Do you approve this change?",
            "timeout_seconds": 3600,
        }

        interaction_id = await hil_service.create_interaction(interaction_data)
        assert interaction_id is not None
        assert interaction_id.startswith("hil_")

        # Verify interaction was stored
        interaction = await hil_service.get_interaction(interaction_id)
        assert interaction is not None
        assert interaction["execution_id"] == "exec_123"
        assert interaction["status"] == "waiting"

    @pytest.mark.asyncio
    async def test_process_response(self, hil_service, mock_classifier):
        """Test processing a response to HIL interaction."""
        # Create interaction first
        interaction_data = {
            "execution_id": "exec_123",
            "node_id": "hil_node_1",
            "workflow_id": "workflow_456",
            "channel": "slack",
            "message": "Approve?",
            "timeout_seconds": 3600,
        }

        interaction_id = await hil_service.create_interaction(interaction_data)

        # Mock classifier to return relevant
        mock_classifier.classify_response_relevance.return_value = ClassificationResult(
            is_relevant=True,
            confidence=0.9,
            reasoning_factors=["timing", "content_match"],
            classification_details={"timing_score": 0.8, "content_similarity_score": 0.9},
        )

        with patch.object(hil_service, "classifier", mock_classifier):
            response_data = {
                "user_id": "user123",
                "text": "Yes, approved",
                "timestamp": datetime.utcnow().isoformat(),
            }

            result = await hil_service.process_response(interaction_id, response_data)

            assert result["processed"] is True
            assert result["classification"]["is_relevant"] is True
            assert result["classification"]["confidence"] == 0.9

            # Verify interaction status was updated
            updated_interaction = await hil_service.get_interaction(interaction_id)
            assert updated_interaction["status"] == "completed"
            assert updated_interaction["response"]["text"] == "Yes, approved"

    @pytest.mark.asyncio
    async def test_process_irrelevant_response(self, hil_service, mock_classifier):
        """Test processing an irrelevant response."""
        interaction_data = {
            "execution_id": "exec_456",
            "node_id": "hil_node_2",
            "channel": "slack",
            "message": "Approve budget?",
            "timeout_seconds": 3600,
        }

        interaction_id = await hil_service.create_interaction(interaction_data)

        # Mock classifier to return irrelevant
        mock_classifier.classify_response_relevance.return_value = ClassificationResult(
            is_relevant=False,
            confidence=0.8,
            reasoning_factors=["content_mismatch", "timing"],
            classification_details={"content_similarity_score": 0.1},
        )

        with patch.object(hil_service, "classifier", mock_classifier):
            response_data = {
                "user_id": "different_user",
                "text": "What's the weather like?",
                "timestamp": datetime.utcnow().isoformat(),
            }

            result = await hil_service.process_response(interaction_id, response_data)

            assert result["processed"] is False
            assert result["classification"]["is_relevant"] is False

            # Verify interaction status remains waiting
            interaction = await hil_service.get_interaction(interaction_id)
            assert interaction["status"] == "waiting"

    @pytest.mark.asyncio
    async def test_timeout_interaction(self, hil_service):
        """Test timing out an interaction."""
        # Create interaction with short timeout
        interaction_data = {
            "execution_id": "exec_timeout",
            "node_id": "hil_timeout",
            "channel": "slack",
            "message": "Quick decision needed",
            "timeout_seconds": 1,  # 1 second timeout
        }

        interaction_id = await hil_service.create_interaction(interaction_data)

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Process timeout
        result = await hil_service.handle_timeout(interaction_id)
        assert result["timed_out"] is True

        # Verify interaction status
        interaction = await hil_service.get_interaction(interaction_id)
        assert interaction["status"] == "timeout"

    @pytest.mark.asyncio
    async def test_list_active_interactions(self, hil_service):
        """Test listing active interactions."""
        # Create multiple interactions
        for i in range(3):
            await hil_service.create_interaction(
                {
                    "execution_id": f"exec_{i}",
                    "node_id": f"node_{i}",
                    "channel": "slack",
                    "message": f"Message {i}",
                    "timeout_seconds": 3600,
                }
            )

        active_interactions = await hil_service.list_active_interactions()
        assert len(active_interactions) >= 3

        # All should be in waiting status
        for interaction in active_interactions:
            assert interaction["status"] == "waiting"

    @pytest.mark.asyncio
    async def test_interaction_statistics(self, hil_service):
        """Test getting interaction statistics."""
        # Create and complete some interactions
        for i in range(2):
            interaction_id = await hil_service.create_interaction(
                {
                    "execution_id": f"stat_exec_{i}",
                    "node_id": f"stat_node_{i}",
                    "channel": "slack",
                    "message": f"Stat message {i}",
                    "timeout_seconds": 3600,
                }
            )

            # Mark as completed
            await hil_service._update_interaction_status(interaction_id, "completed")

        # Create one timeout interaction
        timeout_id = await hil_service.create_interaction(
            {
                "execution_id": "timeout_exec",
                "node_id": "timeout_node",
                "channel": "slack",
                "message": "Timeout message",
                "timeout_seconds": 1,
            }
        )
        await hil_service._update_interaction_status(timeout_id, "timeout")

        stats = await hil_service.get_interaction_statistics()
        assert stats["total_interactions"] >= 3
        assert stats["completed_interactions"] >= 2
        assert stats["timed_out_interactions"] >= 1

    @pytest.mark.asyncio
    async def test_channel_integration(self, hil_service):
        """Test channel-specific integration features."""
        # Test Slack integration
        slack_data = {
            "execution_id": "slack_exec",
            "node_id": "slack_node",
            "channel": "slack",
            "channel_config": {"channel_id": "C123456", "thread_ts": "1234567890.123456"},
            "message": "Slack approval needed",
            "timeout_seconds": 3600,
        }

        interaction_id = await hil_service.create_interaction(slack_data)
        interaction = await hil_service.get_interaction(interaction_id)

        assert interaction["channel"] == "slack"
        assert interaction["channel_config"]["channel_id"] == "C123456"

    @pytest.mark.asyncio
    async def test_error_handling(self, hil_service):
        """Test error handling in HIL service."""
        # Test getting non-existent interaction
        result = await hil_service.get_interaction("non_existent_id")
        assert result is None

        # Test processing response for non-existent interaction
        response_data = {"user_id": "user123", "text": "response"}
        result = await hil_service.process_response("non_existent_id", response_data)
        assert result["error"] is not None
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_interaction_cleanup(self, hil_service):
        """Test cleanup of old interactions."""
        # Create old interaction
        old_interaction_data = {
            "execution_id": "old_exec",
            "node_id": "old_node",
            "channel": "slack",
            "message": "Old message",
            "timeout_seconds": 3600,
        }

        interaction_id = await hil_service.create_interaction(old_interaction_data)

        # Manually set old timestamp
        interaction = await hil_service.get_interaction(interaction_id)
        old_time = datetime.utcnow() - timedelta(days=8)
        await hil_service._update_interaction_timestamp(interaction_id, old_time)

        # Run cleanup (should remove interactions older than 7 days)
        cleaned_count = await hil_service.cleanup_old_interactions(older_than_days=7)
        assert cleaned_count >= 1

        # Verify interaction was removed
        result = await hil_service.get_interaction(interaction_id)
        assert result is None
