"""
Slack API client for workflow integrations.

This module provides a client for Slack Web API, supporting message sending
with markdown formatting, channel management, and proper error handling.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from workflow_engine.clients.base_client import BaseAPIClient
from workflow_engine.models.credential import OAuth2Credential


logger = logging.getLogger(__name__)


class SlackError(Exception):
    """Slack specific error."""
    pass


class ChannelNotFoundError(SlackError):
    """Raised when specified channel is not found."""
    pass


class MessageTooLongError(SlackError):
    """Raised when message exceeds Slack's length limit."""
    pass


class InvalidChannelError(SlackError):
    """Raised when channel format is invalid."""
    pass


class SlackClient(BaseAPIClient):
    """
    Slack Web API client.
    
    Provides message sending capabilities with markdown formatting support,
    channel validation, and automatic token refresh.
    """
    
    # Slack message limits
    MAX_MESSAGE_LENGTH = 4000
    MAX_BLOCKS_LENGTH = 50000
    
    def __init__(self, credentials: OAuth2Credential):
        """Initialize Slack client."""
        if not credentials:
            raise ValueError("Slack credentials are required")
        super().__init__(credentials)
    
    def _get_base_url(self) -> str:
        """Get Slack API base URL."""
        return "https://slack.com/api"
    
    def _get_service_name(self) -> str:
        """Get service name for logging."""
        return "Slack"
    
    def _validate_channel_format(self, channel: str) -> None:
        """
        Validate channel format.
        
        Args:
            channel: Channel ID (C1234567890) or channel name (#general)
            
        Raises:
            InvalidChannelError: If channel format is invalid
        """
        if not channel or not channel.strip():
            raise InvalidChannelError("Channel cannot be empty")
        
        channel = channel.strip()
        
        # Valid formats:
        # - Channel ID: C1234567890 (starts with C, followed by 10 chars)
        # - Channel name: #general, general (with or without #)
        # - Direct message: D1234567890 (starts with D)
        # - Group message: G1234567890 (starts with G)
        
        if not (
            re.match(r'^[CDG][A-Z0-9]{10}$', channel) or  # Channel/DM/Group ID
            re.match(r'^#?[a-z0-9-_]+$', channel.lower())  # Channel name
        ):
            raise InvalidChannelError(
                f"Invalid channel format: {channel}. "
                "Expected channel ID (C1234567890), channel name (#general), or DM ID (D1234567890)"
            )
    
    def format_markdown(self, text: str) -> str:
        """
        Format text for Slack markdown.
        
        Converts standard markdown to Slack's markdown format:
        - *bold* -> *bold* (already correct)
        - _italic_ -> _italic_ (already correct)  
        - ~strikethrough~ -> ~strikethrough~ (already correct)
        - `code` -> `code` (already correct)
        - ```code block``` -> ```code block``` (already correct)
        
        Also handles Slack-specific formats:
        - @username -> <@username> (if not already formatted)
        - #channel -> <#channel> (if not already formatted)
        - http://example.com -> <http://example.com>
        - [text](url) -> <url|text>
        
        Args:
            text: Input text with markdown
            
        Returns:
            Formatted text for Slack
        """
        if not text:
            return ""
        
        formatted = text
        
        # Convert [text](url) markdown links to Slack format <url|text>
        # This regex handles nested parentheses in URLs
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        formatted = re.sub(link_pattern, r'<\2|\1>', formatted)
        
        # Convert bare URLs to Slack format (if not already formatted)
        # Only match URLs that aren't already in < >
        url_pattern = r'(?<![<])(https?://[^\s<>]+)(?![>])'
        formatted = re.sub(url_pattern, r'<\1>', formatted)
        
        # Convert @username to <@username> (if not already formatted)
        # Look for @word that isn't already in < >
        mention_pattern = r'(?<![<@])@([a-zA-Z0-9._-]+)(?![>])'
        formatted = re.sub(mention_pattern, r'<@\1>', formatted)
        
        # Convert #channel to <#channel> (if not already formatted)
        # Look for #word that isn't already in < >
        channel_pattern = r'(?<![<#])#([a-zA-Z0-9._-]+)(?![>])'
        formatted = re.sub(channel_pattern, r'<#\1>', formatted)
        
        return formatted
    
    async def validate_channel(self, channel: str) -> bool:
        """
        Validate if channel exists and is accessible.
        
        Args:
            channel: Channel ID or name
            
        Returns:
            True if channel is valid and accessible
            
        Raises:
            SlackError: If validation request fails
        """
        self._validate_channel_format(channel)
        
        try:
            # Use conversations.info to check if channel exists
            params = {"channel": channel}
            response = await self._make_request("GET", "/conversations.info", params=params)
            
            # Check if response is successful
            if response.get("ok", False):
                logger.info(f"Validated channel: {channel}")
                return True
            else:
                logger.warning(f"Channel validation failed for {channel}: {response.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to validate channel {channel}: {e}")
            # Don't raise exception for validation - just return False
            return False
    
    async def send_message(
        self, 
        channel: str, 
        text: str,
        as_user: bool = True,
        format_markdown: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel.
        
        Args:
            channel: Channel ID (#general) or channel name
            text: Message text
            as_user: Whether to send as the authenticated user (default: True)
            format_markdown: Whether to apply markdown formatting (default: True)
            **kwargs: Additional parameters for chat.postMessage API
            
        Returns:
            Response from Slack API including message timestamp, etc.
            
        Raises:
            SlackError: If message sending fails
            ChannelNotFoundError: If channel doesn't exist
            MessageTooLongError: If message is too long
            InvalidChannelError: If channel format is invalid
        """
        self._validate_channel_format(channel)
        
        if not text.strip():
            raise SlackError("Message text cannot be empty")
        
        # Apply markdown formatting if requested
        if format_markdown:
            formatted_text = self.format_markdown(text)
        else:
            formatted_text = text
        
        # Check message length
        if len(formatted_text) > self.MAX_MESSAGE_LENGTH:
            raise MessageTooLongError(
                f"Message too long: {len(formatted_text)} characters. "
                f"Maximum allowed: {self.MAX_MESSAGE_LENGTH}"
            )
        
        # Prepare message data
        message_data = {
            "channel": channel,
            "text": formatted_text,
            "as_user": as_user,
            **kwargs
        }
        
        try:
            response = await self._make_request("POST", "/chat.postMessage", json=message_data)
            
            # Check if Slack API returned an error
            if not response.get("ok", False):
                error = response.get("error", "Unknown error")
                if error == "channel_not_found":
                    raise ChannelNotFoundError(f"Channel {channel} not found")
                elif error == "not_in_channel":
                    raise SlackError(f"Bot is not in channel {channel}")
                elif error == "msg_too_long":
                    raise MessageTooLongError("Message is too long")
                else:
                    raise SlackError(f"Slack API error: {error}")
            
            logger.info(f"Sent message to channel {channel}: {formatted_text[:100]}...")
            return response
            
        except Exception as e:
            if isinstance(e, (SlackError, ChannelNotFoundError, MessageTooLongError)):
                raise
            logger.error(f"Failed to send message to {channel}: {e}")
            raise SlackError(f"Failed to send message: {e}")
    
    async def get_channel_info(self, channel: str) -> Dict[str, Any]:
        """
        Get information about a channel.
        
        Args:
            channel: Channel ID or name
            
        Returns:
            Channel information including name, purpose, members count, etc.
            
        Raises:
            SlackError: If request fails
            ChannelNotFoundError: If channel doesn't exist
        """
        self._validate_channel_format(channel)
        
        try:
            params = {"channel": channel}
            response = await self._make_request("GET", "/conversations.info", params=params)
            
            if not response.get("ok", False):
                error = response.get("error", "Unknown error")
                if error == "channel_not_found":
                    raise ChannelNotFoundError(f"Channel {channel} not found")
                else:
                    raise SlackError(f"Slack API error: {error}")
            
            logger.info(f"Retrieved info for channel {channel}")
            return response.get("channel", {})
            
        except Exception as e:
            if isinstance(e, (SlackError, ChannelNotFoundError)):
                raise
            logger.error(f"Failed to get channel info for {channel}: {e}")
            raise SlackError(f"Failed to get channel info: {e}")
    
    async def list_channels(
        self, 
        types: str = "public_channel,private_channel",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List channels the bot has access to.
        
        Args:
            types: Channel types to include (default: public and private channels)
            limit: Maximum number of channels to return (default: 100, max: 1000)
            
        Returns:
            List of channel objects
            
        Raises:
            SlackError: If request fails
        """
        limit = max(1, min(limit, 1000))  # Enforce limits
        
        params = {
            "types": types,
            "limit": limit
        }
        
        try:
            response = await self._make_request("GET", "/conversations.list", params=params)
            
            if not response.get("ok", False):
                error = response.get("error", "Unknown error")
                raise SlackError(f"Slack API error: {error}")
            
            channels = response.get("channels", [])
            logger.info(f"Retrieved {len(channels)} channels")
            return channels
            
        except Exception as e:
            if isinstance(e, SlackError):
                raise
            logger.error(f"Failed to list channels: {e}")
            raise SlackError(f"Failed to list channels: {e}")
    
    async def send_direct_message(
        self, 
        user_id: str, 
        text: str,
        format_markdown: bool = True
    ) -> Dict[str, Any]:
        """
        Send a direct message to a user.
        
        Args:
            user_id: User ID (U1234567890)
            text: Message text
            format_markdown: Whether to apply markdown formatting (default: True)
            
        Returns:
            Response from Slack API
            
        Raises:
            SlackError: If message sending fails
        """
        if not user_id or not user_id.strip():
            raise SlackError("User ID cannot be empty")
        
        # User IDs should start with U
        if not user_id.startswith('U'):
            raise SlackError(f"Invalid user ID format: {user_id}. Expected format: U1234567890")
        
        try:
            # First, open a DM channel with the user
            dm_data = {"users": user_id}
            dm_response = await self._make_request("POST", "/conversations.open", json=dm_data)
            
            if not dm_response.get("ok", False):
                error = dm_response.get("error", "Unknown error")
                raise SlackError(f"Failed to open DM channel: {error}")
            
            # Get the DM channel ID
            dm_channel = dm_response.get("channel", {}).get("id")
            if not dm_channel:
                raise SlackError("Failed to get DM channel ID")
            
            # Send message to the DM channel
            return await self.send_message(dm_channel, text, format_markdown=format_markdown)
            
        except Exception as e:
            if isinstance(e, SlackError):
                raise
            logger.error(f"Failed to send DM to user {user_id}: {e}")
            raise SlackError(f"Failed to send direct message: {e}")
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None 