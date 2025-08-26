"""
GitHub SDK for AI Workflow Teams

This SDK provides comprehensive GitHub OAuth2 integration capabilities including:
- Repository operations (read files, create branches, commit code)
- Pull request management (create, comment, review, merge)
- Issue management (create, comment, close, label)
- OAuth2 authentication and token management
"""

# Import OAuth2 client (no JWT dependency)
try:
    from .oauth2_client import GitHubOAuth2SDK

    GitHubSDK = GitHubOAuth2SDK
    _oauth2_available = True
except ImportError as e:
    GitHubSDK = None
    GitHubOAuth2SDK = None
    _oauth2_available = False

# Import GitHub App client (requires JWT dependency)
try:
    from .client import GitHubAppSDK

    _github_app_available = True
except ImportError as e:
    GitHubAppSDK = None
    _github_app_available = False

from .exceptions import (
    GitHubAuthError,
    GitHubError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
)
from .models import Branch, Commit, GitHubUser, Installation, Issue, PullRequest, Repository

__version__ = "1.0.0"
__all__ = [
    "GitHubSDK",
    "GitHubOAuth2SDK",
    "GitHubAppSDK",
    "GitHubError",
    "GitHubAuthError",
    "GitHubRateLimitError",
    "GitHubNotFoundError",
    "GitHubPermissionError",
    "Repository",
    "PullRequest",
    "Issue",
    "Commit",
    "Branch",
    "GitHubUser",
    "Installation",
]
