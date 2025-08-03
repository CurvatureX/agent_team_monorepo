"""
GitHub API适配器测试
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
import json

from workflow_engine.services.api_adapters.github import GitHubAdapter
from workflow_engine.services.api_adapters.base import (
    ValidationError, 
    AuthenticationError, 
    TemporaryError,
    OAuth2Config
)


@pytest.mark.unit
class TestGitHubAdapter:
    """GitHub适配器单元测试"""
    
    @pytest.fixture
    def adapter(self):
        """创建GitHub适配器实例"""
        return GitHubAdapter()
    
    @pytest.fixture
    def valid_credentials_oauth(self):
        """有效的GitHub OAuth凭证"""
        return {
            "access_token": "gho_test_github_access_token_12345"
        }
    
    @pytest.fixture
    def valid_credentials_pat(self):
        """有效的GitHub Personal Access Token凭证"""
        return {
            "api_key": "ghp_test_github_personal_access_token_12345"
        }
    
    @pytest.fixture
    def sample_repo_data(self):
        """示例仓库数据"""
        return {
            "name": "test-repo",
            "description": "A test repository for GitHub integration",
            "private": False,
            "has_issues": True,
            "has_projects": True,
            "has_wiki": True
        }
    
    def test_adapter_initialization(self, adapter):
        """测试：适配器初始化"""
        assert adapter.provider_name == "github"
        assert adapter.BASE_URL == "https://api.github.com"
        assert "list_repos" in adapter.OPERATIONS
        assert "create_issue" in adapter.OPERATIONS
        assert "create_pull_request" in adapter.OPERATIONS
    
    def test_oauth2_config(self, adapter):
        """测试：OAuth2配置"""
        config = adapter.get_oauth2_config()
        
        assert isinstance(config, OAuth2Config)
        assert config.auth_url == "https://github.com/login/oauth/authorize"
        assert config.token_url == "https://github.com/login/oauth/access_token"
        assert "repo" in config.scopes
        assert "issues" in config.scopes
    
    def test_validate_credentials_oauth_valid(self, adapter, valid_credentials_oauth):
        """测试：有效OAuth凭证验证"""
        assert adapter.validate_credentials(valid_credentials_oauth) is True
    
    def test_validate_credentials_pat_valid(self, adapter, valid_credentials_pat):
        """测试：有效PAT凭证验证"""
        assert adapter.validate_credentials(valid_credentials_pat) is True
    
    def test_validate_credentials_invalid(self, adapter):
        """测试：无效凭证验证"""
        # 缺少access_token和api_key
        invalid_creds = {"refresh_token": "refresh_123"}
        assert adapter.validate_credentials(invalid_creds) is False
        
        # 空credentials
        empty_creds = {"access_token": "", "api_key": ""}
        assert adapter.validate_credentials(empty_creds) is False
    
    def test_get_supported_operations(self, adapter):
        """测试：获取支持的操作"""
        operations = adapter.get_supported_operations()
        
        expected_operations = [
            "list_repos", "create_repo", "get_repo",
            "list_issues", "create_issue", "update_issue",
            "list_pull_requests", "create_pull_request",
            "create_webhook", "search_repositories", "get_user"
        ]
        
        for op in expected_operations:
            assert op in operations
    
    def test_get_operation_description(self, adapter):
        """测试：获取操作描述"""
        description = adapter.get_operation_description("list_repos")
        assert description == "列出用户或组织的仓库"
        
        # 不存在的操作
        assert adapter.get_operation_description("nonexistent") is None
    
    def test_prepare_api_key_headers_pat(self, adapter, valid_credentials_pat):
        """测试：准备PAT认证头部"""
        headers = adapter._prepare_api_key_headers(valid_credentials_pat)
        assert headers["Authorization"] == "token ghp_test_github_personal_access_token_12345"
    
    @pytest.mark.asyncio
    async def test_call_unsupported_operation(self, adapter, valid_credentials_oauth):
        """测试：调用不支持的操作"""
        with pytest.raises(ValidationError, match="Unsupported operation"):
            await adapter.call("unsupported_op", {}, valid_credentials_oauth)
    
    @pytest.mark.asyncio
    async def test_call_invalid_credentials(self, adapter):
        """测试：使用无效凭证调用"""
        invalid_creds = {"invalid": "credentials"}
        
        with pytest.raises(ValidationError, match="Invalid credentials"):
            await adapter.call("list_repos", {}, invalid_creds)


@pytest.mark.unit
class TestGitHubRepositories:
    """GitHub仓库操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return GitHubAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"access_token": "gho_test_token"}
    
    @pytest.fixture
    def mock_http_response(self):
        """Mock HTTP响应"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        return mock_response
    
    @pytest.mark.asyncio
    async def test_list_repos_user(self, adapter, valid_credentials, mock_http_response):
        """测试：列出用户仓库"""
        # Mock响应数据
        mock_http_response.json.return_value = [
            {
                "id": 123456,
                "name": "repo1",
                "full_name": "user/repo1",
                "description": "Test repository 1",
                "private": False
            },
            {
                "id": 123457,
                "name": "repo2",
                "full_name": "user/repo2",
                "description": "Test repository 2",
                "private": True
            }
        ]
        
        with patch.object(adapter, 'make_http_request', return_value=mock_http_response):
            result = await adapter.call("list_repos", {}, valid_credentials)
        
        assert result["success"] is True
        assert len(result["repositories"]) == 2
        assert result["total_count"] == 2
    
    @pytest.mark.asyncio
    async def test_list_repos_with_filters(self, adapter, valid_credentials, mock_http_response):
        """测试：带过滤条件的仓库列表"""
        mock_http_response.json.return_value = []
        
        parameters = {
            "owner": "testuser",
            "type": "owner",
            "sort": "updated",
            "direction": "desc",
            "per_page": 50
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_http_response) as mock_request:
            await adapter.call("list_repos", parameters, valid_credentials)
            
            # 验证请求URL包含正确的查询参数
            args, kwargs = mock_request.call_args
            url = args[1]  # 第二个参数是URL
            
            assert "users/testuser/repos" in url
            assert "type=owner" in url
            assert "sort=updated" in url
            assert "direction=desc" in url
            assert "per_page=50" in url
    
    @pytest.mark.asyncio
    async def test_create_repo_basic(self, adapter, valid_credentials, mock_http_response):
        """测试：创建基本仓库"""
        mock_http_response.json.return_value = {
            "id": 123456,
            "name": "new-repo",
            "full_name": "user/new-repo",
            "clone_url": "https://github.com/user/new-repo.git",
            "html_url": "https://github.com/user/new-repo"
        }
        
        parameters = {
            "name": "new-repo",
            "description": "A new test repository",
            "private": False
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_http_response) as mock_request:
            result = await adapter.call("create_repo", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["repo_id"] == 123456
        assert result["clone_url"] == "https://github.com/user/new-repo.git"
        
        # 验证请求数据
        args, kwargs = mock_request.call_args
        assert kwargs["json_data"]["name"] == "new-repo"
        assert kwargs["json_data"]["description"] == "A new test repository"
        assert kwargs["json_data"]["private"] is False
    
    @pytest.mark.asyncio
    async def test_create_repo_missing_name(self, adapter, valid_credentials):
        """测试：创建仓库缺少必需参数"""
        parameters = {
            "description": "Repository without name"
        }
        
        with pytest.raises(ValidationError, match="Missing required parameter: name"):
            await adapter.call("create_repo", parameters, valid_credentials)
    
    @pytest.mark.asyncio
    async def test_create_org_repo(self, adapter, valid_credentials, mock_http_response):
        """测试：创建组织仓库"""
        mock_http_response.json.return_value = {"id": 123456, "name": "org-repo"}
        
        parameters = {
            "name": "org-repo",
            "org": "test-org",
            "description": "Organization repository"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_http_response) as mock_request:
            await adapter.call("create_repo", parameters, valid_credentials)
        
        # 验证URL是组织仓库端点
        args, kwargs = mock_request.call_args
        url = args[1]
        assert "orgs/test-org/repos" in url
    
    @pytest.mark.asyncio
    async def test_get_repo(self, adapter, valid_credentials, mock_http_response):
        """测试：获取仓库详情"""
        mock_http_response.json.return_value = {
            "id": 123456,
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "description": "Test repository",
            "stargazers_count": 42,
            "forks_count": 10
        }
        
        parameters = {
            "owner": "owner",
            "repo": "test-repo"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_http_response):
            result = await adapter.call("get_repo", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["repository"]["name"] == "test-repo"
        assert result["repository"]["stargazers_count"] == 42
    
    @pytest.mark.asyncio
    async def test_get_repo_missing_parameters(self, adapter, valid_credentials):
        """测试：获取仓库缺少参数"""
        parameters = {"owner": "owner"}  # 缺少repo
        
        with pytest.raises(ValidationError, match="Missing required parameters: owner and repo"):
            await adapter.call("get_repo", parameters, valid_credentials)


@pytest.mark.unit
class TestGitHubIssues:
    """GitHub问题操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return GitHubAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"access_token": "gho_test_token"}
    
    @pytest.mark.asyncio
    async def test_list_issues(self, adapter, valid_credentials):
        """测试：列出问题"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = [
            {
                "id": 1,
                "number": 1,
                "title": "Bug report",
                "state": "open",
                "labels": [{"name": "bug"}]
            },
            {
                "id": 2,
                "number": 2,
                "title": "Feature request", 
                "state": "closed",
                "labels": [{"name": "enhancement"}]
            }
        ]
        
        parameters = {
            "owner": "owner",
            "repo": "repo"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.call("list_issues", parameters, valid_credentials)
        
        assert result["success"] is True
        assert len(result["issues"]) == 2
        assert result["total_count"] == 2
    
    @pytest.mark.asyncio
    async def test_list_issues_with_filters(self, adapter, valid_credentials):
        """测试：带过滤条件的问题列表"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = []
        
        parameters = {
            "owner": "owner",
            "repo": "repo",
            "state": "open",
            "labels": ["bug", "critical"],
            "sort": "created",
            "direction": "desc"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            await adapter.call("list_issues", parameters, valid_credentials)
            
            # 验证请求URL包含正确的查询参数
            args, kwargs = mock_request.call_args
            url = args[1]
            
            assert "repos/owner/repo/issues" in url
            assert "state=open" in url
            assert "labels=bug%2Ccritical" in url
            assert "sort=created" in url
            assert "direction=desc" in url
    
    @pytest.mark.asyncio
    async def test_create_issue(self, adapter, valid_credentials):
        """测试：创建问题"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": 123,
            "number": 10,
            "title": "New Bug Report",
            "html_url": "https://github.com/owner/repo/issues/10"
        }
        
        parameters = {
            "owner": "owner",
            "repo": "repo",
            "title": "New Bug Report",
            "body": "Description of the bug",
            "labels": ["bug", "needs-triage"],
            "assignees": ["maintainer1"]
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("create_issue", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["issue_number"] == 10
        assert result["html_url"] == "https://github.com/owner/repo/issues/10"
        
        # 验证请求数据
        json_data = mock_request.call_args[1]["json_data"]
        assert json_data["title"] == "New Bug Report"
        assert json_data["body"] == "Description of the bug"
        assert json_data["labels"] == ["bug", "needs-triage"]
        assert json_data["assignees"] == ["maintainer1"]
    
    @pytest.mark.asyncio
    async def test_create_issue_missing_title(self, adapter, valid_credentials):
        """测试：创建问题缺少标题"""
        parameters = {
            "owner": "owner",
            "repo": "repo",
            "body": "Issue without title"
        }
        
        with pytest.raises(ValidationError, match="Missing required parameters: owner, repo, and title"):
            await adapter.call("create_issue", parameters, valid_credentials)
    
    @pytest.mark.asyncio
    async def test_update_issue(self, adapter, valid_credentials):
        """测试：更新问题"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": 123,
            "number": 10,
            "title": "Updated Bug Report",
            "state": "closed"
        }
        
        parameters = {
            "owner": "owner",
            "repo": "repo",
            "issue_number": 10,
            "title": "Updated Bug Report",
            "state": "closed"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("update_issue", parameters, valid_credentials)
        
        assert result["success"] is True
        assert "title" in result["updated_fields"]
        assert "state" in result["updated_fields"]
        
        # 验证请求方法和URL
        args, kwargs = mock_request.call_args
        assert args[0] == "PATCH"
        assert "issues/10" in args[1]
    
    @pytest.mark.asyncio
    async def test_close_issue(self, adapter, valid_credentials):
        """测试：关闭问题"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": 123,
            "number": 10,
            "state": "closed"
        }
        
        parameters = {
            "owner": "owner",
            "repo": "repo", 
            "issue_number": 10
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("close_issue", parameters, valid_credentials)
        
        assert result["success"] is True
        
        # 验证close_issue实际上调用了update_issue with state=closed
        json_data = mock_request.call_args[1]["json_data"]
        assert json_data["state"] == "closed"


@pytest.mark.unit
class TestGitHubPullRequests:
    """GitHub拉取请求操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return GitHubAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"access_token": "gho_test_token"}
    
    @pytest.mark.asyncio
    async def test_list_pull_requests(self, adapter, valid_credentials):
        """测试：列出拉取请求"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = [
            {
                "id": 1,
                "number": 1,
                "title": "Feature: Add new functionality",
                "state": "open",
                "head": {"ref": "feature-branch"},
                "base": {"ref": "main"}
            }
        ]
        
        parameters = {
            "owner": "owner",
            "repo": "repo"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.call("list_pull_requests", parameters, valid_credentials)
        
        assert result["success"] is True
        assert len(result["pull_requests"]) == 1
        assert result["total_count"] == 1
    
    @pytest.mark.asyncio
    async def test_create_pull_request(self, adapter, valid_credentials):
        """测试：创建拉取请求"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": 123,
            "number": 5,
            "title": "New Feature PR",
            "html_url": "https://github.com/owner/repo/pull/5"
        }
        
        parameters = {
            "owner": "owner",
            "repo": "repo",
            "title": "New Feature PR",
            "head": "feature-branch",
            "base": "main",
            "body": "This PR adds a new feature"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("create_pull_request", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["pr_number"] == 5
        assert result["html_url"] == "https://github.com/owner/repo/pull/5"
        
        # 验证请求数据
        json_data = mock_request.call_args[1]["json_data"]
        assert json_data["title"] == "New Feature PR"
        assert json_data["head"] == "feature-branch"
        assert json_data["base"] == "main"
        assert json_data["body"] == "This PR adds a new feature"
    
    @pytest.mark.asyncio
    async def test_create_pull_request_missing_params(self, adapter, valid_credentials):
        """测试：创建拉取请求缺少参数"""
        parameters = {
            "owner": "owner",
            "repo": "repo",
            "title": "PR without branches"
        }
        
        with pytest.raises(ValidationError, match="Missing required parameters"):
            await adapter.call("create_pull_request", parameters, valid_credentials)


@pytest.mark.unit
class TestGitHubWebhooks:
    """GitHub Webhook操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return GitHubAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"access_token": "gho_test_token"}
    
    @pytest.mark.asyncio
    async def test_create_webhook(self, adapter, valid_credentials):
        """测试：创建Webhook"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": 12345,
            "name": "web",
            "config": {
                "url": "https://myapp.com/webhook",
                "content_type": "json"
            },
            "ping_url": "https://api.github.com/repos/owner/repo/hooks/12345/pings"
        }
        
        parameters = {
            "owner": "owner",
            "repo": "repo",
            "url": "https://myapp.com/webhook",
            "events": ["push", "pull_request"],
            "secret": "webhook_secret"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("create_webhook", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["webhook_id"] == 12345
        assert result["ping_url"] == "https://api.github.com/repos/owner/repo/hooks/12345/pings"
        
        # 验证请求数据
        json_data = mock_request.call_args[1]["json_data"]
        assert json_data["name"] == "web"
        assert json_data["config"]["url"] == "https://myapp.com/webhook"
        assert json_data["config"]["secret"] == "webhook_secret"
        assert json_data["events"] == ["push", "pull_request"]
    
    @pytest.mark.asyncio
    async def test_create_webhook_missing_url(self, adapter, valid_credentials):
        """测试：创建Webhook缺少URL"""
        parameters = {
            "owner": "owner",
            "repo": "repo"
        }
        
        with pytest.raises(ValidationError, match="Missing required parameters: owner, repo, and url"):
            await adapter.call("create_webhook", parameters, valid_credentials)


@pytest.mark.unit
class TestGitHubSearch:
    """GitHub搜索操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return GitHubAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"access_token": "gho_test_token"}
    
    @pytest.mark.asyncio
    async def test_search_repositories(self, adapter, valid_credentials):
        """测试：搜索仓库"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "total_count": 2,
            "incomplete_results": False,
            "items": [
                {
                    "id": 1,
                    "name": "test-repo",
                    "full_name": "owner/test-repo",
                    "stargazers_count": 10
                },
                {
                    "id": 2,
                    "name": "another-repo",
                    "full_name": "owner2/another-repo",
                    "stargazers_count": 5
                }
            ]
        }
        
        parameters = {
            "q": "test language:python",
            "sort": "stars",
            "order": "desc"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("search_repositories", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["total_count"] == 2
        assert result["incomplete_results"] is False
        assert len(result["repositories"]) == 2
        
        # 验证请求URL
        args, kwargs = mock_request.call_args
        url = args[1]
        assert "search/repositories" in url
        assert "q=test+language%3Apython" in url
        assert "sort=stars" in url
        assert "order=desc" in url
    
    @pytest.mark.asyncio
    async def test_search_issues(self, adapter, valid_credentials):
        """测试：搜索问题"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "total_count": 1,
            "incomplete_results": False,
            "items": [
                {
                    "id": 1,
                    "number": 42,
                    "title": "Bug in search feature",
                    "state": "open"
                }
            ]
        }
        
        parameters = {
            "q": "bug is:open repo:owner/repo"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.call("search_issues", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["total_count"] == 1
        assert len(result["issues"]) == 1
    
    @pytest.mark.asyncio
    async def test_search_missing_query(self, adapter, valid_credentials):
        """测试：搜索缺少查询参数"""
        parameters = {"sort": "stars"}
        
        with pytest.raises(ValidationError, match="Missing required parameter: q"):
            await adapter.call("search_repositories", parameters, valid_credentials)


@pytest.mark.unit
class TestGitHubUsers:
    """GitHub用户操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return GitHubAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"access_token": "gho_test_token"}
    
    @pytest.mark.asyncio
    async def test_get_authenticated_user(self, adapter, valid_credentials):
        """测试：获取认证用户信息"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": 123456,
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "public_repos": 10,
            "followers": 5
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.call("get_authenticated_user", {}, valid_credentials)
        
        assert result["success"] is True
        assert result["user"]["login"] == "testuser"
        assert result["user"]["id"] == 123456
    
    @pytest.mark.asyncio
    async def test_get_user(self, adapter, valid_credentials):
        """测试：获取指定用户信息"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": 654321,
            "login": "otheruser",
            "name": "Other User",
            "public_repos": 20
        }
        
        parameters = {"username": "otheruser"}
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("get_user", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["user"]["login"] == "otheruser"
        
        # 验证请求URL
        args, kwargs = mock_request.call_args
        url = args[1]
        assert "users/otheruser" in url
    
    @pytest.mark.asyncio
    async def test_get_user_missing_username(self, adapter, valid_credentials):
        """测试：获取用户缺少用户名"""
        parameters = {}
        
        with pytest.raises(ValidationError, match="Missing required parameter: username"):
            await adapter.call("get_user", parameters, valid_credentials)


@pytest.mark.integration
class TestGitHubIntegration:
    """GitHub适配器集成测试"""
    
    @pytest.mark.asyncio
    async def test_connection_test_success(self):
        """测试：连接测试成功"""
        adapter = GitHubAdapter()
        valid_credentials = {"access_token": "valid_token"}
        
        # Mock成功的API响应
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": 123456,
            "login": "testuser"
        }
        mock_response.headers = {"X-OAuth-Scopes": "repo, user"}
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.test_connection(valid_credentials)
        
        assert result["success"] is True
        assert result["provider"] == "github"
        assert "github_access" in result["details"]
        assert result["details"]["username"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_connection_test_failure(self):
        """测试：连接测试失败"""
        adapter = GitHubAdapter()
        invalid_credentials = {"access_token": "invalid_token"}
        
        # Mock失败的API响应
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 401
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            with patch.object(adapter, '_handle_http_error', side_effect=AuthenticationError("Invalid token")):
                result = await adapter.test_connection(invalid_credentials)
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_context_manager_usage(self):
        """测试：上下文管理器使用"""
        valid_credentials = {"access_token": "test_token"}
        
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = []
        
        async with GitHubAdapter() as adapter:
            with patch.object(adapter, 'make_http_request', return_value=mock_response):
                result = await adapter.call("list_repos", {}, valid_credentials)
                assert result["success"] is True
        
        # 验证HTTP客户端已关闭
        assert adapter._client is None