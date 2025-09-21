"""Test suite for AI provider error handling improvements."""
import os
from unittest.mock import MagicMock, patch

import pytest

# Import the providers
from workflow_engine.nodes.ai_providers import (
    ClaudeProvider,
    ErrorType,
    GeminiProvider,
    OpenAIProvider,
)


class TestOpenAIProviderErrorHandling:
    """Test OpenAI provider error detection."""

    def test_auth_error_detection(self):
        """Test that authentication errors are properly detected."""
        provider = OpenAIProvider(api_key="invalid_key")

        # Mock the OpenAI client to raise auth error
        with patch("openai.OpenAI") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # Simulate authentication error
            from openai import AuthenticationError

            mock_instance.chat.completions.create.side_effect = AuthenticationError(
                "Invalid API key"
            )

            response = provider.call_api(
                system_prompt="Test", user_prompt="Hello", model="gpt-5-nano"
            )

            assert not response.success
            assert response.error_type == ErrorType.AUTH_ERROR
            assert "Invalid or missing OpenAI API key" in response.error_message

    def test_rate_limit_error_detection(self):
        """Test that rate limit errors are properly detected."""
        provider = OpenAIProvider()

        with patch("openai.OpenAI") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # Simulate rate limit error
            class RateLimitError(Exception):
                __name__ = "RateLimitError"

            mock_instance.chat.completions.create.side_effect = RateLimitError(
                "Rate limit exceeded"
            )

            response = provider.call_api(
                system_prompt="Test", user_prompt="Hello", model="gpt-5-nano"
            )

            assert not response.success
            assert response.error_type == ErrorType.RATE_LIMIT
            assert "rate limit exceeded" in response.error_message.lower()

    def test_parameter_error_detection(self):
        """Test that parameter errors are properly detected."""
        provider = OpenAIProvider()

        with patch("openai.OpenAI") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # Simulate parameter error
            mock_instance.chat.completions.create.side_effect = Exception(
                "Unsupported parameter: 'max_tokens' is not supported with this model"
            )

            response = provider.call_api(
                system_prompt="Test", user_prompt="Hello", model="gpt-5", max_tokens=2048
            )

            assert not response.success
            assert response.error_type == ErrorType.INVALID_REQUEST
            assert "max_completion_tokens" in response.error_message

    def test_content_error_detection(self):
        """Test detection of errors in response content."""
        provider = OpenAIProvider()

        # Test various error patterns in content
        error_contents = [
            "Error: Something went wrong",
            "ERROR: API failure",
            "Failed to process request",
            "Unauthorized access",
            "Rate limit exceeded",
            "Invalid request format",
        ]

        for error_content in error_contents:
            is_error, _ = provider.detect_error_in_content(error_content)
            assert is_error, f"Failed to detect error in: {error_content}"

    def test_short_response_detection(self):
        """Test that suspiciously short responses are detected as errors."""
        provider = OpenAIProvider()

        # Very short responses should be detected as errors
        is_error, error_msg = provider.detect_error_in_content("OK")
        assert is_error
        assert "too short" in error_msg

        # Normal responses should not be detected as errors
        is_error, _ = provider.detect_error_in_content(
            "This is a normal response with sufficient content."
        )
        assert not is_error

    def test_successful_response(self):
        """Test that successful responses are handled correctly."""
        provider = OpenAIProvider()

        with patch("openai.OpenAI") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # Mock successful response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "This is a successful response from the AI."
            mock_response.usage = MagicMock()
            mock_response.usage.dict.return_value = {"total_tokens": 50}
            mock_response.choices[0].finish_reason = "stop"

            mock_instance.chat.completions.create.return_value = mock_response

            response = provider.call_api(
                system_prompt="You are helpful", user_prompt="Hello", model="gpt-5-nano"
            )

            assert response.success
            assert response.content == "This is a successful response from the AI."
            assert response.error_type == ErrorType.NONE
            assert "usage" in response.metadata


class TestClaudeProviderErrorHandling:
    """Test Claude provider error detection."""

    def test_auth_error_detection(self):
        """Test that authentication errors are properly detected."""
        provider = ClaudeProvider(api_key="invalid_key")

        with patch("anthropic.Anthropic") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # Simulate authentication error
            class AuthError(Exception):
                __name__ = "AuthenticationError"

            mock_instance.messages.create.side_effect = AuthError("Invalid API key")

            response = provider.call_api(
                system_prompt="Test", user_prompt="Hello", model="claude-3.5-haiku-20241022"
            )

            assert not response.success
            assert response.error_type == ErrorType.AUTH_ERROR

    def test_claude_specific_error_patterns(self):
        """Test Claude-specific error pattern detection."""
        provider = ClaudeProvider()

        # Claude-specific error patterns
        error_contents = [
            "Anthropic API error: Something went wrong",
            "I'm sorry, but an error occurred while processing your request",
        ]

        for content in error_contents:
            is_error, _ = provider._detect_provider_specific_errors(content)
            assert is_error, f"Failed to detect Claude error in: {content}"


class TestGeminiProviderErrorHandling:
    """Test Gemini provider error detection."""

    def test_safety_filter_error_detection(self):
        """Test that safety filter blocks are properly detected."""
        provider = GeminiProvider()

        with patch("google.generativeai.GenerativeModel") as mock_model:
            mock_instance = MagicMock()
            mock_model.return_value = mock_instance

            # Mock blocked response
            mock_response = MagicMock()
            mock_response.text = None
            mock_response.prompt_feedback = "Blocked due to safety concerns"

            mock_instance.generate_content.return_value = mock_response

            response = provider.call_api(
                system_prompt="Test", user_prompt="Hello", model="gemini-2.5-flash"
            )

            assert not response.success
            assert response.error_type == ErrorType.RESPONSE_ERROR
            assert "Blocked" in response.error_message

    def test_gemini_specific_error_patterns(self):
        """Test Gemini-specific error pattern detection."""
        provider = GeminiProvider()

        error_contents = [
            "Google API error occurred",
            "Content was blocked by safety filters",
            "Safety ratings: HARMFUL content detected",
        ]

        for content in error_contents:
            is_error, _ = provider._detect_provider_specific_errors(content)
            assert is_error, f"Failed to detect Gemini error in: {content}"


class TestCrossProviderConsistency:
    """Test that all providers behave consistently."""

    def test_invalid_model_handling(self):
        """Test that all providers handle invalid models consistently."""
        providers = [OpenAIProvider(), ClaudeProvider(), GeminiProvider()]

        for provider in providers:
            # Test with invalid model
            is_valid, error_msg = provider.validate_model("invalid-model-xyz")
            assert not is_valid
            assert "Invalid" in error_msg
            assert "Supported models:" in error_msg

    def test_empty_content_handling(self):
        """Test that all providers handle empty content consistently."""
        providers = [OpenAIProvider(), ClaudeProvider(), GeminiProvider()]

        for provider in providers:
            is_error, error_msg = provider.detect_error_in_content("")
            assert is_error
            assert "Empty" in error_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
