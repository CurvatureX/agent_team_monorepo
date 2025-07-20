"""
Pytest configuration and shared fixtures for workflow agent tests
Updated for simplified 6-node architecture
"""

import asyncio
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.state import (
    ClarificationContext,
    ClarificationPurpose,
    Conversation,
    WorkflowOrigin,
    WorkflowStage,
)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    with patch("core.config.settings") as mock:
        mock.DEFAULT_MODEL_PROVIDER = "openai"
        mock.DEFAULT_MODEL_NAME = "gpt-4"
        mock.OPENAI_API_KEY = "test-openai-key"
        mock.ANTHROPIC_API_KEY = "test-anthropic-key"
        yield mock


@pytest.fixture
def mock_llm():
    """Mock LLM for testing"""
    llm = MagicMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def sample_conversations():
    """Sample conversations for testing"""
    return [
        Conversation(role="user", text="我需要一个系统来自动处理客户邮件咨询"),
        Conversation(role="assistant", text="我理解您需要自动化处理客户邮件。请问您希望如何识别客户邮件？"),
        Conversation(role="user", text="通过邮件内容和发件人分析"),
    ]


@pytest.fixture
def sample_clarification_context():
    """Sample clarification context for testing"""
    return ClarificationContext(
        purpose=ClarificationPurpose.INITIAL_INTENT,
        origin=WorkflowOrigin.NEW_WORKFLOW,
        pending_questions=["请问您希望如何识别客户邮件？", "您希望使用哪种回复方式？"],
    )


@pytest.fixture
def sample_gaps():
    """Sample capability gaps for testing"""
    return ["email_authentication", "ai_integration", "external_service_connection"]


@pytest.fixture
def sample_alternatives():
    """Sample alternative solutions for testing"""
    return ["使用简化版邮件检测（关键词匹配）", "集成第三方AI服务进行邮件分析", "手动配置邮件规则和模板"]


@pytest.fixture
def sample_simple_workflow():
    """Sample simple workflow for testing"""
    return {
        "id": "workflow-test123",
        "name": "客户邮件处理工作流",
        "description": "自动处理客户邮件咨询",
        "nodes": [
            {"id": "start", "type": "trigger", "name": "Start", "parameters": {}},
            {
                "id": "email_monitor",
                "type": "email_trigger",
                "name": "Email Monitor",
                "parameters": {"provider": "gmail"},
            },
            {
                "id": "ai_analyze",
                "type": "ai_agent",
                "name": "AI Analyzer",
                "parameters": {"model": "gpt-4"},
            },
            {
                "id": "send_response",
                "type": "email_sender",
                "name": "Send Response",
                "parameters": {},
            },
        ],
        "connections": [
            {"from": "start", "to": "email_monitor"},
            {"from": "email_monitor", "to": "ai_analyze"},
            {"from": "ai_analyze", "to": "send_response"},
        ],
        "created_at": 1234567890,
    }


@pytest.fixture
def sample_debug_result():
    """Sample debug result for testing"""
    return {"success": True, "errors": [], "warnings": ["建议添加错误处理机制"], "iteration": 1}


@pytest.fixture
def sample_simplified_workflow_state():
    """Sample simplified workflow state for testing"""
    return {
        "metadata": {
            "session_id": "test_session_12345",
            "user_id": "test_user",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "version": "2.0.0",
            "interaction_count": 3,
        },
        "stage": WorkflowStage.CLARIFICATION,
        "clarification_context": ClarificationContext(
            purpose=ClarificationPurpose.INITIAL_INTENT,
            origin=WorkflowOrigin.NEW_WORKFLOW,
            pending_questions=["请问您希望如何识别客户邮件？"],
        ),
        "conversations": [
            Conversation(role="user", text="我需要一个系统来自动处理客户邮件咨询"),
            Conversation(role="assistant", text="我理解您需要自动化处理客户邮件"),
        ],
        "intent_summary": "客户邮件自动化处理系统",
        "gaps": ["email_authentication", "ai_integration"],
        "alternatives": ["使用简化版邮件检测", "集成第三方AI服务"],
        "current_workflow": {
            "id": "workflow-test123",
            "name": "客户邮件处理",
            "nodes": [],
            "connections": [],
        },
        "debug_result": "",
        "debug_loop_count": 0,
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for testing"""

    def _create_response(content: str):
        response = MagicMock()
        response.content = content
        return response

    return _create_response


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response for testing"""

    def _create_response(content: str):
        response = MagicMock()
        response.content = content
        return response

    return _create_response


# Test utility functions
def assert_valid_simple_workflow(workflow: Dict[str, Any]):
    """Assert that a simple workflow has valid structure"""
    required_fields = ["id", "name", "nodes", "connections"]
    for field in required_fields:
        assert field in workflow, f"Missing required field: {field}"

    assert isinstance(workflow["nodes"], list), "Nodes must be a list"
    assert isinstance(workflow["connections"], list), "Connections must be a list"


def assert_valid_workflow_state(state: Dict[str, Any]):
    """Assert that a workflow state has valid structure"""
    required_fields = ["metadata", "stage", "conversations", "intent_summary"]
    for field in required_fields:
        assert field in state, f"Missing required field: {field}"

    assert isinstance(state["conversations"], list), "Conversations must be a list"
    assert isinstance(state["intent_summary"], str), "Intent summary must be a string"


def assert_valid_debug_result(debug_result: Dict[str, Any]):
    """Assert that a debug result has valid structure"""
    required_fields = ["success", "errors", "warnings", "iteration"]
    for field in required_fields:
        assert field in debug_result, f"Missing required field: {field}"

    assert isinstance(debug_result["success"], bool), "Success must be a boolean"
    assert isinstance(debug_result["errors"], list), "Errors must be a list"
    assert isinstance(debug_result["warnings"], list), "Warnings must be a list"
    assert isinstance(debug_result["iteration"], int), "Iteration must be an integer"
