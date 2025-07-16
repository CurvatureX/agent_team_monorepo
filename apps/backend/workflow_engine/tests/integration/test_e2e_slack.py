"""
End-to-end integration tests for Slack tool.

This module tests the complete Slack integration flow including:
- OAuth2 credential management
- Slack API operations (messages, channels)
- Tool node execution
- Markdown formatting
- Error handling and recovery
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from workflow_engine.clients.slack_client import (
    SlackClient,
    SlackError,
    ChannelNotFoundError,
    MessageTooLongError,
    InvalidChannelError
)
from workflow_engine.services.credential_service import CredentialService
from workflow_engine.nodes.tool_node import ToolNodeExecutor
from workflow_engine.models.credential import OAuth2Credential
from workflow_engine.nodes.base import NodeExecutionContext


@pytest.fixture
def mock_valid_credentials():
    """Create valid mock OAuth2 credentials for Slack."""
    credentials = OAuth2Credential()
    credentials.provider = "slack"
    credentials.access_token = "xoxb-test-slack-token"
    credentials.refresh_token = "test_refresh_token"
    credentials.expires_at = int((datetime.now() + timedelta(hours=1)).timestamp())
    credentials.credential_data = {
        "token_type": "bot",
        "scope": "chat:write channels:read"
    }
    return credentials


@pytest.fixture
def mock_expired_credentials():
    """Create expired mock OAuth2 credentials."""
    credentials = OAuth2Credential()
    credentials.provider = "slack"
    credentials.access_token = "expired_slack_token"
    credentials.refresh_token = "test_refresh_token"
    credentials.expires_at = int((datetime.now() - timedelta(hours=1)).timestamp())
    return credentials


class TestSlackE2E:
    """End-to-end tests for Slack integration."""
    
    @pytest.mark.asyncio
    async def test_complete_message_workflow(self, mock_valid_credentials):
        """Test complete message workflow: send message, validate channel."""
        
        # Mock Slack API responses
        message_response = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "message": {
                "type": "message",
                "subtype": "bot_message",
                "text": "Hello, World!",
                "ts": "1234567890.123456",
                "bot_id": "B1234567890"
            }
        }
        
        channel_info_response = {
            "ok": True,
            "channel": {
                "id": "C1234567890",
                "name": "general",
                "is_channel": True,
                "is_member": True,
                "created": 1234567890
            }
        }
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            # Set up mock responses for different operations
            mock_request.side_effect = [
                message_response,       # send_message
                channel_info_response   # validate_channel
            ]
            
            client = SlackClient(mock_valid_credentials)
            
            # Test 1: Send message
            result = await client.send_message(
                channel="#general",
                text="Hello, World!",
                as_user=True
            )
            
            assert result["ok"] == True
            assert result["channel"] == "C1234567890"
            assert result["message"]["text"] == "Hello, World!"
            
            # Test 2: Validate channel
            is_valid = await client.validate_channel("C1234567890")
            assert is_valid == True
            
            # Verify all API calls were made
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_markdown_formatting_integration(self, mock_valid_credentials):
        """Test markdown formatting in message sending."""
        
        # Mock Slack API response
        message_response = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456"
        }
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.return_value = message_response
            
            client = SlackClient(mock_valid_credentials)
            
            # Test markdown formatting
            original_text = """
            Hello @john! Please check the #engineering channel.
            Visit [Google](https://google.com) for more info.
            Use `console.log()` to debug.
            *Important*: This is _urgent_.
            """
            
            result = await client.send_message(
                channel="#general",
                text=original_text,
                format_markdown=True
            )
            
            # Verify the call was made
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            sent_data = call_args[1]["json"]
            
            # Check that markdown was formatted
            formatted_text = sent_data["text"]
            assert "<@john>" in formatted_text
            assert "<#engineering>" in formatted_text
            assert "<https://google.com|Google>" in formatted_text
            assert "`console.log()`" in formatted_text
            assert "*Important*" in formatted_text
            assert "_urgent_" in formatted_text
    
    @pytest.mark.asyncio
    async def test_direct_message_workflow(self, mock_valid_credentials):
        """Test direct message sending workflow."""
        
        # Mock Slack API responses
        dm_open_response = {
            "ok": True,
            "channel": {
                "id": "D1234567890"
            }
        }
        
        message_response = {
            "ok": True,
            "channel": "D1234567890",
            "ts": "1234567890.123456"
        }
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.side_effect = [dm_open_response, message_response]
            
            client = SlackClient(mock_valid_credentials)
            
            # Send direct message
            result = await client.send_direct_message(
                user_id="U1234567890",
                text="Hello! This is a direct message.",
                format_markdown=True
            )
            
            assert result["ok"] == True
            assert result["channel"] == "D1234567890"
            
            # Verify two API calls were made (open DM + send message)
            assert mock_request.call_count == 2
            
            # Verify DM was opened first
            first_call = mock_request.call_args_list[0]
            assert first_call[0][1] == "/conversations.open"
            
            # Verify message was sent
            second_call = mock_request.call_args_list[1]
            assert second_call[0][1] == "/chat.postMessage"
    
    @pytest.mark.asyncio
    async def test_channel_validation_and_management(self, mock_valid_credentials):
        """Test channel validation and management operations."""
        
        # Mock responses for different channel operations
        valid_channel_response = {
            "ok": True,
            "channel": {
                "id": "C1234567890",
                "name": "general",
                "is_channel": True,
                "is_member": True
            }
        }
        
        invalid_channel_response = {
            "ok": False,
            "error": "channel_not_found"
        }
        
        channels_list_response = {
            "ok": True,
            "channels": [
                {"id": "C1111111111", "name": "general"},
                {"id": "C2222222222", "name": "engineering"},
                {"id": "C3333333333", "name": "marketing"}
            ]
        }
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.side_effect = [
                valid_channel_response,    # validate_channel (valid)
                invalid_channel_response,  # validate_channel (invalid)
                valid_channel_response,    # get_channel_info
                channels_list_response     # list_channels
            ]
            
            client = SlackClient(mock_valid_credentials)
            
            # Test 1: Validate valid channel
            is_valid = await client.validate_channel("C1234567890")
            assert is_valid == True
            
            # Test 2: Validate invalid channel
            is_invalid = await client.validate_channel("C9999999999")
            assert is_invalid == False
            
            # Test 3: Get channel info
            channel_info = await client.get_channel_info("C1234567890")
            assert channel_info["channel"]["name"] == "general"
            
            # Test 4: List channels
            channels = await client.list_channels()
            assert len(channels) == 3
            assert channels[0]["name"] == "general"
            
            # Verify all API calls were made
            assert mock_request.call_count == 4
    
    @pytest.mark.asyncio
    async def test_tool_node_slack_execution(self, mock_valid_credentials):
        """Test Slack tool execution through ToolNodeExecutor (as email tool)."""
        
        # Mock credential service
        mock_credential_service = AsyncMock(spec=CredentialService)
        mock_credential_service.get_credential.return_value = mock_valid_credentials
        
        # Mock Slack API response
        api_response = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "message": {
                "text": "**Important Notification**\nThis is a test message sent via tool node."
            }
        }
        
        with patch('workflow_engine.services.credential_service.CredentialService', return_value=mock_credential_service):
            with patch.object(SlackClient, '_make_request', return_value=api_response) as mock_request:
                
                # Create mock execution context
                context = MagicMock(spec=NodeExecutionContext)
                context.get_parameter.side_effect = lambda key, default=None: {
                    "provider": "slack",
                    "action": "send_message",
                    "channel": "#notifications",
                    "user_id": "test_user"
                }.get(key, default)
                
                context.input_data = {
                    "recipient": "#notifications",
                    "subject": "Important Notification",
                    "message": "This is a test message sent via tool node.",
                    "body": "This is a test message sent via tool node."
                }
                
                # Execute tool (email tool uses Slack)
                executor = ToolNodeExecutor()
                result = executor._execute_email_tool(context, [], 0.0)
                
                # Verify result
                assert result.status.value == "SUCCESS"
                assert "tool_type" in result.output_data
                assert result.output_data["tool_type"] == "email"
                assert result.output_data["provider"] == "slack"
                
                # Verify credential was retrieved
                mock_credential_service.get_credential.assert_called_once_with("test_user", "slack")
                
                # Verify API was called
                mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_slack_error_handling_and_retry(self, mock_valid_credentials):
        """Test error handling and retry mechanism for Slack API."""
        
        # Mock initial failures followed by success
        responses = [
            Exception("500 Internal Server Error"),
            Exception("503 Service Unavailable"),
            {
                "ok": True,
                "channel": "C1234567890",
                "ts": "1234567890.123456"
            }
        ]
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.side_effect = responses
            
            client = SlackClient(mock_valid_credentials)
            
            # This should retry and eventually succeed
            with patch('asyncio.sleep'):  # Speed up the test
                result = await client.send_message(
                    channel="#general",
                    text="Retry test message"
                )
            
            assert result["ok"] == True
            assert result["channel"] == "C1234567890"
            assert mock_request.call_count == 3  # Should have retried 3 times
    
    @pytest.mark.asyncio
    async def test_message_length_limits(self, mock_valid_credentials):
        """Test message length validation and handling."""
        
        client = SlackClient(mock_valid_credentials)
        
        # Test message too long
        long_message = "x" * (SlackClient.MAX_MESSAGE_LENGTH + 1)
        
        with pytest.raises(MessageTooLongError) as exc_info:
            await client.send_message("#general", long_message)
        
        assert "Message too long" in str(exc_info.value)
        assert str(SlackClient.MAX_MESSAGE_LENGTH) in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_concurrent_slack_operations(self, mock_valid_credentials):
        """Test concurrent Slack operations."""
        
        # Mock responses for concurrent operations
        mock_responses = [
            {"ok": True, "channel": "C1234567890", "ts": f"123456789{i}.123456"}
            for i in range(5)
        ]
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.side_effect = mock_responses
            
            client = SlackClient(mock_valid_credentials)
            
            # Send multiple messages concurrently
            start_time = datetime.now()
            
            tasks = []
            for i in range(5):
                task = client.send_message(
                    channel="#general",
                    text=f"Concurrent message {i}"
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Verify all messages were sent
            assert len(results) == 5
            for i, result in enumerate(results):
                assert result["ok"] == True
                assert result["ts"] == f"123456789{i}.123456"
            
            # Concurrent execution should complete within reasonable time
            assert execution_time < 10.0
            assert mock_request.call_count == 5
    
    @pytest.mark.asyncio
    async def test_slack_format_validation(self, mock_valid_credentials):
        """Test Slack-specific format validation and edge cases."""
        
        client = SlackClient(mock_valid_credentials)
        
        # Test invalid channel formats
        invalid_channels = [
            "",           # Empty channel
            "   ",        # Whitespace only
            "invalid",    # Invalid format
            "#",          # Hash only
            "C123",       # Too short ID
        ]
        
        for invalid_channel in invalid_channels:
            with pytest.raises(InvalidChannelError):
                await client.send_message(invalid_channel, "Test message")
        
        # Test empty message
        with pytest.raises(SlackError) as exc_info:
            await client.send_message("#general", "")
        assert "cannot be empty" in str(exc_info.value)
        
        # Test empty message with whitespace
        with pytest.raises(SlackError) as exc_info:
            await client.send_message("#general", "   ")
        assert "cannot be empty" in str(exc_info.value)


class TestSlackIntegrationErrors:
    """Test error scenarios and edge cases for Slack integration."""
    
    @pytest.mark.asyncio
    async def test_channel_not_found_error(self, mock_valid_credentials):
        """Test handling of channel not found errors."""
        
        error_response = {
            "ok": False,
            "error": "channel_not_found"
        }
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.return_value = error_response
            
            client = SlackClient(mock_valid_credentials)
            
            with pytest.raises(ChannelNotFoundError):
                await client.send_message("#nonexistent", "Test message")
    
    @pytest.mark.asyncio
    async def test_bot_not_in_channel_error(self, mock_valid_credentials):
        """Test handling of bot not in channel errors."""
        
        error_response = {
            "ok": False,
            "error": "not_in_channel"
        }
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.return_value = error_response
            
            client = SlackClient(mock_valid_credentials)
            
            with pytest.raises(SlackError) as exc_info:
                await client.send_message("#private-channel", "Test message")
            
            assert "not in channel" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_invalid_token_error(self, mock_valid_credentials):
        """Test handling of invalid token errors."""
        
        error_response = {
            "ok": False,
            "error": "invalid_auth"
        }
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.return_value = error_response
            
            client = SlackClient(mock_valid_credentials)
            
            with pytest.raises(SlackError) as exc_info:
                await client.send_message("#general", "Test message")
            
            assert "invalid_auth" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rate_limiting_handling(self, mock_valid_credentials):
        """Test handling of Slack API rate limiting."""
        
        rate_limit_responses = [
            Exception("429 Too Many Requests"),
            Exception("429 Too Many Requests"),
            {"ok": True, "channel": "C1234567890", "ts": "1234567890.123456"}
        ]
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.side_effect = rate_limit_responses
            
            client = SlackClient(mock_valid_credentials)
            
            # Should eventually succeed after rate limit is lifted
            with patch('asyncio.sleep'):  # Speed up the test
                result = await client.send_message(
                    channel="#general",
                    text="Rate limit test message"
                )
            
            assert result["ok"] == True
            assert mock_request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_malformed_api_responses(self, mock_valid_credentials):
        """Test handling of malformed API responses."""
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            # Mock malformed response
            mock_request.return_value = {"unexpected": "format"}
            
            client = SlackClient(mock_valid_credentials)
            
            # Should handle gracefully without crashing
            result = await client.send_message("#general", "Test message")
            assert result == {"unexpected": "format"}
    
    @pytest.mark.asyncio
    async def test_network_connectivity_issues(self, mock_valid_credentials):
        """Test handling of network connectivity issues."""
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.side_effect = Exception("Connection timeout")
            
            client = SlackClient(mock_valid_credentials)
            
            with pytest.raises(SlackError) as exc_info:
                await client.send_message("#general", "Test message")
            
            assert "Connection timeout" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_direct_message_user_not_found(self, mock_valid_credentials):
        """Test handling of user not found in direct messages."""
        
        error_response = {
            "ok": False,
            "error": "user_not_found"
        }
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.return_value = error_response
            
            client = SlackClient(mock_valid_credentials)
            
            with pytest.raises(SlackError) as exc_info:
                await client.send_direct_message("U9999999999", "Test DM")
            
            assert "user_not_found" in str(exc_info.value) 