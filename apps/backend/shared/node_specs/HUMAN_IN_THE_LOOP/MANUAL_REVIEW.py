"""
MANUAL_REVIEW Human-in-the-Loop Node Specification

Manual review node for structured human review processes with built-in AI response analysis.
This HIL node automatically analyzes review decisions and routes execution based on AI classification.

Note: HIL nodes have built-in AI response analysis and multiple output ports.
Do NOT add separate AI_AGENT or IF nodes for response handling.
"""

from typing import Any, Dict, List

from shared.models.node_enums import HumanLoopSubtype, NodeType, OpenAIModel
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


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
                    "default": OpenAIModel.GPT_5_MINI.value,
                    "description": "AI响应分析模型",
                    "required": False,
                    "options": [OpenAIModel.GPT_5_MINI.value, OpenAIModel.GPT_5_NANO.value],
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
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "content": {
                    "type": "object",
                    "default": "",
                    "description": "The content that need to be reviewed",
                    "required": False,
                    "multiline": True,
                },
                "user_mention": {
                    "type": "string",
                    "default": "",
                    "description": "User to mention (e.g., @john)",
                    "required": False,
                },
            },
            output_params={
                "content": {
                    "type": "object",
                    "default": {},
                    "description": "Pass-through content from input_params (unchanged)",
                    "required": False,
                },
                "ai_classification": {
                    "type": "string",
                    "default": "",
                    "description": "AI classification of the response",
                    "required": False,
                    "options": ["confirmed", "rejected", "unrelated", "timeout"],
                },
                "user_response": {
                    "type": "string",
                    "default": "",
                    "description": "The actual text response from the human",
                    "required": False,
                },
            },
            # Port definitions - HIL nodes have multiple output paths based on AI analysis            # Metadata
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
                        "content": {
                            "type": "code_review",
                            "pull_request_id": "PR-2025-0145",
                            "repository": "customer-portal",
                            "branch": "feature/user-auth",
                            "author": "developer_jane",
                            "files_changed": 15,
                            "lines_added": 342,
                            "lines_deleted": 28,
                            "test_files": 8,
                            "commits": 7,
                        },
                        "user_mention": "@senior_dev_001 @tech_lead_002",
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "content": {
                                "type": "code_review",
                                "pull_request_id": "PR-2025-0145",
                                "repository": "customer-portal",
                                "branch": "feature/user-auth",
                                "author": "developer_jane",
                                "files_changed": 15,
                                "lines_added": 342,
                                "lines_deleted": 28,
                                "test_files": 8,
                                "commits": 7,
                            },
                            "ai_classification": "confirmed",
                            "user_response": "✅ Code review passed. Well-structured implementation with good test coverage. Minor suggestions for optimization added as inline comments. Approved for merge.",
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
                        "content": {
                            "type": "content_moderation",
                            "content_id": "post_789012",
                            "author": "user_community_456",
                            "platform": "discussion_forum",
                            "content_type": "forum_post",
                            "title": "New Product Feature Suggestions",
                            "content_text": "I think the app could benefit from dark mode and better notification settings. Also, the search function needs improvement.",
                            "reported_by": "user_reporter_123",
                            "report_reason": "spam",
                        },
                        "user_mention": "@content_mod_001 @content_mod_002",
                    },
                    "expected_outputs": {
                        "rejected": {
                            "content": {
                                "type": "content_moderation",
                                "content_id": "post_789012",
                                "author": "user_community_456",
                                "platform": "discussion_forum",
                                "content_type": "forum_post",
                                "title": "New Product Feature Suggestions",
                                "content_text": "I think the app could benefit from dark mode and better notification settings. Also, the search function needs improvement.",
                                "reported_by": "user_reporter_123",
                                "report_reason": "spam",
                            },
                            "ai_classification": "rejected",
                            "user_response": "Content contains promotional links disguised as suggestions. Violates community guidelines against spam and promotional content.",
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
                        "content": {
                            "type": "financial_audit",
                            "report_period": "Q4 2024",
                            "department": "Finance",
                            "total_revenue": 2450000.00,
                            "prepared_by": "finance_analyst_007",
                        },
                        "user_mention": "@auditor_lead_003",
                    },
                    "expected_outputs": {
                        "timeout": {
                            "content": {
                                "type": "financial_audit",
                                "report_period": "Q4 2024",
                                "department": "Finance",
                                "total_revenue": 2450000.00,
                                "prepared_by": "finance_analyst_007",
                            },
                            "ai_classification": "timeout",
                            "user_response": "",
                        }
                    },
                },
            ],
        )


# Export the specification instance
MANUAL_REVIEW_HIL_SPEC = ManualReviewSpec()
