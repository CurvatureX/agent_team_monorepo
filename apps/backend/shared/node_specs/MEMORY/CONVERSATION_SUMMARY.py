"""
CONVERSATION_SUMMARY Memory Node Specification

Conversation summary memory for maintaining complete conversation memory with
buffer and progressive summarization for optimal LLM context management.

Note: MEMORY nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import MemorySubtype, NodeType, OpenAIModel
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class ConversationSummaryMemorySpec(BaseNodeSpec):
    """Conversation summary memory specification for AI_AGENT attached memory."""

    def __init__(self):
        super().__init__(
            type=NodeType.MEMORY,
            subtype=MemorySubtype.CONVERSATION_SUMMARY,
            name="Conversation_Summary_Memory",
            description="Complete conversation memory with buffer and progressive summarization for optimal LLM context",
            # Configuration parameters
            configurations={
                "summary_trigger": {
                    "type": "string",
                    "default": "message_count",
                    "description": "When to trigger summary generation",
                    "required": False,
                    "options": ["message_count", "token_count", "time_interval"],
                },
                "trigger_threshold": {
                    "type": "integer",
                    "default": 10,
                    "description": "Threshold for summary trigger (messages/tokens/minutes)",
                    "required": False,
                },
                "summarization_model": {
                    "type": "string",
                    "default": OpenAIModel.GPT_5_NANO.value,
                    "description": "Model to use for summarization",
                    "required": False,
                },
                "summary_style": {
                    "type": "string",
                    "default": "progressive",
                    "description": "Style of summary generation",
                    "required": False,
                    "options": ["progressive", "hierarchical", "key_points"],
                },
                "preserve_entities": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to preserve important entities in summaries",
                    "required": False,
                },
                "buffer_window_size": {
                    "type": "integer",
                    "default": 10,
                    "description": "Number of recent messages to keep in buffer",
                    "required": False,
                },
                "summary_context_weight": {
                    "type": "float",
                    "default": 0.3,
                    "description": "Weight given to summary vs buffer context (0.0-1.0)",
                    "required": False,
                },
                "max_total_tokens": {
                    "type": "integer",
                    "default": 4000,
                    "description": "Maximum total tokens for combined context",
                    "required": False,
                },
                "storage_backend": {
                    "type": "string",
                    "default": "redis",
                    "description": "Storage backend for conversation data",
                    "required": False,
                    "options": ["redis", "postgresql", "memory"],
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"messages": [], "session_metadata": {}, "context": {}},
            default_output_params={
                "summary": "",
                "key_points": [],
                "entities": [],
                "recent_messages": [],
                "combined_context": "",
                "token_count": 0,
                "summary_metadata": {},
            },
            # Port definitions - Memory nodes don't use traditional ports
            # They are attached to AI agents via attached_nodes configuration
            input_ports=[],
            output_ports=[],
            # Metadata
            tags=["memory", "conversation", "summary", "context", "llm-context"],
            # Examples
            examples=[
                {
                    "name": "Progressive Session Summary",
                    "description": "Maintain progressive summaries for long conversations with key point extraction",
                    "configurations": {
                        "summary_trigger": "message_count",
                        "trigger_threshold": 15,
                        "summary_style": "progressive",
                        "preserve_entities": True,
                        "buffer_window_size": 8,
                        "summary_context_weight": 0.4,
                        "max_total_tokens": 3500,
                    },
                    "input_example": {
                        "messages": [
                            {
                                "role": "user",
                                "content": "I need help planning a marketing campaign for our new product",
                                "timestamp": "2025-01-20T10:00:00Z",
                            },
                            {
                                "role": "assistant",
                                "content": "I'd be happy to help you plan a marketing campaign. Let me start by understanding your product and target audience.",
                                "timestamp": "2025-01-20T10:01:00Z",
                            },
                            {
                                "role": "user",
                                "content": "It's a new fitness tracker called FitPro X1 targeting health-conscious millennials",
                                "timestamp": "2025-01-20T10:02:00Z",
                            },
                        ],
                        "session_metadata": {
                            "session_id": "planning_session_001",
                            "user_id": "user_456",
                            "topic": "marketing_campaign",
                        },
                    },
                    "expected_outputs": {
                        "summary": "User is planning a marketing campaign for FitPro X1, a new fitness tracker targeting health-conscious millennials. Discussion covers product positioning and target audience analysis.",
                        "key_points": [
                            "Product: FitPro X1 fitness tracker",
                            "Target audience: Health-conscious millennials",
                            "Goal: Create marketing campaign",
                            "Focus: Understanding product and audience",
                        ],
                        "entities": [
                            {"name": "FitPro X1", "type": "product", "importance": 0.9},
                            {"name": "millennials", "type": "demographic", "importance": 0.8},
                            {"name": "marketing campaign", "type": "project", "importance": 0.9},
                        ],
                        "recent_messages": [
                            {
                                "role": "user",
                                "content": "It's a new fitness tracker called FitPro X1 targeting health-conscious millennials",
                                "timestamp": "2025-01-20T10:02:00Z",
                            }
                        ],
                        "combined_context": "## Conversation Summary\nUser is planning a marketing campaign for FitPro X1, a new fitness tracker targeting health-conscious millennials.\n\n## Key Points\n- Product: FitPro X1 fitness tracker\n- Target audience: Health-conscious millennials\n\n## Recent Context\nUser: It's a new fitness tracker called FitPro X1 targeting health-conscious millennials",
                        "token_count": 156,
                        "summary_metadata": {
                            "messages_summarized": 3,
                            "summary_generation_count": 1,
                            "entities_preserved": 3,
                            "last_summary_timestamp": "2025-01-20T10:02:30Z",
                        },
                    },
                },
                {
                    "name": "Technical Discussion Summary",
                    "description": "Hierarchical summary for technical discussions with entity preservation",
                    "configurations": {
                        "summary_trigger": "token_count",
                        "trigger_threshold": 2000,
                        "summary_style": "hierarchical",
                        "preserve_entities": True,
                        "buffer_window_size": 5,
                        "summary_context_weight": 0.6,
                        "summarization_model": OpenAIModel.GPT_5_MINI.value,
                    },
                    "input_example": {
                        "messages": [
                            {
                                "role": "user",
                                "content": "Can you explain how microservices architecture works with Docker containers?",
                                "timestamp": "2025-01-20T14:00:00Z",
                            },
                            {
                                "role": "assistant",
                                "content": "Microservices architecture with Docker containers allows you to decompose applications into small, independent services...",
                                "timestamp": "2025-01-20T14:01:00Z",
                            },
                        ],
                        "session_metadata": {
                            "session_id": "tech_discussion_002",
                            "topic": "microservices_architecture",
                            "domain": "software_engineering",
                        },
                    },
                    "expected_outputs": {
                        "summary": "## Architecture Discussion\n**Topic**: Microservices with Docker\n**Key Concepts**: Service decomposition, containerization, independence\n**Technologies**: Docker, microservices patterns",
                        "key_points": [
                            "Microservices decompose applications into independent services",
                            "Docker containers provide isolation and portability",
                            "Each service can be deployed and scaled independently",
                        ],
                        "entities": [
                            {"name": "Docker", "type": "technology", "importance": 0.9},
                            {
                                "name": "microservices",
                                "type": "architecture_pattern",
                                "importance": 0.9,
                            },
                            {"name": "containers", "type": "technology_concept", "importance": 0.8},
                        ],
                        "summary_metadata": {
                            "summary_style": "hierarchical",
                            "technical_entities_count": 3,
                            "domain": "software_engineering",
                        },
                    },
                },
                {
                    "name": "Customer Support Summary",
                    "description": "Key points summary for customer support conversations with issue tracking",
                    "configurations": {
                        "summary_trigger": "message_count",
                        "trigger_threshold": 12,
                        "summary_style": "key_points",
                        "preserve_entities": True,
                        "buffer_window_size": 6,
                        "max_total_tokens": 2500,
                        "storage_backend": "postgresql",
                    },
                    "input_example": {
                        "messages": [
                            {
                                "role": "user",
                                "content": "I'm having trouble with my account login. It keeps saying invalid credentials.",
                                "timestamp": "2025-01-20T16:00:00Z",
                            },
                            {
                                "role": "assistant",
                                "content": "I can help you with login issues. Let me check your account status and recent activity.",
                                "timestamp": "2025-01-20T16:01:00Z",
                            },
                            {
                                "role": "user",
                                "content": "My email is john.doe@email.com and I last logged in successfully on Monday.",
                                "timestamp": "2025-01-20T16:02:00Z",
                            },
                        ],
                        "session_metadata": {
                            "session_id": "support_ticket_789",
                            "ticket_type": "login_issue",
                            "priority": "medium",
                            "customer_tier": "premium",
                        },
                    },
                    "expected_outputs": {
                        "summary": "Customer john.doe@email.com experiencing login issues with invalid credentials error. Last successful login was Monday. Account status check initiated.",
                        "key_points": [
                            "Issue: Login problems with invalid credentials error",
                            "Customer: john.doe@email.com",
                            "Last successful login: Monday",
                            "Status: Account investigation in progress",
                        ],
                        "entities": [
                            {
                                "name": "john.doe@email.com",
                                "type": "customer_email",
                                "importance": 0.9,
                            },
                            {"name": "login_issue", "type": "problem_type", "importance": 0.8},
                            {
                                "name": "invalid_credentials",
                                "type": "error_type",
                                "importance": 0.7,
                            },
                        ],
                        "summary_metadata": {
                            "ticket_id": "support_ticket_789",
                            "issue_category": "authentication",
                            "customer_tier": "premium",
                            "resolution_status": "investigating",
                        },
                    },
                },
            ],
        )


# Export the specification instance
CONVERSATION_SUMMARY_MEMORY_SPEC = ConversationSummaryMemorySpec()
