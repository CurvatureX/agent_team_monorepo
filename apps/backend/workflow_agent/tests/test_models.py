"""
Tests for simplified workflow agent state management and data models
Updated for 6-node architecture
"""

from datetime import datetime
from typing import Any, Dict

import pytest
from agents.state import (
    ClarificationContext,
    Conversation,
    WorkflowOrigin,
    WorkflowStage,
    WorkflowState,
)


class TestEnums:
    """Test enum definitions for simplified architecture"""

    def test_workflow_stage_enum(self):
        """Test WorkflowStage enum values"""
        assert WorkflowStage.CLARIFICATION == "clarification"
        assert WorkflowStage.NEGOTIATION == "negotiation"
        assert WorkflowStage.GAP_ANALYSIS == "gap_analysis"
        assert WorkflowStage.WORKFLOW_GENERATION == "workflow_generation"
        assert WorkflowStage.DEBUG == "debug"
        assert WorkflowStage.COMPLETED == "completed"

    # Removed ClarificationPurpose enum - purpose field is no longer used

    def test_workflow_origin_enum(self):
        """Test WorkflowOrigin enum values"""
        assert WorkflowOrigin.CREATE == "create"
        assert WorkflowOrigin.EDIT == "edit"
        assert WorkflowOrigin.COPY == "copy"


class TestTypedDictModels:
    """Test TypedDict model definitions"""

    def test_conversation_creation(self):
        """Test Conversation TypedDict creation"""
        conversation = Conversation(role="user", text="我需要一个系统来自动处理客户邮件咨询")

        assert conversation["role"] == "user"
        assert conversation["text"] == "我需要一个系统来自动处理客户邮件咨询"

    def test_clarification_context_creation(self):
        """Test ClarificationContext TypedDict creation"""
        context: ClarificationContext = {
            "origin": WorkflowOrigin.CREATE,
            "pending_questions": ["请问您希望如何识别客户邮件？", "您希望使用哪种回复方式？"],
        }

        assert context["origin"] == WorkflowOrigin.CREATE
        assert len(context["pending_questions"]) == 2
        assert context["pending_questions"][0] == "请问您希望如何识别客户邮件？"

    def test_workflow_state_creation(self):
        """Test WorkflowState TypedDict creation"""
        now = datetime.now()

        state = {
            "session_id": "test_session_123",
            "user_id": "test_user",
            "created_at": int(now.timestamp() * 1000),
            "updated_at": int(now.timestamp() * 1000),
            "stage": WorkflowStage.CLARIFICATION,
            "previous_stage": None,
            "execution_history": [],
            "clarification_context": {
                "origin": WorkflowOrigin.CREATE,
                "pending_questions": ["请详细描述您的需求"],
            },
            "conversations": [
                Conversation(role="user", text="我需要邮件自动化"),
                Conversation(role="assistant", text="请详细描述您的需求"),
            ],
            "intent_summary": "邮件自动化系统",
            "gaps": ["email_authentication", "ai_integration"],
            "alternatives": ["使用简化版实现", "集成第三方服务"],
            "current_workflow": {
                "id": "workflow-123",
                "name": "邮件处理工作流",
                "nodes": [],
                "connections": [],
            },
            "debug_result": "",
            "debug_loop_count": 0,
        }

        # Verify all required fields are present
        assert state["session_id"] == "test_session_123"
        assert state["stage"] == WorkflowStage.CLARIFICATION
        assert "clarification_context" in state
        assert len(state["conversations"]) == 2
        assert state["intent_summary"] == "邮件自动化系统"
        assert len(state["gaps"]) == 2
        assert len(state["alternatives"]) == 2


