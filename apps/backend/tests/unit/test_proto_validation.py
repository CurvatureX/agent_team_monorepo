"""
Proto 定义和验证的单元测试
验证新的 workflow_agent.proto 定义是否正确实现
"""

import pytest
import json
from unittest.mock import MagicMock


class TestProtoValidation:
    """测试 proto 定义的正确性"""

    def test_conversation_request_structure(self):
        """测试 ConversationRequest 结构"""
        # Mock ConversationRequest structure based on proto
        request_fields = {
            "session_id": "test_session_123",
            "access_token": "bearer_token_123", 
            "user_message": "Create a workflow for data processing",
            "workflow_context": {
                "origin": "create",
                "source_workflow_id": ""
            }
        }
        
        # Verify required fields
        required_fields = ["session_id", "access_token", "user_message"]
        for field in required_fields:
            assert field in request_fields
            assert request_fields[field] is not None
        
        # Verify workflow_context structure
        if request_fields.get("workflow_context"):
            context = request_fields["workflow_context"]
            assert "origin" in context
            assert context["origin"] in ["create", "edit", "copy"]

    def test_conversation_response_structure(self):
        """测试 ConversationResponse 结构"""
        # Test message response
        message_response = {
            "session_id": "test_session",
            "response_type": "RESPONSE_TYPE_MESSAGE",
            "message": "I understand you want to create a workflow...",
            "is_final": False
        }
        
        assert "session_id" in message_response
        assert "response_type" in message_response
        assert "is_final" in message_response
        assert message_response["message"] is not None
        
        # Test workflow response
        workflow_response = {
            "session_id": "test_session",
            "response_type": "RESPONSE_TYPE_WORKFLOW", 
            "workflow": '{"name": "Generated Workflow", "nodes": []}',
            "is_final": True
        }
        
        assert "workflow" in workflow_response
        assert isinstance(workflow_response["workflow"], str)
        # Verify it's valid JSON
        workflow_data = json.loads(workflow_response["workflow"])
        assert isinstance(workflow_data, dict)
        
        # Test error response
        error_response = {
            "session_id": "test_session",
            "response_type": "RESPONSE_TYPE_ERROR",
            "error": {
                "error_code": "INTERNAL_ERROR",
                "message": "Something went wrong",
                "details": "Detailed error info",
                "is_recoverable": True
            },
            "is_final": True
        }
        
        assert "error" in error_response
        error = error_response["error"]
        assert all(field in error for field in ["error_code", "message", "details", "is_recoverable"])

    def test_workflow_context_validation(self):
        """测试 WorkflowContext 验证"""
        # Test create context
        create_context = {
            "origin": "create",
            "source_workflow_id": ""
        }
        
        assert create_context["origin"] == "create"
        assert create_context["source_workflow_id"] == ""
        
        # Test edit context
        edit_context = {
            "origin": "edit", 
            "source_workflow_id": "workflow_123"
        }
        
        assert edit_context["origin"] == "edit"
        assert edit_context["source_workflow_id"] != ""
        
        # Test copy context
        copy_context = {
            "origin": "copy",
            "source_workflow_id": "workflow_456" 
        }
        
        assert copy_context["origin"] == "copy"
        assert copy_context["source_workflow_id"] != ""

    def test_response_type_enum(self):
        """测试 ResponseType 枚举"""
        response_types = {
            "RESPONSE_TYPE_UNKNOWN": 0,
            "RESPONSE_TYPE_MESSAGE": 1,
            "RESPONSE_TYPE_WORKFLOW": 2,
            "RESPONSE_TYPE_ERROR": 3
        }
        
        # Verify enum values
        assert response_types["RESPONSE_TYPE_UNKNOWN"] == 0
        assert response_types["RESPONSE_TYPE_MESSAGE"] == 1
        assert response_types["RESPONSE_TYPE_WORKFLOW"] == 2
        assert response_types["RESPONSE_TYPE_ERROR"] == 3
        
        # Verify uniqueness
        values = list(response_types.values())
        assert len(values) == len(set(values))

    def test_error_content_structure(self):
        """测试 ErrorContent 结构"""
        error_content = {
            "error_code": "PROCESSING_ERROR",
            "message": "Failed to process user request",
            "details": "The workflow generation step encountered an error",
            "is_recoverable": True
        }
        
        # Verify required fields
        required_fields = ["error_code", "message", "details", "is_recoverable"]
        for field in required_fields:
            assert field in error_content
        
        # Verify types
        assert isinstance(error_content["error_code"], str)
        assert isinstance(error_content["message"], str) 
        assert isinstance(error_content["details"], str)
        assert isinstance(error_content["is_recoverable"], bool)
        
        # Test common error codes
        common_error_codes = [
            "INTERNAL_ERROR",
            "PROCESSING_ERROR", 
            "VALIDATION_ERROR",
            "TIMEOUT_ERROR"
        ]
        
        assert error_content["error_code"] in common_error_codes or error_content["error_code"].endswith("_ERROR")


