"""Integration test for AI node with new provider architecture."""
import os
from unittest.mock import MagicMock, patch

from workflow_engine.core.execution_context import NodeExecutionContext
from workflow_engine.core.node_result import ExecutionStatus, NodeExecutionResult
from workflow_engine.nodes.ai_agent_node import AIAgentNodeExecutor


def test_ai_node_with_provider_error_handling():
    """Test that AI node correctly handles various error scenarios."""

    # Create node executor
    executor = AIAgentNodeExecutor(subtype="OPENAI_CHATGPT")

    # Create mock context
    mock_node = MagicMock()
    mock_node.id = "test-node-123"
    mock_node.subtype = "OPENAI_CHATGPT"
    mock_node.parameters = {
        "system_prompt": "You are a helpful assistant",
        "model_version": "gpt-5-nano",
        "temperature": 0.7,
        "max_tokens": 2048,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
    }

    context = NodeExecutionContext(
        node=mock_node,
        workflow_id="test-workflow",
        execution_id="test-execution",
        input_data={"content": "Hello, how are you?"},
        static_data={},
        credentials={},
        metadata={},
    )

    # Test 1: Authentication error
    with patch("workflow_engine.nodes.ai_providers.openai_provider.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Simulate auth error
        from openai import AuthenticationError

        mock_client.chat.completions.create.side_effect = AuthenticationError("Invalid key")

        result = executor._execute_openai_agent(context, [], 0)

        assert result.status == ExecutionStatus.ERROR
        assert "error_type" in result.error_details
        assert result.error_details["error_type"] == "auth_error"
        assert "Invalid or missing OpenAI API key" in result.error_message

    # Test 2: Rate limit error
    with patch("workflow_engine.nodes.ai_providers.openai_provider.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Create a mock rate limit error
        class MockRateLimitError(Exception):
            __name__ = "RateLimitError"

        mock_client.chat.completions.create.side_effect = MockRateLimitError("Rate limit")

        result = executor._execute_openai_agent(context, [], 0)

        assert result.status == ExecutionStatus.ERROR
        assert result.error_details["error_type"] == "rate_limit"
        assert "rate limit exceeded" in result.error_message.lower()

    # Test 3: Parameter error (max_tokens vs max_completion_tokens)
    with patch("workflow_engine.nodes.ai_providers.openai_provider.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Simulate parameter error
        mock_client.chat.completions.create.side_effect = Exception(
            "Unsupported parameter: 'max_tokens' is not supported with this model"
        )

        mock_node.parameters["model_version"] = "gpt-5"  # This should trigger max_completion_tokens
        result = executor._execute_openai_agent(context, [], 0)

        assert result.status == ExecutionStatus.ERROR
        assert result.error_details["error_type"] == "invalid_request"
        assert "max_completion_tokens" in result.error_message

    # Test 4: Successful response
    with patch("workflow_engine.nodes.ai_providers.openai_provider.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock successful response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello! I'm doing great, thank you for asking."
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = MagicMock()
        mock_response.usage.dict.return_value = {"total_tokens": 50}

        mock_client.chat.completions.create.return_value = mock_response

        result = executor._execute_openai_agent(context, [], 0)

        assert result.status == ExecutionStatus.SUCCESS
        assert result.output_data["content"] == "Hello! I'm doing great, thank you for asking."
        assert result.output_data["metadata"]["provider"] == "openai"
        assert "usage" in result.output_data["metadata"]

    # Test 5: Error content in successful API response
    with patch("workflow_engine.nodes.ai_providers.openai_provider.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock response that looks like an error
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Error: Unable to process your request"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = MagicMock()
        mock_response.usage.dict.return_value = {"total_tokens": 10}

        mock_client.chat.completions.create.return_value = mock_response

        result = executor._execute_openai_agent(context, [], 0)

        # This should be detected as an error even though API returned 200
        assert result.status == ExecutionStatus.ERROR
        assert result.error_details["error_type"] == "response_error"


def test_provider_fallback_mechanism():
    """Test that the executor falls back to legacy methods when providers aren't available."""

    # Temporarily make providers unavailable
    import workflow_engine.nodes.ai_agent_node as ai_module

    original_value = ai_module.PROVIDERS_AVAILABLE
    ai_module.PROVIDERS_AVAILABLE = False

    try:
        executor = AIAgentNodeExecutor(subtype="OPENAI_CHATGPT")

        mock_node = MagicMock()
        mock_node.id = "test-node"
        mock_node.subtype = "OPENAI_CHATGPT"
        mock_node.parameters = {
            "system_prompt": "Test",
            "model_version": "gpt-5-nano",
            "temperature": 0.7,
            "max_tokens": 100,
            "presence_penalty": 0,
            "frequency_penalty": 0,
        }

        context = NodeExecutionContext(
            node=mock_node,
            workflow_id="test",
            execution_id="test",
            input_data={"content": "Test message"},
            static_data={},
            credentials={},
            metadata={},
        )

        # Mock the legacy _call_openai_api method
        with patch.object(executor, "_call_openai_api") as mock_legacy:
            mock_legacy.return_value = "Legacy response"

            result = executor._execute_openai_agent(context, [], 0)

            # Should have called legacy method
            assert mock_legacy.called

    finally:
        # Restore original value
        ai_module.PROVIDERS_AVAILABLE = original_value


if __name__ == "__main__":
    print("Running AI node integration tests...")
    test_ai_node_with_provider_error_handling()
    print("✓ Error handling tests passed")

    test_provider_fallback_mechanism()
    print("✓ Fallback mechanism tests passed")

    print("\nAll tests passed! 🎉")
