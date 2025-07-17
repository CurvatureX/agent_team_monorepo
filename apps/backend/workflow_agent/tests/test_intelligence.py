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
        return IntelligentAnalyzer()

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

    def test_setup_llm_openai(self, analyzer):
        """Test LLM setup with OpenAI"""
        with (
            patch("core.intelligence.settings") as mock_settings,
            patch("core.intelligence.ChatOpenAI") as mock_openai,
        ):
            mock_settings.DEFAULT_MODEL_PROVIDER = "openai"
            mock_settings.DEFAULT_MODEL_NAME = "gpt-4"
            mock_settings.OPENAI_API_KEY = "test-key"

            llm = analyzer._setup_llm()
            mock_openai.assert_called_once()

    def test_setup_llm_anthropic(self, analyzer):
        """Test LLM setup with Anthropic"""
        with (
            patch("core.intelligence.settings") as mock_settings,
            patch("core.intelligence.ChatAnthropic") as mock_anthropic,
        ):
            mock_settings.DEFAULT_MODEL_PROVIDER = "anthropic"
            mock_settings.DEFAULT_MODEL_NAME = "claude-3-sonnet"
            mock_settings.ANTHROPIC_API_KEY = "test-key"

            llm = analyzer._setup_llm()
            mock_anthropic.assert_called_once()

    def test_setup_llm_invalid_provider(self, analyzer):
        """Test LLM setup with invalid provider"""
        with patch("core.intelligence.settings") as mock_settings:
            mock_settings.DEFAULT_MODEL_PROVIDER = "invalid"

            with pytest.raises(ValueError, match="Unsupported model provider"):
                analyzer._setup_llm()

    @pytest.mark.asyncio
    async def test_parse_intent_basic(self, analyzer, sample_user_input):
        """Test basic intent parsing"""
        with patch.object(analyzer.llm, "ainvoke") as mock_llm:
            mock_llm.return_value = MagicMock(
                content='{"primary_goal": "邮箱监控", "secondary_goals": ["数据存储"], "constraints": ["使用Gmail"]}'
            )

            result = await analyzer.parse_intent(sample_user_input)

            assert result is not None
            assert "primary_goal" in result
            assert "secondary_goals" in result
            assert "constraints" in result
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_intent_with_context(self, analyzer, sample_user_input, sample_context):
        """Test intent parsing with context"""
        with patch.object(analyzer.llm, "ainvoke") as mock_llm:
            mock_llm.return_value = MagicMock(
                content='{"primary_goal": "customer support automation"}'
            )

            result = await analyzer.parse_intent(sample_user_input, sample_context)

            # Check that context was included in the prompt
            call_args = mock_llm.call_args[0][0]
            human_message = next(
                msg
                for msg in call_args
                if hasattr(msg, "content") and sample_user_input in msg.content
            )
            assert human_message is not None

    @pytest.mark.asyncio
    async def test_parse_intent_invalid_json(self, analyzer, sample_user_input):
        """Test intent parsing with invalid JSON response"""
        with patch.object(analyzer.llm, "ainvoke") as mock_llm:
            mock_llm.return_value = MagicMock(content="invalid json response")

            result = await analyzer.parse_intent(sample_user_input)

            # Should return default structure on JSON error
            assert result is not None
            assert "primary_goal" in result

    @pytest.mark.asyncio
    async def test_analyze_capabilities_no_gaps(self, analyzer):
        """Test capability analysis with no gaps"""
        parsed_intent = {
            "primary_goal": "发送邮件通知",
            "secondary_goals": [],
            "constraints": ["使用Gmail"],
        }

        with (
            patch.object(analyzer, "_extract_required_capabilities") as mock_extract,
            patch.object(analyzer, "_check_capability_gaps") as mock_check,
        ):
            mock_extract.return_value = ["email_sending"]
            mock_check.return_value = ([], {}, {})

            result = await analyzer.analyze_capabilities(parsed_intent)

            assert result["capability_gaps"] == []
            assert len(result["potential_solutions"]) == 0

    @pytest.mark.asyncio
    async def test_analyze_capabilities_with_gaps(self, analyzer):
        """Test capability analysis with gaps"""
        parsed_intent = {
            "primary_goal": "监控Twitter并分析情感",
            "secondary_goals": [],
            "constraints": [],
        }

        with (
            patch.object(analyzer, "_extract_required_capabilities") as mock_extract,
            patch.object(analyzer, "_check_capability_gaps") as mock_check,
            patch.object(analyzer, "_search_solutions_for_gaps") as mock_search,
        ):
            mock_extract.return_value = ["twitter_monitoring", "sentiment_analysis"]
            mock_check.return_value = (
                ["twitter_monitoring"],
                {"twitter_monitoring": GapSeverity.HIGH},
                {"twitter_monitoring": 8},
            )
            mock_search.return_value = {
                "twitter_monitoring": [
                    Solution(
                        type=SolutionType.EXTERNAL_SERVICE,
                        complexity=8,
                        setup_time="1-2天",
                        requires_user_action="需要Twitter API申请",
                        reliability=SolutionReliability.MEDIUM,
                        description="使用Twitter API v2",
                    )
                ]
            }

            result = await analyzer.analyze_capabilities(parsed_intent)

            assert "twitter_monitoring" in result["capability_gaps"]
            assert result["gap_severity"]["twitter_monitoring"] == GapSeverity.HIGH
            assert len(result["potential_solutions"]["twitter_monitoring"]) > 0

    def test_extract_required_capabilities_email(self, analyzer):
        """Test capability extraction for email-related tasks"""
        parsed_intent = {
            "primary_goal": "监控邮箱获取客户反馈",
            "secondary_goals": ["发送确认邮件"],
            "constraints": ["使用Gmail"],
        }

        result = analyzer._extract_required_capabilities(parsed_intent)

        assert "email_monitoring" in result
        assert "email_sending" in result

    def test_extract_required_capabilities_data_processing(self, analyzer):
        """Test capability extraction for data processing"""
        parsed_intent = {
            "primary_goal": "从数据库提取数据并生成报告",
            "secondary_goals": ["数据清洗", "格式转换"],
            "constraints": [],
        }

        result = analyzer._extract_required_capabilities(parsed_intent)

        assert "database_integration" in result
        assert "data_processing" in result
        assert "report_generation" in result

    def test_check_capability_gaps(self, analyzer):
        """Test capability gap checking"""
        required_capabilities = ["email_monitoring", "notion_integration", "twitter_api"]

        gaps, severity, complexity = analyzer._check_capability_gaps(required_capabilities)

        # Should identify gaps for non-native capabilities
        assert "notion_integration" in gaps  # Medium complexity
        assert "twitter_api" in gaps  # High complexity, external service

        # Check severity assignment
        assert severity.get("twitter_api") == GapSeverity.HIGH

    def test_assess_gap_severity(self, analyzer):
        """Test gap severity assessment"""
        # Test different capability types
        assert analyzer._assess_gap_severity("email_monitoring") == GapSeverity.LOW  # Native
        assert analyzer._assess_gap_severity("notion_integration") == GapSeverity.MEDIUM  # API
        assert analyzer._assess_gap_severity("twitter_api") == GapSeverity.HIGH  # External
        assert analyzer._assess_gap_severity("custom_ai_model") == GapSeverity.CRITICAL  # Complex

    def test_search_solutions_for_gaps(self, analyzer):
        """Test solution searching for capability gaps"""
        gaps = ["notion_integration", "twitter_api"]

        result = analyzer._search_solutions_for_gaps(gaps)

        assert "notion_integration" in result
        assert "twitter_api" in result

        # Check solution types
        notion_solutions = result["notion_integration"]
        assert any(sol["type"] == SolutionType.API_INTEGRATION for sol in notion_solutions)

    def test_generate_api_integration_solution(self, analyzer):
        """Test API integration solution generation"""
        result = analyzer._generate_api_integration_solution("notion_integration")

        assert result["type"] == SolutionType.API_INTEGRATION
        assert result["complexity"] >= 3
        assert "API" in result["description"]

    def test_generate_external_service_solution(self, analyzer):
        """Test external service solution generation"""
        result = analyzer._generate_external_service_solution("twitter_api")

        assert result["type"] == SolutionType.EXTERNAL_SERVICE
        assert result["complexity"] >= 7
        assert result["reliability"] in [SolutionReliability.LOW, SolutionReliability.MEDIUM]

    @pytest.mark.asyncio
    async def test_identify_constraints_and_preferences(self, analyzer):
        """Test constraint and preference identification"""
        parsed_intent = {
            "primary_goal": "自动化客户服务",
            "constraints": ["使用Gmail", "预算有限", "简单配置"],
            "user_preferences": {"response_speed": "fast"},
        }

        result = await analyzer.identify_constraints_and_preferences(parsed_intent)

        assert len(result) > 0
        gmail_constraint = next((c for c in result if "gmail" in c["description"].lower()), None)
        assert gmail_constraint is not None
        assert gmail_constraint["type"] == "technical"

    def test_categorize_constraint_technical(self, analyzer):
        """Test technical constraint categorization"""
        constraint = "必须使用Gmail邮箱"
        result = analyzer._categorize_constraint(constraint)

        assert result["type"] == "technical"
        assert result["severity"] == GapSeverity.MEDIUM

    def test_categorize_constraint_business(self, analyzer):
        """Test business constraint categorization"""
        constraint = "预算不能超过1000元"
        result = analyzer._categorize_constraint(constraint)

        assert result["type"] == "business"
        assert result["severity"] == GapSeverity.HIGH

    def test_categorize_constraint_user(self, analyzer):
        """Test user constraint categorization"""
        constraint = "界面要简单易用"
        result = analyzer._categorize_constraint(constraint)

        assert result["type"] == "user_experience"
        assert result["severity"] == GapSeverity.LOW


class TestIntelligentNegotiator:
    """Test cases for IntelligentNegotiator"""

    @pytest.fixture
    def negotiator(self):
        """Create IntelligentNegotiator instance for testing"""
        return IntelligentNegotiator()

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

    def test_setup_llm_openai(self, negotiator):
        """Test LLM setup with OpenAI"""
        with (
            patch("core.intelligence.settings") as mock_settings,
            patch("core.intelligence.ChatOpenAI") as mock_openai,
        ):
            mock_settings.DEFAULT_MODEL_PROVIDER = "openai"
            mock_settings.DEFAULT_MODEL_NAME = "gpt-4"
            mock_settings.OPENAI_API_KEY = "test-key"

            llm = negotiator._setup_llm()
            mock_openai.assert_called_once()

    def test_load_negotiation_patterns(self, negotiator):
        """Test negotiation patterns loading"""
        patterns = negotiator._load_negotiation_patterns()

        assert "capability_gap_negotiation" in patterns
        assert "complexity_negotiation" in patterns

        gap_patterns = patterns["capability_gap_negotiation"]
        assert "high_severity" in gap_patterns
        assert "medium_severity" in gap_patterns
        assert "low_severity" in gap_patterns

    @pytest.mark.asyncio
    async def test_generate_contextual_questions_mixed_severity(
        self, negotiator, sample_gaps, sample_capability_analysis
    ):
        """Test generating questions for mixed severity gaps"""
        with (
            patch.object(negotiator, "_generate_high_severity_question") as mock_high,
            patch.object(negotiator, "_generate_medium_severity_question") as mock_medium,
            patch.object(negotiator, "_calculate_question_priority") as mock_priority,
        ):
            mock_high.return_value = "如何处理Twitter API集成的复杂性？"
            mock_medium.return_value = "是否接受Notion API集成方案？"
            mock_priority.return_value = 1

            # Update gaps to match capability analysis
            gaps = ["notion_integration", "twitter_api"]

            result = await negotiator.generate_contextual_questions(
                gaps, sample_capability_analysis
            )

            assert len(result) > 0
            assert isinstance(result, list)
            mock_medium.assert_called_once()  # For notion_integration (medium severity)
            mock_high.assert_called_once()  # For twitter_api (high severity)

    @pytest.mark.asyncio
    async def test_generate_contextual_questions_with_history(
        self, negotiator, sample_capability_analysis
    ):
        """Test generating questions with conversation history"""
        gaps = ["notion_integration"]
        history = [
            {
                "question": "您希望使用哪种存储方案？",
                "user_response": "Notion数据库",
                "timestamp": datetime.now(),
            }
        ]

        with patch.object(negotiator, "_generate_medium_severity_question") as mock_medium:
            mock_medium.return_value = "请确认Notion API密钥配置方式？"

            result = await negotiator.generate_contextual_questions(
                gaps, sample_capability_analysis, history
            )

            assert len(result) > 0
            # History should be passed to question generation
            mock_medium.assert_called_once()
            args = mock_medium.call_args[0]
            assert len(args) >= 3  # gap, solutions, history

    @pytest.mark.asyncio
    async def test_generate_contextual_questions_deduplication(
        self, negotiator, sample_capability_analysis
    ):
        """Test question deduplication and prioritization"""
        gaps = ["notion_integration", "notion_integration"]  # Duplicate gap

        with (
            patch.object(negotiator, "_generate_medium_severity_question") as mock_medium,
            patch.object(negotiator, "_calculate_question_priority") as mock_priority,
        ):
            mock_medium.return_value = "重复的问题"
            mock_priority.return_value = 1

            result = await negotiator.generate_contextual_questions(
                gaps, sample_capability_analysis
            )

            # Should deduplicate questions
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_generate_contextual_questions_limit(self, negotiator):
        """Test question limit (max 5 questions)"""
        # Create many gaps to test limit
        gaps = [f"gap_{i}" for i in range(10)]
        capability_analysis = CapabilityAnalysis(
            required_capabilities=gaps,
            available_capabilities=[],
            capability_gaps=gaps,
            gap_severity={gap: GapSeverity.LOW for gap in gaps},
            potential_solutions={gap: [] for gap in gaps},
            complexity_scores={gap: 1 for gap in gaps},
        )

        with (
            patch.object(negotiator, "_generate_low_severity_question") as mock_low,
            patch.object(negotiator, "_calculate_question_priority") as mock_priority,
        ):
            mock_low.return_value = "简单问题"
            mock_priority.return_value = 1

            result = await negotiator.generate_contextual_questions(gaps, capability_analysis)

            # Should limit to 5 questions
            assert len(result) <= 5

    @pytest.mark.asyncio
    async def test_process_user_input_negotiation_continue(
        self, negotiator, sample_capability_analysis
    ):
        """Test processing user input that continues negotiation"""
        context = {
            "stage": "requirement_negotiation",
            "capability_analysis": sample_capability_analysis,
            "negotiation_history": [],
        }
        user_input = "我希望使用Notion存储数据"

        with (
            patch.object(negotiator, "_analyze_user_response") as mock_analyze,
            patch.object(negotiator, "_update_negotiation_context") as mock_update,
            patch.object(negotiator, "_determine_next_negotiation_step") as mock_next,
        ):
            mock_analyze.return_value = {
                "intent": "solution_acceptance",
                "mentioned_solutions": ["notion_integration"],
                "confidence": 0.8,
            }
            mock_update.return_value = context
            mock_next.return_value = {
                "action": "continue_negotiation",
                "next_questions": ["请确认API配置方式？"],
                "reasoning": "需要更多技术细节",
            }

            result = await negotiator.process_user_input(user_input, context)

            assert result["stage"] == "requirement_negotiation"
            assert result["negotiation_complete"] is False
            assert len(result["next_questions"]) > 0

    @pytest.mark.asyncio
    async def test_process_user_input_negotiation_complete(
        self, negotiator, sample_capability_analysis
    ):
        """Test processing user input that completes negotiation"""
        context = {
            "stage": "requirement_negotiation",
            "capability_analysis": sample_capability_analysis,
            "negotiation_history": [
                {
                    "question": "选择存储方案？",
                    "user_response": "Notion",
                    "analysis": {"intent": "solution_acceptance"},
                }
            ],
        }
        user_input = "确认使用Notion API集成方案"

        with (
            patch.object(negotiator, "_analyze_user_response") as mock_analyze,
            patch.object(negotiator, "_determine_next_negotiation_step") as mock_next,
        ):
            mock_analyze.return_value = {"intent": "final_confirmation", "confidence": 0.9}
            mock_next.return_value = {
                "action": "complete_negotiation",
                "final_requirements": "使用Gmail监控，Notion存储，简化配置",
                "reasoning": "所有关键决策已确认",
            }

            result = await negotiator.process_user_input(user_input, context)

            assert result["negotiation_complete"] is True
            assert "final_requirements" in result
            assert len(result.get("next_questions", [])) == 0

    @pytest.mark.asyncio
    async def test_assess_negotiation_completeness_incomplete(
        self, negotiator, sample_capability_analysis
    ):
        """Test negotiation completeness assessment - incomplete"""
        context = {
            "capability_analysis": sample_capability_analysis,
            "negotiation_history": [
                {
                    "question": "选择存储方案？",
                    "user_response": "Notion",
                    "analysis": {"intent": "solution_acceptance"},
                }
            ],
        }

        result = await negotiator.assess_negotiation_completeness(context)

        assert result["complete"] is False
        assert result["confidence_score"] < 0.8
        assert len(result["remaining_gaps"]) > 0

    @pytest.mark.asyncio
    async def test_assess_negotiation_completeness_complete(
        self, negotiator, sample_capability_analysis
    ):
        """Test negotiation completeness assessment - complete"""
        context = {
            "capability_analysis": sample_capability_analysis,
            "negotiation_history": [
                {
                    "question": "选择存储方案？",
                    "user_response": "Notion API",
                    "analysis": {
                        "intent": "solution_acceptance",
                        "mentioned_solutions": ["notion_integration"],
                    },
                },
                {
                    "question": "Twitter集成方案？",
                    "user_response": "暂不需要Twitter功能",
                    "analysis": {"intent": "requirement_modification"},
                },
            ],
        }

        result = await negotiator.assess_negotiation_completeness(context)

        # Should be more complete after addressing multiple gaps
        assert isinstance(result["complete"], bool)
        assert isinstance(result["confidence_score"], float)
        assert 0.0 <= result["confidence_score"] <= 1.0

    def test_calculate_question_priority(self, negotiator, sample_capability_analysis):
        """Test question priority calculation"""
        # High severity gap should have higher priority
        question_high = "如何处理Twitter API的复杂集成？"
        question_low = "是否需要简单的邮件通知？"

        priority_high = negotiator._calculate_question_priority(
            question_high, sample_capability_analysis
        )
        priority_low = negotiator._calculate_question_priority(
            question_low, sample_capability_analysis
        )

        assert isinstance(priority_high, (int, float))
        assert isinstance(priority_low, (int, float))

    @pytest.mark.asyncio
    async def test_generate_high_severity_question(self, negotiator):
        """Test high severity question generation"""
        gap = "twitter_api"
        solutions = [
            Solution(
                type=SolutionType.EXTERNAL_SERVICE,
                complexity=8,
                setup_time="1-2天",
                requires_user_action="需要Twitter开发者申请",
                reliability=SolutionReliability.MEDIUM,
                description="Twitter API v2集成",
            )
        ]
        history = []

        result = await negotiator._generate_high_severity_question(gap, solutions, history)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "twitter" in result.lower() or "api" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_medium_severity_question(self, negotiator):
        """Test medium severity question generation"""
        gap = "notion_integration"
        solutions = [
            Solution(
                type=SolutionType.API_INTEGRATION,
                complexity=5,
                setup_time="2-3小时",
                requires_user_action="需要API密钥",
                reliability=SolutionReliability.HIGH,
                description="Notion API集成",
            )
        ]
        history = []

        result = await negotiator._generate_medium_severity_question(gap, solutions, history)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_low_severity_question(self, negotiator):
        """Test low severity question generation"""
        gap = "simple_notification"
        solutions = [
            Solution(
                type=SolutionType.NATIVE,
                complexity=2,
                setup_time="10分钟",
                requires_user_action="基本配置",
                reliability=SolutionReliability.HIGH,
                description="内置通知功能",
            )
        ]
        history = []

        result = await negotiator._generate_low_severity_question(gap, solutions, history)

        assert isinstance(result, str)
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
