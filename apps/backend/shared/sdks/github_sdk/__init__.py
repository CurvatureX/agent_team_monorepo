"""
GitHub SDK for AI Workflow Teams

This SDK provides comprehensive GitHub App integration capabilities including:
- Repository operations (read files, create branches, commit code)
- Pull request management (create, comment, review, merge)
- Issue management (create, comment, close, label)
- Authentication and token management
- Webhook utilities
"""

from .client import GitHubSDK
from .oauth2_client import GitHubOAuth2SDK
from .exceptions import (
    GitHubAuthError,
    GitHubError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
)
from .models import Branch, Commit, GitHubUser, Installation, Issue, PullRequest, Repository

# Export OAuth2SDK as the default GitHubSDK for workflow integration
GitHubSDK = GitHubOAuth2SDK

__version__ = "1.0.0"
__all__ = [
    "GitHubSDK",
    "GitHubOAuth2SDK", 
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
