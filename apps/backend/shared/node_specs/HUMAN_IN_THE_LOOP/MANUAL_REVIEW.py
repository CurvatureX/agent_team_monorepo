"""
MANUAL_REVIEW Human-in-the-Loop Node Specification

Manual review node for structured human review processes with built-in AI response analysis.
This HIL node automatically analyzes review decisions and routes execution based on AI classification.

Note: HIL nodes have built-in AI response analysis and multiple output ports.
Do NOT add separate AI_AGENT or IF nodes for response handling.
"""

from typing import Any, Dict, List

from ...models.node_enums import HumanLoopSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class ManualReviewSpec(BaseNodeSpec):
    """Manual review specification with built-in AI response analysis."""

    def __init__(self):
        super().__init__(
            type=NodeType.HUMAN_IN_THE_LOOP,
            subtype=HumanLoopSubtype.MANUAL_REVIEW,
            name="Manual_Review",
            description="Human manual review process with AI-powered decision analysis and classification",
            # Configuration parameters
            configurations={
                "review_type": {
                    "type": "string",
                    "default": "quality_assurance",
                    "description": "审查类型",
                    "required": True,
                    "options": [
                        "quality_assurance",
                        "security_review",
                        "compliance_check",
                        "code_review",
                        "content_moderation",
                        "financial_audit",
                        "legal_review",
                        "medical_review",
                        "safety_inspection",
                    ],
                },
                "review_title": {
                    "type": "string",
                    "default": "",
                    "description": "审查标题",
                    "required": True,
                },
                "review_description": {
                    "type": "string",
                    "default": "",
                    "description": "审查描述和说明",
                    "required": True,
                    "multiline": True,
                },
                "reviewers": {
                    "type": "array",
                    "default": [],
                    "description": "指定审查员列表",
                    "required": True,
                },
                "reviewer_roles": {
                    "type": "array",
                    "default": [],
                    "description": "审查员角色列表",
                    "required": False,
                },
                "review_criteria": {
                    "type": "array",
                    "default": [],
                    "description": "审查标准和检查点",
                    "required": True,
                },
                "scoring_system": {
                    "type": "string",
                    "default": "pass_fail",
                    "description": "评分系统类型",
                    "required": False,
                    "options": [
                        "pass_fail",
                        "numeric_scale",
                        "letter_grade",
                        "checklist",
                        "custom",
                    ],
                },
                "score_range": {
                    "type": "object",
                    "default": {"min": 1, "max": 5},
                    "description": "评分范围",
                    "required": False,
                },
                "passing_threshold": {
                    "type": "number",
                    "default": 3.0,
                    "description": "通过门槛",
                    "required": False,
                },
                "review_deadline": {
                    "type": "integer",
                    "default": 86400,
                    "min": 3600,
                    "max": 2592000,
                    "description": "审查截止时间（秒）",
                    "required": False,
                },
                "ai_analysis_model": {
                    "type": "string",
                    "default": "claude-3-5-haiku-20241022",
                    "description": "AI响应分析模型",
                    "required": False,
                    "options": [
                        "gpt-4",
                        "gpt-3.5-turbo",
                        "claude-3-5-haiku-20241022",
                        "claude-sonnet-4-20250514",
                    ],
                },
                "require_evidence": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否要求提供证据",
                    "required": False,
                },
                "allow_delegation": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否允许委派给其他审查员",
                    "required": False,
                },
                "consensus_required": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否需要多位审查员达成共识",
                    "required": False,
                },
                "escalation_rules": {
                    "type": "object",
                    "default": {
                        "enable_escalation": True,
                        "escalation_after_hours": 24,
                        "escalation_recipients": [],
                    },
                    "description": "升级规则配置",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={
                "context": {},
                "review_subject": {},
                "attachments": [],
                "metadata": {},
            },
            default_output_params={
                "review_completed": False,
                "ai_classification": "",
                "review_decision": "",
                "review_score": None,
                "reviewer_comments": "",
                "review_timestamp": "",
                "execution_path": "",
                "timeout_occurred": False,
                "reviewer_info": {},
                "evidence_provided": [],
                "human_feedback": {},
            },
            # Port definitions - HIL nodes have multiple output paths based on AI analysis
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="dict",
                    description="Input data for manual review process",
                    required=True,
                    max_connections=1,
                )
            ],
            output_ports=[
                create_port(
                    port_id="confirmed",
                    name="confirmed",
                    data_type="dict",
                    description="Output when AI classifies review as approved/passed",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="rejected",
                    name="rejected",
                    data_type="dict",
                    description="Output when AI classifies review as rejected/failed",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="unrelated",
                    name="unrelated",
                    data_type="dict",
                    description="Output when AI classifies review as incomplete/requires revision",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="timeout",
                    name="timeout",
                    data_type="dict",
                    description="Output when no review completed within deadline",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=[
                "human-in-the-loop",
                "review",
                "quality-assurance",
                "approval",
                "audit",
                "ai-analysis",
            ],
            # Examples
            examples=[
                {
                    "name": "Code Review Process",
                    "description": "Manual code review with quality checks and AI decision analysis",
                    "configurations": {
                        "review_type": "code_review",
                        "review_title": "Pull Request Review - Feature Implementation",
                        "review_description": "Please review the following pull request for code quality, security, and adherence to coding standards:\\n\\n**Changes:**\\n- Added user authentication feature\\n- Updated database schema\\n- Added unit tests\\n\\n**Review Criteria:**\\n- Code follows style guidelines\\n- Security best practices implemented\\n- Adequate test coverage\\n- Documentation updated",
                        "reviewers": ["senior_dev_001", "tech_lead_002"],
                        "reviewer_roles": ["senior_developer", "technical_lead"],
                        "review_criteria": [
                            "Code style and formatting",
                            "Security vulnerabilities",
                            "Test coverage >= 80%",
                            "Documentation completeness",
                            "Performance considerations",
                        ],
                        "scoring_system": "checklist",
                        "require_evidence": True,
                        "review_deadline": 86400,
                    },
                    "input_example": {
                        "context": {
                            "pull_request_id": "PR-2025-0145",
                            "repository": "customer-portal",
                            "branch": "feature/user-auth",
                            "author": "developer_jane",
                        },
                        "review_subject": {
                            "files_changed": 15,
                            "lines_added": 342,
                            "lines_deleted": 28,
                            "test_files": 8,
                            "commits": 7,
                        },
                        "attachments": [
                            {"type": "code_diff", "url": "https://github.com/repo/pull/145.diff"},
                            {
                                "type": "test_report",
                                "url": "https://ci.example.com/reports/test-145",
                            },
                        ],
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "review_completed": True,
                            "ai_classification": "CONFIRMED",
                            "review_decision": "approved",
                            "review_score": None,
                            "reviewer_comments": "✅ Code review passed. Well-structured implementation with good test coverage. Minor suggestions for optimization added as inline comments. Approved for merge.",
                            "review_timestamp": "2025-01-20T16:45:00Z",
                            "execution_path": "confirmed",
                            "reviewer_info": {
                                "reviewer_id": "senior_dev_001",
                                "name": "Sarah Chen",
                                "role": "senior_developer",
                            },
                            "evidence_provided": [
                                {
                                    "criterion": "Test coverage",
                                    "evidence": "Coverage report shows 85% line coverage",
                                },
                                {
                                    "criterion": "Security check",
                                    "evidence": "No vulnerabilities found in security scan",
                                },
                                {
                                    "criterion": "Code style",
                                    "evidence": "All linting checks passed",
                                },
                            ],
                            "human_feedback": {
                                "decision": "approved",
                                "quality_score": "high",
                                "improvement_suggestions": [
                                    "Consider caching for user lookup queries"
                                ],
                                "estimated_review_time_minutes": 45,
                            },
                        }
                    },
                },
                {
                    "name": "Content Moderation Review",
                    "description": "Manual content review for community guidelines compliance",
                    "configurations": {
                        "review_type": "content_moderation",
                        "review_title": "User Generated Content Review",
                        "review_description": "Review user-submitted content for compliance with community guidelines and terms of service.",
                        "reviewers": ["content_mod_001", "content_mod_002"],
                        "reviewer_roles": ["content_moderator"],
                        "review_criteria": [
                            "No hate speech or harassment",
                            "No explicit or inappropriate content",
                            "No spam or promotional content",
                            "Factually accurate information",
                            "Appropriate for target audience",
                        ],
                        "scoring_system": "pass_fail",
                        "consensus_required": True,
                        "review_deadline": 3600,
                    },
                    "input_example": {
                        "context": {
                            "content_id": "post_789012",
                            "author": "user_community_456",
                            "platform": "discussion_forum",
                            "content_type": "forum_post",
                        },
                        "review_subject": {
                            "title": "New Product Feature Suggestions",
                            "content": "I think the app could benefit from dark mode and better notification settings. Also, the search function needs improvement.",
                            "attachments": [],
                            "reported_by": ["user_reporter_123"],
                            "report_reason": "spam",
                        },
                    },
                    "expected_outputs": {
                        "rejected": {
                            "review_completed": True,
                            "ai_classification": "REJECTED",
                            "review_decision": "content_violation",
                            "reviewer_comments": "Content contains promotional links disguised as suggestions. Violates community guidelines against spam and promotional content.",
                            "review_timestamp": "2025-01-20T12:30:00Z",
                            "execution_path": "rejected",
                            "reviewer_info": {
                                "reviewer_id": "content_mod_001",
                                "name": "Alex Rodriguez",
                                "role": "content_moderator",
                            },
                            "human_feedback": {
                                "decision": "content_violation",
                                "violation_type": "promotional_spam",
                                "action_taken": "content_removed",
                                "user_notified": True,
                                "appeal_allowed": True,
                            },
                        }
                    },
                },
                {
                    "name": "Financial Audit Review",
                    "description": "Financial document audit with timeout escalation",
                    "configurations": {
                        "review_type": "financial_audit",
                        "review_title": "Quarterly Financial Report Audit",
                        "review_description": "Comprehensive audit of Q4 2024 financial reports for accuracy, compliance, and regulatory requirements.",
                        "reviewers": ["auditor_lead_003"],
                        "reviewer_roles": ["senior_auditor", "cpa"],
                        "review_criteria": [
                            "Mathematical accuracy of calculations",
                            "Supporting documentation completeness",
                            "Compliance with accounting standards",
                            "Regulatory filing requirements met",
                            "Internal control effectiveness",
                        ],
                        "scoring_system": "numeric_scale",
                        "score_range": {"min": 1, "max": 10},
                        "passing_threshold": 8.0,
                        "review_deadline": 172800,
                        "escalation_rules": {
                            "enable_escalation": True,
                            "escalation_after_hours": 48,
                            "escalation_recipients": ["audit_director", "cfo"],
                        },
                    },
                    "input_example": {
                        "context": {
                            "report_period": "Q4 2024",
                            "department": "Finance",
                            "total_revenue": 2450000.00,
                            "prepared_by": "finance_analyst_007",
                        },
                        "attachments": [
                            {
                                "type": "financial_report",
                                "filename": "Q4-2024-Financial-Report.xlsx",
                            },
                            {
                                "type": "supporting_docs",
                                "filename": "Q4-2024-Supporting-Documentation.zip",
                            },
                        ],
                    },
                    "expected_outputs": {
                        "timeout": {
                            "review_completed": False,
                            "ai_classification": "",
                            "review_decision": "",
                            "review_score": None,
                            "reviewer_comments": "",
                            "review_timestamp": "",
                            "execution_path": "timeout",
                            "timeout_occurred": True,
                            "human_feedback": {
                                "timeout_reason": "auditor_unavailable_within_deadline",
                                "escalation_triggered": True,
                                "escalated_to": ["audit_director", "cfo"],
                                "impact_assessment": "regulatory_filing_at_risk",
                                "alternative_reviewers_contacted": True,
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
MANUAL_REVIEW_HIL_SPEC = ManualReviewSpec()
