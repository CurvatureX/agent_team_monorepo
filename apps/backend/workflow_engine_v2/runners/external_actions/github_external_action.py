"""
GitHub external action for workflow_engine_v2.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import httpx

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus, NodeExecutionResult
from workflow_engine_v2.core.context import NodeExecutionContext

from .base_external_action import BaseExternalAction


class GitHubExternalAction(BaseExternalAction):
    """GitHub external action handler for workflow_engine_v2."""

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
        # Get repository info from configurations or input data
        repo_owner = (
            context.node.configurations.get("repo_owner")
            or context.node.configurations.get("owner")
            or context.input_data.get("repo_owner")
        )
        repo_name = (
            context.node.configurations.get("repo_name")
            or context.node.configurations.get("repository")
            or context.input_data.get("repo_name")
        )

        # Get issue details
        title = (
            context.input_data.get("title")
            or context.node.configurations.get("title")
            or "Workflow Generated Issue"
        )
        body = (
            context.input_data.get("body")
            or context.input_data.get("message")
            or context.node.configurations.get("body")
            or context.node.configurations.get("description")
            or "This issue was created by a workflow automation."
        )
        labels = context.node.configurations.get("labels", [])

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
        repo_owner = (
            context.node.configurations.get("repo_owner")
            or context.node.configurations.get("owner")
            or context.input_data.get("repo_owner")
        )
        repo_name = (
            context.node.configurations.get("repo_name")
            or context.node.configurations.get("repository")
            or context.input_data.get("repo_name")
        )

        # Get PR details
        title = (
            context.input_data.get("title")
            or context.node.configurations.get("title")
            or "Workflow Generated PR"
        )
        body = (
            context.input_data.get("body")
            or context.input_data.get("message")
            or context.node.configurations.get("body")
            or "This pull request was created by a workflow automation."
        )
        head = (
            context.input_data.get("head")
            or context.node.configurations.get("head")
            or context.node.configurations.get("source_branch")
        )
        base = (
            context.input_data.get("base")
            or context.node.configurations.get("base")
            or context.node.configurations.get("target_branch")
            or "main"
        )

        if not all([repo_owner, repo_name, head]):
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="GitHub create PR requires 'repo_owner', 'repo_name', and 'head' parameters",
                error_details={
                    "operation": "create_pr",
                    "missing": ["repo_owner", "repo_name", "head"],
                },
            )

        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
        }

        self.log_execution(context, f"Creating GitHub PR in {repo_owner}/{repo_name}: {title}")

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
        repo_owner = (
            context.node.configurations.get("repo_owner")
            or context.node.configurations.get("owner")
            or context.input_data.get("repo_owner")
        )
        repo_name = (
            context.node.configurations.get("repo_name")
            or context.node.configurations.get("repository")
            or context.input_data.get("repo_name")
        )

        if not repo_owner or not repo_name:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="GitHub get repo requires 'repo_owner' and 'repo_name' parameters",
                error_details={"operation": "get_repo", "missing": ["repo_owner", "repo_name"]},
            )

        self.log_execution(context, f"Getting GitHub repository info for {repo_owner}/{repo_name}")

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
                    "name": result.get("name"),
                    "full_name": result.get("full_name"),
                    "description": result.get("description"),
                    "html_url": result.get("html_url"),
                    "clone_url": result.get("clone_url"),
                    "default_branch": result.get("default_branch"),
                    "stars": result.get("stargazers_count"),
                    "forks": result.get("forks_count"),
                    "language": result.get("language"),
                    "private": result.get("private"),
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
        repo_owner = (
            context.node.configurations.get("repo_owner")
            or context.node.configurations.get("owner")
            or context.input_data.get("repo_owner")
        )
        repo_name = (
            context.node.configurations.get("repo_name")
            or context.node.configurations.get("repository")
            or context.input_data.get("repo_name")
        )

        if not repo_owner or not repo_name:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="GitHub list issues requires 'repo_owner' and 'repo_name' parameters",
                error_details={"operation": "list_issues", "missing": ["repo_owner", "repo_name"]},
            )

        # Get optional parameters
        state = context.node.configurations.get("state", "open")  # open, closed, all
        limit = context.node.configurations.get("limit", 30)

        self.log_execution(context, f"Listing GitHub issues for {repo_owner}/{repo_name}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues",
                headers=headers,
                params={"state": state, "per_page": limit},
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            self.log_execution(context, f"✅ Retrieved {len(result)} GitHub issues")

            issues_data = []
            for issue in result:
                issues_data.append(
                    {
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "body": issue.get("body"),
                        "state": issue.get("state"),
                        "html_url": issue.get("html_url"),
                        "created_at": issue.get("created_at"),
                        "updated_at": issue.get("updated_at"),
                        "author": issue.get("user", {}).get("login"),
                        "labels": [label.get("name") for label in issue.get("labels", [])],
                    }
                )

            return self.create_success_result(
                "list_issues",
                {
                    "issues_count": len(issues_data),
                    "issues": issues_data,
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


__all__ = ["GitHubExternalAction"]
