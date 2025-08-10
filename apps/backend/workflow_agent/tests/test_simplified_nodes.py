"""
Tests for simplified workflow agent nodes
Tests the 6-node architecture: Clarification, Negotiation, Gap Analysis,
Alternative Generation, Workflow Generation, and Debug
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agents.nodes import WorkflowAgentNodes
from agents.state import ClarificationContext, Conversation, WorkflowOrigin, WorkflowStage


class TestWorkflowAgentNodes:
    """Test the simplified workflow agent nodes"""

    @pytest.fixture
    def workflow_nodes(self, mock_settings):
        """Create WorkflowAgentNodes instance for testing"""
        with patch("agents.nodes.settings", mock_settings):
            nodes = WorkflowAgentNodes()
            # Mock the LLM with a proper mock object
            nodes.llm = MagicMock()
            nodes.llm.ainvoke = AsyncMock()
            return nodes

    @pytest.fixture
    def sample_state(self):
        """Sample workflow state for testing"""
        return {
            "session_id": "test_session",
            "stage": WorkflowStage.CLARIFICATION,
            "execution_history": [],
            "clarification_context": {
                "origin": WorkflowOrigin.CREATE,
                "pending_questions": [],
            },
            "conversations": [{"role": "user", "text": "我需要邮件自动化系统"}],
            "intent_summary": "",
            "gaps": [],
            "alternatives": [],
            "current_workflow": {},
            "debug_result": "",
            "debug_loop_count": 0,
        }

    @pytest.mark.asyncio
    async def test_clarification_node_initial_intent(self, workflow_nodes, sample_state):
        """Test clarification node with initial intent"""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {"intent_summary": "邮件自动化处理系统", "needs_clarification": False, "questions": []}
        )
        workflow_nodes.llm.ainvoke.return_value = mock_response

        # Test clarification node
        result = await workflow_nodes.clarification_node(sample_state)

        # Verify results
        assert result["stage"] == WorkflowStage.GAP_ANALYSIS
        assert result["intent_summary"] == "邮件自动化处理系统"
        assert "clarification_context" in result

    @pytest.mark.asyncio
    async def test_clarification_node_needs_more_info(self, workflow_nodes, sample_state):
        """Test clarification node when more information is needed"""
        # Mock LLM response requiring clarification
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "intent_summary": "邮件系统",
                "needs_clarification": True,
                "questions": ["请详细描述您的邮件处理需求", "您希望如何集成现有系统？"],
            }
        )
        workflow_nodes.llm.ainvoke.return_value = mock_response

        # Test clarification node
        result = await workflow_nodes.clarification_node(sample_state)

        # Verify results
        assert result["stage"] == WorkflowStage.NEGOTIATION
        assert result["intent_summary"] == "邮件系统"
        assert len(result["clarification_context"]["pending_questions"]) == 2

    @pytest.mark.asyncio
    async def test_negotiation_node(self, workflow_nodes, sample_state):
        """Test negotiation node"""
        # Set up state with pending questions
        sample_state["stage"] = WorkflowStage.NEGOTIATION
        sample_state["clarification_context"] = {
            "origin": WorkflowOrigin.CREATE,
            "pending_questions": ["请详细描述您的需求"],
        }

        # Test negotiation node
        result = await workflow_nodes.negotiation_node(sample_state)

        # Should either wait for user response or process user input and return to clarification
        assert result["stage"] in [WorkflowStage.NEGOTIATION, WorkflowStage.CLARIFICATION]
        # Conversations should be maintained or updated
        assert len(result["conversations"]) >= len(sample_state["conversations"])

    @pytest.mark.asyncio
    async def test_gap_analysis_node(self, workflow_nodes, sample_state):
        """Test gap analysis node"""
        sample_state["stage"] = WorkflowStage.GAP_ANALYSIS
        sample_state["intent_summary"] = "邮件自动化系统"

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {"gaps": ["email_authentication", "ai_integration"], "severity": "medium"}
        )
        workflow_nodes.llm.ainvoke.return_value = mock_response

        # Test gap analysis node
        result = await workflow_nodes.gap_analysis_node(sample_state)

        # Verify results - when gaps are found, should go to alternative generation
        assert result["stage"] == WorkflowStage.ALTERNATIVE_GENERATION
        assert len(result["gaps"]) == 2
        assert "email_authentication" in result["gaps"]
        assert "ai_integration" in result["gaps"]

    @pytest.mark.asyncio
    async def test_gap_analysis_node_no_gaps(self, workflow_nodes, sample_state):
        """Test gap analysis node when no gaps are found"""
        sample_state["stage"] = WorkflowStage.GAP_ANALYSIS
        sample_state["intent_summary"] = "简单邮件检查"

        # Mock LLM response with no gaps
        mock_response = MagicMock()
        mock_response.content = json.dumps({"gaps": [], "severity": "low"})
        workflow_nodes.llm.ainvoke.return_value = mock_response

        # Test gap analysis node
        result = await workflow_nodes.gap_analysis_node(sample_state)

        # Should proceed to generation
        assert result["stage"] == WorkflowStage.WORKFLOW_GENERATION
        assert len(result["gaps"]) == 0

    @pytest.mark.asyncio
    async def test_alternative_solution_generation_node(self, workflow_nodes, sample_state):
        """Test alternative solution generation node"""
        sample_state["gaps"] = ["email_authentication", "ai_integration"]
        sample_state["intent_summary"] = "邮件自动化系统"

        # Store original conversation count before modification
        original_conversation_count = len(sample_state["conversations"])

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {"alternatives": ["使用OAuth2.0进行邮件认证", "集成OpenAI API进行智能分析", "使用简化版本跳过复杂功能"]}
        )
        workflow_nodes.llm.ainvoke.return_value = mock_response

        # Test alternative generation
        result = await workflow_nodes.alternative_solution_generation_node(sample_state)

        # Verify results
        assert result["stage"] == WorkflowStage.NEGOTIATION
        assert len(result["alternatives"]) == 3
        assert "OAuth2.0" in result["alternatives"][0]
        # Should have added one conversation message
        assert len(result["conversations"]) == original_conversation_count + 1

    @pytest.mark.asyncio
    async def test_workflow_generation_node(self, workflow_nodes, sample_state):
        """Test workflow generation node"""
        sample_state["intent_summary"] = "邮件自动化系统"
        sample_state["gaps"] = ["email_authentication"]
        sample_state["alternatives"] = ["使用OAuth认证"]

        # Mock LLM response
        workflow_data = {
            "id": "workflow-12345",
            "name": "邮件处理系统",
            "description": "自动处理邮件",
            "nodes": [
                {"id": "trigger", "type": "email_trigger", "parameters": {"provider": "gmail"}},
                {"id": "processor", "type": "ai_agent", "parameters": {"model": "gpt-4"}},
            ],
            "connections": [{"from": "trigger", "to": "processor"}],
        }
        mock_response = MagicMock()
        mock_response.content = json.dumps(workflow_data)
        workflow_nodes.llm.ainvoke.return_value = mock_response

        # Test workflow generation
        result = await workflow_nodes.workflow_generation_node(sample_state)

        # Verify results
        assert result["stage"] == WorkflowStage.DEBUG
        assert "current_workflow" in result
        assert result["current_workflow"]["id"] == "workflow-12345"
        assert len(result["current_workflow"]["nodes"]) == 2

    @pytest.mark.asyncio
    async def test_workflow_generation_node_fallback(self, workflow_nodes, sample_state):
        """Test workflow generation node with fallback when JSON parsing fails"""
        sample_state["intent_summary"] = "邮件系统"

        # Mock LLM response that's not valid JSON
        mock_response = MagicMock()
        mock_response.content = "This is not valid JSON"
        workflow_nodes.llm.ainvoke.return_value = mock_response

        # Test workflow generation
        result = await workflow_nodes.workflow_generation_node(sample_state)

        # Should create fallback workflow
        assert result["stage"] == WorkflowStage.DEBUG
        assert "current_workflow" in result
        assert "workflow-" in result["current_workflow"]["id"]
        assert len(result["current_workflow"]["nodes"]) == 2  # start and process nodes

    @pytest.mark.asyncio
    async def test_debug_node_success(self, workflow_nodes, sample_state):
        """Test debug node with successful validation"""
        sample_state["current_workflow"] = {
            "id": "workflow-test",
            "nodes": [
                {"id": "trigger", "type": "email_trigger", "parameters": {"provider": "gmail"}},
                {"id": "processor", "type": "ai_agent", "parameters": {"model": "gpt-4"}},
            ],
            "connections": [{"from": "trigger", "to": "processor"}],
        }

        # Test debug node
        result = await workflow_nodes.debug_node(sample_state)

        # Should succeed and complete
        assert result["stage"] == WorkflowStage.COMPLETED
        assert '"success": true' in result["debug_result"]
        assert result["debug_loop_count"] == 1

    @pytest.mark.asyncio
    async def test_debug_node_empty_workflow(self, workflow_nodes, sample_state):
        """Test debug node with empty workflow"""
        sample_state["current_workflow"] = {}

        # Test debug node
        result = await workflow_nodes.debug_node(sample_state)

        # Should detect errors and return to generation
        assert result["stage"] == WorkflowStage.WORKFLOW_GENERATION
        assert '"success": false' in result["debug_result"]
        assert "Empty workflow" in result["debug_result"]

    @pytest.mark.asyncio
    async def test_debug_node_missing_connections(self, workflow_nodes, sample_state):
        """Test debug node with missing connections"""
        sample_state["current_workflow"] = {
            "nodes": [
                {"id": "trigger", "type": "email_trigger"},
                {"id": "processor", "type": "ai_agent"},
            ],
            "connections": [],  # Missing connections
        }

        # Test debug node
        result = await workflow_nodes.debug_node(sample_state)

        # Should detect warnings but may still succeed
        debug_result = json.loads(result["debug_result"])
        assert "warnings" in debug_result
        assert len(debug_result["warnings"]) > 0

    def test_should_continue_stage_mapping(self, workflow_nodes):
        """Test should_continue method stage mapping"""
        test_cases = [
            (WorkflowStage.CLARIFICATION, "clarification"),
            (WorkflowStage.NEGOTIATION, "negotiation"),
            (WorkflowStage.GAP_ANALYSIS, "gap_analysis"),
            (WorkflowStage.WORKFLOW_GENERATION, "workflow_generation"),
            (WorkflowStage.DEBUG, "debug"),
            (WorkflowStage.COMPLETED, "END"),
        ]

        for stage, expected_node in test_cases:
            state = {"stage": stage}
            result = workflow_nodes.should_continue(state)
            assert result == expected_node

    def test_should_continue_unknown_stage(self, workflow_nodes):
        """Test should_continue with unknown stage"""
        state = {"stage": "unknown_stage"}
        result = workflow_nodes.should_continue(state)
        assert result == "END"

    @pytest.mark.asyncio
    async def test_error_handling_in_nodes(self, workflow_nodes, sample_state):
        """Test error handling in nodes"""
        # Mock LLM to raise an exception
        workflow_nodes.llm.ainvoke.side_effect = Exception("LLM Error")

        # Test that nodes handle errors gracefully
        result = await workflow_nodes.clarification_node(sample_state)

        # Should return error state
        assert result["stage"] == WorkflowStage.CLARIFICATION
        assert "error" in result["debug_result"].lower()

    def test_conversation_updates(self, workflow_nodes, sample_state):
        """Test conversation update utility method"""
        initial_count = len(sample_state.get("conversations", []))

        workflow_nodes._update_conversations(sample_state, "assistant", "测试回复")

        assert len(sample_state["conversations"]) == initial_count + 1
        assert sample_state["conversations"][-1]["role"] == "assistant"
        assert sample_state["conversations"][-1]["text"] == "测试回复"

    def test_session_id_extraction(self, workflow_nodes, sample_state):
        """Test session ID extraction utility method"""
        session_id = workflow_nodes._get_session_id(sample_state)
        assert session_id == "test_session"

        # Test with missing metadata
        empty_state = {}
        session_id = workflow_nodes._get_session_id(empty_state)
        assert session_id == ""
