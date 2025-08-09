"""
Slack SDK exceptions.

Custom exception classes for handling various Slack API errors
and authentication issues.
"""


class SlackAPIError(Exception):
    """Base exception for Slack API errors."""

    def __init__(self, message: str, error_code: str = None, response_data: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.response_data = response_data or {}


class SlackAuthError(SlackAPIError):
    """Exception for Slack authentication errors."""

    pass


class SlackRateLimitError(SlackAPIError):
    """Exception for Slack rate limit errors."""

    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class SlackChannelNotFoundError(SlackAPIError):
    """Exception for when Slack channel is not found."""

    pass


class SlackUserNotFoundError(SlackAPIError):
    """Exception for when Slack user is not found."""

    pass
