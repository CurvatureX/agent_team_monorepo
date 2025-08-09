"""GitHub SDK data models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    """GitHub user model."""

    id: int
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: str
    html_url: str
    type: str  # "User", "Bot", "Organization"


class Repository(BaseModel):
    """GitHub repository model."""

    id: int
    name: str
    full_name: str
    description: Optional[str] = None
    private: bool
    owner: GitHubUser
    html_url: str
    clone_url: str
    ssh_url: str
    default_branch: str
    language: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    size: int
    stargazers_count: int
    watchers_count: int
    forks_count: int
    open_issues_count: int


class Branch(BaseModel):
    """GitHub branch model."""

    name: str
    commit_sha: str
    protected: bool = False


class Commit(BaseModel):
    """GitHub commit model."""

    sha: str
    message: str
    author: GitHubUser
    committer: GitHubUser
    parents: List[str] = Field(default_factory=list)
    stats: Optional[Dict[str, int]] = None
    files: List[Dict[str, Any]] = Field(default_factory=list)
    html_url: str
    created_at: datetime


class PullRequest(BaseModel):
    """GitHub pull request model."""

    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str  # "open", "closed"
    draft: bool = False
    merged: bool = False
    mergeable: Optional[bool] = None
    author: GitHubUser
    assignees: List[GitHubUser] = Field(default_factory=list)
    reviewers: List[GitHubUser] = Field(default_factory=list)
    head_branch: str
    head_sha: str
    base_branch: str
    base_sha: str
    html_url: str
    diff_url: str
    patch_url: str
    commits: int
    additions: int
    deletions: int
    changed_files: int
    labels: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    merged_at: Optional[datetime] = None


class Issue(BaseModel):
    """GitHub issue model."""

    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str  # "open", "closed"
    author: GitHubUser
    assignees: List[GitHubUser] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)
    milestone: Optional[str] = None
    comments: int
    html_url: str
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None


class Comment(BaseModel):
    """GitHub comment model."""

    id: int
    body: str
    author: GitHubUser
    html_url: str
    created_at: datetime
    updated_at: datetime


class Installation(BaseModel):
    """GitHub App installation model."""

    id: int
    account: GitHubUser
    repository_selection: str  # "selected" or "all"
    permissions: Dict[str, str]
    events: List[str]
    created_at: datetime
    updated_at: datetime
    suspended_at: Optional[datetime] = None


class FileContent(BaseModel):
    """GitHub file content model."""

    path: str
    content: str
    encoding: str
    size: int
    sha: str
    download_url: str


class TreeItem(BaseModel):
    """GitHub tree item model."""

    path: str
    mode: str
    type: str  # "blob", "tree"
    sha: str
    size: Optional[int] = None


class WebhookEvent(BaseModel):
    """GitHub webhook event model."""

    event_type: str
    action: Optional[str] = None
    installation_id: int
    repository: Repository
    sender: GitHubUser
    payload: Dict[str, Any]
    delivery_id: str
    signature: str
    timestamp: datetime
