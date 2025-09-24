"""
GitHub external action for external actions.
"""

from datetime import datetime
from typing import Any, Dict

import httpx

from nodes.base import ExecutionStatus, NodeExecutionContext, NodeExecutionResult

from .base_external_action import BaseExternalAction


class GitHubExternalAction(BaseExternalAction):
    """GitHub external action handler."""

    def __init__(self):
        super().__init__("github")

    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle GitHub-specific operations."""
        try:
            # Get GitHub OAuth token from oauth_tokens table
            github_token = await self.get_oauth_token(context)

            if not github_token:
                error_msg = "❌ No GitHub authentication token found. Please connect your GitHub account in integrations settings."
                self.log_execution(context, error_msg, "ERROR")
                return self.create_error_result(error_msg, operation)

            # Prepare headers with OAuth token
            headers = {
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
                "User-Agent": "Workflow-Engine/1.0",
            }

            # Handle different GitHub operations
            if operation.lower() in ["create_issue", "create-issue"]:
                return await self._create_issue(context, headers)
            elif operation.lower() in ["create_pr", "create-pr", "create_pull_request"]:
                return await self._create_pr(context, headers)
            elif operation.lower() in ["get_repo", "get-repo", "get_repository"]:
                return await self._get_repo(context, headers)
            elif operation.lower() in ["list_issues", "list-issues"]:
                return await self._list_issues(context, headers)
            else:
                # Default: get repository info
                return await self._get_repo(context, headers)

        except Exception as e:
            self.log_execution(context, f"GitHub action failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"GitHub action failed: {str(e)}",
                error_details={"integration_type": "github", "operation": operation},
            )

    async def _create_issue(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """Create a GitHub issue."""
        # Get repository info
        repo_owner = context.get_parameter("repo_owner") or context.get_parameter("owner")
        repo_name = context.get_parameter("repo_name") or context.get_parameter("repository")

        # Get issue details
        title = (
            context.get_parameter("title")
            or context.input_data.get("title")
            or "Workflow Generated Issue"
        )
        body = (
            context.get_parameter("body")
            or context.get_parameter("description")
            or context.input_data.get("message")
            or context.input_data.get("body")
            or "This issue was created by a workflow automation."
        )
        labels = context.get_parameter("labels", [])

        if not repo_owner or not repo_name:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="GitHub create issue requires 'repo_owner' and 'repo_name' parameters",
                error_details={"operation": "create_issue", "missing": ["repo_owner", "repo_name"]},
            )

        payload = {
            "title": title,
            "body": body,
        }
        if labels:
            payload["labels"] = labels if isinstance(labels, list) else [labels]

        self.log_execution(context, f"Creating GitHub issue in {repo_owner}/{repo_name}: {title}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues",
                headers=headers,
                json=payload,
                timeout=30.0,
            )

        if response.status_code == 201:
            result = response.json()
            self.log_execution(
                context, f"✅ GitHub issue created successfully: #{result.get('number')}"
            )

            return self.create_success_result(
                "create_issue",
                {
                    "issue_number": result.get("number"),
                    "issue_url": result.get("html_url"),
                    "issue_id": result.get("id"),
                    "title": result.get("title"),
                    "body": result.get("body"),
                    "state": result.get("state"),
                    "repository": f"{repo_owner}/{repo_name}",
                },
            )
        else:
            error = f"GitHub API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )

    async def _create_pr(self, context: NodeExecutionContext, headers: dict) -> NodeExecutionResult:
        """Create a GitHub pull request."""
        # Get repository info
        repo_owner = context.get_parameter("repo_owner") or context.get_parameter("owner")
        repo_name = context.get_parameter("repo_name") or context.get_parameter("repository")

        # Get PR details
        title = (
            context.get_parameter("title")
            or context.input_data.get("title")
            or "Workflow Generated PR"
        )
        body = (
            context.get_parameter("body")
            or context.get_parameter("description")
            or context.input_data.get("message")
            or context.input_data.get("body")
            or "This pull request was created by a workflow automation."
        )
        head_branch = context.get_parameter("head") or context.get_parameter("head_branch")
        base_branch = context.get_parameter("base") or context.get_parameter("base_branch", "main")

        if not all([repo_owner, repo_name, head_branch]):
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="GitHub create PR requires 'repo_owner', 'repo_name', and 'head_branch' parameters",
                error_details={
                    "operation": "create_pr",
                    "missing": ["repo_owner", "repo_name", "head_branch"],
                },
            )

        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
        }

        self.log_execution(
            context,
            f"Creating GitHub PR in {repo_owner}/{repo_name}: {head_branch} -> {base_branch}",
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls",
                headers=headers,
                json=payload,
                timeout=30.0,
            )

        if response.status_code == 201:
            result = response.json()
            self.log_execution(
                context, f"✅ GitHub PR created successfully: #{result.get('number')}"
            )

            return self.create_success_result(
                "create_pr",
                {
                    "pr_number": result.get("number"),
                    "pr_url": result.get("html_url"),
                    "pr_id": result.get("id"),
                    "title": result.get("title"),
                    "body": result.get("body"),
                    "state": result.get("state"),
                    "head": result.get("head", {}).get("ref"),
                    "base": result.get("base", {}).get("ref"),
                    "repository": f"{repo_owner}/{repo_name}",
                },
            )
        else:
            error = f"GitHub API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )

    async def _get_repo(self, context: NodeExecutionContext, headers: dict) -> NodeExecutionResult:
        """Get GitHub repository information."""
        # Get repository info
        repo_owner = context.get_parameter("repo_owner") or context.get_parameter("owner")
        repo_name = context.get_parameter("repo_name") or context.get_parameter("repository")

        if not repo_owner or not repo_name:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="GitHub get repo requires 'repo_owner' and 'repo_name' parameters",
                error_details={"operation": "get_repo", "missing": ["repo_owner", "repo_name"]},
            )

        self.log_execution(context, f"Getting GitHub repository info: {repo_owner}/{repo_name}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}",
                headers=headers,
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            self.log_execution(context, f"✅ GitHub repository info retrieved successfully")

            return self.create_success_result(
                "get_repo",
                {
                    "repo_id": result.get("id"),
                    "repo_name": result.get("name"),
                    "full_name": result.get("full_name"),
                    "description": result.get("description"),
                    "url": result.get("html_url"),
                    "clone_url": result.get("clone_url"),
                    "language": result.get("language"),
                    "stars": result.get("stargazers_count"),
                    "forks": result.get("forks_count"),
                    "open_issues": result.get("open_issues_count"),
                },
            )
        else:
            error = f"GitHub API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )

    async def _list_issues(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """List GitHub repository issues."""
        # Get repository info
        repo_owner = context.get_parameter("repo_owner") or context.get_parameter("owner")
        repo_name = context.get_parameter("repo_name") or context.get_parameter("repository")
        state = context.get_parameter("state", "open")  # open, closed, all
        limit = context.get_parameter("limit", 10)

        if not repo_owner or not repo_name:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="GitHub list issues requires 'repo_owner' and 'repo_name' parameters",
                error_details={"operation": "list_issues", "missing": ["repo_owner", "repo_name"]},
            )

        params = {
            "state": state,
            "per_page": min(limit, 100),  # GitHub API max is 100
        }

        self.log_execution(
            context, f"Listing GitHub issues in {repo_owner}/{repo_name} (state: {state})"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues",
                headers=headers,
                params=params,
                timeout=30.0,
            )

        if response.status_code == 200:
            issues = response.json()
            self.log_execution(context, f"✅ Retrieved {len(issues)} GitHub issues")

            # Process issues data
            issues_data = []
            for issue in issues:
                issues_data.append(
                    {
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "body": issue.get("body", "")[:200],  # Truncate body
                        "state": issue.get("state"),
                        "url": issue.get("html_url"),
                        "author": issue.get("user", {}).get("login"),
                        "created_at": issue.get("created_at"),
                        "labels": [label.get("name") for label in issue.get("labels", [])],
                    }
                )

            return self.create_success_result(
                "list_issues",
                {
                    "issues_count": len(issues_data),
                    "issues": issues_data,
                    "repository": f"{repo_owner}/{repo_name}",
                    "state_filter": state,
                },
            )
        else:
            error = f"GitHub API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )
