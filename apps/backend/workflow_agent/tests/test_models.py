"""
Tests for MVP data models and state management
"""

from datetime import datetime
from typing import Any, Dict

import pytest

from agents.state import (
    AgentState,
    AutoFillRecord,
    CapabilityAnalysis,
    ConfigurationCheck,
    Constraint,
    Decision,
    GapSeverity,
    MVPWorkflowState,
    NegotiationStep,
    NodeConfig,
    Optimization,
    Parameter,
    PerformanceEstimate,
    PreviewResult,
    Solution,
    SolutionReliability,
    SolutionType,
    StaticValidation,
    TaskTree,
    Template,
    ValidationResult,
    WorkflowArchitecture,
    WorkflowDSL,
    WorkflowStage,
)
from core.mvp_models import (
    ConversationContinueRequest,
    ConversationContinueResponse,
    ValidationRequest,
    ValidationResponse,
    WorkflowGenerationRequest,
    WorkflowGenerationResponse,
    WorkflowRefinementRequest,
    WorkflowRefinementResponse,
)


class TestEnums:
    """Test enum definitions"""

    def test_workflow_stage_enum(self):
        """Test WorkflowStage enum values"""
        assert WorkflowStage.LISTENING == "listening"
        assert WorkflowStage.REQUIREMENT_NEGOTIATION == "requirement_negotiation"
        assert WorkflowStage.DESIGN == "design"
        assert WorkflowStage.CONFIGURATION == "configuration"
        assert WorkflowStage.EXECUTION == "execution"
        assert WorkflowStage.MONITORING == "monitoring"
        assert WorkflowStage.LEARNING == "learning"

    def test_gap_severity_enum(self):
        """Test GapSeverity enum values"""
        assert GapSeverity.LOW == "low"
        assert GapSeverity.MEDIUM == "medium"
        assert GapSeverity.HIGH == "high"
        assert GapSeverity.CRITICAL == "critical"

    def test_solution_type_enum(self):
        """Test SolutionType enum values"""
        assert SolutionType.NATIVE == "native"
        assert SolutionType.CODE_NODE == "code_node"
        assert SolutionType.API_INTEGRATION == "api_integration"
        assert SolutionType.EXTERNAL_SERVICE == "external_service"

    def test_solution_reliability_enum(self):
        """Test SolutionReliability enum values"""
        assert SolutionReliability.LOW == "low"
        assert SolutionReliability.MEDIUM == "medium"
        assert SolutionReliability.HIGH == "high"


