"""
Tests for enhanced Gap Analysis Node with MCP integration and smart negotiation
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from agents.nodes import WorkflowAgentNodes
from agents.state import WorkflowStage, GapDetail
from core.config import settings


class TestEnhancedGapAnalysis:
    """Test the enhanced Gap Analysis Node with MCP and smart recommendations"""

    @pytest.fixture
    def workflow_nodes(self):
        """Create WorkflowAgentNodes instance with mocked dependencies"""
        with patch("agents.nodes.settings") as mock_settings:
            # Configure settings for testing
            mock_settings.GAP_ANALYSIS_MAX_ROUNDS = 1
            mock_settings.GAP_ANALYSIS_AUTO_SELECT = True
            mock_settings.GAP_ANALYSIS_USE_MCP = True
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.DEFAULT_MODEL_NAME = "gpt-4"
            
            nodes = WorkflowAgentNodes()
            # Mock the LLM
            nodes.llm = MagicMock()
            nodes.llm.ainvoke = AsyncMock()
            # Mock MCP client
            nodes.mcp_client = MagicMock()
            nodes.mcp_client.get_node_types = AsyncMock()
            return nodes

    @pytest.fixture
    def sample_state(self):
        """Sample state for gap analysis testing"""
        return {
            "session_id": "test_session",
            "stage": WorkflowStage.GAP_ANALYSIS,
            "intent_summary": "I need to sync Gmail emails to Slack in real-time",
            "conversations": [
                {"role": "user", "text": "I need to sync Gmail emails to Slack in real-time"}
            ],
            "clarification_context": {},
            "gap_negotiation_count": 0,
            "identified_gaps": [],
            "gap_status": "no_gap"
        }

    @pytest.mark.asyncio
    async def test_gap_analysis_with_mcp_no_gaps(self, workflow_nodes, sample_state):
        """Test gap analysis when MCP shows all capabilities are available"""
        # Mock MCP response with all needed capabilities
        workflow_nodes.mcp_client.get_node_types.return_value = {
            "TRIGGER_NODE": ["email", "webhook", "schedule"],
            "EXTERNAL_ACTION_NODE": ["gmail", "slack", "api_call"],
            "AI_AGENT_NODE": ["ai_agent"]
        }
        
        # Mock LLM response - no gaps found
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "gap_status": "no_gap",
            "negotiation_phrase": None,
            "identified_gaps": []
        })
        workflow_nodes.llm.ainvoke.return_value = mock_response
        
        # Run gap analysis
        result = await workflow_nodes.gap_analysis_node(sample_state)
        
        # Verify results
        assert result["gap_status"] == "no_gap"
        assert len(result["identified_gaps"]) == 0
        assert workflow_nodes.mcp_client.get_node_types.called
        
    @pytest.mark.asyncio
    async def test_gap_analysis_with_gaps_first_round(self, workflow_nodes, sample_state):
        """Test gap analysis finding gaps and presenting smart alternatives"""
        # Mock MCP response - missing real-time capability
        workflow_nodes.mcp_client.get_node_types.return_value = {
            "TRIGGER_NODE": ["schedule", "manual"],  # No webhook/email trigger
            "EXTERNAL_ACTION_NODE": ["slack", "api_call"],  # Has Slack but no Gmail
            "AI_AGENT_NODE": ["ai_agent"]
        }
        
        # Mock LLM response - gaps identified with alternatives
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "gap_status": "has_gap",
            "negotiation_phrase": "I found gaps for real-time sync. Choose an approach:",
            "identified_gaps": [
                {
                    "required_capability": "Real-time Gmail monitoring",
                    "missing_component": "Gmail webhook trigger",
                    "alternatives": [
                        "Use scheduled checks every 5 minutes",
                        "Use Gmail API with polling",
                        "Use third-party service like Zapier"
                    ]
                }
            ]
        })
        workflow_nodes.llm.ainvoke.return_value = mock_response
        
        # Mock the smart negotiation message
        with patch.object(workflow_nodes, '_create_smart_negotiation_message', 
                         new_callable=AsyncMock) as mock_create_msg:
            mock_create_msg.return_value = (
                "I found 1 capability gap for your workflow.\n\n"
                "For Real-time Gmail monitoring:\n"
                "⭐ A) Use scheduled checks every 5 minutes\n"
                "B) Use Gmail API with polling\n"
                "C) Use third-party service like Zapier\n\n"
                "A is recommended based on your requirements.\n"
                "Choose an option (A/B/C) or describe your preference:"
            )
            
            # Run gap analysis
            result = await workflow_nodes.gap_analysis_node(sample_state)
            
            # Verify results
            assert result["gap_status"] == "has_gap"
            assert len(result["identified_gaps"]) == 1
            assert result["gap_negotiation_count"] == 1
            assert "clarification_context" in result
            assert result["clarification_context"]["purpose"] == "gap_negotiation"
            assert mock_create_msg.called

    @pytest.mark.asyncio
    async def test_gap_analysis_auto_resolution_after_max_rounds(self, workflow_nodes, sample_state):
        """Test automatic resolution when max negotiation rounds reached"""
        # Set state to indicate we've already negotiated once
        sample_state["gap_negotiation_count"] = 1
        sample_state["gap_status"] = "has_gap"
        
        # Mock MCP response
        workflow_nodes.mcp_client.get_node_types.return_value = {
            "TRIGGER_NODE": ["schedule", "manual"]
        }
        
        # Mock LLM response - still has gaps
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "gap_status": "has_gap",
            "negotiation_phrase": "Still have gaps",
            "identified_gaps": [
                {
                    "required_capability": "Real-time sync",
                    "missing_component": "webhook",
                    "alternatives": ["Schedule checks", "Polling", "External service"]
                }
            ]
        })
        workflow_nodes.llm.ainvoke.return_value = mock_response
        
        # Run gap analysis
        result = await workflow_nodes.gap_analysis_node(sample_state)
        
        # Verify auto-resolution
        assert result["gap_negotiation_count"] == 2
        assert result["gap_status"] == "gap_resolved"  # Auto-resolved
        assert "selected_alternative" in result  # Auto-selected first alternative

    @pytest.mark.asyncio
    async def test_mcp_fallback_on_error(self, workflow_nodes, sample_state):
        """Test fallback behavior when MCP fails"""
        # Mock MCP failure
        workflow_nodes.mcp_client.get_node_types.side_effect = Exception("MCP connection failed")
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "gap_status": "no_gap",
            "negotiation_phrase": None,
            "identified_gaps": []
        })
        workflow_nodes.llm.ainvoke.return_value = mock_response
        
        # Run gap analysis - should use fallback
        result = await workflow_nodes.gap_analysis_node(sample_state)
        
        # Verify fallback was used
        assert result["stage"] == WorkflowStage.GAP_ANALYSIS
        # Should still work with fallback node types

    @pytest.mark.asyncio
    async def test_smart_alternative_scoring(self, workflow_nodes):
        """Test the smart alternative scoring logic"""
        # Test scoring for automation request
        score1 = workflow_nodes._score_alternative(
            "Use scheduled checks every hour",
            "I need email automation"
        )
        score2 = workflow_nodes._score_alternative(
            "Use complex custom webhook integration",
            "I need email automation"
        )
        
        # Scheduled + automation should score higher than complex
        assert score1 > score2
        
        # Test scoring for real-time request
        score3 = workflow_nodes._score_alternative(
            "Use webhook for instant updates",
            "I need real-time notifications"
        )
        score4 = workflow_nodes._score_alternative(
            "Use scheduled polling",
            "I need real-time notifications"
        )
        
        # Webhook + real-time should score higher
        assert score3 > score4

    @pytest.mark.asyncio
    async def test_routing_with_enhanced_gap_analysis(self, workflow_nodes, sample_state):
        """Test routing logic with enhanced gap analysis"""
        # Test routing with no gaps
        sample_state["gap_status"] = "no_gap"
        next_stage = workflow_nodes.should_continue(sample_state)
        assert next_stage == "workflow_generation"
        
        # Test routing with gaps (first round)
        sample_state["gap_status"] = "has_gap"
        sample_state["gap_negotiation_count"] = 0
        next_stage = workflow_nodes.should_continue(sample_state)
        assert next_stage == "clarification"
        
        # Test routing with gaps (max rounds reached)
        with patch("agents.nodes.settings.GAP_ANALYSIS_MAX_ROUNDS", 1):
            sample_state["gap_negotiation_count"] = 1
            next_stage = workflow_nodes.should_continue(sample_state)
            assert next_stage == "workflow_generation"

    @pytest.mark.asyncio
    async def test_configuration_settings(self, workflow_nodes, sample_state):
        """Test that configuration settings are properly applied"""
        with patch("agents.nodes.settings") as mock_settings:
            # Test with MCP disabled
            mock_settings.GAP_ANALYSIS_USE_MCP = False
            mock_settings.GAP_ANALYSIS_MAX_ROUNDS = 2
            mock_settings.GAP_ANALYSIS_AUTO_SELECT = True
            mock_settings.OPENAI_API_KEY = "test"
            mock_settings.DEFAULT_MODEL_NAME = "gpt-4"
            
            # Mock LLM response
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "gap_status": "no_gap",
                "negotiation_phrase": None,
                "identified_gaps": []
            })
            workflow_nodes.llm.ainvoke.return_value = mock_response
            
            # Run gap analysis
            result = await workflow_nodes.gap_analysis_node(sample_state)
            
            # MCP should not be called when disabled
            assert not workflow_nodes.mcp_client.get_node_types.called