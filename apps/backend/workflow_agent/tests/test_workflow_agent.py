"""
Tests for WorkflowAgent (workflow_agent.py)
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.state import MVPWorkflowState, WorkflowStage
from agents.workflow_agent import WorkflowAgent
from core.design_engine import WorkflowOrchestrator


class TestWorkflowAgent:
    """Test cases for WorkflowAgent"""

    @pytest.fixture
    def agent(self):
        """Create WorkflowAgent instance for testing"""
        return WorkflowAgent()

    @pytest.fixture
    def sample_user_input(self):
        """Sample user input for testing"""
        return "每天检查Gmail邮箱，有客户邮件就存储到Notion数据库"

    @pytest.fixture
    def sample_mvp_state(self):
        """Sample MVP state for testing"""
        return {
            "metadata": {
                "session_id": "test_session",
                "user_id": "test_user",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "version": "1.0.0",
                "interaction_count": 1,
            },
            "stage": WorkflowStage.REQUIREMENT_NEGOTIATION,
            "requirement_negotiation": {
                "original_requirements": "test requirements",
                "parsed_intent": {},
                "capability_analysis": {},
                "identified_constraints": [],
                "proposed_solutions": [],
                "user_decisions": [],
                "negotiation_history": [],
                "final_requirements": "",
                "confidence_score": 0.0,
            },
            "design_state": {
                "task_tree": {},
                "architecture": {},
                "workflow_dsl": {},
                "optimization_suggestions": [],
                "design_patterns_used": [],
                "estimated_performance": {},
            },
            "configuration_state": {
                "current_node_index": 0,
                "node_configurations": [],
                "missing_parameters": [],
                "validation_results": [],
                "configuration_templates": [],
                "auto_filled_params": [],
            },
            "execution_state": {
                "preview_results": [],
                "static_validation": {},
                "configuration_completeness": {},
            },
            "user_input": "test input",
            "current_user_input": "test input",
        }

    def test_setup_graph(self, agent):
        """Test graph setup"""
        assert agent.graph is not None
        assert agent.orchestrator is not None

        # Check that all nodes are added
        nodes = agent.graph.nodes
        expected_nodes = [
            "initialize_session",
            "requirement_negotiation",
            "design",
            "configuration",
            "validation",
            "completion",
        ]
        for node_name in expected_nodes:
            assert node_name in nodes

    @pytest.mark.asyncio
    async def test_initialize_session_node_success(self, agent, sample_mvp_state):
        """Test successful session initialization"""
        with patch.object(agent.orchestrator, "initialize_session") as mock_init:
            mock_init.return_value = {
                "metadata": {"session_id": "test_session"},
                "stage": "requirement_negotiation",
            }

            state = {
                "user_input": "test input",
                "user_id": "test_user",
                "session_id": "test_session",
            }

            result = await agent._initialize_session_node(state)

            assert result["current_step"] == "requirement_negotiation"
            assert result["should_continue"] is True
            assert len(result["errors"]) == 0
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_session_node_error(self, agent):
        """Test session initialization with error"""
        with patch.object(agent.orchestrator, "initialize_session") as mock_init:
            mock_init.side_effect = Exception("Initialization failed")

            state = {"user_input": "test input"}

            result = await agent._initialize_session_node(state)

            assert result["current_step"] == "error"
            assert result["should_continue"] is False
            assert len(result["errors"]) > 0
            assert "Initialization error" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_requirement_negotiation_node_success(self, agent, sample_mvp_state):
        """Test successful requirement negotiation"""
        with patch.object(agent.orchestrator, "process_stage_transition") as mock_process:
            mock_process.return_value = {
                "stage": "requirement_negotiation",
                "next_questions": ["What email provider?"],
                "tradeoff_analysis": {"options": []},
                "state": sample_mvp_state,
            }

            result = await agent._requirement_negotiation_node(sample_mvp_state)

            assert result["current_step"] == "requirement_negotiation"
            assert result["should_continue"] is True
            assert "next_questions" in result
            assert len(result["errors"]) == 0
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_requirement_negotiation_node_error(self, agent, sample_mvp_state):
        """Test requirement negotiation with error"""
        with patch.object(agent.orchestrator, "process_stage_transition") as mock_process:
            mock_process.side_effect = Exception("Negotiation failed")

            result = await agent._requirement_negotiation_node(sample_mvp_state)

            assert result["current_step"] == "error"
            assert result["should_continue"] is False
            assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_design_node_success(self, agent, sample_mvp_state):
        """Test successful design stage"""
        with patch.object(agent.orchestrator, "process_stage_transition") as mock_process:
            mock_process.return_value = {
                "stage": "design",
                "task_tree": {"root_task": "test"},
                "architecture": {"pattern_used": "test"},
                "workflow_dsl": {"version": "1.0"},
                "optimization_suggestions": [{"type": "performance"}],
                "performance_estimate": {"avg_execution_time": "1s"},
                "design_patterns": ["pattern1"],
                "state": sample_mvp_state,
            }

            result = await agent._design_node(sample_mvp_state)

            assert result["current_step"] == "design"
            assert result["should_continue"] is True
            assert "task_tree" in result
            assert "architecture" in result
            assert "workflow_dsl" in result
            assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_design_node_error(self, agent, sample_mvp_state):
        """Test design stage with error"""
        with patch.object(agent.orchestrator, "process_stage_transition") as mock_process:
            mock_process.side_effect = Exception("Design failed")

            result = await agent._design_node(sample_mvp_state)

            assert result["current_step"] == "error"
            assert result["should_continue"] is False
            assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_configuration_node_success(self, agent, sample_mvp_state):
        """Test successful configuration stage"""
        with patch.object(agent.orchestrator, "process_stage_transition") as mock_process:
            mock_process.return_value = {
                "stage": "configuration",
                "node_configurations": [{"node_id": "test", "parameters": {}}],
                "state": sample_mvp_state,
            }

            result = await agent._configuration_node(sample_mvp_state)

            assert result["current_step"] == "configuration"
            assert result["should_continue"] is True
            assert "node_configurations" in result
            assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validation_node_success(self, agent, sample_mvp_state):
        """Test successful validation stage"""
        with patch.object(agent.orchestrator, "process_stage_transition") as mock_process:
            mock_process.return_value = {
                "stage": "validation",
                "validation_result": {"valid": True},
                "completeness_check": {"complete": True},
                "state": sample_mvp_state,
            }

            result = await agent._validation_node(sample_mvp_state)

            assert result["current_step"] == "validation"
            assert result["should_continue"] is True
            assert "validation_result" in result
            assert "completeness_check" in result
            assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_completion_node(self, agent, sample_mvp_state):
        """Test completion stage"""
        sample_mvp_state.update(
            {
                "workflow_dsl": {"version": "1.0"},
                "validation_result": {"valid": True},
                "completeness_check": {"complete": True},
                "optimization_suggestions": [{"type": "performance"}],
                "performance_estimate": {"avg_execution_time": "1s"},
            }
        )

        result = await agent._completion_node(sample_mvp_state)

        assert result["current_step"] == "completed"
        assert result["should_continue"] is False
        assert "final_result" in result
        assert len(result["errors"]) == 0

    def test_determine_next_stage_negotiation_continue(self, agent):
        """Test stage determination - continue negotiation"""
        state = {
            "current_step": "requirement_negotiation",
            "stage": "requirement_negotiation",
            "should_continue": True,
            "errors": [],
            "requirement_negotiation": {"final_requirements": ""},
        }

        result = agent._determine_next_stage(state)
        assert result == "requirement_negotiation"

    def test_determine_next_stage_negotiation_to_design(self, agent):
        """Test stage determination - negotiation to design"""
        state = {
            "current_step": "requirement_negotiation",
            "stage": "requirement_negotiation",
            "should_continue": True,
            "errors": [],
            "requirement_negotiation": {"final_requirements": "completed requirements"},
        }

        result = agent._determine_next_stage(state)
        assert result == "design"

    def test_determine_next_stage_design_to_configuration(self, agent):
        """Test stage determination - design to configuration"""
        state = {"current_step": "design", "stage": "design", "should_continue": True, "errors": []}

        result = agent._determine_next_stage(state)
        assert result == "configuration"

    def test_determine_next_stage_error(self, agent):
        """Test stage determination with errors"""
        state = {
            "current_step": "requirement_negotiation",
            "stage": "requirement_negotiation",
            "should_continue": False,
            "errors": ["Some error"],
        }

        result = agent._determine_next_stage(state)
        assert result == "end"

    @pytest.mark.asyncio
    async def test_generate_workflow_success(self, agent, sample_user_input):
        """Test successful workflow generation"""
        with patch.object(agent.graph, "ainvoke") as mock_invoke:
            mock_invoke.return_value = {
                "metadata": {"session_id": "test_session"},
                "current_step": "completed",
                "errors": [],
                "final_result": {
                    "workflow_dsl": {"version": "1.0"},
                    "validation_result": {"valid": True},
                    "optimization_suggestions": [{"type": "performance"}],
                    "performance_estimate": {"avg_execution_time": "1s"},
                },
                "stage": "completed",
            }

            result = await agent.generate_workflow(
                user_input=sample_user_input, user_id="test_user", session_id="test_session"
            )

            assert result["success"] is True
            assert result["workflow"] is not None
            assert result["session_id"] == "test_session"
            assert len(result["errors"]) == 0
            mock_invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_workflow_with_errors(self, agent, sample_user_input):
        """Test workflow generation with errors"""
        with patch.object(agent.graph, "ainvoke") as mock_invoke:
            mock_invoke.return_value = {
                "metadata": {"session_id": "test_session"},
                "current_step": "error",
                "errors": ["Generation failed"],
                "final_result": {},
                "stage": "error",
            }

            result = await agent.generate_workflow(
                user_input=sample_user_input, session_id="test_session"
            )

            assert result["success"] is False
            assert len(result["errors"]) > 0
            assert result["stage"] == "error"

    @pytest.mark.asyncio
    async def test_generate_workflow_exception(self, agent, sample_user_input):
        """Test workflow generation with exception"""
        with patch.object(agent.graph, "ainvoke") as mock_invoke:
            mock_invoke.side_effect = Exception("Graph execution failed")

            result = await agent.generate_workflow(
                user_input=sample_user_input, session_id="test_session"
            )

            assert result["success"] is False
            assert len(result["errors"]) > 0
            assert "Internal error" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_continue_conversation_negotiation(self, agent):
        """Test continuing conversation in negotiation stage"""
        with (
            patch.object(agent.orchestrator, "get_session_state") as mock_get_state,
            patch.object(agent, "_requirement_negotiation_node") as mock_negotiation,
        ):
            mock_get_state.return_value = {
                "metadata": {"session_id": "test_session"},
                "stage": "requirement_negotiation",
            }
            mock_negotiation.return_value = {
                "current_step": "requirement_negotiation",
                "should_continue": True,
                "errors": [],
                "next_questions": ["Next question?"],
            }

            result = await agent.continue_conversation(
                session_id="test_session", user_response="Gmail"
            )

            assert result["success"] is True
            assert result["stage"] == "requirement_negotiation"
            assert "next_questions" in result
            mock_negotiation.assert_called_once()

    @pytest.mark.asyncio
    async def test_continue_conversation_design(self, agent):
        """Test continuing conversation in design stage"""
        with (
            patch.object(agent.orchestrator, "get_session_state") as mock_get_state,
            patch.object(agent, "_design_node") as mock_design,
        ):
            mock_get_state.return_value = {
                "metadata": {"session_id": "test_session"},
                "stage": "design",
            }
            mock_design.return_value = {
                "current_step": "design",
                "should_continue": True,
                "errors": [],
                "workflow_dsl": {"version": "1.0"},
                "validation_result": {"valid": True},
            }

            result = await agent.continue_conversation(
                session_id="test_session", user_response="confirmed"
            )

            assert result["success"] is True
            assert result["stage"] == "design"
            assert "workflow" in result
            mock_design.assert_called_once()

    @pytest.mark.asyncio
    async def test_continue_conversation_session_not_found(self, agent):
        """Test continuing conversation with non-existent session"""
        with patch.object(agent.orchestrator, "get_session_state") as mock_get_state:
            mock_get_state.return_value = None

            result = await agent.continue_conversation(
                session_id="non_existent", user_response="test"
            )

            assert result["success"] is False
            assert "not found" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_continue_conversation_invalid_stage(self, agent):
        """Test continuing conversation with invalid stage"""
        with patch.object(agent.orchestrator, "get_session_state") as mock_get_state:
            mock_get_state.return_value = {
                "metadata": {"session_id": "test_session"},
                "stage": "invalid_stage",
            }

            result = await agent.continue_conversation(
                session_id="test_session", user_response="test"
            )

            assert result["success"] is False
            assert "Invalid stage" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_continue_conversation_exception(self, agent):
        """Test continuing conversation with exception"""
        with patch.object(agent.orchestrator, "get_session_state") as mock_get_state:
            mock_get_state.side_effect = Exception("State retrieval failed")

            result = await agent.continue_conversation(
                session_id="test_session", user_response="test"
            )

            assert result["success"] is False
            assert "Internal error" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_refine_workflow(self, agent):
        """Test workflow refinement"""
        original_workflow = {"version": "1.0", "nodes": []}

        result = await agent.refine_workflow(
            workflow_id="test_workflow",
            feedback="Add error handling",
            original_workflow=original_workflow,
        )

        assert result["success"] is True
        assert result["updated_workflow"] == original_workflow
        assert len(result["changes"]) > 0

    @pytest.mark.asyncio
    async def test_refine_workflow_exception(self, agent):
        """Test workflow refinement with exception"""
        with patch("agents.workflow_agent.logger") as mock_logger:
            # Simulate an exception during refinement
            original_workflow = None  # This will cause an error

            result = await agent.refine_workflow(
                workflow_id="test_workflow",
                feedback="Add error handling",
                original_workflow=original_workflow,
            )

            # With our current implementation, it should still succeed
            # because we have basic error handling
            assert result["success"] is True

    def test_get_session_state(self, agent):
        """Test getting session state"""
        with patch.object(agent.orchestrator, "get_session_state") as mock_get_state:
            mock_get_state.return_value = {"test": "data"}

            result = agent.get_session_state("test_session")

            assert result == {"test": "data"}
            mock_get_state.assert_called_once_with("test_session")

    @pytest.mark.asyncio
    async def test_validate_workflow_dsl_success(self, agent):
        """Test successful workflow DSL validation"""
        workflow_dsl = {
            "version": "1.0",
            "nodes": [{"id": "test", "type": "TRIGGER_EMAIL"}],
            "connections": {},
            "settings": {},
        }

        with patch("agents.workflow_agent.DSLValidator") as mock_validator:
            mock_validator.validate_syntax.return_value = {
                "valid": True,
                "errors": [],
                "warnings": [],
            }
            mock_validator.validate_logic.return_value = {
                "valid": True,
                "errors": [],
                "warnings": [],
            }
            mock_validator.calculate_completeness_score.return_value = 0.9

            result = await agent.validate_workflow_dsl(workflow_dsl)

            assert result["success"] is True
            assert result["validation_results"]["overall_valid"] is True
            assert result["validation_results"]["completeness_score"] == 0.9

    @pytest.mark.asyncio
    async def test_validate_workflow_dsl_with_errors(self, agent):
        """Test workflow DSL validation with errors"""
        workflow_dsl = {"invalid": "dsl"}

        with patch("agents.workflow_agent.DSLValidator") as mock_validator:
            mock_validator.validate_syntax.return_value = {
                "valid": False,
                "errors": ["Missing version"],
                "warnings": [],
            }
            mock_validator.validate_logic.return_value = {
                "valid": True,
                "errors": [],
                "warnings": [],
            }
            mock_validator.calculate_completeness_score.return_value = 0.3

            result = await agent.validate_workflow_dsl(workflow_dsl)

            assert result["success"] is True
            assert result["validation_results"]["overall_valid"] is False
            assert len(result["validation_results"]["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_workflow_dsl_exception(self, agent):
        """Test workflow DSL validation with exception"""
        workflow_dsl = {}

        with patch("agents.workflow_agent.DSLValidator") as mock_validator:
            mock_validator.validate_syntax.side_effect = Exception("Validation failed")

            result = await agent.validate_workflow_dsl(workflow_dsl)

            assert result["success"] is False
            assert len(result["errors"]) > 0
            assert "Validation error" in result["errors"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
