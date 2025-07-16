"""
Tests for Slack API client.

This module tests the SlackClient implementation including message sending,
markdown formatting, channel validation, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from workflow_engine.clients.slack_client import (
    SlackClient,
    SlackError,
    ChannelNotFoundError,
    MessageTooLongError,
    InvalidChannelError
)
from workflow_engine.models.credential import OAuth2Credential


@pytest.fixture
def mock_credentials():
    """Create mock OAuth2 credentials."""
    credentials = OAuth2Credential()
    credentials.access_token = "xoxb-test-slack-token"
    credentials.refresh_token = "test_refresh_token"
    credentials.expires_at = int((datetime.now().timestamp() + 3600))
    return credentials


@pytest.fixture
def slack_client(mock_credentials):
    """Create Slack client with mock credentials."""
    return SlackClient(mock_credentials)


class TestSlackClientInitialization:
    """Test Slack client initialization."""
    
    def test_init_with_credentials(self, mock_credentials):
        """Test initialization with valid credentials."""
        client = SlackClient(mock_credentials)
        assert client.credentials == mock_credentials
        assert client.base_url == "https://slack.com/api"
    
    def test_init_without_credentials(self):
        """Test initialization without credentials raises error."""
        with pytest.raises(ValueError, match="Slack credentials are required"):
            SlackClient(None)
    
    def test_get_base_url(self, slack_client):
        """Test base URL is correctly set."""
        assert slack_client._get_base_url() == "https://slack.com/api"
    
    def test_get_service_name(self, slack_client):
        """Test service name is correctly set."""
        assert slack_client._get_service_name() == "Slack"


class TestChannelValidation:
    """Test channel format validation."""
    
    def test_validate_channel_format_valid(self, slack_client):
        """Test valid channel formats."""
        # Should not raise any exception
        slack_client._validate_channel_format("C1234567890")  # Channel ID
        slack_client._validate_channel_format("#general")     # Channel name with #
        slack_client._validate_channel_format("general")      # Channel name without #
        slack_client._validate_channel_format("D1234567890")  # DM ID
        slack_client._validate_channel_format("G1234567890")  # Group ID
        slack_client._validate_channel_format("random-channel")  # Channel with dash
        slack_client._validate_channel_format("test_channel")    # Channel with underscore
    
    def test_validate_channel_format_invalid(self, slack_client):
        """Test invalid channel formats."""
        with pytest.raises(InvalidChannelError, match="Channel cannot be empty"):
            slack_client._validate_channel_format("")
        
        with pytest.raises(InvalidChannelError, match="Channel cannot be empty"):
            slack_client._validate_channel_format("   ")
        
        with pytest.raises(InvalidChannelError, match="Invalid channel format"):
            slack_client._validate_channel_format("invalid@channel")
        
        with pytest.raises(InvalidChannelError, match="Invalid channel format"):
            slack_client._validate_channel_format("C123")  # Too short
        
        with pytest.raises(InvalidChannelError, match="Invalid channel format"):
            slack_client._validate_channel_format("#Invalid Channel")  # Spaces not allowed


class TestMarkdownFormatting:
    """Test markdown formatting functionality."""
    
    def test_format_markdown_basic(self, slack_client):
        """Test basic markdown formatting (already Slack-compatible)."""
        # These should remain unchanged as they're already Slack format
        assert slack_client.format_markdown("*bold*") == "*bold*"
        assert slack_client.format_markdown("_italic_") == "_italic_"
        assert slack_client.format_markdown("~strikethrough~") == "~strikethrough~"
        assert slack_client.format_markdown("`code`") == "`code`"
        assert slack_client.format_markdown("```code block```") == "```code block```"
    
    def test_format_markdown_links(self, slack_client):
        """Test markdown link conversion."""
        # [text](url) -> <url|text>
        assert slack_client.format_markdown("[Google](https://google.com)") == "<https://google.com|Google>"
        assert slack_client.format_markdown("[Link with spaces](https://example.com/path)") == "<https://example.com/path|Link with spaces>"
    
    def test_format_markdown_urls(self, slack_client):
        """Test URL auto-formatting."""
        # Bare URLs -> <url>
        assert slack_client.format_markdown("https://google.com") == "<https://google.com>"
        assert slack_client.format_markdown("http://example.com/path") == "<http://example.com/path>"
        
        # Already formatted URLs should remain unchanged
        assert slack_client.format_markdown("<https://google.com>") == "<https://google.com>"
    
    def test_format_markdown_mentions(self, slack_client):
        """Test mention formatting."""
        # @username -> <@username>
        assert slack_client.format_markdown("@john") == "<@john>"
        assert slack_client.format_markdown("@john.doe") == "<@john.doe>"
        assert slack_client.format_markdown("@user_123") == "<@user_123>"
        
        # Already formatted mentions should remain unchanged
        assert slack_client.format_markdown("<@john>") == "<@john>"
    
    def test_format_markdown_channels(self, slack_client):
        """Test channel reference formatting."""
        # #channel -> <#channel>
        assert slack_client.format_markdown("#general") == "<#general>"
        assert slack_client.format_markdown("#random-channel") == "<#random-channel>"
        assert slack_client.format_markdown("#test_channel") == "<#test_channel>"
        
        # Already formatted channels should remain unchanged
        assert slack_client.format_markdown("<#general>") == "<#general>"
    
    def test_format_markdown_mixed(self, slack_client):
        """Test mixed markdown formatting."""
        text = "Check out [Google](https://google.com) and message @john in #general"
        expected = "Check out <https://google.com|Google> and message <@john> in <#general>"
        assert slack_client.format_markdown(text) == expected
    
    def test_format_markdown_empty(self, slack_client):
        """Test empty text formatting."""
        assert slack_client.format_markdown("") == ""
        assert slack_client.format_markdown(None) == ""


class TestChannelValidation:
    """Test channel validation functionality."""
    
    @pytest.mark.asyncio
    async def test_validate_channel_success(self, slack_client):
        """Test successful channel validation."""
        mock_response = {
            "ok": True,
            "channel": {
                "id": "C1234567890",
                "name": "general",
                "is_channel": True
            }
        }
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await slack_client.validate_channel("C1234567890")
            
            assert result is True
            mock_request.assert_called_once_with(
                "GET", 
                "/conversations.info",
                params={"channel": "C1234567890"}
            )
    
    @pytest.mark.asyncio
    async def test_validate_channel_not_found(self, slack_client):
        """Test channel validation when channel doesn't exist."""
        mock_response = {
            "ok": False,
            "error": "channel_not_found"
        }
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await slack_client.validate_channel("C1234567890")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_channel_api_error(self, slack_client):
        """Test channel validation with API error."""
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("Network error")
            
            result = await slack_client.validate_channel("C1234567890")
            
            assert result is False


