"""
CONVERSATION_BUFFER Memory Node Specification

Conversation buffer memory for storing and retrieving chat history and context.
This memory node is attached to AI_AGENT nodes and provides conversation
continuity and context management.

Note: MEMORY nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import MemorySubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class ConversationBufferMemorySpec(BaseNodeSpec):
    """Conversation buffer memory specification for AI_AGENT attached memory."""

    def __init__(self):
        super().__init__(
            type=NodeType.MEMORY,
            subtype=MemorySubtype.CONVERSATION_BUFFER,
            name="Conversation_Buffer_Memory",
            description="Conversation buffer memory for chat history and context management",
            # Configuration parameters
            configurations={
                "max_messages": {
                    "type": "integer",
                    "default": 50,
                    "min": 1,
                    "max": 1000,
                    "description": "最大消息存储数量",
                    "required": False,
                },
                "max_tokens": {
                    "type": "integer",
                    "default": 4000,
                    "min": 100,
                    "max": 32000,
                    "description": "最大token存储数量",
                    "required": False,
                },
                "buffer_strategy": {
                    "type": "string",
                    "default": "sliding_window",
                    "description": "缓冲区策略",
                    "required": True,
                    "options": ["sliding_window", "summarize_old", "fixed_size", "token_limit"],
                },
                "message_roles": {
                    "type": "array",
                    "default": ["user", "assistant", "system"],
                    "description": "允许的消息角色类型",
                    "required": False,
                },
                "include_metadata": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否包含消息元数据",
                    "required": False,
                },
                "auto_summarize": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否自动总结旧消息",
                    "required": False,
                },
                "summary_threshold": {
                    "type": "integer",
                    "default": 80,
                    "min": 10,
                    "max": 100,
                    "description": "触发总结的消息数量百分比",
                    "required": False,
                },
                "persist_to_disk": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否持久化到磁盘",
                    "required": False,
                },
                "conversation_id": {
                    "type": "string",
                    "default": "",
                    "description": "会话标识符",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters for memory operations
            default_input_params={
                "message": "",
                "role": "user",
                "metadata": {},
                "operation": "add",  # add, get, clear, summarize
            },
            default_output_params={
                "messages": [],
                "total_messages": 0,
                "total_tokens": 0,
                "buffer_full": False,
                "summary": "",
                "success": False,
            },
            # MEMORY nodes have no ports - they are attached to AI_AGENT nodes
            input_ports=[],
            output_ports=[],
            # Memory nodes don't have attached_nodes (only AI_AGENT has this)
            attached_nodes=None,
            # Metadata
            tags=["memory", "conversation", "chat", "buffer", "attached"],
            # Examples
            examples=[
                {
                    "name": "Customer Support Chat Memory",
                    "description": "Store customer support conversation history with context",
                    "configurations": {
                        "max_messages": 30,
                        "max_tokens": 3000,
                        "buffer_strategy": "sliding_window",
                        "message_roles": ["user", "assistant", "system"],
                        "include_metadata": True,
                        "conversation_id": "support_{{session_id}}",
                    },
                    "usage_example": {
                        "attached_to": "customer_support_ai",
                        "memory_operations": [
                            {
                                "operation": "add",
                                "message": "Hi, I'm having trouble with my account login",
                                "role": "user",
                                "metadata": {
                                    "timestamp": "2025-01-20T10:30:00Z",
                                    "user_id": "user_12345",
                                    "channel": "chat",
                                },
                            },
                            {
                                "operation": "add",
                                "message": "I'd be happy to help you with your account login. Can you please provide me with your email address?",
                                "role": "assistant",
                                "metadata": {
                                    "timestamp": "2025-01-20T10:30:15Z",
                                    "agent_id": "support_ai",
                                },
                            },
                        ],
                        "expected_result": {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": "Hi, I'm having trouble with my account login",
                                    "metadata": {
                                        "timestamp": "2025-01-20T10:30:00Z",
                                        "user_id": "user_12345",
                                        "channel": "chat",
                                    },
                                },
                                {
                                    "role": "assistant",
                                    "content": "I'd be happy to help you with your account login. Can you please provide me with your email address?",
                                    "metadata": {
                                        "timestamp": "2025-01-20T10:30:15Z",
                                        "agent_id": "support_ai",
                                    },
                                },
                            ],
                            "total_messages": 2,
                            "total_tokens": 45,
                            "buffer_full": False,
                            "success": True,
                        },
                    },
                },
                {
                    "name": "Long Conversation with Auto-Summary",
                    "description": "Manage long conversations with automatic summarization",
                    "configurations": {
                        "max_messages": 20,
                        "max_tokens": 2000,
                        "buffer_strategy": "summarize_old",
                        "auto_summarize": True,
                        "summary_threshold": 75,
                        "persist_to_disk": True,
                    },
                    "usage_example": {
                        "attached_to": "consultation_ai",
                        "scenario": "conversation_reaches_threshold",
                        "expected_result": {
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "Summary of previous conversation: User discussed project requirements, budget constraints, and timeline expectations. Key decisions made: React frontend, PostgreSQL database, 3-month timeline.",
                                }
                            ],
                            "total_messages": 15,
                            "total_tokens": 1800,
                            "buffer_full": False,
                            "summary": "User discussed project requirements, budget constraints, and timeline expectations. Key decisions made: React frontend, PostgreSQL database, 3-month timeline.",
                            "success": True,
                        },
                    },
                },
                {
                    "name": "Team Chat Memory",
                    "description": "Store team collaboration messages with role-based filtering",
                    "configurations": {
                        "max_messages": 100,
                        "buffer_strategy": "sliding_window",
                        "message_roles": ["user", "assistant", "team_member", "moderator"],
                        "include_metadata": True,
                        "conversation_id": "team_{{team_id}}",
                    },
                    "usage_example": {
                        "attached_to": "team_collaboration_ai",
                        "memory_operations": [
                            {
                                "operation": "get",
                                "filters": {
                                    "role": ["team_member", "moderator"],
                                    "recent_count": 10,
                                },
                            }
                        ],
                        "expected_result": {
                            "messages": [
                                {
                                    "role": "team_member",
                                    "content": "@channel The new feature branch is ready for review",
                                    "metadata": {
                                        "timestamp": "2025-01-20T14:15:00Z",
                                        "user_id": "dev_alice",
                                        "channel": "development",
                                    },
                                },
                                {
                                    "role": "moderator",
                                    "content": "Thanks Alice! I'll assign reviewers shortly.",
                                    "metadata": {
                                        "timestamp": "2025-01-20T14:16:00Z",
                                        "user_id": "lead_bob",
                                        "channel": "development",
                                    },
                                },
                            ],
                            "total_messages": 10,
                            "success": True,
                        },
                    },
                },
            ],
        )


# Export the specification instance
CONVERSATION_BUFFER_MEMORY_SPEC = ConversationBufferMemorySpec()
