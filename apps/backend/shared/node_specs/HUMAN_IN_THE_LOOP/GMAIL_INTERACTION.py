"""
GMAIL_INTERACTION Human-in-the-Loop Node Specification

Gmail interaction node for email-based human feedback with built-in AI response analysis.
This HIL node automatically analyzes email responses and routes execution based on AI classification.

Note: HIL nodes have built-in AI response analysis and multiple output ports.
Do NOT add separate AI_AGENT or IF nodes for response handling.
"""

from typing import Any, Dict, List

from shared.models.node_enums import HumanLoopSubtype, NodeType, OpenAIModel
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


class GmailInteractionSpec(BaseNodeSpec):
    """Gmail interaction specification with built-in AI response analysis."""

    def __init__(self):
        super().__init__(
            type=NodeType.HUMAN_IN_THE_LOOP,
            subtype=HumanLoopSubtype.GMAIL_INTERACTION,
            name="Gmail_Interaction",
            description="Gmail-based human interaction with AI-powered response analysis and classification",
            # Configuration parameters
            configurations={
                "gmail_credentials": {
                    "type": "object",
                    "default": {},
                    "description": "Gmail API凭据配置",
                    "required": True,
                    "sensitive": True,
                },
                "sender_email": {
                    "type": "string",
                    "default": "",
                    "description": "发送邮件的Gmail地址",
                    "required": True,
                },
                "recipient_emails": {
                    "type": "array",
                    "default": [],
                    "description": "接收者邮件地址列表",
                    "required": True,
                },
                "email_subject": {
                    "type": "string",
                    "default": "",
                    "description": "邮件主题",
                    "required": True,
                },
                "email_template": {
                    "type": "string",
                    "default": "",
                    "description": "邮件模板内容",
                    "required": True,
                    "multiline": True,
                },
                "response_timeout": {
                    "type": "integer",
                    "default": 86400,
                    "min": 300,
                    "max": 604800,
                    "description": "响应超时时间（秒）",
                    "required": False,
                },
                "ai_analysis_model": {
                    "type": "string",
                    "default": OpenAIModel.GPT_5_MINI.value,
                    "description": "AI响应分析模型",
                    "required": False,
                    "options": [OpenAIModel.GPT_5_MINI.value, OpenAIModel.GPT_5_NANO.value],
                },
                "response_analysis_prompt": {
                    "type": "string",
                    "default": "Analyze this email response and classify it as: CONFIRMED (user agrees/approves), REJECTED (user declines/disapproves), or UNRELATED (unclear/off-topic response). Only respond with one word: CONFIRMED, REJECTED, or UNRELATED.",
                    "description": "AI响应分析提示词",
                    "required": False,
                    "multiline": True,
                },
                "include_attachments": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否包含附件",
                    "required": False,
                },
                "auto_reply_enabled": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否启用自动回复",
                    "required": False,
                },
                "confirmation_messages": {
                    "type": "object",
                    "default": {
                        "confirmed": "Thank you for your confirmation. Your approval has been recorded.",
                        "rejected": "Thank you for your response. Your decision has been noted.",
                        "unrelated": "Thank you for your response. Please provide a clear approval or rejection.",
                        "timeout": "No response received within the specified timeframe. The request has expired.",
                    },
                    "description": "不同分类的确认消息",
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
            tags=["human-in-the-loop", "gmail", "email", "approval", "ai-analysis"],
            # Examples
            examples=[
                {
                    "name": "Budget Approval via Gmail",
                    "description": "Request budget approval from manager via email with AI response analysis",
                    "configurations": {
                        "gmail_credentials": {
                            "type": "service_account",
                            "client_email": "workflow-bot@company.iam.gserviceaccount.com",
                            "private_key": "-----BEGIN PRIVATE KEY-----\\n...",
                        },
                        "sender_email": "workflow-bot@company.com",
                        "recipient_emails": ["manager@company.com"],
                        "email_subject": "Budget Approval Request - Q1 Marketing Campaign",
                        "email_template": "Hi {{manager_name}},\\n\\nI need your approval for the Q1 marketing campaign budget of ${{amount}}.\\n\\nCampaign Details:\\n- Duration: {{duration}}\\n- Target Audience: {{audience}}\\n- Expected ROI: {{roi}}\\n\\nPlease reply with 'APPROVE' or 'REJECT' along with any comments.\\n\\nBest regards,\\nWorkflow System",
                        "response_timeout": 86400,
                        "ai_analysis_model": OpenAIModel.GPT_5_MINI.value,
                    },
                    "input_example": {
                        "content": {
                            "type": "budget_approval",
                            "manager_name": "Sarah Johnson",
                            "amount": "$25,000",
                            "duration": "3 months",
                            "audience": "Tech professionals aged 25-45",
                            "roi": "150%",
                            "requester": "john.doe@company.com",
                            "department": "marketing",
                            "urgency": "high",
                        },
                        "user_mention": "manager@company.com",
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "content": {
                                "type": "budget_approval",
                                "manager_name": "Sarah Johnson",
                                "amount": "$25,000",
                                "duration": "3 months",
                                "audience": "Tech professionals aged 25-45",
                                "roi": "150%",
                                "requester": "john.doe@company.com",
                                "department": "marketing",
                                "urgency": "high",
                            },
                            "ai_classification": "confirmed",
                            "user_response": "APPROVE - This looks like a solid campaign plan. Please proceed with the budget allocation. Let me know if you need any additional resources.",
                        }
                    },
                },
                {
                    "name": "Document Review Request",
                    "description": "Request document review from legal team via Gmail",
                    "configurations": {
                        "sender_email": "legal-requests@company.com",
                        "recipient_emails": ["legal-team@company.com", "compliance@company.com"],
                        "email_subject": "Legal Review Required - {{document_type}}",
                        "email_template": "Legal Team,\\n\\nPlease review the attached {{document_type}} for compliance and legal issues.\\n\\nDocument: {{document_name}}\\nDeadline: {{review_deadline}}\\nPriority: {{priority_level}}\\n\\nReply with your review status and any concerns.\\n\\nThanks,\\nContract System",
                        "response_timeout": 172800,
                        "include_attachments": True,
                        "auto_reply_enabled": True,
                    },
                    "input_example": {
                        "content": {
                            "type": "legal_review",
                            "document_type": "Software License Agreement",
                            "document_name": "SaaS-License-v2.1.pdf",
                            "review_deadline": "January 25, 2025",
                            "priority_level": "High",
                        },
                        "user_mention": "legal-team@company.com",
                    },
                    "expected_outputs": {
                        "rejected": {
                            "content": {
                                "type": "legal_review",
                                "document_type": "Software License Agreement",
                                "document_name": "SaaS-License-v2.1.pdf",
                                "review_deadline": "January 25, 2025",
                                "priority_level": "High",
                            },
                            "ai_classification": "rejected",
                            "user_response": "After review, we found several concerning clauses in sections 4.2 and 7.1 that need revision before approval. Please see attached comments.",
                        }
                    },
                },
                {
                    "name": "Expense Report Approval",
                    "description": "Expense report approval workflow with timeout handling",
                    "configurations": {
                        "sender_email": "expenses@company.com",
                        "recipient_emails": ["finance-manager@company.com"],
                        "email_subject": "Expense Report Approval - {{employee_name}}",
                        "email_template": "Hi Finance Team,\\n\\n{{employee_name}} has submitted an expense report for approval:\\n\\nTotal Amount: ${{total_amount}}\\nSubmission Date: {{submission_date}}\\nExpense Categories: {{categories}}\\n\\nPlease review the attached receipts and approve or reject this expense report.\\n\\nExpense System",
                        "response_timeout": 259200,
                        "confirmation_messages": {
                            "timeout": "Expense report approval request expired. Escalating to senior management."
                        },
                    },
                    "input_example": {
                        "content": {
                            "type": "expense_approval",
                            "employee_name": "Alice Chen",
                            "total_amount": "842.50",
                            "submission_date": "January 18, 2025",
                            "categories": "Travel, Meals, Office Supplies",
                        },
                        "user_mention": "finance-manager@company.com",
                    },
                    "expected_outputs": {
                        "timeout": {
                            "content": {
                                "type": "expense_approval",
                                "employee_name": "Alice Chen",
                                "total_amount": "842.50",
                                "submission_date": "January 18, 2025",
                                "categories": "Travel, Meals, Office Supplies",
                            },
                            "ai_classification": "timeout",
                            "user_response": "",
                        }
                    },
                },
            ],
        )


# Export the specification instance
GMAIL_INTERACTION_HIL_SPEC = GmailInteractionSpec()
