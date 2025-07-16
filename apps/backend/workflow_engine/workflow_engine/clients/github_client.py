"""
GitHub API client for workflow integrations.

This module provides a comprehensive client for GitHub REST API v4,
supporting repository operations, issue management, pull request creation,
and file operations with proper error handling and authentication.
"""

import base64
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from workflow_engine.clients.base_client import BaseAPIClient
from workflow_engine.models.credential import OAuth2Credential


logger = logging.getLogger(__name__)


class GitHubError(Exception):
    """GitHub specific error."""
    pass


class RepositoryNotFoundError(GitHubError):
    """Raised when specified repository is not found."""
    pass


class IssueNotFoundError(GitHubError):
    """Raised when specified issue is not found."""
    pass


class PullRequestNotFoundError(GitHubError):
    """Raised when specified pull request is not found."""
    pass


class FileNotFoundError(GitHubError):
    """Raised when specified file is not found."""
    pass


class InsufficientPermissionsError(GitHubError):
    """Raised when user lacks required permissions."""
    pass


class GitHubClient(BaseAPIClient):
    """
    GitHub REST API v4 client.
    
    Provides repository operations, issue management, pull request creation,
    and file operations with support for authentication and error handling.
    """
    
    def __init__(self, credentials: OAuth2Credential):
        """Initialize GitHub client."""
        if not credentials:
            raise ValueError("GitHub credentials are required")
        super().__init__(credentials)
    
    def _get_base_url(self) -> str:
        """Get GitHub API base URL."""
        return "https://api.github.com"
    
    def _get_service_name(self) -> str:
        """Get service name for logging."""
        return "GitHub"
    
    def _validate_repo_format(self, repo: str) -> None:
        """Validate repository format (owner/repo)."""
        if not repo or "/" not in repo:
            raise GitHubError(f"Invalid repository format: {repo}. Expected 'owner/repo'")
        
        parts = repo.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise GitHubError(f"Invalid repository format: {repo}. Expected 'owner/repo'")
    
    async def get_repository_info(self, repo: str) -> Dict[str, Any]:
        """
        Get repository information.
        
        Args:
            repo: Repository in format 'owner/repo'
            
        Returns:
            Repository information including name, description, stats, etc.
            
        Raises:
            GitHubError: If the request fails
            RepositoryNotFoundError: If repository doesn't exist
        """
        self._validate_repo_format(repo)
        
        try:
            endpoint = f"/repos/{repo}"
            response = await self._make_request("GET", endpoint)
            
            logger.info(f"Retrieved info for repository {repo}")
            return response
            
        except Exception as e:
            if "404" in str(e):
                raise RepositoryNotFoundError(f"Repository {repo} not found")
            logger.error(f"Failed to get repository info for {repo}: {e}")
            raise GitHubError(f"Failed to get repository info: {e}")
    
    async def create_issue(
        self, 
        repo: str, 
        title: str, 
        body: str = "", 
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new issue in the repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            title: Issue title
            body: Issue description (optional)
            labels: List of label names (optional)
            assignees: List of usernames to assign (optional)
            
        Returns:
            Created issue data with number, URL, etc.
            
        Raises:
            GitHubError: If issue creation fails
            RepositoryNotFoundError: If repository doesn't exist
            InsufficientPermissionsError: If user lacks permissions
        """
        self._validate_repo_format(repo)
        
        if not title.strip():
            raise GitHubError("Issue title cannot be empty")
        
        issue_data = {
            "title": title.strip(),
            "body": body
        }
        
        if labels:
            issue_data["labels"] = labels
        if assignees:
            issue_data["assignees"] = assignees
        
        try:
            endpoint = f"/repos/{repo}/issues"
            response = await self._make_request("POST", endpoint, json=issue_data)
            
            logger.info(f"Created issue #{response.get('number')} in {repo}: {title}")
            return response
            
        except Exception as e:
            if "404" in str(e):
                raise RepositoryNotFoundError(f"Repository {repo} not found")
            if "403" in str(e):
                raise InsufficientPermissionsError(f"Insufficient permissions to create issue in {repo}")
            logger.error(f"Failed to create issue in {repo}: {e}")
            raise GitHubError(f"Failed to create issue: {e}")
    
    async def create_pull_request(
        self, 
        repo: str, 
        title: str, 
        head: str, 
        base: str, 
        body: str = "",
        draft: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new pull request.
        
        Args:
            repo: Repository in format 'owner/repo'
            title: Pull request title
            head: The name of the branch where your changes are implemented
            base: The name of the branch you want the changes pulled into
            body: Pull request description (optional)
            draft: Whether to create as draft PR (optional)
            
        Returns:
            Created pull request data with number, URL, etc.
            
        Raises:
            GitHubError: If PR creation fails
            RepositoryNotFoundError: If repository doesn't exist
            InsufficientPermissionsError: If user lacks permissions
        """
        self._validate_repo_format(repo)
        
        if not title.strip():
            raise GitHubError("Pull request title cannot be empty")
        if not head.strip() or not base.strip():
            raise GitHubError("Both head and base branches must be specified")
        
        pr_data = {
            "title": title.strip(),
            "head": head.strip(),
            "base": base.strip(),
            "body": body,
            "draft": draft
        }
        
        try:
            endpoint = f"/repos/{repo}/pulls"
            response = await self._make_request("POST", endpoint, json=pr_data)
            
            logger.info(f"Created PR #{response.get('number')} in {repo}: {title}")
            return response
            
        except Exception as e:
            if "404" in str(e):
                raise RepositoryNotFoundError(f"Repository {repo} not found")
            if "403" in str(e):
                raise InsufficientPermissionsError(f"Insufficient permissions to create PR in {repo}")
            logger.error(f"Failed to create pull request in {repo}: {e}")
            raise GitHubError(f"Failed to create pull request: {e}")
    
    async def get_file_content(
        self, 
        repo: str, 
        path: str, 
        branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Get file content from repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            path: File path in repository
            branch: Branch name (default: "main")
            
        Returns:
            File content and metadata including SHA, content (base64), etc.
            
        Raises:
            GitHubError: If the request fails
            RepositoryNotFoundError: If repository doesn't exist
            FileNotFoundError: If file doesn't exist
        """
        self._validate_repo_format(repo)
        
        if not path.strip():
            raise GitHubError("File path cannot be empty")
        
        try:
            endpoint = f"/repos/{repo}/contents/{quote(path.strip(), safe='/')}"
            params = {"ref": branch}
            response = await self._make_request("GET", endpoint, params=params)
            
            # Decode base64 content if it's a file
            if response.get("type") == "file" and "content" in response:
                content = base64.b64decode(response["content"]).decode("utf-8", errors="ignore")
                response["decoded_content"] = content
            
            logger.info(f"Retrieved file {path} from {repo}:{branch}")
            return response
            
        except Exception as e:
            if "404" in str(e):
                raise FileNotFoundError(f"File {path} not found in {repo}:{branch}")
            logger.error(f"Failed to get file {path} from {repo}: {e}")
            raise GitHubError(f"Failed to get file content: {e}")
    
    async def create_file(
        self, 
        repo: str, 
        path: str, 
        content: str, 
        message: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Create a new file in repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            path: File path in repository
            content: File content (string)
            message: Commit message
            branch: Branch name (default: "main")
            
        Returns:
            Created file data with commit info, etc.
            
        Raises:
            GitHubError: If file creation fails
            RepositoryNotFoundError: If repository doesn't exist
            InsufficientPermissionsError: If user lacks permissions
        """
        self._validate_repo_format(repo)
        
        if not path.strip():
            raise GitHubError("File path cannot be empty")
        if not message.strip():
            raise GitHubError("Commit message cannot be empty")
        
        # Encode content to base64
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
        
        file_data = {
            "message": message.strip(),
            "content": encoded_content,
            "branch": branch
        }
        
        try:
            endpoint = f"/repos/{repo}/contents/{quote(path.strip(), safe='/')}"
            response = await self._make_request("PUT", endpoint, json=file_data)
            
            logger.info(f"Created file {path} in {repo}:{branch}")
            return response
            
        except Exception as e:
            if "404" in str(e):
                raise RepositoryNotFoundError(f"Repository {repo} not found")
            if "403" in str(e):
                raise InsufficientPermissionsError(f"Insufficient permissions to create file in {repo}")
            logger.error(f"Failed to create file {path} in {repo}: {e}")
            raise GitHubError(f"Failed to create file: {e}")
    
    async def update_file(
        self, 
        repo: str, 
        path: str, 
        content: str, 
        message: str,
        sha: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Update an existing file in repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            path: File path in repository
            content: New file content (string)
            message: Commit message
            sha: SHA of the file being updated
            branch: Branch name (default: "main")
            
        Returns:
            Updated file data with commit info, etc.
            
        Raises:
            GitHubError: If file update fails
            RepositoryNotFoundError: If repository doesn't exist
            FileNotFoundError: If file doesn't exist
            InsufficientPermissionsError: If user lacks permissions
        """
        self._validate_repo_format(repo)
        
        if not path.strip():
            raise GitHubError("File path cannot be empty")
        if not message.strip():
            raise GitHubError("Commit message cannot be empty")
        if not sha.strip():
            raise GitHubError("File SHA is required for updates")
        
        # Encode content to base64
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
        
        file_data = {
            "message": message.strip(),
            "content": encoded_content,
            "sha": sha.strip(),
            "branch": branch
        }
        
        try:
            endpoint = f"/repos/{repo}/contents/{quote(path.strip(), safe='/')}"
            response = await self._make_request("PUT", endpoint, json=file_data)
            
            logger.info(f"Updated file {path} in {repo}:{branch}")
            return response
            
        except Exception as e:
            if "404" in str(e):
                raise FileNotFoundError(f"File {path} not found in {repo}:{branch}")
            if "403" in str(e):
                raise InsufficientPermissionsError(f"Insufficient permissions to update file in {repo}")
            logger.error(f"Failed to update file {path} in {repo}: {e}")
            raise GitHubError(f"Failed to update file: {e}")
    
    async def search_repositories(
        self, 
        query: str, 
        limit: int = 10,
        sort: str = "updated"
    ) -> List[Dict[str, Any]]:
        """
        Search for repositories.
        
        Args:
            query: Search query (e.g., "python machine learning")
            limit: Maximum number of results (default: 10, max: 100)
            sort: Sort field ("stars", "forks", "updated") (default: "updated")
            
        Returns:
            List of repository objects matching the search
            
        Raises:
            GitHubError: If search fails
        """
        if not query.strip():
            raise GitHubError("Search query cannot be empty")
        
        limit = max(1, min(limit, 100))  # Enforce limits
        
        params = {
            "q": query.strip(),
            "per_page": limit,
            "sort": sort
        }
        
        try:
            endpoint = "/search/repositories"
            response = await self._make_request("GET", endpoint, params=params)
            
            repositories = response.get("items", [])
            logger.info(f"Found {len(repositories)} repositories for query: {query}")
            return repositories
            
        except Exception as e:
            logger.error(f"Failed to search repositories for query '{query}': {e}")
            raise GitHubError(f"Failed to search repositories: {e}")
    
    async def list_repository_issues(
        self, 
        repo: str, 
        state: str = "open",
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        List issues for a repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            state: Issue state ("open", "closed", "all") (default: "open")
            limit: Maximum number of issues (default: 30, max: 100)
            
        Returns:
            List of issue objects
            
        Raises:
            GitHubError: If the request fails
            RepositoryNotFoundError: If repository doesn't exist
        """
        self._validate_repo_format(repo)
        
        limit = max(1, min(limit, 100))  # Enforce limits
        
        params = {
            "state": state,
            "per_page": limit
        }
        
        try:
            endpoint = f"/repos/{repo}/issues"
            response = await self._make_request("GET", endpoint, params=params)
            
            logger.info(f"Retrieved {len(response)} issues for {repo}")
            return response
            
        except Exception as e:
            if "404" in str(e):
                raise RepositoryNotFoundError(f"Repository {repo} not found")
            logger.error(f"Failed to list issues for {repo}: {e}")
            raise GitHubError(f"Failed to list issues: {e}")
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None 