class TestWorkflowStateStructure:
    """Test WorkflowState structure and behavior"""

    def test_minimal_workflow_state(self):
        """Test minimal required WorkflowState fields"""
        state = {
            "session_id": "test",
            "user_id": "test_user",
            "created_at": 1234567890,
            "updated_at": 1234567890,
            "stage": WorkflowStage.CLARIFICATION,
            "previous_stage": None,
            "execution_history": [],
            "clarification_context": {
                "origin": WorkflowOrigin.CREATE,
                "pending_questions": [],
            },
            "conversations": [],
            "intent_summary": "",
            "gaps": [],
            "alternatives": [],
            "current_workflow": {},
            "debug_result": "",
            "debug_loop_count": 0,
        }

        # Verify structure
        assert "session_id" in state
        assert "user_id" in state
        assert "created_at" in state
        assert "updated_at" in state
        assert "stage" in state
        assert "conversations" in state
        assert "intent_summary" in state
        assert "gaps" in state
        assert "alternatives" in state
        assert "current_workflow" in state
        assert "debug_result" in state
        assert "debug_loop_count" in state

    def test_clarification_stage_state(self):
        """Test state structure in clarification stage"""
        state = {
            "session_id": "test_clarification",
            "stage": WorkflowStage.CLARIFICATION,
            "previous_stage": None,
            "execution_history": [],
            "clarification_context": {
                "origin": WorkflowOrigin.CREATE,
                "pending_questions": ["需要更多信息"],
            },
            "conversations": [
                Conversation(role="user", text="创建邮件工作流"),
                Conversation(role="assistant", text="需要更多信息"),
            ],
            "intent_summary": "邮件工作流创建",
            "gaps": [],
            "alternatives": [],
            "current_workflow": {},
            "debug_result": "",
            "debug_loop_count": 0,
        }

        # Verify clarification-specific fields
        assert state["stage"] == WorkflowStage.CLARIFICATION
        assert "clarification_context" in state
        assert state["clarification_context"]["origin"] == WorkflowOrigin.CREATE
        assert len(state["clarification_context"]["pending_questions"]) == 1

    def test_gap_analysis_stage_state(self):
        """Test state structure in gap analysis stage"""
        state = {
            "session_id": "test_gap_analysis",
            "stage": WorkflowStage.GAP_ANALYSIS,
            "previous_stage": None,
            "execution_history": [],
            "clarification_context": {
                "origin": WorkflowOrigin.CREATE,
                "pending_questions": [],
            },
            "conversations": [
                Conversation(role="user", text="邮件自动回复系统"),
                Conversation(role="assistant", text="分析能力差距中..."),
            ],
            "intent_summary": "邮件自动回复系统",
            "gaps": ["email_api_access", "ai_response_generation"],
            "alternatives": [],
            "current_workflow": {},
            "debug_result": "",
            "debug_loop_count": 0,
        }

        # Verify gap analysis stage
        assert state["stage"] == WorkflowStage.GAP_ANALYSIS
        assert len(state["gaps"]) == 2
        assert "email_api_access" in state["gaps"]
        assert "ai_response_generation" in state["gaps"]

    def test_generation_stage_state(self):
        """Test state structure in generation stage"""
        workflow = {
            "id": "workflow-456",
            "name": "邮件处理系统",
            "description": "自动处理客户邮件",
            "nodes": [
                {"id": "trigger", "type": "email_trigger", "name": "邮件触发器"},
                {"id": "analyzer", "type": "ai_agent", "name": "AI分析器"},
            ],
            "connections": [{"from": "trigger", "to": "analyzer"}],
        }

        state = {
            "session_id": "test_generation",
            "stage": WorkflowStage.WORKFLOW_GENERATION,
            "previous_stage": None,
            "execution_history": [],
            "clarification_context": {
                "origin": WorkflowOrigin.CREATE,
                "pending_questions": [],
            },
            "conversations": [
                Conversation(role="user", text="生成邮件处理工作流"),
                Conversation(role="assistant", text="正在生成工作流..."),
            ],
            "intent_summary": "邮件处理自动化",
            "gaps": ["email_authentication"],
            "alternatives": ["使用OAuth认证", "使用API密钥"],
            "current_workflow": workflow,
            "debug_result": "",
            "debug_loop_count": 0,
        }

        # Verify generation stage
        assert state["stage"] == WorkflowStage.WORKFLOW_GENERATION
        assert "current_workflow" in state
        assert state["current_workflow"]["id"] == "workflow-456"
        assert len(state["current_workflow"]["nodes"]) == 2
        assert len(state["current_workflow"]["connections"]) == 1

    def test_debugging_stage_state(self):
        """Test state structure in debugging stage"""
        debug_result = {
            "success": False,
            "errors": ["Missing email credentials"],
            "warnings": ["Consider adding error handling"],
            "iteration": 1,
        }

        state = {
            "session_id": "test_debugging",
            "stage": WorkflowStage.DEBUG,
            "previous_stage": None,
            "execution_history": [],
            "clarification_context": {
                "origin": WorkflowOrigin.CREATE,
                "pending_questions": [],
            },
            "conversations": [
                Conversation(role="assistant", text="工作流验证中发现问题"),
                Conversation(role="user", text="请修复这些问题"),
            ],
            "intent_summary": "邮件工作流调试",
            "gaps": ["email_credentials"],
            "alternatives": [],
            "current_workflow": {"id": "workflow-debug", "nodes": [], "connections": []},
            "debug_result": str(debug_result),
            "debug_loop_count": 1,
        }

        # Verify debugging stage
        assert state["stage"] == WorkflowStage.DEBUG
        assert state["debug_loop_count"] == 1
        assert "Missing email credentials" in state["debug_result"]

    def test_completed_stage_state(self):
        """Test state structure in completed stage"""
        final_workflow = {
            "id": "workflow-final",
            "name": "完整邮件处理系统",
            "nodes": [
                {"id": "email_trigger", "type": "trigger"},
                {"id": "ai_processor", "type": "ai_agent"},
                {"id": "email_sender", "type": "action"},
            ],
            "connections": [
                {"from": "email_trigger", "to": "ai_processor"},
                {"from": "ai_processor", "to": "email_sender"},
            ],
        }

        state = {
            "session_id": "test_completed",
            "stage": WorkflowStage.COMPLETED,
            "previous_stage": None,
            "execution_history": [],
            "clarification_context": {
                "origin": WorkflowOrigin.CREATE,
                "pending_questions": [],
            },
            "conversations": [
                Conversation(role="assistant", text="工作流生成成功！"),
                Conversation(role="user", text="谢谢！"),
            ],
            "intent_summary": "完整的邮件处理系统",
            "gaps": [],
            "alternatives": [],
            "current_workflow": final_workflow,
            "debug_result": '{"success": true, "errors": [], "warnings": []}',
            "debug_loop_count": 1,
        }

        # Verify completed stage
        assert state["stage"] == WorkflowStage.COMPLETED
        assert len(state["gaps"]) == 0  # No gaps remaining
        assert len(state["current_workflow"]["nodes"]) == 3
        assert '"success": true' in state["debug_result"]


