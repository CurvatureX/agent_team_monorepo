"""
GitHub API Adapter
基于shared/sdks/github_sdk的GitHub集成适配器
支持issues、pull requests、comments等操作
"""

import logging
from typing import Dict, Any, Optional
import json

from .base import (
    APIAdapter, 
    OAuth2Config, 
    ValidationError, 
    AuthenticationError,
    TemporaryError,
    PermanentError,
    register_adapter
)

logger = logging.getLogger(__name__)


@register_adapter("github")
class GitHubAdapter(APIAdapter):
    """GitHub API适配器 - 集成GitHub SDK功能"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://api.github.com"
    
    async def call(self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        执行GitHub API操作
        
        Args:
            operation: GitHub操作类型 (create_issue, create_pull_request等)
            parameters: 操作参数
            credentials: 认证凭据
            
        Returns:
            GitHub API响应数据
        """
        try:
            self.logger.info(f"GitHub operation: {operation} with params: {list(parameters.keys())}")
            
            # 验证凭据
            if not self.validate_credentials(credentials):
                raise AuthenticationError("Invalid GitHub credentials")
            
            # 验证参数
            self._validate_parameters(operation, parameters)
            
            # 根据操作类型调用相应的方法
            if operation == "create_issue":
                return await self._create_issue(parameters, credentials)
            elif operation == "create_pull_request":
                return await self._create_pull_request(parameters, credentials)
            elif operation == "add_comment":
                return await self._add_comment(parameters, credentials)
            elif operation == "close_issue":
                return await self._close_issue(parameters, credentials)
            elif operation == "merge_pr":
                return await self._merge_pull_request(parameters, credentials)
            elif operation == "list_issues":
                return await self._list_issues(parameters, credentials)
            elif operation == "get_issue":
                return await self._get_issue(parameters, credentials)
            else:
                raise ValidationError(f"Unsupported GitHub operation: {operation}")
                
        except Exception as e:
            self.logger.error(f"GitHub API call failed: {e}")
            raise
    
    def get_oauth2_config(self) -> OAuth2Config:
        """获取GitHub OAuth2配置"""
        import os
        return OAuth2Config(
            client_id=os.getenv("GITHUB_CLIENT_ID", ""),
            client_secret=os.getenv("GITHUB_CLIENT_SECRET", ""),
            auth_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=["repo", "user"]
        )
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """验证GitHub凭据"""
        return "access_token" in credentials or "auth_token" in credentials
    
    def _validate_parameters(self, operation: str, parameters: Dict[str, Any]):
        """验证操作参数"""
        required_params = {
            "create_issue": ["repository", "title"],
            "create_pull_request": ["repository", "title", "head", "base"],
            "add_comment": ["repository", "issue_number", "body"],
            "close_issue": ["repository", "issue_number"],
            "merge_pr": ["repository", "issue_number"],
            "list_issues": ["repository"],
            "get_issue": ["repository", "issue_number"]
        }
        
        if operation in required_params:
            for param in required_params[operation]:
                if param not in parameters:
                    raise ValidationError(f"Missing required parameter: {param}")
    
    async def _create_issue(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建GitHub Issue"""
        repo = parameters["repository"]
        
        # 构建请求数据
        issue_data = {
            "title": parameters["title"],
            "body": parameters.get("body", ""),
        }
        
        # 可选参数
        if "labels" in parameters and parameters["labels"]:
            issue_data["labels"] = parameters["labels"]
        if "assignees" in parameters and parameters["assignees"]:
            issue_data["assignees"] = parameters["assignees"]
        if "milestone" in parameters:
            issue_data["milestone"] = parameters["milestone"]
        
        # 发送请求
        response = await self.make_http_request(
            method="POST",
            url=f"{self.base_url}/repos/{repo}/issues",
            headers=self._prepare_headers(credentials),
            json_data=issue_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        issue = response.json()
        return {
            "success": True,
            "issue_id": issue["id"],
            "issue_number": issue["number"],
            "url": issue["html_url"],
            "state": issue["state"],
            "created_at": issue["created_at"],
            "issue": issue
        }
    
    async def _create_pull_request(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建Pull Request"""
        repo = parameters["repository"]
        
        pr_data = {
            "title": parameters["title"],
            "head": parameters.get("head", parameters.get("branch", "main")),
            "base": parameters.get("base", "main"),
            "body": parameters.get("body", ""),
            "draft": parameters.get("draft", False)
        }
        
        response = await self.make_http_request(
            method="POST",
            url=f"{self.base_url}/repos/{repo}/pulls",
            headers=self._prepare_headers(credentials),
            json_data=pr_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        pr = response.json()
        return {
            "success": True,
            "pr_id": pr["id"],
            "pr_number": pr["number"],
            "url": pr["html_url"],
            "state": pr["state"],
            "mergeable": pr.get("mergeable"),
            "created_at": pr["created_at"],
            "pull_request": pr
        }
    
    async def _add_comment(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """添加评论到Issue或PR"""
        repo = parameters["repository"]
        issue_number = parameters["issue_number"]
        
        comment_data = {
            "body": parameters["body"]
        }
        
        response = await self.make_http_request(
            method="POST",
            url=f"{self.base_url}/repos/{repo}/issues/{issue_number}/comments",
            headers=self._prepare_headers(credentials),
            json_data=comment_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        comment = response.json()
        return {
            "success": True,
            "comment_id": comment["id"],
            "url": comment["html_url"],
            "created_at": comment["created_at"],
            "comment": comment
        }
    
    async def _close_issue(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """关闭Issue"""
        repo = parameters["repository"]
        issue_number = parameters["issue_number"]
        
        update_data = {
            "state": "closed"
        }
        
        response = await self.make_http_request(
            method="PATCH",
            url=f"{self.base_url}/repos/{repo}/issues/{issue_number}",
            headers=self._prepare_headers(credentials),
            json_data=update_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        issue = response.json()
        return {
            "success": True,
            "issue_id": issue["id"],
            "issue_number": issue["number"],
            "state": issue["state"],
            "closed_at": issue.get("closed_at"),
            "issue": issue
        }
    
    async def _merge_pull_request(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """合并Pull Request"""
        repo = parameters["repository"]
        pr_number = parameters["issue_number"]  # 使用issue_number作为PR number
        
        merge_data = {
            "commit_title": parameters.get("commit_title", ""),
            "commit_message": parameters.get("commit_message", ""),
            "merge_method": parameters.get("merge_method", "merge")
        }
        
        response = await self.make_http_request(
            method="PUT",
            url=f"{self.base_url}/repos/{repo}/pulls/{pr_number}/merge",
            headers=self._prepare_headers(credentials),
            json_data=merge_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        merge_result = response.json()
        return {
            "success": True,
            "merged": merge_result["merged"],
            "sha": merge_result["sha"],
            "message": merge_result["message"],
            "merge_result": merge_result
        }
    
    async def _list_issues(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出Repository的Issues"""
        repo = parameters["repository"]
        
        # 查询参数
        params = {
            "state": parameters.get("state", "open"),
            "sort": parameters.get("sort", "created"),
            "direction": parameters.get("direction", "desc"),
            "per_page": min(int(parameters.get("per_page", 30)), 100)
        }
        
        # 过滤参数
        if "labels" in parameters and parameters["labels"]:
            params["labels"] = ",".join(parameters["labels"])
        if "assignee" in parameters:
            params["assignee"] = parameters["assignee"]
        if "since" in parameters:
            params["since"] = parameters["since"]
        
        response = await self.make_http_request(
            method="GET",
            url=f"{self.base_url}/repos/{repo}/issues",
            headers=self._prepare_headers(credentials),
            params=params
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        issues = response.json()
        return {
            "success": True,
            "total_count": len(issues),
            "issues": issues,
            "repository": repo
        }
    
    async def _get_issue(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取特定Issue详情"""
        repo = parameters["repository"]
        issue_number = parameters["issue_number"]
        
        response = await self.make_http_request(
            method="GET",
            url=f"{self.base_url}/repos/{repo}/issues/{issue_number}",
            headers=self._prepare_headers(credentials)
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        issue = response.json()
        return {
            "success": True,
            "issue_id": issue["id"],
            "issue_number": issue["number"],
            "title": issue["title"],
            "state": issue["state"],
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
            "url": issue["html_url"],
            "issue": issue
        }
    
    def _prepare_headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """准备GitHub API请求头"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AgentTeam-Workflow-Engine/1.0"
        }
        
        # 添加认证
        token = credentials.get("access_token") or credentials.get("auth_token")
        if token:
            headers["Authorization"] = f"token {token}"
        
        return headers