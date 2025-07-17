"""
Pytest configuration and shared fixtures for workflow agent tests
"""

import asyncio
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.state import GapSeverity, SolutionReliability, SolutionType, WorkflowStage


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
def sample_parsed_intent():
    """Sample parsed intent for testing"""
    return {
        "primary_goal": "监控邮箱并自动处理客户咨询",
        "secondary_goals": ["提高响应速度", "减少人工工作量", "保持专业服务质量"],
        "constraints": ["使用现有Gmail账户", "保持24小时内回复", "确保回复专业性"],
        "success_criteria": ["自动识别客户邮件", "智能生成回复内容", "人工审核复杂问题"],
    }


@pytest.fixture
def sample_capability_analysis():
    """Sample capability analysis for testing"""
    return {
        "required_capabilities": [
            "email_monitoring",
            "customer_detection",
            "ai_response_generation",
            "human_escalation",
        ],
        "available_capabilities": ["email_monitoring", "human_escalation"],
        "capability_gaps": ["customer_detection", "ai_response_generation"],
        "gap_severity": {
            "customer_detection": GapSeverity.MEDIUM,
            "ai_response_generation": GapSeverity.HIGH,
        },
        "potential_solutions": {
            "customer_detection": [
                {
                    "type": SolutionType.CODE_NODE,
                    "complexity": 4,
                    "setup_time": "1-2小时",
                    "requires_user_action": "配置关键词规则",
                    "reliability": SolutionReliability.MEDIUM,
                    "description": "基于关键词的客户邮件识别",
                },
                {
                    "type": SolutionType.API_INTEGRATION,
                    "complexity": 7,
                    "setup_time": "4-6小时",
                    "requires_user_action": "集成NLP API",
                    "reliability": SolutionReliability.HIGH,
                    "description": "使用AI进行邮件内容分析",
                },
            ],
            "ai_response_generation": [
                {
                    "type": SolutionType.NATIVE,
                    "complexity": 5,
                    "setup_time": "2-3小时",
                    "requires_user_action": "配置AI模板",
                    "reliability": SolutionReliability.HIGH,
                    "description": "使用内置AI回复生成器",
                }
            ],
        },
        "complexity_scores": {"customer_detection": 5, "ai_response_generation": 6},
    }


@pytest.fixture
def sample_task_tree():
    """Sample task tree for testing"""
    return {
        "root_task": "智能客户邮件处理系统",
        "subtasks": [
            {
                "name": "邮件监控",
                "description": "持续监控Gmail邮箱新邮件",
                "estimated_complexity": 3,
                "critical_path": True,
                "dependencies": [],
                "parallel_opportunity": False,
            },
            {
                "name": "客户识别",
                "description": "识别和分类客户邮件",
                "estimated_complexity": 5,
                "critical_path": True,
                "dependencies": ["邮件监控"],
                "parallel_opportunity": False,
            },
            {
                "name": "内容分析",
                "description": "分析邮件内容和意图",
                "estimated_complexity": 6,
                "critical_path": True,
                "dependencies": ["客户识别"],
                "parallel_opportunity": True,
            },
            {
                "name": "回复生成",
                "description": "生成个性化回复内容",
                "estimated_complexity": 7,
                "critical_path": True,
                "dependencies": ["内容分析"],
                "parallel_opportunity": False,
            },
            {
                "name": "质量审核",
                "description": "审核回复质量和适当性",
                "estimated_complexity": 4,
                "critical_path": True,
                "dependencies": ["回复生成"],
                "parallel_opportunity": True,
            },
            {
                "name": "邮件发送",
                "description": "发送最终回复邮件",
                "estimated_complexity": 2,
                "critical_path": True,
                "dependencies": ["质量审核"],
                "parallel_opportunity": False,
            },
        ],
        "dependencies": [
            {"from": "邮件监控", "to": "客户识别", "type": "sequential"},
            {"from": "客户识别", "to": "内容分析", "type": "sequential"},
            {"from": "内容分析", "to": "回复生成", "type": "sequential"},
            {"from": "回复生成", "to": "质量审核", "type": "sequential"},
            {"from": "质量审核", "to": "邮件发送", "type": "sequential"},
        ],
        "parallel_opportunities": [["内容分析", "客户历史查询"], ["质量审核", "回复模板匹配"]],
    }


