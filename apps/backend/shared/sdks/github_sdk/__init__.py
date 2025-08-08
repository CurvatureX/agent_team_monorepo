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
