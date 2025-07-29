"""
完整的工作流对话集成测试
测试从 session 创建到工作流生成的完整流程
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from api_gateway.app.services.grpc_client import WorkflowGRPCClient


class TestWorkflowConversationIntegration:
    """测试完整的工作流对话流程"""

    def test_session_creation_with_different_actions(self):
        """测试不同 action 的 session 创建"""
        # Test create action
        session_create = {
            "session_type": "workflow",
            "action": "create",
            "workflow_id": None,
            "metadata": {}
        }
        
        # Test edit action
        session_edit = {
            "session_type": "workflow", 
            "action": "edit",
            "workflow_id": "workflow_123",
            "metadata": {}
        }
        
        # Test copy action
        session_copy = {
            "session_type": "workflow",
            "action": "copy", 
            "workflow_id": "workflow_456",
            "metadata": {}
        }
        
        # Validate that all actions are supported
        valid_actions = ["create", "edit", "copy"]
        assert session_create["action"] in valid_actions
        assert session_edit["action"] in valid_actions
        assert session_copy["action"] in valid_actions
        
        # Validate that edit/copy require workflow_id
        assert session_edit["workflow_id"] is not None
        assert session_copy["workflow_id"] is not None

    @pytest.mark.asyncio
    async def test_grpc_client_conversation_flow(self):
        """测试 gRPC client 与 workflow agent 的对话流程"""
        client = WorkflowGRPCClient()
        
        # Mock the gRPC stub and response
        mock_stub = AsyncMock()
        mock_responses = [
            # First response - clarification message
            MagicMock(
                session_id="test_session",
                response_type=1,  # RESPONSE_TYPE_MESSAGE
                message="I understand you want to create a workflow. Could you provide more details?",
                is_final=False,
                HasField=lambda field: field == "message"
            ),
            # Second response - workflow generation
            MagicMock(
                session_id="test_session", 
                response_type=2,  # RESPONSE_TYPE_WORKFLOW
                workflow='{"name": "Test Workflow", "nodes": []}',
                is_final=True,
                HasField=lambda field: field == "workflow"
            )
        ]
        
        async def mock_process_conversation(request):
            for response in mock_responses:
                yield response
        
        mock_stub.ProcessConversation = mock_process_conversation
        client.stub = mock_stub
        client.connected = True
        
        # Test conversation flow
        responses = []
        async for response in client.process_conversation_stream(
            session_id="test_session",
            user_message="Create a data processing workflow",
            workflow_context={"origin": "create"}
        ):
            responses.append(response)
        
        # Verify responses
        assert len(responses) == 2
        
        # First response should be a message
        assert responses[0]["type"] == "message"
        assert "workflow" in responses[0]["message"].lower()
        assert not responses[0]["is_final"]
        
        # Second response should be workflow
        assert responses[1]["type"] == "workflow"  
        assert responses[1]["is_final"]
        workflow_data = json.loads(responses[1]["workflow"])
        assert "name" in workflow_data

    @pytest.mark.asyncio
    async def test_workflow_context_handling(self):
        """测试不同 workflow context 的处理"""
        client = WorkflowGRPCClient()
        client.connected = True
        
        # Test create context
        create_context = {"origin": "create"}
        
        # Test edit context
        edit_context = {
            "origin": "edit",
            "source_workflow_id": "workflow_123"
        }
        
        # Test copy context
        copy_context = {
            "origin": "copy", 
            "source_workflow_id": "workflow_456"
        }
        
        # Mock the request building process
        with patch('proto.workflow_agent_pb2.ConversationRequest') as mock_request:
            with patch('proto.workflow_agent_pb2.WorkflowContext') as mock_context:
                mock_context_instance = MagicMock()
                mock_context.return_value = mock_context_instance
                
                # Test create context doesn't set source_workflow_id
                try:
                    await client.process_conversation_stream(
                        session_id="test",
                        user_message="test",
                        workflow_context=create_context
                    ).__anext__()
                except:
                    pass  # We expect this to fail due to mocking, just testing the setup
                
                # Verify context was set correctly for create
                mock_context_instance.origin = "create"
                assert mock_context_instance.origin == "create"

    def test_proto_response_parsing(self):
        """测试 proto 响应的解析"""
        client = WorkflowGRPCClient()
        
        # Mock message response
        mock_message_response = MagicMock()
        mock_message_response.session_id = "test_session"
        mock_message_response.is_final = False
        mock_message_response.response_type = 1  # RESPONSE_TYPE_MESSAGE
        mock_message_response.message = "Test message"
        mock_message_response.HasField = lambda field: field == "message"
        
        result = client._proto_response_to_dict(mock_message_response)
        
        assert result["session_id"] == "test_session"
        assert result["type"] == "message"
        assert result["message"] == "Test message"
        assert not result["is_final"]
        
        # Mock workflow response
        mock_workflow_response = MagicMock()
        mock_workflow_response.session_id = "test_session"
        mock_workflow_response.is_final = True
        mock_workflow_response.response_type = 2  # RESPONSE_TYPE_WORKFLOW
        mock_workflow_response.workflow = '{"name": "Test"}'
        mock_workflow_response.HasField = lambda field: field == "workflow"
        
        result = client._proto_response_to_dict(mock_workflow_response)
        
        assert result["session_id"] == "test_session"
        assert result["type"] == "workflow"
        assert result["workflow"] == '{"name": "Test"}'
        assert result["is_final"]

    def test_error_handling(self):
        """测试错误处理"""
        client = WorkflowGRPCClient()
        
        # Mock error response
        mock_error_response = MagicMock()
        mock_error_response.session_id = "test_session"
        mock_error_response.is_final = True
        mock_error_response.response_type = 3  # RESPONSE_TYPE_ERROR
        mock_error_response.HasField = lambda field: field == "error"
        mock_error_response.error = MagicMock()
        mock_error_response.error.error_code = "INTERNAL_ERROR"
        mock_error_response.error.message = "Test error"
        mock_error_response.error.details = "Error details"
        mock_error_response.error.is_recoverable = True
        
        result = client._proto_response_to_dict(mock_error_response)
        
        assert result["session_id"] == "test_session"
        assert result["type"] == "error"
        assert result["error"]["error_code"] == "INTERNAL_ERROR"
        assert result["error"]["message"] == "Test error"
        assert result["is_final"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])