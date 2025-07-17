"""
Tests for IntelligentDesigner (design_engine.py)
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.design_engine import DSLValidator, IntelligentDesigner, WorkflowOrchestrator


class TestIntelligentDesigner:
    """Test cases for IntelligentDesigner"""

    @pytest.fixture
    def designer(self):
        """Create IntelligentDesigner instance for testing"""
        return IntelligentDesigner()

    @pytest.fixture
    def sample_requirements(self):
        """Sample requirements for testing"""
        return {
            "primary_goal": "监控邮箱，将客户邮件存储到Notion",
            "secondary_goals": ["发送Slack通知"],
            "constraints": ["使用Gmail", "简单关键词过滤"],
            "user_decisions": [
                {"question": "关键词过滤方案", "answer": "keyword_filtering", "confidence": 0.8}
            ],
        }

    @pytest.fixture
    def sample_task_tree(self):
        """Sample task tree for testing"""
        return {
            "root_task": "邮箱监控自动化",
            "subtasks": [
                {
                    "name": "邮箱监控",
                    "description": "定时检查Gmail新邮件",
                    "estimated_complexity": 3,
                    "critical_path": True,
                },
                {
                    "name": "客户识别",
                    "description": "使用关键词识别客户邮件",
                    "estimated_complexity": 5,
                    "critical_path": True,
                },
                {
                    "name": "数据存储",
                    "description": "将邮件信息存储到Notion",
                    "estimated_complexity": 4,
                    "critical_path": True,
                },
            ],
            "dependencies": [
                {"from": "邮箱监控", "to": "客户识别", "type": "sequential"},
                {"from": "客户识别", "to": "数据存储", "type": "sequential"},
            ],
            "parallel_opportunities": [],
        }

    @pytest.mark.asyncio
    async def test_decompose_tasks_basic(self, designer, sample_requirements):
        """Test basic task decomposition"""
        with patch.object(designer, "_call_llm") as mock_llm:
            mock_llm.return_value = {
                "root_task": "邮箱监控自动化",
                "subtasks": [{"name": "邮箱监控", "description": "定时检查Gmail新邮件"}],
            }

            result = await designer.decompose_tasks(sample_requirements)

            assert result is not None
            assert "root_task" in result
            assert "subtasks" in result
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_decompose_tasks_with_enhancement(self, designer, sample_requirements):
        """Test task decomposition with enhancement"""
        with (
            patch.object(designer, "_call_llm") as mock_llm,
            patch.object(designer, "_enhance_task_tree") as mock_enhance,
        ):
            mock_llm.return_value = {"root_task": "test", "subtasks": []}
            mock_enhance.return_value = {"enhanced": True}

            result = await designer.decompose_tasks(sample_requirements)

            mock_enhance.assert_called_once()
            assert result == {"enhanced": True}

    @pytest.mark.asyncio
    async def test_design_architecture_customer_service_pattern(self, designer, sample_task_tree):
        """Test architecture design with customer service pattern"""
        with (
            patch.object(designer, "_match_architecture_pattern") as mock_pattern,
            patch.object(designer, "_generate_node_mappings") as mock_nodes,
            patch.object(designer, "_design_data_flow") as mock_flow,
            patch.object(designer, "_design_error_handling") as mock_error,
        ):
            mock_pattern.return_value = {
                "pattern_name": "customer_service_automation",
                "confidence": 0.8,
                "pattern_data": designer.pattern_library["customer_service_automation"],
            }
            mock_nodes.return_value = [
                {"type": "TRIGGER_EMAIL", "role": "trigger"},
                {"type": "AI_TASK_ANALYZER", "role": "analysis"},
            ]
            mock_flow.return_value = {"input_schema": {}, "output_schema": {}}
            mock_error.return_value = {"retry_policies": {}}

            result = await designer.design_architecture(sample_task_tree, {})

            assert result is not None
            assert result["pattern_used"] == "customer_service_automation"
            assert "nodes" in result
            assert "data_flow" in result
            mock_pattern.assert_called_once()
            mock_nodes.assert_called_once()

    @pytest.mark.asyncio
    async def test_estimate_performance(self, designer):
        """Test performance estimation"""
        sample_architecture = {
            "nodes": [
                {"type": "TRIGGER_EMAIL", "role": "trigger"},
                {"type": "AI_TASK_ANALYZER", "role": "analysis"},
                {"type": "EXTERNAL_NOTION", "role": "storage"},
            ],
            "pattern_used": "customer_service_automation",
        }

        result = await designer.estimate_performance(sample_architecture)

        assert result is not None
        assert "avg_execution_time" in result
        assert "throughput" in result
        assert "resource_usage" in result
        assert "reliability_score" in result
        assert isinstance(result["reliability_score"], (int, float))

    @pytest.mark.asyncio
    async def test_generate_workflow_dsl(self, designer):
        """Test DSL generation"""
        sample_architecture = {
            "nodes": [
                {
                    "id": "trigger",
                    "type": "TRIGGER_EMAIL",
                    "role": "trigger",
                    "parameters": {"email_provider": "gmail"},
                }
            ],
            "connections": [{"source": "trigger", "target": "analyzer", "type": "main"}],
            "pattern_used": "customer_service_automation",
        }

        result = await designer.generate_workflow_dsl(sample_architecture)

        assert result is not None
        assert "version" in result
        assert "nodes" in result
        assert "connections" in result
        assert "settings" in result
        assert "metadata" in result

    def test_match_architecture_pattern_customer_service(self, designer):
        """Test pattern matching for customer service"""
        task_tree = {
            "subtasks": [
                {"name": "email monitoring"},
                {"name": "customer response"},
                {"name": "support ticket"},
            ]
        }

        result = designer._match_architecture_pattern(task_tree)

        assert result["pattern_name"] == "customer_service_automation"
        assert result["confidence"] > 0.7

    def test_match_architecture_pattern_data_integration(self, designer):
        """Test pattern matching for data integration"""
        task_tree = {
            "subtasks": [
                {"name": "data extraction"},
                {"name": "data transformation"},
                {"name": "data integration"},
            ]
        }

        result = designer._match_architecture_pattern(task_tree)

        assert result["pattern_name"] == "data_integration_pipeline"
        assert result["confidence"] > 0.6

    def test_match_architecture_pattern_fallback(self, designer):
        """Test pattern matching fallback"""
        task_tree = {"subtasks": [{"name": "unknown task"}, {"name": "custom processing"}]}

        result = designer._match_architecture_pattern(task_tree)

        assert result["pattern_name"] == "custom"
        assert "pattern_data" in result

    @pytest.mark.asyncio
    async def test_generate_node_mappings(self, designer, sample_task_tree):
        """Test node mapping generation"""
        pattern_match = {
            "pattern_name": "customer_service_automation",
            "pattern_data": designer.pattern_library["customer_service_automation"],
        }

        result = await designer._generate_node_mappings(sample_task_tree, pattern_match)

        assert isinstance(result, list)
        assert len(result) > 0
        for node in result:
            assert "id" in node
            assert "type" in node
            assert "role" in node
            assert "parameters" in node

    def test_generate_node_parameters_email_trigger(self, designer):
        """Test parameter generation for email trigger"""
        task = {"name": "email monitoring", "description": "Monitor Gmail"}

        result = designer._generate_node_parameters(task, "TRIGGER_EMAIL")

        assert "email_provider" in result
        assert result["email_provider"] == "gmail"
        assert "check_interval" in result
        assert "folder" in result

    def test_generate_node_parameters_ai_analyzer(self, designer):
        """Test parameter generation for AI analyzer"""
        task = {"name": "analyze email", "description": "Analyze email content"}

        result = designer._generate_node_parameters(task, "AI_TASK_ANALYZER")

        assert "model" in result
        assert "temperature" in result
        assert "max_tokens" in result

    def test_generate_node_parameters_flow_if(self, designer):
        """Test parameter generation for conditional flow"""
        task = {"name": "routing decision", "description": "Route based on condition"}

        result = designer._generate_node_parameters(task, "FLOW_IF")

        assert "condition" in result
        assert "true_branch" in result
        assert "false_branch" in result

    @pytest.mark.asyncio
    async def test_analyze_optimizations_performance(self, designer):
        """Test performance optimization analysis"""
        architecture = {
            "nodes": [
                {"type": "TRIGGER_EMAIL", "metadata": {"critical_path": True}},
                {"type": "AI_TASK_ANALYZER", "metadata": {"critical_path": False}},
                {"type": "EXTERNAL_NOTION", "metadata": {"critical_path": False}},
            ]
        }

        result = await designer.analyze_optimizations(architecture)

        performance_opts = [opt for opt in result if opt["type"] == "performance"]
        assert len(performance_opts) > 0

        parallel_opt = next(
            (opt for opt in performance_opts if opt["category"] == "parallelization"), None
        )
        assert parallel_opt is not None
        assert parallel_opt["priority"] == "high"

    @pytest.mark.asyncio
    async def test_analyze_optimizations_reliability(self, designer):
        """Test reliability optimization analysis"""
        architecture = {"nodes": [{"type": "EXTERNAL_API"}]}

        result = await designer.analyze_optimizations(architecture)

        reliability_opts = [opt for opt in result if opt["type"] == "reliability"]
        assert len(reliability_opts) > 0

    @pytest.mark.asyncio
    async def test_call_llm_openai(self, designer):
        """Test LLM call with OpenAI"""
        with (
            patch("core.design_engine.settings") as mock_settings,
            patch("core.design_engine.ChatOpenAI") as mock_openai,
        ):
            mock_settings.DEFAULT_MODEL_PROVIDER = "openai"
            mock_settings.DEFAULT_MODEL_NAME = "gpt-4"
            mock_settings.OPENAI_API_KEY = "test-key"

            mock_chat = MagicMock()
            mock_chat.ainvoke = AsyncMock(return_value=MagicMock(content='{"result": "test"}'))
            mock_openai.return_value = mock_chat

            result = await designer._call_llm("test system", "test user")

            assert result == {"result": "test"}
            mock_openai.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_anthropic(self, designer):
        """Test LLM call with Anthropic"""
        with (
            patch("core.design_engine.settings") as mock_settings,
            patch("core.design_engine.ChatAnthropic") as mock_anthropic,
        ):
            mock_settings.DEFAULT_MODEL_PROVIDER = "anthropic"
            mock_settings.DEFAULT_MODEL_NAME = "claude-3-sonnet"
            mock_settings.ANTHROPIC_API_KEY = "test-key"

            mock_chat = MagicMock()
            mock_chat.ainvoke = AsyncMock(return_value=MagicMock(content='{"result": "test"}'))
            mock_anthropic.return_value = mock_chat

            result = await designer._call_llm("test system", "test user")

            assert result == {"result": "test"}
            mock_anthropic.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_invalid_json(self, designer):
        """Test LLM call with invalid JSON response"""
        with (
            patch("core.design_engine.settings") as mock_settings,
            patch("core.design_engine.ChatOpenAI") as mock_openai,
        ):
            mock_settings.DEFAULT_MODEL_PROVIDER = "openai"
            mock_chat = MagicMock()
            mock_chat.ainvoke = AsyncMock(return_value=MagicMock(content="invalid json"))
            mock_openai.return_value = mock_chat

            result = await designer._call_llm("test system", "test user")

            assert result == {}

    def test_enhance_task_tree(self, designer, sample_task_tree, sample_requirements):
        """Test task tree enhancement"""
        result = designer._enhance_task_tree(sample_task_tree, sample_requirements)

        # Should enhance existing subtasks
        for subtask in result.get("subtasks", []):
            assert "criticality" in subtask
            assert "dependencies" in subtask
            assert "estimated_complexity" in subtask

    def test_calculate_critical_path_time(self, designer):
        """Test critical path time calculation"""
        architecture = {
            "nodes": [
                {"type": "TRIGGER_EMAIL"},
                {"type": "AI_TASK_ANALYZER"},
                {"type": "EXTERNAL_NOTION"},
            ]
        }

        result = designer._calculate_critical_path_time(architecture)

        assert isinstance(result, (int, float))
        assert result > 0

    def test_assess_scalability(self, designer):
        """Test scalability assessment"""
        architecture = {
            "nodes": [{"type": "AI_TASK_ANALYZER"}],
            "pattern_used": "customer_service_automation",
        }

        result = designer._assess_scalability(architecture)

        assert "horizontal_scaling" in result
        assert "vertical_scaling" in result
        assert "bottlenecks" in result
        assert "scaling_recommendations" in result

    def test_identify_bottlenecks(self, designer):
        """Test bottleneck identification"""
        architecture = {
            "nodes": [
                {"type": "AI_TASK_ANALYZER"},
                {"type": "EXTERNAL_API"},
                {"type": "MEMORY_VECTOR_STORE"},
            ]
        }

        result = designer._identify_bottlenecks(architecture)

        assert isinstance(result, list)
        # Should identify AI and vector store as potential bottlenecks
        bottleneck_types = [b["type"] for b in result]
        assert "AI_TASK_ANALYZER" in bottleneck_types


class TestWorkflowOrchestrator:
    """Test cases for WorkflowOrchestrator"""

    @pytest.fixture
    def orchestrator(self):
        """Create WorkflowOrchestrator instance for testing"""
        return WorkflowOrchestrator()

    @pytest.fixture
    def sample_user_input(self):
        """Sample user input for testing"""
        return "每天定时检查Gmail，有客户邮件就存到Notion并发Slack通知"

    @pytest.mark.asyncio
    async def test_initialize_session(self, orchestrator, sample_user_input):
        """Test session initialization"""
        result = await orchestrator.initialize_session(
            user_input=sample_user_input, user_id="test_user", session_id="test_session"
        )

        assert result is not None
        assert result["metadata"]["session_id"] == "test_session"
        assert result["metadata"]["user_id"] == "test_user"
        assert result["stage"] == "requirement_negotiation"
        assert result["requirement_negotiation"]["original_requirements"] == sample_user_input

    @pytest.mark.asyncio
    async def test_process_stage_transition_negotiation(self, orchestrator):
        """Test stage transition for negotiation"""
        # Initialize session first
        await orchestrator.initialize_session(user_input="test input", session_id="test_session")

        with patch.object(
            orchestrator.intelligent_negotiator, "process_user_input"
        ) as mock_negotiator:
            mock_negotiator.return_value = {
                "stage": "requirement_negotiation",
                "negotiation_complete": False,
                "next_questions": ["What email provider?"],
                "analysis": {},
            }

            result = await orchestrator.process_stage_transition(
                session_id="test_session", user_input="I want to use Gmail"
            )

            assert result["stage"] == "requirement_negotiation"
            assert "next_questions" in result
            mock_negotiator.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_stage_transition_design(self, orchestrator):
        """Test stage transition to design"""
        # Setup state in design stage
        state = {
            "metadata": {"session_id": "test_session"},
            "stage": "design",
            "requirement_negotiation": {
                "final_requirements": "Gmail monitoring with Notion storage"
            },
        }
        orchestrator.state_store["test_session"] = state

        with (
            patch.object(orchestrator.intelligent_designer, "decompose_tasks") as mock_decompose,
            patch.object(orchestrator.intelligent_designer, "design_architecture") as mock_design,
            patch.object(
                orchestrator.intelligent_designer, "estimate_performance"
            ) as mock_performance,
            patch.object(orchestrator.intelligent_designer, "generate_workflow_dsl") as mock_dsl,
        ):
            mock_decompose.return_value = {"root_task": "test"}
            mock_design.return_value = {"pattern_used": "test"}
            mock_performance.return_value = {"avg_execution_time": "1s"}
            mock_dsl.return_value = {"version": "1.0"}

            result = await orchestrator.process_stage_transition(
                session_id="test_session", user_input="confirmed"
            )

            assert result["stage"] == "configuration"
            assert "task_tree" in result
            assert "architecture" in result
            mock_decompose.assert_called_once()
            mock_design.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_stage_transition_configuration(self, orchestrator):
        """Test stage transition for configuration"""
        # Setup state in configuration stage
        state = {
            "metadata": {"session_id": "test_session"},
            "stage": "configuration",
            "design_state": {"workflow_dsl": {"nodes": [{"id": "test", "type": "TRIGGER_EMAIL"}]}},
        }
        orchestrator.state_store["test_session"] = state

        result = await orchestrator.process_stage_transition(
            session_id="test_session", user_input="configure"
        )

        assert result["stage"] == "completed"
        assert "validation_result" in result
        assert "completeness_check" in result

    def test_get_session_state(self, orchestrator):
        """Test getting session state"""
        test_state = {"test": "data"}
        orchestrator.state_store["test_session"] = test_state

        result = orchestrator.get_session_state("test_session")
        assert result == test_state

        # Test non-existent session
        result = orchestrator.get_session_state("non_existent")
        assert result is None

    def test_get_current_stage(self, orchestrator):
        """Test getting current stage"""
        state = {"stage": "design"}
        orchestrator.state_store["test_session"] = state

        result = orchestrator.get_current_stage("test_session")
        assert result == "design"

        # Test non-existent session
        result = orchestrator.get_current_stage("non_existent")
        assert result is None

    def test_validate_state_transition(self, orchestrator):
        """Test state transition validation"""
        # Valid transitions
        assert orchestrator.validate_state_transition("requirement_negotiation", "design", {})
        assert orchestrator.validate_state_transition("design", "configuration", {})
        assert orchestrator.validate_state_transition("configuration", "completed", {})

        # Invalid transitions
        assert not orchestrator.validate_state_transition(
            "requirement_negotiation", "completed", {}
        )
        assert not orchestrator.validate_state_transition("completed", "design", {})

    async def test_save_and_load_session_state(self, orchestrator):
        """Test saving and loading session state"""
        test_state = {
            "metadata": {"session_id": "test_session"},
            "stage": "design",
            "test_data": "value",
        }

        await orchestrator.save_session_state(test_state)
        loaded_state = orchestrator.get_session_state("test_session")

        assert loaded_state == test_state


class TestDSLValidator:
    """Test cases for DSLValidator"""

    @pytest.fixture
    def valid_workflow_dsl(self):
        """Valid workflow DSL for testing"""
        return {
            "version": "1.0",
            "nodes": [
                {
                    "id": "trigger",
                    "type": "TRIGGER_EMAIL",
                    "parameters": {"email_provider": "gmail"},
                },
                {"id": "analyzer", "type": "AI_TASK_ANALYZER", "parameters": {"model": "gpt-4"}},
            ],
            "connections": {
                "trigger": {"main": [{"node": "analyzer", "type": "main", "index": 0}]}
            },
            "settings": {"timeout": 300},
        }

    @pytest.fixture
    def invalid_workflow_dsl(self):
        """Invalid workflow DSL for testing"""
        return {
            # Missing version
            "nodes": "not_a_list",  # Should be list
            "connections": "not_an_object",  # Should be object
        }

    @pytest.mark.asyncio
    async def test_validate_syntax_valid(self, valid_workflow_dsl):
        """Test syntax validation with valid DSL"""
        result = await DSLValidator.validate_syntax(valid_workflow_dsl)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_syntax_invalid(self, invalid_workflow_dsl):
        """Test syntax validation with invalid DSL"""
        result = await DSLValidator.validate_syntax(invalid_workflow_dsl)

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("version" in error for error in result["errors"])

    @pytest.mark.asyncio
    async def test_validate_logic_valid(self, valid_workflow_dsl):
        """Test logic validation with valid DSL"""
        result = await DSLValidator.validate_logic(valid_workflow_dsl)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_logic_orphaned_nodes(self):
        """Test logic validation with orphaned nodes"""
        workflow_dsl = {
            "version": "1.0",
            "nodes": [
                {"id": "node1", "type": "TRIGGER_EMAIL"},
                {"id": "node2", "type": "AI_TASK_ANALYZER"},
                {"id": "orphan", "type": "EXTERNAL_API"},  # Not connected
            ],
            "connections": {"node1": {"main": [{"node": "node2", "type": "main", "index": 0}]}},
            "settings": {},
        }

        result = await DSLValidator.validate_logic(workflow_dsl)

        assert len(result["warnings"]) > 0
        assert any("orphan" in warning.lower() for warning in result["warnings"])

    @pytest.mark.asyncio
    async def test_calculate_completeness_score_complete(self, valid_workflow_dsl):
        """Test completeness calculation with complete workflow"""
        result = await DSLValidator.calculate_completeness_score(valid_workflow_dsl)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        assert result > 0.8  # Should be high for valid workflow

    @pytest.mark.asyncio
    async def test_calculate_completeness_score_incomplete(self):
        """Test completeness calculation with incomplete workflow"""
        incomplete_dsl = {
            "version": "1.0",
            "nodes": [
                {"id": "trigger", "type": "TRIGGER_EMAIL"}
                # Missing parameters
            ],
            "connections": {},
            "settings": {},
        }

        result = await DSLValidator.calculate_completeness_score(incomplete_dsl)

        assert isinstance(result, float)
        assert result < 0.8  # Should be lower for incomplete workflow


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
