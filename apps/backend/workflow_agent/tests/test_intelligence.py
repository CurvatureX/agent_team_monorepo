"""
Tests for Intelligence engines (intelligence.py)
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.state import (
    CapabilityAnalysis,
    GapSeverity,
    Solution,
    SolutionReliability,
    SolutionType,
)
from core.intelligence import IntelligentAnalyzer, IntelligentNegotiator


class TestIntelligentAnalyzer:
    """Test cases for IntelligentAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        """Create IntelligentAnalyzer instance for testing"""
        with patch("core.intelligence.IntelligentAnalyzer._setup_llm") as mock_setup_llm, patch(
            "core.intelligence.get_node_knowledge_rag"
        ) as mock_get_rag:
            mock_setup_llm.return_value = MagicMock()
            mock_get_rag.return_value = MagicMock()
            yield IntelligentAnalyzer()

    @pytest.fixture
    def sample_user_input(self):
        """Sample user input for testing"""
        return "每天定时检查Gmail邮箱，有客户邮件就存储到Notion数据库并发Slack通知"

    @pytest.fixture
    def sample_context(self):
        """Sample context for testing"""
        return {
            "user_preferences": {"email_provider": "gmail"},
            "business_domain": "customer_support",
            "technical_level": "beginner",
        }

    @pytest.fixture
    def sample_capability_analysis(self):
        """Sample capability analysis for testing"""
        return CapabilityAnalysis(
            required_capabilities=["email_monitoring", "notion_integration", "slack_messaging"],
            available_capabilities=["email_monitoring", "slack_messaging"],
            capability_gaps=["notion_integration"],
            gap_severity={"notion_integration": GapSeverity.MEDIUM},
            potential_solutions={
                "notion_integration": [
                    Solution(
                        type=SolutionType.API_INTEGRATION,
                        complexity=5,
                        setup_time="2-3小时",
                        requires_user_action="需要Notion API密钥",
                        reliability=SolutionReliability.HIGH,
                        description="使用Notion API直接集成",
                    )
                ]
            },
            complexity_scores={"notion_integration": 5},
        )

    def test_analyzer_creation(self, analyzer):
        """Test if the analyzer fixture is created correctly."""
        assert analyzer is not None


class TestIntelligentNegotiator:
    """Test cases for IntelligentNegotiator"""

    @pytest.fixture
    def negotiator(self):
        """Create IntelligentNegotiator instance for testing"""
        with patch("core.intelligence.IntelligentNegotiator._setup_llm") as mock_setup_llm, patch(
            "core.intelligence.get_node_knowledge_rag"
        ) as mock_get_rag:
            mock_setup_llm.return_value = MagicMock()
            mock_get_rag.return_value = MagicMock()
            yield IntelligentNegotiator()

    @pytest.fixture
    def sample_gaps(self):
        """Sample capability gaps for testing"""
        return ["notion_integration", "twitter_api", "custom_ai_model"]

    @pytest.fixture
    def sample_capability_analysis(self):
        """Sample capability analysis for testing"""
        return CapabilityAnalysis(
            required_capabilities=["email_monitoring", "notion_integration", "twitter_api"],
            available_capabilities=["email_monitoring"],
            capability_gaps=["notion_integration", "twitter_api"],
            gap_severity={
                "notion_integration": GapSeverity.MEDIUM,
                "twitter_api": GapSeverity.HIGH,
            },
            potential_solutions={
                "notion_integration": [
                    Solution(
                        type=SolutionType.API_INTEGRATION,
                        complexity=5,
                        setup_time="2-3小时",
                        requires_user_action="需要Notion API密钥",
                        reliability=SolutionReliability.HIGH,
                        description="使用Notion API",
                    )
                ],
                "twitter_api": [
                    Solution(
                        type=SolutionType.EXTERNAL_SERVICE,
                        complexity=8,
                        setup_time="1-2天",
                        requires_user_action="需要Twitter开发者申请",
                        reliability=SolutionReliability.MEDIUM,
                        description="使用Twitter API v2",
                    )
                ],
            },
            complexity_scores={"notion_integration": 5, "twitter_api": 8},
        )

    def test_negotiator_creation(self, negotiator):
        """Test if the negotiator fixture is created correctly."""
        assert negotiator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
