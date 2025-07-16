"""
End-to-end integration tests for GitHub tool.

This module tests the complete GitHub integration flow including:
- OAuth2 credential management
- GitHub API operations (Issues, PRs, files, repositories)
- Tool node execution
- Error handling and recovery
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from workflow_engine.clients.github_client import (
    GitHubClient,
    GitHubError,
    RepositoryNotFoundError,
    InsufficientPermissionsError,
    FileNotFoundError
)
from workflow_engine.services.credential_service import CredentialService
from workflow_engine.nodes.tool_node import ToolNodeExecutor
from workflow_engine.models.credential import OAuth2Credential
from workflow_engine.nodes.base import NodeExecutionContext


@pytest.fixture
def mock_valid_credentials():
    """Create valid mock OAuth2 credentials for GitHub."""
    credentials = OAuth2Credential()
    credentials.provider = "github"
    credentials.access_token = "test_github_token"
    credentials.refresh_token = "test_refresh_token"
    credentials.expires_at = int((datetime.now() + timedelta(hours=1)).timestamp())
    credentials.credential_data = {
        "token_type": "token",
        "scope": "repo read:user"
    }
    return credentials


@pytest.fixture
def mock_expired_credentials():
    """Create expired mock OAuth2 credentials."""
    credentials = OAuth2Credential()
    credentials.provider = "github"
    credentials.access_token = "expired_github_token"
    credentials.refresh_token = "test_refresh_token"
    credentials.expires_at = int((datetime.now() - timedelta(hours=1)).timestamp())
    return credentials


class TestGitHubE2E:
    """End-to-end tests for GitHub integration."""
    
    @pytest.mark.asyncio
    async def test_complete_issue_workflow(self, mock_valid_credentials):
        """Test complete issue workflow: create, list, comment."""
        
        # Mock GitHub API responses
        created_issue = {
            "id": 123456789,
            "number": 42,
            "title": "Test Issue",
            "body": "This is a test issue",
            "state": "open",
            "user": {"login": "testuser"},
            "html_url": "https://github.com/testuser/testrepo/issues/42",
            "created_at": "2025-01-20T10:00:00Z"
        }
        
        issues_list = [created_issue]
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            # Set up mock responses for different operations
            mock_request.side_effect = [
                created_issue,  # create_issue
                issues_list,    # list_repository_issues
            ]
            
            client = GitHubClient(mock_valid_credentials)
            
            # Test 1: Create issue
            result = await client.create_issue(
                repo="testuser/testrepo",
                title="Test Issue",
                body="This is a test issue",
                labels=["bug", "test"],
                assignees=["testuser"]
            )
            
            assert result["number"] == 42
            assert result["title"] == "Test Issue"
            assert result["state"] == "open"
            
            # Test 2: List repository issues
            issues = await client.list_repository_issues("testuser/testrepo")
            assert len(issues) == 1
            assert issues[0]["number"] == 42
            
            # Verify all API calls were made
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_pull_request_workflow(self, mock_valid_credentials):
        """Test pull request creation and management."""
        
        # Mock GitHub API responses
        created_pr = {
            "id": 987654321,
            "number": 123,
            "title": "Test Pull Request",
            "body": "This is a test PR",
            "state": "open",
            "head": {"ref": "feature-branch"},
            "base": {"ref": "main"},
            "user": {"login": "testuser"},
            "html_url": "https://github.com/testuser/testrepo/pull/123",
            "mergeable": True,
            "created_at": "2025-01-20T11:00:00Z"
        }
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            mock_request.return_value = created_pr
            
            client = GitHubClient(mock_valid_credentials)
            
            # Create pull request
            result = await client.create_pull_request(
                repo="testuser/testrepo",
                title="Test Pull Request",
                head="feature-branch",
                base="main",
                body="This is a test PR",
                draft=False
            )
            
            assert result["number"] == 123
            assert result["title"] == "Test Pull Request"
            assert result["head"]["ref"] == "feature-branch"
            assert result["base"]["ref"] == "main"
            assert result["mergeable"] == True
            
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_file_operations_workflow(self, mock_valid_credentials):
        """Test complete file operations: create, read, update."""
        
        import base64
        
        # Mock file content
        file_content = "# Test README\nThis is a test file."
        encoded_content = base64.b64encode(file_content.encode()).decode()
        
        # Mock GitHub API responses
        file_creation_response = {
            "content": {
                "name": "README.md",
                "path": "README.md",
                "sha": "abc123sha",
                "size": len(file_content),
                "url": "https://api.github.com/repos/testuser/testrepo/contents/README.md",
                "html_url": "https://github.com/testuser/testrepo/blob/main/README.md",
                "download_url": "https://raw.githubusercontent.com/testuser/testrepo/main/README.md"
            },
            "commit": {
                "sha": "def456commit",
                "message": "Create README.md"
            }
        }
        
        file_content_response = {
            "name": "README.md",
            "path": "README.md",
            "sha": "abc123sha",
            "size": len(file_content),
            "type": "file",
            "content": encoded_content,
            "encoding": "base64"
        }
        
        updated_file_response = {
            **file_creation_response,
            "commit": {"sha": "ghi789commit", "message": "Update README.md"}
        }
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            mock_request.side_effect = [
                file_creation_response,  # create_file
                file_content_response,   # get_file_content
                updated_file_response    # update_file
            ]
            
            client = GitHubClient(mock_valid_credentials)
            
            # Test 1: Create file
            result = await client.create_file(
                repo="testuser/testrepo",
                path="README.md",
                content=file_content,
                message="Create README.md",
                branch="main"
            )
            
            assert result["content"]["name"] == "README.md"
            assert result["commit"]["message"] == "Create README.md"
            
            # Test 2: Get file content
            result = await client.get_file_content(
                repo="testuser/testrepo",
                path="README.md",
                branch="main"
            )
            
            assert result["name"] == "README.md"
            assert result["type"] == "file"
            assert "decoded_content" in result
            
            # Test 3: Update file
            updated_content = "# Updated README\nThis file has been updated."
            result = await client.update_file(
                repo="testuser/testrepo",
                path="README.md",
                content=updated_content,
                message="Update README.md",
                sha="abc123sha",
                branch="main"
            )
            
            assert result["commit"]["message"] == "Update README.md"
            
            # Verify all API calls were made
            assert mock_request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_repository_operations(self, mock_valid_credentials):
        """Test repository information and search operations."""
        
        # Mock repository info response
        repo_info = {
            "id": 123456789,
            "name": "testrepo",
            "full_name": "testuser/testrepo",
            "private": False,
            "description": "A test repository",
            "language": "Python",
            "stargazers_count": 42,
            "forks_count": 7,
            "open_issues_count": 3,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-20T12:00:00Z",
            "html_url": "https://github.com/testuser/testrepo",
            "clone_url": "https://github.com/testuser/testrepo.git"
        }
        
        # Mock search results
        search_results = [
            {
                "id": 111111111,
                "name": "python-project",
                "full_name": "user1/python-project",
                "description": "A Python project",
                "stargazers_count": 100
            },
            {
                "id": 222222222,
                "name": "machine-learning",
                "full_name": "user2/machine-learning",
                "description": "ML algorithms in Python",
                "stargazers_count": 250
            }
        ]
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            mock_request.side_effect = [
                repo_info,         # get_repository_info
                {"items": search_results}  # search_repositories
            ]
            
            client = GitHubClient(mock_valid_credentials)
            
            # Test 1: Get repository info
            result = await client.get_repository_info("testuser/testrepo")
            
            assert result["name"] == "testrepo"
            assert result["full_name"] == "testuser/testrepo"
            assert result["language"] == "Python"
            assert result["stargazers_count"] == 42
            
            # Test 2: Search repositories
            results = await client.search_repositories(
                query="python machine learning",
                limit=10,
                sort="stars"
            )
            
            assert len(results) == 2
            assert results[0]["name"] == "python-project"
            assert results[1]["stargazers_count"] == 250
            
            # Verify all API calls were made
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_tool_node_github_execution(self, mock_valid_credentials):
        """Test GitHub tool execution through ToolNodeExecutor."""
        
        # Mock credential service
        mock_credential_service = AsyncMock(spec=CredentialService)
        mock_credential_service.get_credential.return_value = mock_valid_credentials
        
        # Mock GitHub API response for issue creation
        api_response = {
            "id": 987654321,
            "number": 456,
            "title": "Tool Test Issue",
            "body": "Created via tool node",
            "state": "open",
            "html_url": "https://github.com/testuser/testrepo/issues/456"
        }
        
        with patch('workflow_engine.services.credential_service.CredentialService', return_value=mock_credential_service):
            with patch.object(GitHubClient, '_make_request', return_value=api_response) as mock_request:
                
                # Create mock execution context
                context = MagicMock(spec=NodeExecutionContext)
                context.get_parameter.side_effect = lambda key, default=None: {
                    "provider": "github",
                    "action": "create_issue",
                    "repository": "testuser/testrepo",
                    "user_id": "test_user"
                }.get(key, default)
                
                context.input_data = {
                    "title": "Tool Test Issue",
                    "body": "Created via tool node",
                    "labels": ["test"],
                    "assignees": []
                }
                
                # Execute tool
                executor = ToolNodeExecutor()
                result = executor._execute_github_tool(context, [], 0.0)
                
                # Verify result
                assert result.status.value == "SUCCESS"
                assert "tool_type" in result.output_data
                assert result.output_data["tool_type"] == "github"
                assert result.output_data["action"] == "create_issue"
                
                # Verify credential was retrieved
                mock_credential_service.get_credential.assert_called_once_with("test_user", "github")
                
                # Verify API was called
                mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_github_error_handling_and_retry(self, mock_valid_credentials):
        """Test error handling and retry mechanism for GitHub API."""
        
        # Mock initial failures followed by success
        responses = [
            Exception("500 Internal Server Error"),
            Exception("502 Bad Gateway"),
            {
                "id": 123456789,
                "number": 789,
                "title": "Retry Success Issue"
            }
        ]
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            mock_request.side_effect = responses
            
            client = GitHubClient(mock_valid_credentials)
            
            # This should retry and eventually succeed
            with patch('asyncio.sleep'):  # Speed up the test
                result = await client.create_issue(
                    repo="testuser/testrepo",
                    title="Retry Test Issue",
                    body="Testing retry mechanism"
                )
            
            assert result["number"] == 789
            assert result["title"] == "Retry Success Issue"
            assert mock_request.call_count == 3  # Should have retried 3 times
    
    @pytest.mark.asyncio
    async def test_concurrent_github_operations(self, mock_valid_credentials):
        """Test concurrent GitHub operations."""
        
        # Mock responses for concurrent operations
        mock_responses = [
            {"id": i, "number": i + 100, "title": f"Concurrent Issue {i}"}
            for i in range(5)
        ]
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            mock_request.side_effect = mock_responses
            
            client = GitHubClient(mock_valid_credentials)
            
            # Create multiple issues concurrently
            start_time = datetime.now()
            
            tasks = []
            for i in range(5):
                task = client.create_issue(
                    repo="testuser/testrepo",
                    title=f"Concurrent Issue {i}",
                    body=f"Issue created concurrently {i}"
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Verify all issues were created
            assert len(results) == 5
            for i, result in enumerate(results):
                assert result["number"] == i + 100
                assert f"Concurrent Issue {i}" in result["title"]
            
            # Concurrent execution should complete within reasonable time
            assert execution_time < 10.0
            assert mock_request.call_count == 5
    
    @pytest.mark.asyncio
    async def test_github_permissions_and_validation(self, mock_valid_credentials):
        """Test GitHub permissions and input validation."""
        
        client = GitHubClient(mock_valid_credentials)
        
        # Test invalid repository format
        with pytest.raises(GitHubError) as exc_info:
            await client.create_issue("invalid-repo-format", "Test", "Test")
        assert "Invalid repository format" in str(exc_info.value)
        
        # Test empty title
        with pytest.raises(GitHubError) as exc_info:
            await client.create_issue("user/repo", "", "Test body")
        assert "title cannot be empty" in str(exc_info.value)
        
        # Test empty commit message for file operations
        with pytest.raises(GitHubError) as exc_info:
            await client.create_file("user/repo", "test.txt", "content", "")
        assert "message cannot be empty" in str(exc_info.value)


class TestGitHubIntegrationErrors:
    """Test error scenarios and edge cases for GitHub integration."""
    
    @pytest.mark.asyncio
    async def test_repository_not_found_error(self, mock_valid_credentials):
        """Test handling of repository not found errors."""
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            mock_request.side_effect = Exception("404 Not Found")
            
            client = GitHubClient(mock_valid_credentials)
            
            with pytest.raises(RepositoryNotFoundError):
                await client.get_repository_info("nonexistent/repo")
    
    @pytest.mark.asyncio
    async def test_insufficient_permissions_error(self, mock_valid_credentials):
        """Test handling of insufficient permissions errors."""
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            mock_request.side_effect = Exception("403 Forbidden")
            
            client = GitHubClient(mock_valid_credentials)
            
            with pytest.raises(InsufficientPermissionsError):
                await client.create_issue("private/repo", "Test Issue", "Test body")
    
    @pytest.mark.asyncio
    async def test_file_not_found_error(self, mock_valid_credentials):
        """Test handling of file not found errors."""
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            mock_request.side_effect = Exception("404 Not Found")
            
            client = GitHubClient(mock_valid_credentials)
            
            with pytest.raises(FileNotFoundError):
                await client.get_file_content("user/repo", "nonexistent.txt")
    
    @pytest.mark.asyncio
    async def test_rate_limiting_handling(self, mock_valid_credentials):
        """Test handling of GitHub API rate limiting."""
        
        rate_limit_responses = [
            Exception("403 API rate limit exceeded"),
            Exception("403 API rate limit exceeded"),
            {"id": 123, "number": 1, "title": "Success after rate limit"}
        ]
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            mock_request.side_effect = rate_limit_responses
            
            client = GitHubClient(mock_valid_credentials)
            
            # Should eventually succeed after rate limit is lifted
            with patch('asyncio.sleep'):  # Speed up the test
                result = await client.create_issue(
                    repo="user/repo",
                    title="Rate Limit Test",
                    body="Testing rate limit handling"
                )
            
            assert result["title"] == "Success after rate limit"
            assert mock_request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_malformed_api_responses(self, mock_valid_credentials):
        """Test handling of malformed API responses."""
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            # Mock malformed response
            mock_request.return_value = {"unexpected": "format"}
            
            client = GitHubClient(mock_valid_credentials)
            
            # Should handle gracefully without crashing
            result = await client.create_issue("user/repo", "Test", "Test body")
            assert result == {"unexpected": "format"}
    
    @pytest.mark.asyncio
    async def test_network_connectivity_issues(self, mock_valid_credentials):
        """Test handling of network connectivity issues."""
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            mock_request.side_effect = Exception("Connection timeout")
            
            client = GitHubClient(mock_valid_credentials)
            
            with pytest.raises(GitHubError) as exc_info:
                await client.create_issue("user/repo", "Test", "Test body")
            
            assert "Connection timeout" in str(exc_info.value) 