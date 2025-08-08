"""GitHub SDK exceptions."""


class GitHubError(Exception):
    """Base exception for GitHub SDK errors."""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}


class GitHubAuthError(GitHubError):
    """Authentication or authorization error."""

    pass


class GitHubRateLimitError(GitHubError):
    """Rate limit exceeded error."""

    def __init__(self, message: str, reset_time: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.reset_time = reset_time


class GitHubNotFoundError(GitHubError):
    """Resource not found error."""

    pass


class GitHubPermissionError(GitHubError):
    """Permission denied error."""

    pass


class GitHubValidationError(GitHubError):
    """Data validation error."""

    pass


class GitHubWebhookError(GitHubError):
    """Webhook-related error."""

    pass
