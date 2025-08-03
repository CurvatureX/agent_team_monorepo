"""
GitHub API适配器
实现GitHub API的统一调用接口
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
import json

from .base import APIAdapter, OAuth2Config, PermanentError, TemporaryError, ValidationError, register_adapter

logger = logging.getLogger(__name__)


@register_adapter("github")
class GitHubAdapter(APIAdapter):
    """GitHub API适配器
    
    支持的操作:
    - list_repos: 列出仓库
    - create_repo: 创建仓库
    - get_repo: 获取仓库详情
    - list_issues: 列出问题
    - create_issue: 创建问题
    - update_issue: 更新问题
    - close_issue: 关闭问题
    - get_issue: 获取问题详情
    - list_pull_requests: 列出拉取请求
    - create_pull_request: 创建拉取请求
    - update_pull_request: 更新拉取请求
    - merge_pull_request: 合并拉取请求
    - get_pull_request: 获取拉取请求详情
    - list_commits: 列出提交
    - get_commit: 获取提交详情
    - create_webhook: 创建Webhook
    - list_webhooks: 列出Webhook
    - delete_webhook: 删除Webhook
    - get_user: 获取用户信息
    - list_organizations: 列出组织
    - search_repositories: 搜索仓库
    - search_issues: 搜索问题
    - search_users: 搜索用户
    """
    
    # GitHub API基础URL
    BASE_URL = "https://api.github.com"
    
    # 支持的操作定义
    OPERATIONS = {
        # 仓库操作
        "list_repos": "列出用户或组织的仓库",
        "create_repo": "创建新仓库",
        "get_repo": "获取仓库详情",
        "update_repo": "更新仓库设置",
        "delete_repo": "删除仓库",
        
        # 问题操作
        "list_issues": "列出仓库问题",
        "create_issue": "创建新问题",
        "update_issue": "更新问题",
        "close_issue": "关闭问题",
        "get_issue": "获取问题详情",
        "add_issue_comment": "添加问题评论",
        "list_issue_comments": "列出问题评论",
        
        # 拉取请求操作
        "list_pull_requests": "列出拉取请求",
        "create_pull_request": "创建拉取请求",
        "update_pull_request": "更新拉取请求",
        "merge_pull_request": "合并拉取请求",
        "get_pull_request": "获取拉取请求详情",
        
        # 提交操作
        "list_commits": "列出仓库提交",
        "get_commit": "获取提交详情",
        "compare_commits": "比较提交差异",
        
        # Webhook操作
        "create_webhook": "创建仓库Webhook",
        "list_webhooks": "列出仓库Webhook",
        "update_webhook": "更新Webhook",
        "delete_webhook": "删除Webhook",
        "ping_webhook": "测试Webhook",
        
        # 用户和组织
        "get_user": "获取用户信息",
        "get_authenticated_user": "获取认证用户信息",
        "list_organizations": "列出用户的组织",
        
        # 搜索操作
        "search_repositories": "搜索仓库",
        "search_issues": "搜索问题",
        "search_users": "搜索用户",
        "search_code": "搜索代码",
        
        # 分支和标签
        "list_branches": "列出分支",
        "get_branch": "获取分支详情",
        "create_branch": "创建分支",
        "list_tags": "列出标签",
        "get_tag": "获取标签详情",
        
        # 发布操作
        "list_releases": "列出发布版本",
        "create_release": "创建发布版本",
        "get_release": "获取发布版本详情",
        "update_release": "更新发布版本",
        "delete_release": "删除发布版本"
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.provider_name = "github"
    
    def get_oauth2_config(self) -> OAuth2Config:
        """获取GitHub OAuth2配置"""
        return OAuth2Config(
            client_id="",  # 将从环境变量或配置中加载
            client_secret="",  # 将从环境变量或配置中加载
            auth_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            revoke_url="https://api.github.com/applications/{client_id}/tokens/{access_token}",
            scopes=[
                "repo",           # 访问仓库
                "issues",         # 访问问题
                "pull_requests",  # 访问拉取请求
                "user",           # 访问用户信息
                "admin:repo_hook" # 管理Webhook
            ],
            redirect_uri="http://localhost:8000/auth/github/callback"
        )
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """验证GitHub凭证"""
        return ("access_token" in credentials and credentials["access_token"]) or \
               ("api_key" in credentials and credentials["api_key"])
    
    def _prepare_api_key_headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """准备GitHub API密钥认证头部"""
        if "api_key" in credentials:
            # GitHub personal access token
            return {"Authorization": f"token {credentials['api_key']}"}
        return super()._prepare_api_key_headers(credentials)
    
    async def call(self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """统一的API调用接口"""
        if not self.validate_credentials(credentials):
            raise ValidationError("Invalid credentials: missing access_token or api_key")
        
        if operation not in self.OPERATIONS:
            raise ValidationError(f"Unsupported operation: {operation}")
        
        # 根据操作类型分发到具体的处理方法
        handler_mapping = {
            # 仓库操作
            "list_repos": self._list_repos,
            "create_repo": self._create_repo,
            "get_repo": self._get_repo,
            "update_repo": self._update_repo,
            "delete_repo": self._delete_repo,
            
            # 问题操作
            "list_issues": self._list_issues,
            "create_issue": self._create_issue,
            "update_issue": self._update_issue,
            "close_issue": self._close_issue,
            "get_issue": self._get_issue,
            "add_issue_comment": self._add_issue_comment,
            "list_issue_comments": self._list_issue_comments,
            
            # 拉取请求操作
            "list_pull_requests": self._list_pull_requests,
            "create_pull_request": self._create_pull_request,
            "update_pull_request": self._update_pull_request,
            "merge_pull_request": self._merge_pull_request,
            "get_pull_request": self._get_pull_request,
            
            # 提交操作
            "list_commits": self._list_commits,
            "get_commit": self._get_commit,
            "compare_commits": self._compare_commits,
            
            # Webhook操作
            "create_webhook": self._create_webhook,
            "list_webhooks": self._list_webhooks,
            "update_webhook": self._update_webhook,
            "delete_webhook": self._delete_webhook,
            "ping_webhook": self._ping_webhook,
            
            # 用户和组织
            "get_user": self._get_user,
            "get_authenticated_user": self._get_authenticated_user,
            "list_organizations": self._list_organizations,
            
            # 搜索操作
            "search_repositories": self._search_repositories,
            "search_issues": self._search_issues,
            "search_users": self._search_users,
            "search_code": self._search_code,
            
            # 分支和标签
            "list_branches": self._list_branches,
            "get_branch": self._get_branch,
            "create_branch": self._create_branch,
            "list_tags": self._list_tags,
            "get_tag": self._get_tag,
            
            # 发布操作
            "list_releases": self._list_releases,
            "create_release": self._create_release,
            "get_release": self._get_release,
            "update_release": self._update_release,
            "delete_release": self._delete_release
        }
        
        handler = handler_mapping[operation]
        return await handler(parameters, credentials)
    
    # ========================================================================
    # 仓库操作
    # ========================================================================
    
    async def _list_repos(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出仓库"""
        # 构建URL
        owner = parameters.get("owner")
        if owner:
            # 列出指定用户或组织的仓库
            url = f"{self.BASE_URL}/users/{owner}/repos"
        else:
            # 列出认证用户的仓库
            url = f"{self.BASE_URL}/user/repos"
        
        # 构建查询参数
        query_params = {}
        if "type" in parameters:
            query_params["type"] = parameters["type"]  # all, owner, member
        if "sort" in parameters:
            query_params["sort"] = parameters["sort"]  # created, updated, pushed, full_name
        if "direction" in parameters:
            query_params["direction"] = parameters["direction"]  # asc, desc
        if "per_page" in parameters:
            query_params["per_page"] = min(int(parameters["per_page"]), 100)
        if "page" in parameters:
            query_params["page"] = int(parameters["page"])
        
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        repos = response.json()
        
        return {
            "success": True,
            "repositories": repos,
            "total_count": len(repos)
        }
    
    async def _create_repo(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建仓库"""
        if "name" not in parameters:
            raise ValidationError("Missing required parameter: name")
        
        # 构建仓库数据
        repo_data = {
            "name": parameters["name"]
        }
        
        # 可选参数
        optional_fields = [
            "description", "homepage", "private", "has_issues", "has_projects",
            "has_wiki", "is_template", "team_id", "auto_init", "gitignore_template",
            "license_template", "allow_squash_merge", "allow_merge_commit",
            "allow_rebase_merge", "delete_branch_on_merge"
        ]
        
        for field in optional_fields:
            if field in parameters:
                repo_data[field] = parameters[field]
        
        # 确定URL（组织仓库 vs 用户仓库）
        org = parameters.get("org")
        if org:
            url = f"{self.BASE_URL}/orgs/{org}/repos"
        else:
            url = f"{self.BASE_URL}/user/repos"
        
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("POST", url, headers=headers, json_data=repo_data)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        repo = response.json()
        
        return {
            "success": True,
            "repository": repo,
            "repo_id": repo.get("id"),
            "clone_url": repo.get("clone_url"),
            "html_url": repo.get("html_url")
        }
    
    async def _get_repo(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取仓库详情"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        
        if not owner or not repo:
            raise ValidationError("Missing required parameters: owner and repo")
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        repo_data = response.json()
        
        return {
            "success": True,
            "repository": repo_data
        }
    
    # ========================================================================
    # 问题操作
    # ========================================================================
    
    async def _list_issues(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出问题"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        
        if not owner or not repo:
            raise ValidationError("Missing required parameters: owner and repo")
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues"
        
        # 构建查询参数
        query_params = {}
        if "state" in parameters:
            query_params["state"] = parameters["state"]  # open, closed, all
        if "labels" in parameters:
            query_params["labels"] = ",".join(parameters["labels"])
        if "sort" in parameters:
            query_params["sort"] = parameters["sort"]  # created, updated, comments
        if "direction" in parameters:
            query_params["direction"] = parameters["direction"]  # asc, desc
        if "since" in parameters:
            query_params["since"] = parameters["since"]
        if "per_page" in parameters:
            query_params["per_page"] = min(int(parameters["per_page"]), 100)
        if "page" in parameters:
            query_params["page"] = int(parameters["page"])
        
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        issues = response.json()
        
        return {
            "success": True,
            "issues": issues,
            "total_count": len(issues)
        }
    
    async def _create_issue(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建问题"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        title = parameters.get("title")
        
        if not owner or not repo or not title:
            raise ValidationError("Missing required parameters: owner, repo, and title")
        
        # 构建问题数据
        issue_data = {
            "title": title
        }
        
        # 可选参数
        if "body" in parameters:
            issue_data["body"] = parameters["body"]
        if "assignees" in parameters:
            issue_data["assignees"] = parameters["assignees"]
        if "milestone" in parameters:
            issue_data["milestone"] = parameters["milestone"]
        if "labels" in parameters:
            issue_data["labels"] = parameters["labels"]
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues"
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("POST", url, headers=headers, json_data=issue_data)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        issue = response.json()
        
        return {
            "success": True,
            "issue": issue,
            "issue_number": issue.get("number"),
            "html_url": issue.get("html_url")
        }
    
    async def _update_issue(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """更新问题"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        issue_number = parameters.get("issue_number")
        
        if not owner or not repo or not issue_number:
            raise ValidationError("Missing required parameters: owner, repo, and issue_number")
        
        # 构建更新数据
        update_data = {}
        updateable_fields = ["title", "body", "state", "assignees", "milestone", "labels"]
        
        for field in updateable_fields:
            if field in parameters:
                update_data[field] = parameters[field]
        
        if not update_data:
            raise ValidationError("No fields to update specified")
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{issue_number}"
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("PATCH", url, headers=headers, json_data=update_data)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        issue = response.json()
        
        return {
            "success": True,
            "issue": issue,
            "updated_fields": list(update_data.keys())
        }
    
    async def _close_issue(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """关闭问题"""
        # 这是一个便捷方法，实际上调用update_issue
        close_params = parameters.copy()
        close_params["state"] = "closed"
        return await self._update_issue(close_params, credentials)
    
    # ========================================================================
    # 拉取请求操作
    # ========================================================================
    
    async def _list_pull_requests(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出拉取请求"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        
        if not owner or not repo:
            raise ValidationError("Missing required parameters: owner and repo")
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls"
        
        # 构建查询参数
        query_params = {}
        if "state" in parameters:
            query_params["state"] = parameters["state"]  # open, closed, all
        if "head" in parameters:
            query_params["head"] = parameters["head"]
        if "base" in parameters:
            query_params["base"] = parameters["base"]
        if "sort" in parameters:
            query_params["sort"] = parameters["sort"]  # created, updated, popularity
        if "direction" in parameters:
            query_params["direction"] = parameters["direction"]  # asc, desc
        if "per_page" in parameters:
            query_params["per_page"] = min(int(parameters["per_page"]), 100)
        if "page" in parameters:
            query_params["page"] = int(parameters["page"])
        
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        pull_requests = response.json()
        
        return {
            "success": True,
            "pull_requests": pull_requests,
            "total_count": len(pull_requests)
        }
    
    async def _create_pull_request(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建拉取请求"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        title = parameters.get("title")
        head = parameters.get("head")
        base = parameters.get("base")
        
        if not all([owner, repo, title, head, base]):
            raise ValidationError("Missing required parameters: owner, repo, title, head, and base")
        
        # 构建PR数据
        pr_data = {
            "title": title,
            "head": head,
            "base": base
        }
        
        # 可选参数
        if "body" in parameters:
            pr_data["body"] = parameters["body"]
        if "maintainer_can_modify" in parameters:
            pr_data["maintainer_can_modify"] = bool(parameters["maintainer_can_modify"])
        if "draft" in parameters:
            pr_data["draft"] = bool(parameters["draft"])
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls"
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("POST", url, headers=headers, json_data=pr_data)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        pull_request = response.json()
        
        return {
            "success": True,
            "pull_request": pull_request,
            "pr_number": pull_request.get("number"),
            "html_url": pull_request.get("html_url")
        }
    
    # ========================================================================
    # Webhook操作
    # ========================================================================
    
    async def _create_webhook(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建Webhook"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        url_param = parameters.get("url")
        
        if not owner or not repo or not url_param:
            raise ValidationError("Missing required parameters: owner, repo, and url")
        
        # 构建Webhook数据
        webhook_data = {
            "name": "web",
            "config": {
                "url": url_param,
                "content_type": parameters.get("content_type", "json")
            },
            "events": parameters.get("events", ["push"]),
            "active": parameters.get("active", True)
        }
        
        # 添加密钥如果提供
        if "secret" in parameters:
            webhook_data["config"]["secret"] = parameters["secret"]
        
        # 添加SSL验证设置
        if "insecure_ssl" in parameters:
            webhook_data["config"]["insecure_ssl"] = str(int(parameters["insecure_ssl"]))
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/hooks"
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("POST", url, headers=headers, json_data=webhook_data)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        webhook = response.json()
        
        return {
            "success": True,
            "webhook": webhook,
            "webhook_id": webhook.get("id"),
            "ping_url": webhook.get("ping_url")
        }
    
    # ========================================================================
    # 搜索操作
    # ========================================================================
    
    async def _search_repositories(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """搜索仓库"""
        query = parameters.get("q")
        if not query:
            raise ValidationError("Missing required parameter: q (search query)")
        
        url = f"{self.BASE_URL}/search/repositories"
        
        # 构建查询参数
        query_params = {"q": query}
        if "sort" in parameters:
            query_params["sort"] = parameters["sort"]  # stars, forks, updated
        if "order" in parameters:
            query_params["order"] = parameters["order"]  # asc, desc
        if "per_page" in parameters:
            query_params["per_page"] = min(int(parameters["per_page"]), 100)
        if "page" in parameters:
            query_params["page"] = int(parameters["page"])
        
        url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        search_results = response.json()
        
        return {
            "success": True,
            "total_count": search_results.get("total_count", 0),
            "incomplete_results": search_results.get("incomplete_results", False),
            "repositories": search_results.get("items", [])
        }
    
    async def _search_issues(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """搜索问题"""
        query = parameters.get("q")
        if not query:
            raise ValidationError("Missing required parameter: q (search query)")
        
        url = f"{self.BASE_URL}/search/issues"
        
        # 构建查询参数
        query_params = {"q": query}
        if "sort" in parameters:
            query_params["sort"] = parameters["sort"]  # comments, created, updated
        if "order" in parameters:
            query_params["order"] = parameters["order"]  # asc, desc
        if "per_page" in parameters:
            query_params["per_page"] = min(int(parameters["per_page"]), 100)
        if "page" in parameters:
            query_params["page"] = int(parameters["page"])
        
        url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        search_results = response.json()
        
        return {
            "success": True,
            "total_count": search_results.get("total_count", 0),
            "incomplete_results": search_results.get("incomplete_results", False),
            "issues": search_results.get("items", [])
        }
    
    # ========================================================================
    # 用户操作
    # ========================================================================
    
    async def _get_authenticated_user(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取认证用户信息"""
        url = f"{self.BASE_URL}/user"
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        user = response.json()
        
        return {
            "success": True,
            "user": user
        }
    
    async def _get_user(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取指定用户信息"""
        username = parameters.get("username")
        if not username:
            raise ValidationError("Missing required parameter: username")
        
        url = f"{self.BASE_URL}/users/{username}"
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        user = response.json()
        
        return {
            "success": True,
            "user": user
        }
    
    # ========================================================================
    # 其他操作的占位符实现
    # ========================================================================
    
    async def _update_repo(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """更新仓库设置"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        repo_data = parameters.get("repo_data", {})
        
        if not all([owner, repo]):
            raise ValidationError("Missing required parameters: owner, repo")
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        headers = self._prepare_headers(credentials)
        
        # 准备更新数据
        update_data = {}
        if "name" in repo_data:
            update_data["name"] = repo_data["name"]
        if "description" in repo_data:
            update_data["description"] = repo_data["description"]
        if "homepage" in repo_data:
            update_data["homepage"] = repo_data["homepage"]
        if "private" in repo_data:
            update_data["private"] = repo_data["private"]
        if "has_issues" in repo_data:
            update_data["has_issues"] = repo_data["has_issues"]
        if "has_projects" in repo_data:
            update_data["has_projects"] = repo_data["has_projects"]
        if "has_wiki" in repo_data:
            update_data["has_wiki"] = repo_data["has_wiki"]
        
        response = await self.make_http_request("PATCH", url, headers=headers, json=update_data)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        updated_repo = response.json()
        
        return {
            "success": True,
            "repository": updated_repo,
            "message": f"Repository {owner}/{repo} updated successfully"
        }
    
    async def _delete_repo(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """删除仓库"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        confirm = parameters.get("confirm", False)
        
        if not all([owner, repo]):
            raise ValidationError("Missing required parameters: owner, repo")
        
        if not confirm:
            raise ValidationError("Repository deletion requires explicit confirmation. Set 'confirm': true")
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("DELETE", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        return {
            "success": True,
            "message": f"Repository {owner}/{repo} deleted successfully"
        }
    
    async def _get_issue(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取问题详情"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        issue_number = parameters.get("issue_number")
        
        if not all([owner, repo, issue_number]):
            raise ValidationError("Missing required parameters: owner, repo, issue_number")
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{issue_number}"
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        issue = response.json()
        
        return {
            "success": True,
            "issue": issue
        }
    
    async def _add_issue_comment(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """添加问题评论"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        issue_number = parameters.get("issue_number")
        body = parameters.get("body")
        
        if not all([owner, repo, issue_number, body]):
            raise ValidationError("Missing required parameters: owner, repo, issue_number, body")
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        headers = self._prepare_headers(credentials)
        payload = {"body": body}
        
        response = await self.make_http_request("POST", url, json=payload, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        comment = response.json()
        
        return {
            "success": True,
            "comment": comment
        }
    
    async def _list_issue_comments(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出问题评论"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        issue_number = parameters.get("issue_number")
        
        if not all([owner, repo, issue_number]):
            raise ValidationError("Missing required parameters: owner, repo, issue_number")
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        headers = self._prepare_headers(credentials)
        
        # 支持分页
        params = {}
        per_page = parameters.get("per_page", 30)
        page = parameters.get("page", 1)
        params["per_page"] = min(per_page, 100)  # GitHub API 限制
        params["page"] = page
        
        response = await self.make_http_request("GET", url, params=params, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        comments = response.json()
        
        return {
            "success": True,
            "comments": comments,
            "total_count": len(comments)
        }
    
    async def _update_pull_request(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """更新拉取请求"""
        # TODO: 实现更新PR逻辑
        return {"success": True, "message": "Update pull request not implemented yet"}
    
    async def _merge_pull_request(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """合并拉取请求"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        pull_number = parameters.get("pull_number")
        commit_title = parameters.get("commit_title")
        commit_message = parameters.get("commit_message")
        merge_method = parameters.get("merge_method", "merge")  # merge, squash, rebase
        
        if not all([owner, repo, pull_number]):
            raise ValidationError("Missing required parameters: owner, repo, pull_number")
        
        # 验证合并方法
        valid_methods = ["merge", "squash", "rebase"]
        if merge_method not in valid_methods:
            merge_method = "merge"
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pull_number}/merge"
        headers = self._prepare_headers(credentials)
        payload = {
            "merge_method": merge_method
        }
        
        if commit_title:
            payload["commit_title"] = commit_title
        if commit_message:
            payload["commit_message"] = commit_message
        
        response = await self.make_http_request("PUT", url, json=payload, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        merge_result = response.json()
        
        return {
            "success": True,
            "merge_result": merge_result,
            "merged": True
        }
    
    async def _get_pull_request(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取拉取请求详情"""
        # TODO: 实现获取PR详情逻辑
        return {"success": True, "message": "Get pull request not implemented yet"}
    
    async def _list_commits(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出提交"""
        # TODO: 实现列出提交逻辑
        return {"success": True, "message": "List commits not implemented yet"}
    
    async def _get_commit(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取提交详情"""
        # TODO: 实现获取提交详情逻辑
        return {"success": True, "message": "Get commit not implemented yet"}
    
    async def _compare_commits(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """比较提交"""
        # TODO: 实现比较提交逻辑
        return {"success": True, "message": "Compare commits not implemented yet"}
    
    async def _list_webhooks(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出Webhook"""
        # TODO: 实现列出Webhook逻辑
        return {"success": True, "message": "List webhooks not implemented yet"}
    
    async def _update_webhook(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """更新Webhook"""
        # TODO: 实现更新Webhook逻辑
        return {"success": True, "message": "Update webhook not implemented yet"}
    
    async def _delete_webhook(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """删除Webhook"""
        # TODO: 实现删除Webhook逻辑
        return {"success": True, "message": "Delete webhook not implemented yet"}
    
    async def _ping_webhook(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """测试Webhook"""
        # TODO: 实现测试Webhook逻辑
        return {"success": True, "message": "Ping webhook not implemented yet"}
    
    async def _list_organizations(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出组织"""
        # TODO: 实现列出组织逻辑
        return {"success": True, "message": "List organizations not implemented yet"}
    
    async def _search_users(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """搜索用户"""
        # TODO: 实现搜索用户逻辑
        return {"success": True, "message": "Search users not implemented yet"}
    
    async def _search_code(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """搜索代码"""
        # TODO: 实现搜索代码逻辑
        return {"success": True, "message": "Search code not implemented yet"}
    
    async def _list_branches(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出分支"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        
        if not all([owner, repo]):
            raise ValidationError("Missing required parameters: owner, repo")
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/branches"
        headers = self._prepare_headers(credentials)
        
        # 支持分页
        params = {}
        per_page = parameters.get("per_page", 30)
        page = parameters.get("page", 1)
        params["per_page"] = min(per_page, 100)  # GitHub API 限制
        params["page"] = page
        
        response = await self.make_http_request("GET", url, params=params, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        branches = response.json()
        
        return {
            "success": True,
            "branches": branches,
            "total_count": len(branches)
        }
    
    async def _get_branch(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取分支详情"""
        # TODO: 实现获取分支详情逻辑
        return {"success": True, "message": "Get branch not implemented yet"}
    
    async def _create_branch(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建分支"""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        branch_name = parameters.get("branch_name")
        source_branch = parameters.get("source_branch", "main")  # 默认从main分支创建
        
        if not all([owner, repo, branch_name]):
            raise ValidationError("Missing required parameters: owner, repo, branch_name")
        
        # 先获取源分支的SHA
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/git/ref/heads/{source_branch}"
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        source_ref = response.json()
        source_sha = source_ref["object"]["sha"]
        
        # 创建新分支
        create_url = f"{self.BASE_URL}/repos/{owner}/{repo}/git/refs"
        payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": source_sha
        }
        
        create_response = await self.make_http_request("POST", create_url, json=payload, headers=headers)
        
        if not create_response.is_success:
            self._handle_http_error(create_response)
        
        new_branch = create_response.json()
        
        return {
            "success": True,
            "branch": new_branch,
            "branch_name": branch_name,
            "source_branch": source_branch
        }
    
    async def _list_tags(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出标签"""
        # TODO: 实现列出标签逻辑
        return {"success": True, "message": "List tags not implemented yet"}
    
    async def _get_tag(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取标签详情"""
        # TODO: 实现获取标签详情逻辑
        return {"success": True, "message": "Get tag not implemented yet"}
    
    async def _list_releases(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出发布版本"""
        # TODO: 实现列出发布版本逻辑
        return {"success": True, "message": "List releases not implemented yet"}
    
    async def _create_release(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建发布版本"""
        # TODO: 实现创建发布版本逻辑
        return {"success": True, "message": "Create release not implemented yet"}
    
    async def _get_release(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取发布版本详情"""
        # TODO: 实现获取发布版本详情逻辑
        return {"success": True, "message": "Get release not implemented yet"}
    
    async def _update_release(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """更新发布版本"""
        # TODO: 实现更新发布版本逻辑
        return {"success": True, "message": "Update release not implemented yet"}
    
    async def _delete_release(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """删除发布版本"""
        # TODO: 实现删除发布版本逻辑
        return {"success": True, "message": "Delete release not implemented yet"}
    
    async def _default_connection_test(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """GitHub特定的连接测试"""
        try:
            # 尝试获取认证用户信息
            url = f"{self.BASE_URL}/user"
            headers = self._prepare_headers(credentials)
            
            response = await self.make_http_request("GET", url, headers=headers)
            
            if response.is_success:
                user_data = response.json()
                return {
                    "credentials_valid": True,
                    "github_access": True,
                    "username": user_data.get("login"),
                    "user_id": user_data.get("id"),
                    "scopes": response.headers.get("X-OAuth-Scopes", "").split(", ") if "X-OAuth-Scopes" in response.headers else []
                }
            else:
                self._handle_http_error(response)
                
        except Exception as e:
            logger.warning(f"GitHub connection test failed: {str(e)}")
            return {
                "credentials_valid": False,
                "error": str(e)
            }