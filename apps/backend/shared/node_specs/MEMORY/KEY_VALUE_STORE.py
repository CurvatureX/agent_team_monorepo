"""
KEY_VALUE_STORE Memory Node Specification

Key-value store memory for simple data storage and retrieval operations.
This memory node is attached to AI_AGENT nodes and provides basic
key-value storage capabilities for workflow state and data caching.

Note: MEMORY nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import MemorySubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class KeyValueStoreMemorySpec(BaseNodeSpec):
    """Key-value store memory specification for AI_AGENT attached memory."""

    def __init__(self):
        super().__init__(
            type=NodeType.MEMORY,
            subtype=MemorySubtype.KEY_VALUE_STORE,
            name="Key_Value_Store_Memory",
            description="Key-value store memory for simple data storage and retrieval",
            # Configuration parameters (simplified)
            configurations={
                "storage_backend": {
                    "type": "string",
                    "default": "memory",
                    "description": "存储后端类型",
                    "required": True,
                    "options": ["memory", "redis", "sqlite", "file"],
                },
                "connection_config": {
                    "type": "object",
                    "default": {},
                    "description": "存储后端连接配置",
                    "required": False,
                    "sensitive": True,
                },
                "default_ttl": {
                    "type": "integer",
                    "default": 0,
                    "min": 0,
                    "max": 86400,
                    "description": "默认生存时间（秒，0为永不过期）",
                    "required": False,
                },
                "key_prefix": {
                    "type": "string",
                    "default": "",
                    "description": "键名前缀",
                    "required": False,
                },
                "max_keys": {
                    "type": "integer",
                    "default": 1000,
                    "min": 1,
                    "max": 100000,
                    "description": "最大键数量",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Runtime parameters (schema-style)
            input_params={
                "operation": {
                    "type": "string",
                    "default": "get",
                    "description": "操作类型",
                    "required": False,
                    "options": ["get", "set", "delete", "exists", "keys", "clear"],
                },
                "key": {
                    "type": "string",
                    "default": "",
                    "description": "键",
                    "required": False,
                },
                "value": {
                    "type": "object",
                    "default": {},
                    "description": "值（可序列化对象）",
                    "required": False,
                },
                "options": {
                    "type": "object",
                    "default": {},
                    "description": "可选操作参数",
                    "required": False,
                },
            },
            output_params={
                "value": {
                    "type": "object",
                    "default": {},
                    "description": "返回的值（get时）",
                    "required": False,
                },
                "exists": {
                    "type": "boolean",
                    "default": False,
                    "description": "键是否存在",
                    "required": False,
                },
                "keys": {
                    "type": "array",
                    "default": [],
                    "description": "匹配的键列表（keys时）",
                    "required": False,
                },
                "success": {
                    "type": "boolean",
                    "default": False,
                    "description": "操作是否成功",
                    "required": False,
                },
                "error_message": {
                    "type": "string",
                    "default": "",
                    "description": "错误消息",
                    "required": False,
                },
                "operation_time": {
                    "type": "number",
                    "default": 0,
                    "description": "操作耗时（秒）",
                    "required": False,
                },
                "cache_hit": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否命中缓存（如适用）",
                    "required": False,
                },
            },
            # MEMORY nodes have no ports - they are attached to AI_AGENT nodes
            input_ports=[],
            output_ports=[],
            # Memory nodes don't have attached_nodes (only AI_AGENT has this)
            attached_nodes=None,
            # Metadata
            tags=["memory", "key-value", "storage", "cache", "attached"],
            # Examples
            examples=[
                {
                    "name": "Session Data Storage",
                    "description": "Store user session data and preferences",
                    "configurations": {
                        "storage_backend": "redis",
                        "connection_config": {"host": "localhost", "port": 6379, "db": 1},
                        "key_prefix": "session:",
                        "default_ttl": 3600,
                        "max_keys": 10000,
                    },
                    "usage_example": {
                        "attached_to": "session_management_ai",
                        "operations": [
                            {
                                "operation": "set",
                                "key": "user_12345",
                                "value": {
                                    "name": "John Doe",
                                    "preferences": {"theme": "dark", "language": "en"},
                                    "last_activity": "2025-01-20T10:30:00Z",
                                },
                                "ttl": 3600,
                            },
                            {"operation": "get", "key": "user_12345"},
                        ],
                        "expected_results": [
                            {"success": True, "operation_time": 0.002},
                            {
                                "value": {
                                    "name": "John Doe",
                                    "preferences": {"theme": "dark", "language": "en"},
                                    "last_activity": "2025-01-20T10:30:00Z",
                                },
                                "exists": True,
                                "success": True,
                                "cache_hit": True,
                                "operation_time": 0.001,
                            },
                        ],
                    },
                },
                {
                    "name": "Workflow State Management",
                    "description": "Store and retrieve workflow execution state",
                    "configurations": {
                        "storage_backend": "sqlite",
                        "connection_config": {"database": "workflow_state.db"},
                        "key_prefix": "workflow:",
                        "persistence_mode": "sync",
                        "backup_enabled": True,
                        "serialization_format": "json",
                    },
                    "usage_example": {
                        "attached_to": "workflow_orchestrator_ai",
                        "operations": [
                            {
                                "operation": "set",
                                "key": "process_456_state",
                                "value": {
                                    "current_step": "user_approval",
                                    "completed_steps": ["data_validation", "processing"],
                                    "pending_steps": ["final_review", "completion"],
                                    "variables": {"user_id": "12345", "document_id": "doc_789"},
                                },
                            },
                            {"operation": "get", "key": "process_456_state"},
                        ],
                        "expected_results": [
                            {"success": True, "operation_time": 0.005},
                            {
                                "value": {
                                    "current_step": "user_approval",
                                    "completed_steps": ["data_validation", "processing"],
                                    "pending_steps": ["final_review", "completion"],
                                    "variables": {"user_id": "12345", "document_id": "doc_789"},
                                },
                                "exists": True,
                                "success": True,
                                "operation_time": 0.003,
                            },
                        ],
                    },
                },
                {
                    "name": "Simple Cache Store",
                    "description": "Basic caching for API responses and computed values",
                    "configurations": {
                        "storage_backend": "memory",
                        "max_keys": 500,
                        "max_value_size": 524288,
                        "default_ttl": 300,
                        "enable_compression": True,
                    },
                    "usage_example": {
                        "attached_to": "api_response_ai",
                        "operations": [
                            {"operation": "exists", "key": "api_response_hash_abc123"},
                            {
                                "operation": "set",
                                "key": "api_response_hash_abc123",
                                "value": {
                                    "data": [
                                        {"id": 1, "name": "Item 1"},
                                        {"id": 2, "name": "Item 2"},
                                    ],
                                    "timestamp": "2025-01-20T10:30:00Z",
                                    "expires": "2025-01-20T10:35:00Z",
                                },
                                "ttl": 300,
                            },
                            {"operation": "keys", "options": {"pattern": "api_response_*"}},
                        ],
                        "expected_results": [
                            {"exists": False, "success": True, "operation_time": 0.001},
                            {"success": True, "operation_time": 0.002},
                            {
                                "keys": ["api_response_hash_abc123"],
                                "success": True,
                                "operation_time": 0.001,
                            },
                        ],
                    },
                },
            ],
        )


# Export the specification instance
KEY_VALUE_STORE_MEMORY_SPEC = KeyValueStoreMemorySpec()