@pytest.fixture
def sample_workflow_architecture():
    """Sample workflow architecture for testing"""
    return {
        "pattern_used": "customer_service_automation",
        "nodes": [
            {
                "id": "email_trigger",
                "type": "TRIGGER_EMAIL",
                "role": "trigger",
                "parameters": {
                    "email_provider": "gmail",
                    "check_interval": "*/5 * * * *",
                    "folder": "INBOX",
                },
                "position": {"x": 100, "y": 100},
            },
            {
                "id": "customer_filter",
                "type": "AI_TASK_ANALYZER",
                "role": "analysis",
                "parameters": {"model": "gpt-4", "temperature": 0.1, "task": "customer_detection"},
                "position": {"x": 300, "y": 100},
            },
            {
                "id": "content_analyzer",
                "type": "AI_TASK_ANALYZER",
                "role": "analysis",
                "parameters": {"model": "gpt-4", "temperature": 0.2, "task": "content_analysis"},
                "position": {"x": 500, "y": 100},
            },
            {
                "id": "response_generator",
                "type": "AI_AGENT_NODE",
                "role": "generation",
                "parameters": {
                    "model": "gpt-4",
                    "temperature": 0.3,
                    "system_prompt": "You are a professional customer service agent.",
                },
                "position": {"x": 700, "y": 100},
            },
            {
                "id": "quality_check",
                "type": "FLOW_IF",
                "role": "routing",
                "parameters": {
                    "condition": "{{response.confidence}} > 0.8",
                    "true_branch": "send_email",
                    "false_branch": "human_review",
                },
                "position": {"x": 900, "y": 100},
            },
            {
                "id": "email_sender",
                "type": "EXTERNAL_EMAIL",
                "role": "output",
                "parameters": {"provider": "gmail", "template": "customer_response"},
                "position": {"x": 1100, "y": 100},
            },
        ],
        "connections": [
            {
                "source": "email_trigger",
                "target": "customer_filter",
                "type": "main",
                "data_mapping": {"email_data": "input"},
            },
            {
                "source": "customer_filter",
                "target": "content_analyzer",
                "type": "main",
                "condition": "{{customer_detected}} == true",
            },
            {
                "source": "content_analyzer",
                "target": "response_generator",
                "type": "main",
                "data_mapping": {"analysis": "context"},
            },
            {
                "source": "response_generator",
                "target": "quality_check",
                "type": "main",
                "data_mapping": {"response": "input"},
            },
            {
                "source": "quality_check",
                "target": "email_sender",
                "type": "true",
                "data_mapping": {"response": "content"},
            },
        ],
        "data_flow": {
            "input_schema": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "object",
                        "properties": {
                            "subject": {"type": "string"},
                            "body": {"type": "string"},
                            "sender": {"type": "string"},
                            "timestamp": {"type": "string"},
                        },
                    }
                },
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "response_sent": {"type": "boolean"},
                    "response_content": {"type": "string"},
                    "confidence": {"type": "number"},
                },
            },
            "intermediate_data": {
                "customer_detection": {"type": "boolean"},
                "content_analysis": {"type": "object"},
                "generated_response": {"type": "string"},
                "quality_score": {"type": "number"},
            },
        },
        "error_handling": {
            "retry_policies": {
                "default": {"max_attempts": 3, "backoff": "exponential"},
                "ai_analysis": {"max_attempts": 2, "backoff": "linear"},
                "email_sending": {"max_attempts": 5, "backoff": "exponential"},
            },
            "fallback_strategies": {
                "ai_analysis_failure": "use_rule_based_detection",
                "response_generation_failure": "use_template_response",
                "email_sending_failure": "queue_for_manual_sending",
            },
            "error_notification": {
                "enabled": True,
                "channels": ["email", "slack"],
                "severity_threshold": "medium",
            },
        },
        "performance_considerations": [
            "缓存邮件分析结果避免重复处理",
            "批量处理多个邮件提高效率",
            "异步处理提高响应速度",
            "限制并发AI调用避免超出配额",
        ],
    }


