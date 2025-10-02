"""
Conversation Memory Node Specification

Single conversation buffer memory with built‑in auto‑summary capability.
When auto_summarize is enabled and the buffer is nearly full (within 5
messages of max_messages), the node summarizes the oldest summarize_count
messages into the summary and frees space in the buffer.

Note: MEMORY nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List, Optional

from shared.models.node_enums import MemorySubtype, NodeType
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


class ConversationMemorySpec(BaseNodeSpec):
    """Conversation buffer with simple, built‑in summarization policy."""

    def __init__(self, *, subtype: MemorySubtype, name: Optional[str] = None):
        super().__init__(
            type=NodeType.MEMORY,
            subtype=subtype,
            name=name
            or (
                "Conversation_Buffer_Memory"
                if subtype == MemorySubtype.CONVERSATION_BUFFER
                else "Conversation_Summary_Memory"
            ),
            description=(
                "Conversation buffer with auto‑summary when nearly full for efficient context management"
            ),
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
                "auto_summarize": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否在接近容量时自动总结旧消息",
                    "required": False,
                },
                "summarize_count": {
                    "type": "integer",
                    "default": 10,
                    "min": 1,
                    "description": "接近容量时汇总的最旧消息数量",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas for memory operations and summarization
            input_params={
                # Buffer-style ops
                "message": {
                    "type": "string",
                    "default": "",
                    "description": "Single message to add to the buffer",
                    "required": False,
                },
                "role": {
                    "type": "string",
                    "default": "user",
                    "description": "Role of the message author",
                    "required": False,
                    "options": ["user", "assistant", "system"],
                },
                "metadata": {
                    "type": "object",
                    "default": {},
                    "description": "Optional metadata to store with message",
                    "required": False,
                },
            },
            output_params={
                # Buffer outputs
                "messages": {
                    "type": "array",
                    "default": [],
                    "description": "Messages currently in buffer",
                    "required": False,
                },
                "total_messages": {
                    "type": "integer",
                    "default": 0,
                    "description": "Total number of messages stored",
                    "required": False,
                },
                "buffer_full": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether buffer hit configured limits",
                    "required": False,
                },
                "success": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether the operation succeeded",
                    "required": False,
                },
                # Summary outputs
                "summary": {
                    "type": "string",
                    "default": "",
                    "description": "Generated conversation summary",
                    "required": False,
                },
                "summary_metadata": {
                    "type": "object",
                    "default": {},
                    "description": "Metadata about the summary",
                    "required": False,
                },
            },
            # MEMORY nodes have no ports - they are attached to AI_AGENT nodes
            input_ports=[],
            output_ports=[],
            # Memory nodes don't have attached_nodes (only AI_AGENT has this)
            attached_nodes=None,
            # Examples (simplified to reflect auto-summary on near capacity)
            examples=[
                {
                    "name": "Customer Support Chat Memory",
                    "description": "Store customer support conversation history with context",
                    "configurations": {
                        "max_messages": 30,
                        "auto_summarize": True,
                        "summarize_count": 5,
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
                        "auto_summarize": True,
                        "summarize_count": 5,
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
                        "auto_summarize": True,
                        "summarize_count": 10,
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


# Export single Conversation Buffer spec with built-in summarization capability
CONVERSATION_BUFFER_MEMORY_SPEC = ConversationMemorySpec(
    subtype=MemorySubtype.CONVERSATION_BUFFER, name="Conversation_Buffer_Memory"
)
