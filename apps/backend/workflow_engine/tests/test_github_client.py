"""
Tests for GitHub API client.

This module tests the GitHubClient implementation including repository operations,
issue management, pull request creation, and file operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import base64
from datetime import datetime

from workflow_engine.clients.github_client import (
    GitHubClient,
    GitHubError,
    RepositoryNotFoundError,
    IssueNotFoundError,
    PullRequestNotFoundError,
    FileNotFoundError,
    InsufficientPermissionsError
)
from workflow_engine.models.credential import OAuth2Credential


@pytest.fixture
def mock_credentials():
    """Create mock OAuth2 credentials."""
    credentials = OAuth2Credential()
    credentials.access_token = "test_access_token"
    credentials.refresh_token = "test_refresh_token"
    credentials.expires_at = int((datetime.now().timestamp() + 3600))
    return credentials


@pytest.fixture
def github_client(mock_credentials):
    """Create GitHub client with mock credentials."""
    return GitHubClient(mock_credentials)


class TestGitHubClientInitialization:
    """Test GitHub client initialization."""
    
    def test_init_with_credentials(self, mock_credentials):
        """Test initialization with valid credentials."""
        client = GitHubClient(mock_credentials)
        assert client.credentials == mock_credentials
        assert client.base_url == "https://api.github.com"
    
    def test_init_without_credentials(self):
        """Test initialization without credentials raises error."""
        with pytest.raises(ValueError, match="GitHub credentials are required"):
            GitHubClient(None)
    
    def test_get_base_url(self, github_client):
        """Test base URL is correctly set."""
        assert github_client._get_base_url() == "https://api.github.com"
    
    def test_get_service_name(self, github_client):
        """Test service name is correctly set."""
        assert github_client._get_service_name() == "GitHub"


class TestRepositoryValidation:
    """Test repository format validation."""
    
    def test_validate_repo_format_valid(self, github_client):
        """Test valid repository format."""
        # Should not raise any exception
        github_client._validate_repo_format("owner/repo")
        github_client._validate_repo_format("microsoft/vscode")
    
    def test_validate_repo_format_invalid(self, github_client):
        """Test invalid repository format."""
        with pytest.raises(GitHubError, match="Invalid repository format"):
            github_client._validate_repo_format("invalid")
        
        with pytest.raises(GitHubError, match="Invalid repository format"):
            github_client._validate_repo_format("owner/")
        
        with pytest.raises(GitHubError, match="Invalid repository format"):
            github_client._validate_repo_format("/repo")
        
        with pytest.raises(GitHubError, match="Invalid repository format"):
            github_client._validate_repo_format("")


class TestRepositoryInfo:
    """Test repository information retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_repository_info_success(self, github_client):
        """Test successful repository info retrieval."""
        mock_response = {
            "id": 123456,
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "description": "Test repository",
            "private": False,
            "html_url": "https://github.com/owner/test-repo",
            "stargazers_count": 100,
            "forks_count": 25
        }
        
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await github_client.get_repository_info("owner/test-repo")
            
            assert result == mock_response
            mock_request.assert_called_once_with("GET", "/repos/owner/test-repo")
    
    @pytest.mark.asyncio
    async def test_get_repository_info_not_found(self, github_client):
        """Test repository not found error."""
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("404 Not Found")
            
            with pytest.raises(RepositoryNotFoundError, match="Repository owner/test-repo not found"):
                await github_client.get_repository_info("owner/test-repo")
    
    @pytest.mark.asyncio
    async def test_get_repository_info_invalid_format(self, github_client):
        """Test invalid repository format."""
        with pytest.raises(GitHubError, match="Invalid repository format"):
            await github_client.get_repository_info("invalid")


