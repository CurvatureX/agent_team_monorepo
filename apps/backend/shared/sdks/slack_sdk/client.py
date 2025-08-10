"""
Slack Web API client implementation.

Provides a comprehensive client for interacting with the Slack Web API,
including message sending, user lookups, and channel operations.
"""

import json
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx

from .exceptions import (
    SlackAPIError,
    SlackAuthError,
    SlackChannelNotFoundError,
    SlackRateLimitError,
    SlackUserNotFoundError,
)


class SlackWebClient:
    """
    Slack Web API client for sending messages and interacting with Slack workspace.

    This client handles authentication, rate limiting, and provides methods for
    common Slack operations like sending messages, looking up users, and managing channels.
    """

    BASE_URL = "https://slack.com/api/"

    def __init__(
        self,
        token: str,
        timeout: int = 30,
        rate_limit_retry: bool = True,
        max_retries: int = 3,
    ):
        """
        Initialize Slack Web API client.

        Args:
            token: Bot User OAuth Token (starts with xoxb-)
            timeout: Request timeout in seconds
            rate_limit_retry: Whether to automatically retry on rate limit
            max_retries: Maximum number of retries for failed requests
        """
        self.token = token
        self.timeout = timeout
        self.rate_limit_retry = rate_limit_retry
        self.max_retries = max_retries

        self.client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=self.timeout,
            headers={"Authorization": f"Bearer {token}"},
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.client.close()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
    ) -> Dict:
        """
        Make a request to the Slack API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            data: Request data
            files: Files to upload

        Returns:
            Response data as dictionary

        Raises:
            SlackAPIError: For various API errors
            SlackAuthError: For authentication errors
            SlackRateLimitError: For rate limit errors
        """
        url = urljoin(self.BASE_URL, endpoint)

        for attempt in range(self.max_retries + 1):
            try:
                if method.upper() == "POST":
                    if files:
                        response = self.client.post(url, data=data, files=files)
                    else:
                        response = self.client.post(url, json=data)
                else:
                    response = self.client.request(method, url, params=data)

                response.raise_for_status()
                response_data = response.json()

                # Handle Slack API errors
                if not response_data.get("ok", False):
                    error_code = response_data.get("error", "unknown_error")
                    error_message = response_data.get("error", "Unknown error occurred")

                    # Handle specific error types
                    if error_code in ["invalid_auth", "account_inactive", "token_revoked"]:
                        raise SlackAuthError(
                            f"Authentication failed: {error_message}", error_code, response_data
                        )
                    elif error_code == "rate_limited":
                        retry_after = int(response.headers.get("Retry-After", 60))
                        if self.rate_limit_retry and attempt < self.max_retries:
                            time.sleep(retry_after)
                            continue
                        raise SlackRateLimitError(
                            f"Rate limit exceeded. Retry after {retry_after} seconds",
                            retry_after=retry_after,
                            error_code=error_code,
                            response_data=response_data,
                        )
                    elif error_code == "channel_not_found":
                        raise SlackChannelNotFoundError(
                            f"Channel not found: {error_message}", error_code, response_data
                        )
                    elif error_code in ["user_not_found", "users_not_found"]:
                        raise SlackUserNotFoundError(
                            f"User not found: {error_message}", error_code, response_data
                        )
                    else:
                        raise SlackAPIError(
                            f"Slack API error: {error_message}", error_code, response_data
                        )

                return response_data

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limited
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    if self.rate_limit_retry and attempt < self.max_retries:
                        time.sleep(retry_after)
                        continue
                    raise SlackRateLimitError(
                        f"Rate limit exceeded. Retry after {retry_after} seconds",
                        retry_after=retry_after,
                    )
                elif attempt == self.max_retries:
                    raise SlackAPIError(f"HTTP error: {e.response.status_code} - {e.response.text}")
            except httpx.RequestError as e:
                if attempt == self.max_retries:
                    raise SlackAPIError(f"Request failed: {str(e)}")
                time.sleep(2**attempt)  # Exponential backoff

        raise SlackAPIError("Max retries exceeded")

    def send_message(
        self,
        channel: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict]] = None,
        thread_ts: Optional[str] = None,
        reply_broadcast: bool = False,
        unfurl_links: bool = True,
        unfurl_media: bool = True,
        attachments: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict:
        """
        Send a message to a Slack channel or DM.

        Args:
            channel: Channel ID, channel name, or user ID for DM
            text: Message text (required if blocks not provided)
            blocks: Slack Block Kit blocks for rich formatting
            thread_ts: Timestamp of parent message to reply in thread
            reply_broadcast: Broadcast thread reply to channel
            unfurl_links: Whether to unfurl links
            unfurl_media: Whether to unfurl media
            attachments: Legacy message attachments
            **kwargs: Additional parameters for chat.postMessage

        Returns:
            Response containing message timestamp and other metadata

        Raises:
            SlackAPIError: If message sending fails
            SlackChannelNotFoundError: If channel doesn't exist
        """
        data = {
            "channel": channel,
            "unfurl_links": unfurl_links,
            "unfurl_media": unfurl_media,
            **kwargs,
        }

        if text:
            data["text"] = text
        if blocks:
            data["blocks"] = blocks
        if thread_ts:
            data["thread_ts"] = thread_ts
        if reply_broadcast:
            data["reply_broadcast"] = reply_broadcast
        if attachments:
            data["attachments"] = attachments

        # At least text or blocks must be provided
        if not text and not blocks:
            raise ValueError("Either 'text' or 'blocks' must be provided")

        return self._make_request("POST", "chat.postMessage", data)

    def send_dm(
        self,
        user_id: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict:
        """
        Send a direct message to a user.

        Args:
            user_id: User ID to send DM to
            text: Message text
            blocks: Slack Block Kit blocks
            **kwargs: Additional parameters

        Returns:
            Response containing message timestamp and other metadata
        """
        # For DMs, we can use the user ID directly as the channel
        return self.send_message(channel=user_id, text=text, blocks=blocks, **kwargs)

    def get_user_info(self, user_id: str) -> Dict:
        """
        Get information about a user.

        Args:
            user_id: User ID to look up

        Returns:
            User information dictionary

        Raises:
            SlackUserNotFoundError: If user doesn't exist
        """
        data = {"user": user_id}
        response = self._make_request("GET", "users.info", data)
        return response.get("user", {})

    def get_channel_info(self, channel_id: str) -> Dict:
        """
        Get information about a channel.

        Args:
            channel_id: Channel ID to look up

        Returns:
            Channel information dictionary

        Raises:
            SlackChannelNotFoundError: If channel doesn't exist
        """
        data = {"channel": channel_id}
        response = self._make_request("GET", "conversations.info", data)
        return response.get("channel", {})

    def list_channels(self, types: str = "public_channel,private_channel") -> List[Dict]:
        """
        List channels in the workspace.

        Args:
            types: Comma-separated list of channel types to include

        Returns:
            List of channel dictionaries
        """
        data = {"types": types}
        response = self._make_request("GET", "conversations.list", data)
        return response.get("channels", [])

    def auth_test(self) -> Dict:
        """
        Test authentication and get bot information.

        Returns:
            Authentication information including bot user ID and team

        Raises:
            SlackAuthError: If authentication fails
        """
        return self._make_request("POST", "auth.test")

    def close(self):
        """Close the HTTP client."""
        self.client.close()