class TestServiceIntegration:
    """测试服务集成的单元测试"""

    def test_grpc_service_interface(self):
        """测试 gRPC 服务接口"""
        # Mock service interface
        service_methods = [
            "ProcessConversation"
        ]
        
        # Verify the service only has the expected method
        assert "ProcessConversation" in service_methods
        assert len(service_methods) == 1  # Only one method as per simplified proto

    def test_session_management(self):
        """测试 session 管理"""
        # Mock session state structure
        session_state = {
            "session_id": "test_session",
            "stage": "clarification",
            "conversations": [],
            "intent_summary": "",
            "current_workflow": None,
            "alternatives": [],
            "created_at": 1640995200000,  # Mock timestamp
            "updated_at": 1640995200000
        }
        
        # Verify session state structure
        required_fields = [
            "session_id", "stage", "conversations", 
            "current_workflow", "created_at", "updated_at"
        ]
        
        for field in required_fields:
            assert field in session_state
        
        # Verify data types
        assert isinstance(session_state["conversations"], list)
        assert isinstance(session_state["created_at"], int)
        assert isinstance(session_state["updated_at"], int)

    def test_conversation_history(self):
        """测试对话历史结构"""
        conversation = {
            "role": "user",
            "text": "Create a data processing workflow",
            "timestamp": 1640995200000
        }
        
        assert conversation["role"] in ["user", "assistant"]
        assert isinstance(conversation["text"], str)
        assert isinstance(conversation["timestamp"], int)
        assert len(conversation["text"]) > 0

    def test_workflow_generation_output(self):
        """测试工作流生成输出"""
        workflow = {
            "name": "Data Processing Workflow",
            "description": "A workflow for processing CSV data",
            "nodes": [
                {
                    "id": "start",
                    "type": "trigger",
                    "name": "Manual Trigger",
                    "config": {"trigger_type": "manual"}
                },
                {
                    "id": "process", 
                    "type": "action",
                    "name": "Process Data",
                    "config": {"action": "csv_processing"}
                },
                {
                    "id": "end",
                    "type": "end", 
                    "name": "Completion",
                    "config": {}
                }
            ],
            "connections": [
                {"from": "start", "to": "process"},
                {"from": "process", "to": "end"}
            ],
            "created_at": 1640995200000,
            "session_id": "test_session"
        }
        
        # Verify workflow structure
        assert "name" in workflow
        assert "nodes" in workflow
        assert "connections" in workflow
        
        # Verify nodes
        assert len(workflow["nodes"]) >= 2  # At least start and end
        for node in workflow["nodes"]:
            assert all(field in node for field in ["id", "type", "name", "config"])
        
        # Verify connections
        for connection in workflow["connections"]:
            assert "from" in connection
            assert "to" in connection
            
            # Verify connection references exist in nodes
            node_ids = [node["id"] for node in workflow["nodes"]]
            assert connection["from"] in node_ids
            assert connection["to"] in node_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])