@pytest.fixture
def sample_workflow_dsl():
    """Sample workflow DSL for testing"""
    return {
        "version": "1.0",
        "metadata": {
            "name": "智能客户邮件处理",
            "description": "自动监控、分析和回复客户邮件",
            "pattern": "customer_service_automation",
            "created_at": datetime.now().isoformat(),
            "estimated_performance": {
                "avg_execution_time": "3-8秒",
                "throughput": "50-200邮件/小时",
                "reliability": "95%+ (含重试机制)",
            },
        },
        "nodes": [
            {
                "id": "email_trigger",
                "type": "TRIGGER_EMAIL",
                "name": "邮件监控触发器",
                "description": "监控Gmail邮箱新邮件",
                "position": {"x": 100, "y": 100},
                "parameters": {
                    "email_provider": "gmail",
                    "check_interval": "*/5 * * * *",
                    "folder": "INBOX",
                    "mark_as_read": False,
                },
            },
            {
                "id": "customer_detector",
                "type": "AI_TASK_ANALYZER",
                "name": "客户邮件识别",
                "description": "识别和分类客户邮件",
                "position": {"x": 300, "y": 100},
                "parameters": {
                    "model": "gpt-4",
                    "temperature": 0.1,
                    "max_tokens": 500,
                    "system_prompt": "分析邮件内容，判断是否为客户咨询邮件",
                    "output_format": "json",
                },
            },
            {
                "id": "response_generator",
                "type": "AI_AGENT_NODE",
                "name": "智能回复生成",
                "description": "生成个性化客户回复",
                "position": {"x": 500, "y": 100},
                "parameters": {
                    "model": "gpt-4",
                    "temperature": 0.3,
                    "max_tokens": 1000,
                    "system_prompt": "你是专业的客户服务代表，请生成礼貌、专业的回复",
                    "memory_enabled": True,
                },
            },
        ],
        "connections": {
            "email_trigger": {"main": [{"node": "customer_detector", "type": "main", "index": 0}]},
            "customer_detector": {
                "main": [{"node": "response_generator", "type": "main", "index": 0}]
            },
        },
        "settings": {
            "timeout": 300,
            "error_policy": "STOP_WORKFLOW",
            "caller_policy": "WORKFLOW_MAIN",
            "retry_on_failure": True,
            "max_execution_time": 600,
        },
    }


@pytest.fixture
def sample_optimization_suggestions():
    """Sample optimization suggestions for testing"""
    return [
        {
            "type": "performance",
            "category": "parallelization",
            "description": "将邮件分析和客户历史查询并行执行",
            "impact_score": 8,
            "implementation_complexity": 4,
            "priority": "high",
            "estimated_improvement": "减少30-50%执行时间",
        },
        {
            "type": "performance",
            "category": "caching",
            "description": "缓存常见问题的回复模板",
            "impact_score": 6,
            "implementation_complexity": 3,
            "priority": "medium",
            "estimated_improvement": "减少20%AI调用成本",
        },
        {
            "type": "reliability",
            "category": "error_handling",
            "description": "添加AI服务降级和重试机制",
            "impact_score": 9,
            "implementation_complexity": 5,
            "priority": "high",
            "estimated_improvement": "提升可靠性至99%+",
        },
        {
            "type": "reliability",
            "category": "monitoring",
            "description": "添加邮件处理状态监控和告警",
            "impact_score": 7,
            "implementation_complexity": 4,
            "priority": "medium",
            "estimated_improvement": "快速发现和解决问题",
        },
        {
            "type": "cost",
            "category": "resource_optimization",
            "description": "优化AI模型调用频率和批处理策略",
            "impact_score": 6,
            "implementation_complexity": 3,
            "priority": "medium",
            "estimated_improvement": "降低运营成本25%",
        },
    ]