class TestMessageSending:
    """Test message sending functionality."""
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, slack_client):
        """Test successful message sending."""
        mock_response = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "message": {
                "type": "message",
                "subtype": "bot_message",
                "text": "Hello, World!",
                "ts": "1234567890.123456"
            }
        }
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await slack_client.send_message("#general", "Hello, World!")
            
            assert result == mock_response
            mock_request.assert_called_once_with(
                "POST",
                "/chat.postMessage",
                json={
                    "channel": "#general",
                    "text": "Hello, World!",
                    "as_user": True
                }
            )
    
    @pytest.mark.asyncio
    async def test_send_message_with_markdown(self, slack_client):
        """Test message sending with markdown formatting."""
        mock_response = {"ok": True, "ts": "1234567890.123456"}
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            await slack_client.send_message(
                "#general", 
                "Check @john and visit [Google](https://google.com)",
                format_markdown=True
            )
            
            # Check that markdown was formatted
            call_args = mock_request.call_args
            sent_text = call_args[1]["json"]["text"]
            assert "<@john>" in sent_text
            assert "<https://google.com|Google>" in sent_text
    
    @pytest.mark.asyncio
    async def test_send_message_without_markdown(self, slack_client):
        """Test message sending without markdown formatting."""
        mock_response = {"ok": True, "ts": "1234567890.123456"}
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            original_text = "Check @john and visit [Google](https://google.com)"
            await slack_client.send_message("#general", original_text, format_markdown=False)
            
            # Check that markdown was NOT formatted
            call_args = mock_request.call_args
            sent_text = call_args[1]["json"]["text"]
            assert sent_text == original_text
    
    @pytest.mark.asyncio
    async def test_send_message_empty_text(self, slack_client):
        """Test sending empty message."""
        with pytest.raises(SlackError, match="Message text cannot be empty"):
            await slack_client.send_message("#general", "")
        
        with pytest.raises(SlackError, match="Message text cannot be empty"):
            await slack_client.send_message("#general", "   ")
    
    @pytest.mark.asyncio
    async def test_send_message_too_long(self, slack_client):
        """Test sending message that exceeds length limit."""
        long_message = "A" * 5000  # Exceeds MAX_MESSAGE_LENGTH (4000)
        
        with pytest.raises(MessageTooLongError):
            await slack_client.send_message("#general", long_message)
    
    @pytest.mark.asyncio
    async def test_send_message_channel_not_found(self, slack_client):
        """Test sending message to non-existent channel."""
        mock_response = {
            "ok": False,
            "error": "channel_not_found"
        }
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            with pytest.raises(ChannelNotFoundError, match="Channel #nonexistent not found"):
                await slack_client.send_message("#nonexistent", "Hello")
    
    @pytest.mark.asyncio
    async def test_send_message_not_in_channel(self, slack_client):
        """Test sending message when bot is not in channel."""
        mock_response = {
            "ok": False,
            "error": "not_in_channel"
        }
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            with pytest.raises(SlackError, match="Bot is not in channel #private"):
                await slack_client.send_message("#private", "Hello")
    
    @pytest.mark.asyncio
    async def test_send_message_with_kwargs(self, slack_client):
        """Test sending message with additional parameters."""
        mock_response = {"ok": True, "ts": "1234567890.123456"}
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            await slack_client.send_message(
                "#general", 
                "Hello",
                thread_ts="1234567890.000000",
                icon_emoji=":robot_face:"
            )
            
            call_args = mock_request.call_args
            json_data = call_args[1]["json"]
            assert json_data["thread_ts"] == "1234567890.000000"
            assert json_data["icon_emoji"] == ":robot_face:"