class TestIssueManagement:
    """Test issue creation and management."""
    
    @pytest.mark.asyncio
    async def test_create_issue_success(self, github_client):
        """Test successful issue creation."""
        mock_response = {
            "id": 1,
            "number": 42,
            "title": "Test Issue",
            "body": "Test description",
            "state": "open",
            "html_url": "https://github.com/owner/repo/issues/42",
            "created_at": "2025-01-20T10:00:00Z"
        }
        
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await github_client.create_issue(
                "owner/repo", 
                "Test Issue", 
                "Test description",
                labels=["bug", "enhancement"],
                assignees=["developer"]
            )
            
            assert result == mock_response
            mock_request.assert_called_once_with(
                "POST", 
                "/repos/owner/repo/issues",
                json={
                    "title": "Test Issue",
                    "body": "Test description",
                    "labels": ["bug", "enhancement"],
                    "assignees": ["developer"]
                }
            )
    
    @pytest.mark.asyncio
    async def test_create_issue_empty_title(self, github_client):
        """Test issue creation with empty title."""
        with pytest.raises(GitHubError, match="Issue title cannot be empty"):
            await github_client.create_issue("owner/repo", "", "Test description")
    
    @pytest.mark.asyncio
    async def test_create_issue_repository_not_found(self, github_client):
        """Test issue creation with non-existent repository."""
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("404 Not Found")
            
            with pytest.raises(RepositoryNotFoundError):
                await github_client.create_issue("owner/nonexistent", "Test Issue")
    
    @pytest.mark.asyncio
    async def test_create_issue_insufficient_permissions(self, github_client):
        """Test issue creation with insufficient permissions."""
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("403 Forbidden")
            
            with pytest.raises(InsufficientPermissionsError):
                await github_client.create_issue("owner/repo", "Test Issue")
    
    @pytest.mark.asyncio
    async def test_list_repository_issues_success(self, github_client):
        """Test successful issue listing."""
        mock_response = [
            {"id": 1, "number": 1, "title": "Issue 1", "state": "open"},
            {"id": 2, "number": 2, "title": "Issue 2", "state": "open"}
        ]
        
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await github_client.list_repository_issues("owner/repo", state="open", limit=30)
            
            assert result == mock_response
            mock_request.assert_called_once_with(
                "GET", 
                "/repos/owner/repo/issues",
                params={"state": "open", "per_page": 30}
            )


class TestPullRequestManagement:
    """Test pull request creation and management."""
    
    @pytest.mark.asyncio
    async def test_create_pull_request_success(self, github_client):
        """Test successful pull request creation."""
        mock_response = {
            "id": 1,
            "number": 123,
            "title": "Test PR",
            "body": "Test PR description",
            "state": "open",
            "head": {"ref": "feature-branch"},
            "base": {"ref": "main"},
            "html_url": "https://github.com/owner/repo/pull/123",
            "created_at": "2025-01-20T10:00:00Z"
        }
        
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await github_client.create_pull_request(
                "owner/repo",
                "Test PR",
                "feature-branch",
                "main",
                "Test PR description",
                draft=False
            )
            
            assert result == mock_response
            mock_request.assert_called_once_with(
                "POST",
                "/repos/owner/repo/pulls",
                json={
                    "title": "Test PR",
                    "head": "feature-branch",
                    "base": "main",
                    "body": "Test PR description",
                    "draft": False
                }
            )
    
    @pytest.mark.asyncio
    async def test_create_pull_request_empty_title(self, github_client):
        """Test PR creation with empty title."""
        with pytest.raises(GitHubError, match="Pull request title cannot be empty"):
            await github_client.create_pull_request("owner/repo", "", "head", "base")
    
    @pytest.mark.asyncio
    async def test_create_pull_request_empty_branches(self, github_client):
        """Test PR creation with empty branch names."""
        with pytest.raises(GitHubError, match="Both head and base branches must be specified"):
            await github_client.create_pull_request("owner/repo", "Test PR", "", "main")
        
        with pytest.raises(GitHubError, match="Both head and base branches must be specified"):
            await github_client.create_pull_request("owner/repo", "Test PR", "feature", "")