@pytest.fixture
def sample_mvp_session_state():
    """Sample complete MVP session state for testing"""
    return {
        "metadata": {
            "session_id": "test_session_12345",
            "user_id": "test_user",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "version": "1.0.0",
            "interaction_count": 3,
        },
        "stage": WorkflowStage.DESIGN,
        "requirement_negotiation": {
            "original_requirements": "我需要一个系统来自动处理客户邮件咨询",
            "parsed_intent": {
                "primary_goal": "客户邮件自动化处理",
                "secondary_goals": ["提高响应速度", "减少人工工作量"],
                "constraints": ["使用Gmail", "保持专业回复", "24小时内响应"],
            },
            "capability_analysis": {
                "required_capabilities": ["email_monitoring", "ai_analysis", "response_generation"],
                "available_capabilities": ["email_monitoring"],
                "capability_gaps": ["ai_analysis", "response_generation"],
                "gap_severity": {
                    "ai_analysis": GapSeverity.MEDIUM,
                    "response_generation": GapSeverity.HIGH,
                },
                "potential_solutions": {},
                "complexity_scores": {"ai_analysis": 5, "response_generation": 7},
            },
            "identified_constraints": [
                {
                    "type": "technical",
                    "description": "使用Gmail账户",
                    "severity": GapSeverity.LOW,
                    "impact": "限制邮件提供商选择",
                }
            ],
            "proposed_solutions": [],
            "user_decisions": [
                {
                    "question": "选择AI分析方案？",
                    "answer": "使用GPT-4进行邮件分析",
                    "timestamp": datetime.now(),
                    "confidence": 0.9,
                }
            ],
            "negotiation_history": [
                {
                    "question": "您希望系统如何识别客户邮件？",
                    "user_response": "通过邮件内容和发件人分析",
                    "analysis": {"intent": "analysis_preference"},
                    "recommendations": ["使用AI分析邮件内容"],
                    "timestamp": datetime.now(),
                }
            ],
            "final_requirements": "使用Gmail监控客户邮件，AI分析内容并生成专业回复",
            "confidence_score": 0.85,
        },
        "design_state": {
            "task_tree": {},
            "architecture": {},
            "workflow_dsl": {},
            "optimization_suggestions": [],
            "design_patterns_used": ["customer_service_automation"],
            "estimated_performance": {
                "avg_execution_time": "3-8秒",
                "throughput": "100邮件/小时",
                "resource_usage": {"cpu": "1核", "memory": "512MB"},
                "reliability_score": 0.95,
            },
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
            "static_validation": {
                "syntax_valid": True,
                "logic_valid": True,
                "completeness_score": 0.9,
            },
            "configuration_completeness": {
                "complete": False,
                "missing_parameters": ["gmail_oauth_token"],
                "completeness_percentage": 0.8,
            },
        },
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
def assert_valid_workflow_dsl(dsl: Dict[str, Any]):
    """Assert that a workflow DSL has valid structure"""
    required_fields = ["version", "nodes", "connections", "settings"]
    for field in required_fields:
        assert field in dsl, f"Missing required field: {field}"

    assert isinstance(dsl["nodes"], list), "Nodes must be a list"
    assert isinstance(dsl["connections"], dict), "Connections must be a dict"
    assert isinstance(dsl["settings"], dict), "Settings must be a dict"


def assert_valid_task_tree(task_tree: Dict[str, Any]):
    """Assert that a task tree has valid structure"""
    required_fields = ["root_task", "subtasks", "dependencies"]
    for field in required_fields:
        assert field in task_tree, f"Missing required field: {field}"

    assert isinstance(task_tree["subtasks"], list), "Subtasks must be a list"
    assert isinstance(task_tree["dependencies"], list), "Dependencies must be a list"


def assert_valid_capability_analysis(analysis: Dict[str, Any]):
    """Assert that capability analysis has valid structure"""
    required_fields = [
        "required_capabilities",
        "available_capabilities",
        "capability_gaps",
        "gap_severity",
        "potential_solutions",
    ]
    for field in required_fields:
        assert field in analysis, f"Missing required field: {field}"

    assert isinstance(analysis["required_capabilities"], list)
    assert isinstance(analysis["available_capabilities"], list)
    assert isinstance(analysis["capability_gaps"], list)
    assert isinstance(analysis["gap_severity"], dict)
    assert isinstance(analysis["potential_solutions"], dict)