class TestChannelInfo:
    """Test channel information retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_channel_info_success(self, slack_client):
        """Test successful channel info retrieval."""
        mock_response = {
            "ok": True,
            "channel": {
                "id": "C1234567890",
                "name": "general",
                "is_channel": True,
                "created": 1234567890,
                "creator": "U1234567890",
                "purpose": {
                    "value": "This is the general channel",
                    "creator": "U1234567890",
                    "last_set": 1234567890
                },
                "num_members": 42
            }
        }
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await slack_client.get_channel_info("#general")
            
            assert result == mock_response["channel"]
            mock_request.assert_called_once_with(
                "GET",
                "/conversations.info",
                params={"channel": "#general"}
            )
    
    @pytest.mark.asyncio
    async def test_get_channel_info_not_found(self, slack_client):
        """Test channel info when channel doesn't exist."""
        mock_response = {
            "ok": False,
            "error": "channel_not_found"
        }
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            with pytest.raises(ChannelNotFoundError, match="Channel #nonexistent not found"):
                await slack_client.get_channel_info("#nonexistent")


class TestDirectMessages:
    """Test direct message functionality."""
    
    @pytest.mark.asyncio
    async def test_send_direct_message_success(self, slack_client):
        """Test successful direct message sending."""
        # Mock responses for opening DM and sending message
        dm_response = {
            "ok": True,
            "channel": {
                "id": "D1234567890",
                "is_im": True
            }
        }
        
        message_response = {
            "ok": True,
            "channel": "D1234567890",
            "ts": "1234567890.123456"
        }
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [dm_response, message_response]
            
            result = await slack_client.send_direct_message("U1234567890", "Hello!")
            
            assert result == message_response
            assert mock_request.call_count == 2
            
            # Check DM opening call
            first_call = mock_request.call_args_list[0]
            assert first_call[0] == ("POST", "/conversations.open")
            assert first_call[1]["json"]["users"] == "U1234567890"
    
    @pytest.mark.asyncio
    async def test_send_direct_message_invalid_user_id(self, slack_client):
        """Test direct message with invalid user ID."""
        with pytest.raises(SlackError, match="User ID cannot be empty"):
            await slack_client.send_direct_message("", "Hello")
        
        with pytest.raises(SlackError, match="Invalid user ID format"):
            await slack_client.send_direct_message("invalid", "Hello")


class TestChannelListing:
    """Test channel listing functionality."""
    
    @pytest.mark.asyncio
    async def test_list_channels_success(self, slack_client):
        """Test successful channel listing."""
        mock_response = {
            "ok": True,
            "channels": [
                {
                    "id": "C1234567890",
                    "name": "general",
                    "is_channel": True,
                    "is_private": False
                },
                {
                    "id": "C0987654321",
                    "name": "random",
                    "is_channel": True,
                    "is_private": False
                }
            ]
        }
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await slack_client.list_channels()
            
            assert result == mock_response["channels"]
            mock_request.assert_called_once_with(
                "GET",
                "/conversations.list",
                params={
                    "types": "public_channel,private_channel",
                    "limit": 100
                }
            )
    
    @pytest.mark.asyncio
    async def test_list_channels_with_limits(self, slack_client):
        """Test channel listing with custom limits."""
        mock_response = {"ok": True, "channels": []}
        
        with patch.object(slack_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            # Test minimum limit
            await slack_client.list_channels(limit=0)
            call_args = mock_request.call_args
            assert call_args[1]["params"]["limit"] == 1
            
            # Test maximum limit
            await slack_client.list_channels(limit=2000)
            call_args = mock_request.call_args
            assert call_args[1]["params"]["limit"] == 1000


class TestClientCleanup:
    """Test client cleanup operations."""
    
    @pytest.mark.asyncio
    async def test_close_client(self, slack_client):
        """Test client cleanup."""
        # Mock the HTTP client
        mock_http_client = AsyncMock()
        slack_client._http_client = mock_http_client
        
        await slack_client.close()
        
        mock_http_client.aclose.assert_called_once()
        assert slack_client._http_client is None
    
    @pytest.mark.asyncio
    async def test_close_client_no_http_client(self, slack_client):
        """Test client cleanup when no HTTP client exists."""
        slack_client._http_client = None
        
        # Should not raise any exception
        await slack_client.close()
        assert slack_client._http_client is None 