class TestFileOperations:
    """Test file content operations."""
    
    @pytest.mark.asyncio
    async def test_get_file_content_success(self, github_client):
        """Test successful file content retrieval."""
        file_content = "Hello, World!"
        encoded_content = base64.b64encode(file_content.encode("utf-8")).decode("ascii")
        
        mock_response = {
            "type": "file",
            "name": "README.md",
            "path": "README.md",
            "sha": "abc123",
            "content": encoded_content,
            "encoding": "base64"
        }
        
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await github_client.get_file_content("owner/repo", "README.md", "main")
            
            assert result["decoded_content"] == file_content
            assert result["content"] == encoded_content
            mock_request.assert_called_once_with(
                "GET",
                "/repos/owner/repo/contents/README.md",
                params={"ref": "main"}
            )
    
    @pytest.mark.asyncio
    async def test_get_file_content_not_found(self, github_client):
        """Test file not found error."""
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("404 Not Found")
            
            with pytest.raises(FileNotFoundError, match="File README.md not found in owner/repo:main"):
                await github_client.get_file_content("owner/repo", "README.md")
    
    @pytest.mark.asyncio
    async def test_create_file_success(self, github_client):
        """Test successful file creation."""
        file_content = "# New File\n\nThis is a new file."
        
        mock_response = {
            "content": {
                "name": "new-file.md",
                "path": "new-file.md",
                "sha": "def456"
            },
            "commit": {
                "sha": "abc123",
                "message": "Create new file"
            }
        }
        
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await github_client.create_file(
                "owner/repo",
                "new-file.md",
                file_content,
                "Create new file",
                "main"
            )
            
            assert result == mock_response
            # Verify the request was made with base64 encoded content
            call_args = mock_request.call_args
            assert call_args[0][0] == "PUT"
            assert call_args[0][1] == "/repos/owner/repo/contents/new-file.md"
            assert "content" in call_args[1]["json"]
            # Decode and verify the content
            decoded = base64.b64decode(call_args[1]["json"]["content"]).decode("utf-8")
            assert decoded == file_content
    
    @pytest.mark.asyncio
    async def test_create_file_empty_path(self, github_client):
        """Test file creation with empty path."""
        with pytest.raises(GitHubError, match="File path cannot be empty"):
            await github_client.create_file("owner/repo", "", "content", "message")
    
    @pytest.mark.asyncio
    async def test_create_file_empty_message(self, github_client):
        """Test file creation with empty commit message."""
        with pytest.raises(GitHubError, match="Commit message cannot be empty"):
            await github_client.create_file("owner/repo", "file.txt", "content", "")
    
    @pytest.mark.asyncio
    async def test_update_file_success(self, github_client):
        """Test successful file update."""
        file_content = "# Updated File\n\nThis file has been updated."
        
        mock_response = {
            "content": {
                "name": "updated-file.md",
                "path": "updated-file.md",
                "sha": "new_sha"
            },
            "commit": {
                "sha": "new_commit_sha",
                "message": "Update file"
            }
        }
        
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await github_client.update_file(
                "owner/repo",
                "updated-file.md",
                file_content,
                "Update file",
                "old_sha",
                "main"
            )
            
            assert result == mock_response
            call_args = mock_request.call_args
            assert call_args[1]["json"]["sha"] == "old_sha"
    
    @pytest.mark.asyncio
    async def test_update_file_missing_sha(self, github_client):
        """Test file update without SHA."""
        with pytest.raises(GitHubError, match="File SHA is required for updates"):
            await github_client.update_file("owner/repo", "file.txt", "content", "message", "")


class TestRepositorySearch:
    """Test repository search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_repositories_success(self, github_client):
        """Test successful repository search."""
        mock_response = {
            "items": [
                {
                    "id": 1,
                    "name": "repo1",
                    "full_name": "owner/repo1",
                    "description": "First repository",
                    "stargazers_count": 100
                },
                {
                    "id": 2,
                    "name": "repo2",
                    "full_name": "owner/repo2",
                    "description": "Second repository",
                    "stargazers_count": 50
                }
            ]
        }
        
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await github_client.search_repositories("python machine learning", limit=10, sort="stars")
            
            assert result == mock_response["items"]
            mock_request.assert_called_once_with(
                "GET",
                "/search/repositories",
                params={
                    "q": "python machine learning",
                    "per_page": 10,
                    "sort": "stars"
                }
            )
    
    @pytest.mark.asyncio
    async def test_search_repositories_empty_query(self, github_client):
        """Test repository search with empty query."""
        with pytest.raises(GitHubError, match="Search query cannot be empty"):
            await github_client.search_repositories("")
    
    @pytest.mark.asyncio
    async def test_search_repositories_limit_enforcement(self, github_client):
        """Test repository search limit enforcement."""
        mock_response = {"items": []}
        
        with patch.object(github_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            # Test minimum limit
            await github_client.search_repositories("test", limit=0)
            call_args = mock_request.call_args
            assert call_args[1]["params"]["per_page"] == 1
            
            # Test maximum limit
            await github_client.search_repositories("test", limit=200)
            call_args = mock_request.call_args
            assert call_args[1]["params"]["per_page"] == 100


class TestClientCleanup:
    """Test client cleanup operations."""
    
    @pytest.mark.asyncio
    async def test_close_client(self, github_client):
        """Test client cleanup."""
        # Mock the HTTP client
        mock_http_client = AsyncMock()
        github_client._http_client = mock_http_client
        
        await github_client.close()
        
        mock_http_client.aclose.assert_called_once()
        assert github_client._http_client is None
    
    @pytest.mark.asyncio
    async def test_close_client_no_http_client(self, github_client):
        """Test client cleanup when no HTTP client exists."""
        github_client._http_client = None
        
        # Should not raise any exception
        await github_client.close()
        assert github_client._http_client is None 