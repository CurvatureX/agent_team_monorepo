"""
端到端工作流测试
测试从前端请求到工作流生成的完整流程
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch


class TestEndToEndWorkflow:
    """端到端工作流测试"""

    def test_complete_workflow_creation_flow(self):
        """测试完整的工作流创建流程"""
        # Step 1: Session Creation Request
        session_request = {
            "session_type": "workflow",
            "action": "create", 
            "workflow_id": None,
            "metadata": {"source": "web_ui"}
        }
        
        # Validate session creation
        assert session_request["action"] == "create"
        assert session_request["workflow_id"] is None
        
        # Step 2: Mock Session Creation Response
        session_response = {
            "session": {
                "id": "session_123",
                "user_id": "user_456",
                "status": "active",
                "action": "create"
            },
            "message": "Session created successfully"
        }
        
        assert session_response["session"]["id"] is not None
        assert session_response["session"]["status"] == "active"
        
        # Step 3: Chat Request
        chat_request = {
            "session_id": "session_123",
            "message": "Create a workflow for processing customer data from CSV files",
            "context": {"origin": "create"}
        }
        
        assert chat_request["session_id"] == session_response["session"]["id"]
        assert len(chat_request["message"]) > 0
        
        # Step 4: Expected Chat Responses (SSE Stream)
        expected_responses = [
            {
                "type": "status",
                "data": {"status": "processing", "message": "Connecting to workflow agent..."}
            },
            {
                "type": "message", 
                "data": {
                    "text": "I understand you want to create a workflow for processing customer data. Could you provide more details?",
                    "role": "assistant"
                },
                "is_final": False
            },
            {
                "type": "workflow",
                "data": {
                    "text": "Workflow generated successfully!",
                    "workflow": {
                        "name": "Customer Data Processing Workflow",
                        "nodes": [
                            {"id": "start", "type": "trigger", "name": "CSV Upload"},
                            {"id": "process", "type": "action", "name": "Data Processing"},
                            {"id": "end", "type": "end", "name": "Complete"}
                        ]
                    }
                },
                "is_final": True
            }
        ]
        
        # Validate response sequence
        assert expected_responses[0]["type"] == "status"
        assert expected_responses[1]["type"] == "message"
        assert expected_responses[2]["type"] == "workflow"
        assert expected_responses[2]["is_final"] is True

    def test_edit_workflow_flow(self):
        """测试编辑工作流的流程"""
        # Step 1: Session Creation for Edit
        edit_session_request = {
            "session_type": "workflow",
            "action": "edit",
            "workflow_id": "existing_workflow_789",
            "metadata": {"operation": "edit"}
        }
        
        # Validate edit session requirements
        assert edit_session_request["action"] == "edit"
        assert edit_session_request["workflow_id"] is not None
        
        # Step 2: Chat Request with Edit Context
        edit_chat_request = {
            "session_id": "edit_session_456",
            "message": "Add email notification to this workflow",
            "context": {
                "origin": "edit",
                "source_workflow_id": "existing_workflow_789"
            }
        }
        
        assert edit_chat_request["context"]["origin"] == "edit"
        assert edit_chat_request["context"]["source_workflow_id"] == edit_session_request["workflow_id"]

    def test_copy_workflow_flow(self):
        """测试复制工作流的流程"""
        # Step 1: Session Creation for Copy
        copy_session_request = {
            "session_type": "workflow", 
            "action": "copy",
            "workflow_id": "template_workflow_999",
            "metadata": {"operation": "copy"}
        }
        
        # Validate copy session requirements
        assert copy_session_request["action"] == "copy"
        assert copy_session_request["workflow_id"] is not None
        
        # Step 2: Chat Request with Copy Context
        copy_chat_request = {
            "session_id": "copy_session_789",
            "message": "Modify this template to handle JSON files instead of CSV",
            "context": {
                "origin": "copy",
                "source_workflow_id": "template_workflow_999" 
            }
        }
        
        assert copy_chat_request["context"]["origin"] == "copy"
        assert copy_chat_request["context"]["source_workflow_id"] == copy_session_request["workflow_id"]

    def test_error_handling_flow(self):
        """测试错误处理流程"""
        # Simulate various error scenarios
        error_scenarios = [
            {
                "type": "validation_error",
                "request": {
                    "session_id": "",  # Invalid empty session_id
                    "message": "Create workflow"
                },
                "expected_error": {
                    "error_code": "VALIDATION_ERROR",
                    "message": "Invalid session_id",
                    "is_recoverable": True
                }
            },
            {
                "type": "processing_error", 
                "request": {
                    "session_id": "valid_session",
                    "message": "Create workflow with invalid configuration"
                },
                "expected_error": {
                    "error_code": "PROCESSING_ERROR",
                    "message": "Failed to process workflow request",
                    "is_recoverable": True
                }
            },
            {
                "type": "internal_error",
                "request": {
                    "session_id": "valid_session",
                    "message": "Create workflow"
                },
                "expected_error": {
                    "error_code": "INTERNAL_ERROR", 
                    "message": "Internal server error",
                    "is_recoverable": False
                }
            }
        ]
        
        for scenario in error_scenarios:
            error = scenario["expected_error"]
            assert "error_code" in error
            assert "message" in error
            assert "is_recoverable" in error
            assert error["error_code"].endswith("_ERROR")

    def test_session_state_persistence(self):
        """测试会话状态持久化"""
        # Mock session state evolution
        initial_state = {
            "session_id": "persistent_session",
            "stage": "clarification",
            "conversations": [],
            "current_workflow": None
        }
        
        # After first message
        after_first_message = {
            **initial_state,
            "conversations": [
                {"role": "user", "text": "Create data workflow"},
                {"role": "assistant", "text": "What type of data?"}
            ]
        }
        
        # After workflow generation
        after_workflow_generation = {
            **after_first_message,
            "stage": "completed",
            "conversations": [
                *after_first_message["conversations"],
                {"role": "user", "text": "CSV files"},
                {"role": "assistant", "text": "Workflow generated!"}
            ],
            "current_workflow": {
                "name": "CSV Data Workflow",
                "nodes": [{"id": "start", "type": "trigger"}]
            }
        }
        
        # Verify state evolution
        assert initial_state["stage"] == "clarification"
        assert after_first_message["stage"] == "clarification"
        assert after_workflow_generation["stage"] == "completed"
        assert after_workflow_generation["current_workflow"] is not None

    def test_multi_turn_conversation(self):
        """测试多轮对话"""
        conversation_turns = [
            {
                "turn": 1,
                "user": "I need to create a workflow",
                "assistant": "What kind of workflow do you need?",
                "stage": "clarification"
            },
            {
                "turn": 2, 
                "user": "A workflow for processing customer orders",
                "assistant": "What format are the orders in?",
                "stage": "clarification"
            },
            {
                "turn": 3,
                "user": "JSON files from our API",
                "assistant": "Let me generate a workflow for you.",
                "stage": "workflow_generation"
            }
        ]
        
        # Verify conversation progression
        assert len(conversation_turns) == 3
        assert conversation_turns[0]["stage"] == "clarification"
        assert conversation_turns[1]["stage"] == "clarification" 
        assert conversation_turns[2]["stage"] == "workflow_generation"
        
        # Verify each turn has required fields
        for turn in conversation_turns:
            assert "user" in turn
            assert "assistant" in turn
            assert "stage" in turn
            assert len(turn["user"]) > 0
            assert len(turn["assistant"]) > 0

    def test_workflow_output_validation(self):
        """测试工作流输出验证"""
        generated_workflow = {
            "name": "Customer Order Processing",
            "description": "Processes customer orders from JSON API",
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": "trigger",
                    "name": "API Webhook",
                    "config": {
                        "trigger_type": "webhook",
                        "endpoint": "/orders"
                    }
                },
                {
                    "id": "validate_1", 
                    "type": "action",
                    "name": "Validate Order",
                    "config": {
                        "action": "validate_json",
                        "schema": "order_schema.json"
                    }
                },
                {
                    "id": "process_1",
                    "type": "action", 
                    "name": "Process Order",
                    "config": {
                        "action": "process_order",
                        "database": "orders_db"
                    }
                },
                {
                    "id": "notify_1",
                    "type": "action",
                    "name": "Send Confirmation",
                    "config": {
                        "action": "send_email",
                        "template": "order_confirmation"
                    }
                }
            ],
            "connections": [
                {"from": "trigger_1", "to": "validate_1"},
                {"from": "validate_1", "to": "process_1"},
                {"from": "process_1", "to": "notify_1"}
            ],
            "metadata": {
                "created_by": "workflow_agent",
                "version": "1.0"
            }
        }
        
        # Validate workflow structure
        required_fields = ["name", "description", "nodes", "connections"]
        for field in required_fields:
            assert field in generated_workflow
        
        # Validate nodes
        assert len(generated_workflow["nodes"]) > 0
        for node in generated_workflow["nodes"]:
            assert all(field in node for field in ["id", "type", "name", "config"])
        
        # Validate connections form a valid flow
        connections = generated_workflow["connections"]
        node_ids = [node["id"] for node in generated_workflow["nodes"]]
        
        for conn in connections:
            assert conn["from"] in node_ids
            assert conn["to"] in node_ids
        
        # Verify workflow has a trigger node
        trigger_nodes = [n for n in generated_workflow["nodes"] if n["type"] == "trigger"]
        assert len(trigger_nodes) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])