class TestStateTransitions:
    """Test valid state transitions in the workflow"""

    def test_stage_progression(self):
        """Test normal stage progression"""
        stages = [
            WorkflowStage.CLARIFICATION,
            WorkflowStage.NEGOTIATION,
            WorkflowStage.GAP_ANALYSIS,
            WorkflowStage.WORKFLOW_GENERATION,
            WorkflowStage.DEBUG,
            WorkflowStage.COMPLETED,
        ]

        # Verify all stages are accessible
        for stage in stages:
            assert isinstance(stage, str)
            assert stage in [s.value for s in WorkflowStage]

    def test_state_history_tracking(self):
        """Test previous_stage and execution_history tracking"""
        state = {
            "session_id": "test_history",
            "stage": WorkflowStage.GAP_ANALYSIS,
            "previous_stage": "clarification",
            "execution_history": ["clarification", "negotiation", "gap_analysis"],
            "clarification_context": {
                "origin": WorkflowOrigin.CREATE,
                "pending_questions": [],
            },
            "conversations": [],
            "intent_summary": "",
            "gaps": [],
            "alternatives": [],
            "current_workflow": {},
            "debug_result": "",
            "debug_loop_count": 0,
        }

        assert state["previous_stage"] == "clarification"
        assert len(state["execution_history"]) == 3
        assert state["execution_history"][-1] == "gap_analysis"

    def test_workflow_origins(self):
        """Test different workflow origins"""
        origins = [WorkflowOrigin.CREATE, WorkflowOrigin.EDIT, WorkflowOrigin.COPY]

        for origin in origins:
            context: ClarificationContext = {"origin": origin, "pending_questions": []}
            assert context["origin"] == origin


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