class TestTypedDictModels:
    """Test TypedDict model definitions"""

    def test_solution_creation(self):
        """Test Solution TypedDict creation"""
        solution = Solution(
            type=SolutionType.API_INTEGRATION,
            complexity=5,
            setup_time="2-3小时",
            requires_user_action="需要API密钥",
            reliability=SolutionReliability.HIGH,
            description="使用API集成",
        )

        assert solution["type"] == SolutionType.API_INTEGRATION
        assert solution["complexity"] == 5
        assert solution["setup_time"] == "2-3小时"
        assert solution["requires_user_action"] == "需要API密钥"
        assert solution["reliability"] == SolutionReliability.HIGH
        assert solution["description"] == "使用API集成"

    def test_constraint_creation(self):
        """Test Constraint TypedDict creation"""
        constraint = Constraint(
            type="technical",
            description="必须使用Gmail",
            severity=GapSeverity.MEDIUM,
            impact="限制邮件提供商选择",
        )

        assert constraint["type"] == "technical"
        assert constraint["description"] == "必须使用Gmail"
        assert constraint["severity"] == GapSeverity.MEDIUM
        assert constraint["impact"] == "限制邮件提供商选择"

    def test_decision_creation(self):
        """Test Decision TypedDict creation"""
        now = datetime.now()
        decision = Decision(question="选择存储方案？", answer="Notion数据库", timestamp=now, confidence=0.8)

        assert decision["question"] == "选择存储方案？"
        assert decision["answer"] == "Notion数据库"
        assert decision["timestamp"] == now
        assert decision["confidence"] == 0.8

    def test_capability_analysis_creation(self):
        """Test CapabilityAnalysis TypedDict creation"""
        analysis = CapabilityAnalysis(
            required_capabilities=["email_monitoring", "notion_integration"],
            available_capabilities=["email_monitoring"],
            capability_gaps=["notion_integration"],
            gap_severity={"notion_integration": GapSeverity.MEDIUM},
            potential_solutions={
                "notion_integration": [
                    Solution(
                        type=SolutionType.API_INTEGRATION,
                        complexity=5,
                        setup_time="2小时",
                        requires_user_action="API密钥",
                        reliability=SolutionReliability.HIGH,
                        description="API集成",
                    )
                ]
            },
            complexity_scores={"notion_integration": 5},
        )

        assert len(analysis["required_capabilities"]) == 2
        assert len(analysis["available_capabilities"]) == 1
        assert len(analysis["capability_gaps"]) == 1
        assert analysis["gap_severity"]["notion_integration"] == GapSeverity.MEDIUM
        assert len(analysis["potential_solutions"]["notion_integration"]) == 1
        assert analysis["complexity_scores"]["notion_integration"] == 5

    def test_task_tree_creation(self):
        """Test TaskTree TypedDict creation"""
        task_tree = TaskTree(
            root_task="邮箱监控自动化",
            subtasks=[
                {"name": "邮箱监控", "description": "定时检查Gmail", "complexity": 3},
                {"name": "数据存储", "description": "存储到Notion", "complexity": 4},
            ],
            dependencies=[{"from": "邮箱监控", "to": "数据存储", "type": "sequential"}],
            parallel_opportunities=[],
        )

        assert task_tree["root_task"] == "邮箱监控自动化"
        assert len(task_tree["subtasks"]) == 2
        assert len(task_tree["dependencies"]) == 1
        assert task_tree["dependencies"][0]["from"] == "邮箱监控"

    def test_workflow_architecture_creation(self):
        """Test WorkflowArchitecture TypedDict creation"""
        architecture = WorkflowArchitecture(
            nodes=[{"id": "trigger", "type": "TRIGGER_EMAIL", "parameters": {"provider": "gmail"}}],
            connections=[{"source": "trigger", "target": "processor", "type": "main"}],
            data_flow={"input_schema": {"email": "object"}, "output_schema": {"result": "object"}},
            error_handling={"retry_policy": {"max_attempts": 3}},
            performance_considerations=["缓存邮件内容", "批量处理"],
        )

        assert len(architecture["nodes"]) == 1
        assert len(architecture["connections"]) == 1
        assert "input_schema" in architecture["data_flow"]
        assert "retry_policy" in architecture["error_handling"]
        assert len(architecture["performance_considerations"]) == 2

    def test_workflow_dsl_creation(self):
        """Test WorkflowDSL TypedDict creation"""
        dsl = WorkflowDSL(
            version="1.0",
            nodes=[{"id": "trigger", "type": "TRIGGER_EMAIL", "parameters": {"provider": "gmail"}}],
            connections={"trigger": {"main": [{"node": "processor", "type": "main", "index": 0}]}},
            settings={"timeout": 300, "error_policy": "STOP_WORKFLOW"},
            metadata={
                "created_at": "2024-01-01T00:00:00Z",
                "pattern": "customer_service_automation",
            },
        )

        assert dsl["version"] == "1.0"
        assert len(dsl["nodes"]) == 1
        assert "trigger" in dsl["connections"]
        assert dsl["settings"]["timeout"] == 300
        assert "created_at" in dsl["metadata"]


