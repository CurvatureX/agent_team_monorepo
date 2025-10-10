"""
OUTLOOK_INTERACTION Human-in-the-Loop Node Specification

Outlook interaction node for email-based human feedback with built-in AI response analysis.
This HIL node automatically analyzes email responses and routes execution based on AI classification.

Note: HIL nodes have built-in AI response analysis and multiple output ports.
Do NOT add separate AI_AGENT or IF nodes for response handling.
"""

from typing import Any, Dict, List

from shared.models.node_enums import HumanLoopSubtype, NodeType, OpenAIModel
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


class OutlookInteractionSpec(BaseNodeSpec):
    """Outlook interaction specification with built-in AI response analysis."""

    def __init__(self):
        super().__init__(
            type=NodeType.HUMAN_IN_THE_LOOP,
            subtype=HumanLoopSubtype.OUTLOOK_INTERACTION,
            name="Outlook_Interaction",
            description="Outlook-based human interaction with AI-powered response analysis and classification",
            # Configuration parameters
            configurations={
                "outlook_credentials": {
                    "type": "object",
                    "default": {},
                    "description": "Outlook API凭据配置",
                    "required": True,
                    "sensitive": True,
                },
                "sender_email": {
                    "type": "string",
                    "default": "",
                    "description": "发送邮件的Outlook地址",
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
                    "default": "Analyze this Outlook email response and classify it as: CONFIRMED (user agrees/approves), REJECTED (user declines/disapproves), or UNRELATED (unclear/off-topic response). Only respond with one word: CONFIRMED, REJECTED, or UNRELATED.",
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
                "use_rich_formatting": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否使用富文本格式",
                    "required": False,
                },
                "auto_reply_enabled": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否启用自动回复",
                    "required": False,
                },
                "priority_level": {
                    "type": "string",
                    "default": "normal",
                    "description": "邮件优先级",
                    "required": False,
                    "options": ["low", "normal", "high"],
                },
                "delivery_receipt": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否要求送达回执",
                    "required": False,
                },
                "read_receipt": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否要求阅读回执",
                    "required": False,
                },
                "folder_monitoring": {
                    "type": "object",
                    "default": {
                        "monitor_inbox": True,
                        "monitor_specific_folder": False,
                        "folder_name": "Workflow Responses",
                    },
                    "description": "文件夹监控配置",
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
            tags=["human-in-the-loop", "outlook", "email", "approval", "ai-analysis", "office365"],
            # Examples
            examples=[
                {
                    "name": "HR Policy Approval",
                    "description": "Request policy approval from HR manager via Outlook with AI response analysis",
                    "configurations": {
                        "outlook_credentials": {
                            "tenant_id": "your-tenant-id",
                            "client_id": "your-client-id",
                            "client_secret": "your-client-secret",
                        },
                        "sender_email": "hr-policies@company.com",
                        "recipient_emails": ["hr-manager@company.com"],
                        "email_subject": "Policy Approval Required - {{policy_name}}",
                        "email_template": "Dear HR Team,\\n\\nWe need your approval for the updated policy:\\n\\n**Policy Name:** {{policy_name}}\\n**Effective Date:** {{effective_date}}\\n**Changes Summary:** {{changes_summary}}\\n\\nPlease review the attached policy document and reply with 'APPROVE' or 'REJECT' along with any comments.\\n\\nBest regards,\\nHR Policy System",
                        "response_timeout": 172800,
                        "priority_level": "high",
                        "include_attachments": True,
                        "delivery_receipt": True,
                    },
                    "input_example": {
                        "content": {
                            "type": "policy_approval",
                            "policy_name": "Remote Work Guidelines 2025",
                            "effective_date": "February 1, 2025",
                            "changes_summary": "Added flexibility for hybrid work schedules and updated equipment allowances",
                            "requester": "policy.admin@company.com",
                            "department": "human_resources",
                            "urgency": "high",
                        },
                        "user_mention": "hr-manager@company.com",
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "content": {
                                "type": "policy_approval",
                                "policy_name": "Remote Work Guidelines 2025",
                                "effective_date": "February 1, 2025",
                                "changes_summary": "Added flexibility for hybrid work schedules and updated equipment allowances",
                                "requester": "policy.admin@company.com",
                                "department": "human_resources",
                                "urgency": "high",
                            },
                            "ai_classification": "confirmed",
                            "user_response": "APPROVE - The updated remote work guidelines look comprehensive and address current needs. I approve implementation starting February 1st. Please ensure all employees receive training on the new guidelines.",
                        }
                    },
                },
                {
                    "name": "Contract Review Request",
                    "description": "Legal contract review via Outlook with timeout handling",
                    "configurations": {
                        "sender_email": "legal-contracts@company.com",
                        "recipient_emails": [
                            "legal-counsel@company.com",
                            "contracts-team@company.com",
                        ],
                        "email_subject": "Contract Review - {{contract_type}} with {{vendor_name}}",
                        "email_template": "Legal Team,\\n\\nPlease review the attached contract for legal compliance and risk assessment:\\n\\n**Contract Type:** {{contract_type}}\\n**Vendor:** {{vendor_name}}\\n**Contract Value:** ${{contract_value}}\\n**Term:** {{contract_term}}\\n**Deadline:** {{review_deadline}}\\n\\nReply with your approval status and any legal concerns.\\n\\nThanks,\\nContract Management System",
                        "response_timeout": 259200,
                        "use_rich_formatting": True,
                        "read_receipt": True,
                        "folder_monitoring": {
                            "monitor_inbox": True,
                            "monitor_specific_folder": True,
                            "folder_name": "Contract Reviews",
                        },
                    },
                    "input_example": {
                        "content": {
                            "type": "contract_review",
                            "contract_type": "Software Licensing Agreement",
                            "vendor_name": "TechSoft Solutions Inc.",
                            "contract_value": "75,000",
                            "contract_term": "3 years",
                            "review_deadline": "January 28, 2025",
                        },
                        "user_mention": "legal-counsel@company.com",
                    },
                    "expected_outputs": {
                        "rejected": {
                            "content": {
                                "type": "contract_review",
                                "contract_type": "Software Licensing Agreement",
                                "vendor_name": "TechSoft Solutions Inc.",
                                "contract_value": "75,000",
                                "contract_term": "3 years",
                                "review_deadline": "January 28, 2025",
                            },
                            "ai_classification": "rejected",
                            "user_response": "REJECT - After review, the contract contains several problematic clauses in sections 8.3 and 12.1 regarding liability and data ownership. Vendor needs to revise these terms before we can approve. See attached marked-up version with specific concerns.",
                        }
                    },
                },
                {
                    "name": "IT Security Approval",
                    "description": "IT security review for system changes with escalation timeout",
                    "configurations": {
                        "sender_email": "it-security@company.com",
                        "recipient_emails": ["security-team@company.com"],
                        "email_subject": "Security Approval Required - {{change_type}}",
                        "email_template": "IT Security Team,\\n\\n🔒 **Security Review Required**\\n\\n**Change Type:** {{change_type}}\\n**System:** {{system_name}}\\n**Risk Level:** {{risk_level}}\\n**Requested by:** {{requester}}\\n**Implementation Date:** {{implementation_date}}\\n\\n**Change Details:**\\n{{change_description}}\\n\\n**Security Impact Assessment:**\\n{{security_impact}}\\n\\nPlease review and provide security approval or concerns.\\n\\nIT Change Management",
                        "response_timeout": 43200,
                        "priority_level": "high",
                        "delivery_receipt": True,
                        "read_receipt": True,
                    },
                    "input_example": {
                        "content": {
                            "type": "security_approval",
                            "change_type": "Firewall Rule Update",
                            "system_name": "Production Web Server",
                            "risk_level": "Medium",
                            "requester": "DevOps Team",
                            "implementation_date": "January 25, 2025",
                            "change_description": "Opening port 8080 for new API endpoint",
                            "security_impact": "Limited exposure to external traffic on specific port",
                        },
                        "user_mention": "security-team@company.com",
                    },
                    "expected_outputs": {
                        "timeout": {
                            "content": {
                                "type": "security_approval",
                                "change_type": "Firewall Rule Update",
                                "system_name": "Production Web Server",
                                "risk_level": "Medium",
                                "requester": "DevOps Team",
                                "implementation_date": "January 25, 2025",
                                "change_description": "Opening port 8080 for new API endpoint",
                                "security_impact": "Limited exposure to external traffic on specific port",
                            },
                            "ai_classification": "timeout",
                            "user_response": "",
                        }
                    },
                },
            ],
        )


# Export the specification instance
OUTLOOK_INTERACTION_HIL_SPEC = OutlookInteractionSpec()