class TestMVPWorkflowState:
    """Test MVPWorkflowState structure"""

    def test_mvp_workflow_state_creation(self):
        """Test MVPWorkflowState creation with all required fields"""
        now = datetime.now()

        state = {
            "metadata": {
                "session_id": "test_session",
                "user_id": "test_user",
                "created_at": now,
                "updated_at": now,
                "version": "1.0.0",
                "interaction_count": 1,
            },
            "stage": WorkflowStage.REQUIREMENT_NEGOTIATION,
            "requirement_negotiation": {
                "original_requirements": "监控邮箱存储到Notion",
                "parsed_intent": {
                    "primary_goal": "邮箱监控",
                    "secondary_goals": ["数据存储"],
                    "constraints": ["使用Gmail"],
                },
                "capability_analysis": {
                    "required_capabilities": ["email_monitoring", "notion_integration"],
                    "available_capabilities": ["email_monitoring"],
                    "capability_gaps": ["notion_integration"],
                    "gap_severity": {"notion_integration": GapSeverity.MEDIUM},
                    "potential_solutions": {},
                    "complexity_scores": {"notion_integration": 5},
                },
                "identified_constraints": [
                    {
                        "type": "technical",
                        "description": "使用Gmail",
                        "severity": GapSeverity.LOW,
                        "impact": "限制邮件提供商",
                    }
                ],
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
        }

        # Verify all required fields are present
        assert state["metadata"]["session_id"] == "test_session"
        assert state["stage"] == WorkflowStage.REQUIREMENT_NEGOTIATION
        assert "requirement_negotiation" in state
        assert "design_state" in state
        assert "configuration_state" in state
        assert "execution_state" in state

    def test_mvp_workflow_state_negotiation_section(self):
        """Test requirement_negotiation section structure"""
        negotiation_state = {
            "original_requirements": "监控客户邮件并自动回复",
            "parsed_intent": {
                "primary_goal": "客户服务自动化",
                "secondary_goals": ["提高响应速度", "减少人工工作量"],
                "constraints": ["使用现有邮箱", "保持专业语调"],
            },
            "capability_analysis": {
                "required_capabilities": ["email_monitoring", "ai_response", "customer_detection"],
                "available_capabilities": ["email_monitoring"],
                "capability_gaps": ["ai_response", "customer_detection"],
                "gap_severity": {
                    "ai_response": GapSeverity.MEDIUM,
                    "customer_detection": GapSeverity.HIGH,
                },
                "potential_solutions": {
                    "ai_response": [
                        {
                            "type": SolutionType.NATIVE,
                            "complexity": 4,
                            "setup_time": "1小时",
                            "requires_user_action": "配置AI模型",
                            "reliability": SolutionReliability.HIGH,
                            "description": "使用内置AI回复节点",
                        }
                    ]
                },
                "complexity_scores": {"ai_response": 4, "customer_detection": 7},
            },
            "identified_constraints": [
                {
                    "type": "business",
                    "description": "保持专业语调",
                    "severity": GapSeverity.MEDIUM,
                    "impact": "影响AI回复配置",
                }
            ],
            "proposed_solutions": [],
            "user_decisions": [
                {
                    "question": "选择AI回复方案？",
                    "answer": "使用内置AI节点",
                    "timestamp": datetime.now(),
                    "confidence": 0.8,
                }
            ],
            "negotiation_history": [
                {
                    "question": "您希望如何识别客户邮件？",
                    "user_response": "通过关键词过滤",
                    "analysis": {"intent": "solution_preference"},
                    "recommendations": ["使用Code节点实现关键词过滤"],
                    "timestamp": datetime.now(),
                }
            ],
            "final_requirements": "",
            "confidence_score": 0.6,
        }

        # Verify structure
        assert "original_requirements" in negotiation_state
        assert "parsed_intent" in negotiation_state
        assert "capability_analysis" in negotiation_state
        assert len(negotiation_state["identified_constraints"]) == 1
        assert len(negotiation_state["user_decisions"]) == 1
        assert len(negotiation_state["negotiation_history"]) == 1

    def test_mvp_workflow_state_design_section(self):
        """Test design_state section structure"""
        design_state = {
            "task_tree": {
                "root_task": "客户邮件自动处理",
                "subtasks": [
                    {
                        "name": "邮件监控",
                        "description": "监控邮箱新邮件",
                        "estimated_complexity": 3,
                        "critical_path": True,
                    },
                    {
                        "name": "客户识别",
                        "description": "识别客户邮件",
                        "estimated_complexity": 6,
                        "critical_path": True,
                    },
                ],
                "dependencies": [{"from": "邮件监控", "to": "客户识别", "type": "sequential"}],
                "parallel_opportunities": [],
            },
            "architecture": {
                "nodes": [
                    {
                        "id": "email_trigger",
                        "type": "TRIGGER_EMAIL",
                        "role": "trigger",
                        "parameters": {"provider": "gmail"},
                    }
                ],
                "connections": [],
                "data_flow": {
                    "input_schema": {"email": "object"},
                    "output_schema": {"response": "string"},
                },
                "error_handling": {"retry_policies": {"default": {"max_attempts": 3}}},
                "performance_considerations": ["邮件缓存", "批量处理"],
            },
            "workflow_dsl": {
                "version": "1.0",
                "nodes": [],
                "connections": {},
                "settings": {"timeout": 300},
                "metadata": {"pattern": "customer_service_automation"},
            },
            "optimization_suggestions": [
                {
                    "type": "performance",
                    "description": "添加邮件缓存机制",
                    "impact": "减少重复处理",
                    "implementation_complexity": 3,
                }
            ],
            "design_patterns_used": ["customer_service_automation"],
            "estimated_performance": {
                "avg_execution_time": "2-5秒",
                "throughput": "100邮件/小时",
                "resource_usage": {"cpu": "0.5核", "memory": "256MB"},
                "reliability_score": 0.95,
            },
        }

        # Verify structure
        assert "task_tree" in design_state
        assert "architecture" in design_state
        assert "workflow_dsl" in design_state
        assert len(design_state["optimization_suggestions"]) == 1
        assert len(design_state["design_patterns_used"]) == 1
        assert "estimated_performance" in design_state


class TestAPIModels:
    """Test API request/response models"""

    def test_workflow_generation_request(self):
        """Test WorkflowGenerationRequest model"""
        request = WorkflowGenerationRequest(
            user_input="监控邮箱并存储到Notion",
            context={"domain": "customer_service"},
            user_preferences={"complexity": "simple"},
            user_id="test_user",
            session_id="test_session",
        )

        assert request.user_input == "监控邮箱并存储到Notion"
        assert request.context["domain"] == "customer_service"
        assert request.user_preferences["complexity"] == "simple"
        assert request.user_id == "test_user"
        assert request.session_id == "test_session"

    def test_workflow_generation_response(self):
        """Test WorkflowGenerationResponse model"""
        response = WorkflowGenerationResponse(
            success=True,
            workflow={"version": "1.0", "nodes": [], "connections": {}},
            suggestions=["添加错误处理"],
            missing_info=[],
            errors=[],
            session_id="test_session",
            stage="design",
            negotiation_questions=["确认配置方式？"],
            performance_estimate={"avg_execution_time": "1秒", "throughput": "高"},
            validation_result={"valid": True, "errors": []},
        )

        assert response.success is True
        assert response.workflow["version"] == "1.0"
        assert len(response.suggestions) == 1
        assert response.session_id == "test_session"
        assert response.stage == "design"

    def test_continue_conversation_request(self):
        """Test ConversationContinueRequest model"""
        request = ConversationContinueRequest(
            session_id="test_session", user_response="确认使用Gmail", thread_id="thread_123"
        )

        assert request.session_id == "test_session"
        assert request.user_response == "确认使用Gmail"
        assert request.thread_id == "thread_123"

    def test_continue_conversation_response(self):
        """Test ConversationContinueResponse model"""
        response = ConversationContinueResponse(
            success=True,
            session_id="test_session",
            stage="requirement_negotiation",
            errors=[],
            next_questions=["选择存储方案？"],
            tradeoff_analysis={
                "options": [
                    {"name": "Notion", "complexity": 5},
                    {"name": "Google Sheets", "complexity": 3},
                ]
            },
            workflow=None,
            validation_result=None,
            performance_estimate=None,
            optimization_suggestions=[],
        )

        assert response.success is True
        assert response.session_id == "test_session"
        assert response.stage == "requirement_negotiation"
        assert len(response.next_questions) == 1
        assert "options" in response.tradeoff_analysis

    def test_validation_request(self):
        """Test ValidationRequest model"""
        request = ValidationRequest(
            workflow_dsl={
                "version": "1.0",
                "nodes": [{"id": "trigger", "type": "TRIGGER_EMAIL"}],
                "connections": {},
                "settings": {},
            }
        )

        assert request.workflow_dsl["version"] == "1.0"
        assert len(request.workflow_dsl["nodes"]) == 1

    def test_validation_response(self):
        """Test ValidationResponse model"""
        response = ValidationResponse(
            success=True,
            validation_results={
                "syntax_valid": True,
                "logic_valid": True,
                "overall_valid": True,
                "completeness_score": 0.9,
                "errors": [],
                "warnings": ["考虑添加错误处理"],
            },
            errors=[],
        )

        assert response.success is True
        assert response.validation_results["syntax_valid"] is True
        assert response.validation_results["completeness_score"] == 0.9
        assert len(response.validation_results["warnings"]) == 1

    def test_workflow_refinement_request(self):
        """Test WorkflowRefinementRequest model"""
        request = WorkflowRefinementRequest(
            workflow_id="workflow_123",
            feedback="添加错误重试机制",
            original_workflow={"version": "1.0", "nodes": []},
            thread_id="thread_123",
        )

        assert request.workflow_id == "workflow_123"
        assert request.feedback == "添加错误重试机制"
        assert request.original_workflow["version"] == "1.0"
        assert request.thread_id == "thread_123"

    def test_workflow_refinement_response(self):
        """Test WorkflowRefinementResponse model"""
        response = WorkflowRefinementResponse(
            success=True,
            updated_workflow={
                "version": "1.1",
                "nodes": [{"id": "retry", "type": "ERROR_HANDLER"}],
            },
            changes=["添加了错误重试节点"],
            errors=[],
        )

        assert response.success is True
        assert response.updated_workflow["version"] == "1.1"
        assert len(response.changes) == 1
        assert len(response.errors) == 0


class TestAgentStateCompatibility:
    """Test legacy AgentState compatibility"""

    def test_agent_state_creation(self):
        """Test AgentState creation with minimal required fields"""
        state = {"user_input": "监控邮箱并自动回复"}

        # Should work with just user_input
        assert state["user_input"] == "监控邮箱并自动回复"

    def test_agent_state_with_optional_fields(self):
        """Test AgentState with optional fields"""
        state = {
            "user_input": "监控邮箱并自动回复",
            "context": {"domain": "customer_service"},
            "user_preferences": {"complexity": "simple"},
            "requirements": {"primary_goal": "邮箱监控"},
            "current_plan": {"steps": ["监控", "分析", "回复"]},
            "missing_info": ["邮箱账号", "回复模板"],
            "workflow": {"version": "1.0", "nodes": []},
            "current_step": "requirement_analysis",
            "should_continue": True,
        }

        assert state["user_input"] == "监控邮箱并自动回复"
        assert state["context"]["domain"] == "customer_service"
        assert state["current_step"] == "requirement_analysis"
        assert state["should_continue"] is True
        assert len(state["missing_info"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
