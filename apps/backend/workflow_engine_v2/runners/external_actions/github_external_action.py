"""
GitHub external action for workflow_engine_v2 using GitHub SDK.

This implementation uses the shared GitHub SDK for all operations,
strictly following the node specification in shared/node_specs/EXTERNAL_ACTION/GITHUB.py.
"""

from __future__ import annotations

import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus, NodeExecutionResult
from shared.models.execution_new import LogLevel
from shared.sdks.github_sdk.client import GitHubSDK
from shared.sdks.github_sdk.exceptions import (
    GitHubAuthError,
    GitHubError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
)
from workflow_engine_v2.core.context import NodeExecutionContext

from .base_external_action import BaseExternalAction


class GitHubExternalAction(BaseExternalAction):
    """
    GitHub external action handler using GitHub SDK.

    Follows node spec output format:
    - success: boolean
    - github_response: object (parsed API response)
    - resource_id: string
    - resource_url: string
    - error_message: string
    - rate_limit_info: object
    - execution_metadata: object
    """

    def __init__(self):
        super().__init__("github")
        # GitHub App credentials from environment (required)
        self.github_app_id = os.getenv("GITHUB_APP_ID", "")
        self.github_private_key = os.getenv("GITHUB_PRIVATE_KEY", "")

        if not self.github_app_id or not self.github_private_key:
            self.logger.warning(
                "GitHub App credentials not configured. Set GITHUB_APP_ID and GITHUB_PRIVATE_KEY environment variables."
            )

    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle GitHub-specific operations using SDK."""
        try:
            # Validate GitHub App configuration
            if not self.github_app_id or not self.github_private_key:
                return self._create_spec_error_result(
                    "GitHub App not configured. Set GITHUB_APP_ID and GITHUB_PRIVATE_KEY environment variables.",
                    operation,
                    {
                        "reason": "missing_app_credentials",
                        "solution": "Configure GitHub App credentials in environment variables",
                        "required_env_vars": ["GITHUB_APP_ID", "GITHUB_PRIVATE_KEY"],
                    },
                )

            # Get installation_id from oauth_tokens table or configurations
            installation_id = await self._get_installation_id(context)
            if not installation_id:
                return self._create_spec_error_result(
                    "GitHub installation_id is required. Please connect GitHub account or provide installation_id.",
                    operation,
                    {
                        "reason": "missing_installation_id",
                        "solution": "Connect GitHub account in integrations or add 'installation_id' to node configurations",
                        "documentation": "https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app",
                    },
                )

            # Initialize GitHub SDK
            async with GitHubSDK(self.github_app_id, self.github_private_key) as github:
                # Route to appropriate operation handler
                return await self._route_operation(context, operation, github, installation_id)

        except GitHubAuthError as e:
            self.log_execution(
                context, f"GitHub authentication error: {str(e)}", LogLevel.ERROR.value
            )
            return self._create_spec_error_result(
                f"GitHub authentication failed: {str(e)}",
                operation,
                {
                    "reason": "authentication_error",
                    "solution": "Check GitHub App credentials and installation permissions",
                },
            )
        except GitHubRateLimitError as e:
            self.log_execution(
                context, f"GitHub rate limit exceeded: {str(e)}", LogLevel.ERROR.value
            )
            return self._create_spec_error_result(
                f"GitHub rate limit exceeded: {str(e)}",
                operation,
                {
                    "reason": "rate_limit_exceeded",
                    "solution": "Wait for rate limit reset or use a different GitHub App",
                    "reset_time": getattr(e, "reset_time", None),
                },
            )
        except GitHubNotFoundError as e:
            self.log_execution(
                context, f"GitHub resource not found: {str(e)}", LogLevel.ERROR.value
            )
            return self._create_spec_error_result(
                f"GitHub resource not found: {str(e)}",
                operation,
                {
                    "reason": "resource_not_found",
                    "solution": "Verify repository name and resource identifiers",
                },
            )
        except GitHubPermissionError as e:
            self.log_execution(context, f"GitHub permission denied: {str(e)}", LogLevel.ERROR.value)
            return self._create_spec_error_result(
                f"GitHub permission denied: {str(e)}",
                operation,
                {
                    "reason": "permission_denied",
                    "solution": "Check GitHub App installation permissions",
                },
            )
        except GitHubError as e:
            self.log_execution(context, f"GitHub API error: {str(e)}", LogLevel.ERROR.value)
            return self._create_spec_error_result(
                f"GitHub API error: {str(e)}",
                operation,
                {
                    "reason": "api_error",
                    "status_code": getattr(e, "status_code", None),
                    "response_data": getattr(e, "response_data", {}),
                },
            )
        except Exception as e:
            self.log_execution(context, f"Unexpected error: {str(e)}", LogLevel.ERROR.value)
            return self._create_spec_error_result(
                f"GitHub action failed: {str(e)}",
                operation,
                {"exception_type": type(e).__name__, "exception": str(e)},
            )

    async def _get_installation_id(self, context: NodeExecutionContext) -> Optional[int]:
        """Extract installation_id from OAuth token or context."""
        # Priority 1: From configurations
        installation_id = context.node.configurations.get("installation_id")
        if installation_id:
            try:
                return int(installation_id)
            except (ValueError, TypeError):
                pass

        # Priority 2: From input parameters
        installation_id = context.input_data.get("installation_id")
        if installation_id:
            try:
                return int(installation_id)
            except (ValueError, TypeError):
                pass

        # Priority 3: From OAuth token (stored in oauth_tokens table)
        github_token = await self.get_oauth_token(context)
        if github_token:
            if github_token.startswith("github_installation_"):
                return int(github_token.replace("github_installation_", ""))
            if github_token.isdigit():
                return int(github_token)

        return None

    def _get_repo_params(self, context: NodeExecutionContext) -> tuple[str, str]:
        """
        Extract owner and repo from input_params (follows node spec).

        Priority: input_params > configurations
        """
        # From input_params (highest priority - as per node spec)
        owner = context.input_data.get("owner") or context.input_data.get("repo_owner")
        repo = (
            context.input_data.get("repo")
            or context.input_data.get("repo_name")
            or context.input_data.get("repository")
        )

        # Fallback to configurations
        if not owner or not repo:
            repo_config = context.node.configurations.get("repository_config", {})
            owner = owner or repo_config.get("owner")
            repo = repo or repo_config.get("repo")

        return owner or "", repo or ""

    def _get_repo_name(self, context: NodeExecutionContext) -> str:
        """Get repository name in owner/repo format."""
        owner, repo = self._get_repo_params(context)
        if owner and repo:
            return f"{owner}/{repo}"
        return ""

    def _create_spec_error_result(
        self, message: str, operation: str, error_details: Dict[str, Any] = None
    ) -> NodeExecutionResult:
        """
        Create error result following node spec output format.

        Spec output_params:
        - success: false
        - error_message: string
        - github_response: {}
        - resource_id: ""
        - resource_url: ""
        - rate_limit_info: {}
        - execution_metadata: {...}
        """
        return NodeExecutionResult(
            status=ExecutionStatus.ERROR,
            error_message=message,
            error_details={
                "integration": self.integration_name,
                "operation": operation,
                **(error_details or {}),
            },
            output_data={
                "success": False,
                "error_message": message,
                "github_response": {},
                "resource_id": "",
                "resource_url": "",
                "rate_limit_info": {},
                "execution_metadata": {
                    "integration_type": self.integration_name,
                    "operation": operation,
                    "timestamp": datetime.now().isoformat(),
                    "error_details": error_details or {},
                },
            },
            metadata={
                "node_type": "external_action",
                "integration": self.integration_name,
                "operation": operation,
            },
        )

    def _create_spec_success_result(
        self, operation: str, github_response: Any, resource_id: str = "", resource_url: str = ""
    ) -> NodeExecutionResult:
        """
        Create success result following node spec output format.

        Spec output_params:
        - success: true
        - github_response: object (parsed API response)
        - resource_id: string
        - resource_url: string
        - error_message: ""
        - rate_limit_info: {}
        - execution_metadata: {...}
        """
        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data={
                "success": True,
                "github_response": github_response,
                "resource_id": resource_id,
                "resource_url": resource_url,
                "error_message": "",
                "rate_limit_info": {},  # TODO: Extract from SDK if available
                "execution_metadata": {
                    "integration_type": self.integration_name,
                    "operation": operation,
                    "timestamp": datetime.now().isoformat(),
                },
            },
            metadata={
                "node_type": "external_action",
                "integration": self.integration_name,
                "operation": operation,
            },
        )

    async def _route_operation(
        self,
        context: NodeExecutionContext,
        operation: str,
        github: GitHubSDK,
        installation_id: int,
    ) -> NodeExecutionResult:
        """Route operation to appropriate SDK handler."""
        op_lower = operation.lower().replace("-", "_")

        # Issue operations
        if op_lower == "create_issue":
            return await self._create_issue(context, github, installation_id)
        elif op_lower == "update_issue":
            return await self._update_issue(context, github, installation_id)
        elif op_lower == "close_issue":
            return await self._close_issue(context, github, installation_id)
        elif op_lower == "reopen_issue":
            return await self._reopen_issue(context, github, installation_id)
        elif op_lower == "list_issues":
            return await self._list_issues(context, github, installation_id)
        elif op_lower == "add_issue_comment":
            return await self._add_issue_comment(context, github, installation_id)
        elif op_lower == "assign_issue":
            return await self._assign_issue(context, github, installation_id)
        elif op_lower == "add_issue_labels":
            return await self._add_issue_labels(context, github, installation_id)

        # Pull Request operations
        elif op_lower == "create_pull_request":
            return await self._create_pull_request(context, github, installation_id)
        elif op_lower == "update_pull_request":
            return await self._update_pull_request(context, github, installation_id)
        elif op_lower == "merge_pull_request":
            return await self._merge_pull_request(context, github, installation_id)
        elif op_lower == "list_pull_requests":
            return await self._list_pull_requests(context, github, installation_id)
        elif op_lower == "add_pr_comment":
            return await self._add_pr_comment(context, github, installation_id)
        elif op_lower == "request_pr_review":
            return await self._request_pr_review(context, github, installation_id)

        # Repository operations
        elif op_lower == "list_repositories":
            return await self._list_repositories(context, github, installation_id)

        # File operations
        elif op_lower == "get_file_content":
            return await self._get_file_content(context, github, installation_id)
        elif op_lower in ["create_file", "update_file"]:
            return await self._create_or_update_file(context, github, installation_id)

        # Branch operations
        elif op_lower == "create_branch":
            return await self._create_branch(context, github, installation_id)
        elif op_lower == "delete_branch":
            return await self._delete_branch(context, github, installation_id)

        else:
            return self._create_spec_error_result(
                f"Unsupported GitHub operation: {operation}",
                operation,
                {
                    "reason": "unsupported_operation",
                    "solution": "Use one of the supported operations from node spec",
                    "supported_operations": [
                        "create_issue",
                        "update_issue",
                        "close_issue",
                        "reopen_issue",
                        "list_issues",
                        "add_issue_comment",
                        "assign_issue",
                        "add_issue_labels",
                        "create_pull_request",
                        "update_pull_request",
                        "merge_pull_request",
                        "list_pull_requests",
                        "add_pr_comment",
                        "request_pr_review",
                        "list_repositories",
                        "get_file_content",
                        "create_file",
                        "update_file",
                        "create_branch",
                        "delete_branch",
                    ],
                },
            )

    # ============================================================================
    # Issue Operations
    # ============================================================================

    async def _create_issue(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Create a GitHub issue (follows node spec input_params)."""
        repo_name = self._get_repo_name(context)
        if not repo_name:
            return self._create_spec_error_result(
                "Repository name required (owner and repo)",
                "create_issue",
                {"missing_parameters": ["owner", "repo"]},
            )

        # Extract from input_params (as per node spec)
        title = context.input_data.get("title", "Workflow Generated Issue")
        body = context.input_data.get("body", "")
        labels = context.input_data.get("labels", [])
        assignees = context.input_data.get("assignees", [])

        self.log_execution(context, f"Creating issue in {repo_name}: {title}")

        issue = await github.create_issue(
            installation_id, repo_name, title, body, assignees, labels
        )

        self.log_execution(context, f"✅ Created issue #{issue.number} in {repo_name}")

        return self._create_spec_success_result(
            "create_issue",
            asdict(issue),
            resource_id=str(issue.id),
            resource_url=issue.html_url,
        )

    async def _update_issue(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Update an existing issue."""
        repo_name = self._get_repo_name(context)
        issue_number = context.input_data.get("issue_number")

        if not repo_name or not issue_number:
            return self._create_spec_error_result(
                "Repository name and issue_number required",
                "update_issue",
                {"missing_parameters": ["owner", "repo", "issue_number"]},
            )

        title = context.input_data.get("title")
        body = context.input_data.get("body")
        state = context.input_data.get("state")
        labels = context.input_data.get("labels")
        assignees = context.input_data.get("assignees")

        issue = await github.update_issue(
            installation_id, repo_name, int(issue_number), title, body, state, assignees, labels
        )

        self.log_execution(context, f"✅ Updated issue #{issue.number}")

        return self._create_spec_success_result(
            "update_issue",
            asdict(issue),
            resource_id=str(issue.id),
            resource_url=issue.html_url,
        )

    async def _close_issue(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Close an issue."""
        repo_name = self._get_repo_name(context)
        issue_number = context.input_data.get("issue_number")

        if not repo_name or not issue_number:
            return self._create_spec_error_result(
                "Repository name and issue_number required", "close_issue"
            )

        issue = await github.close_issue(installation_id, repo_name, int(issue_number))

        self.log_execution(context, f"✅ Closed issue #{issue.number}")

        return self._create_spec_success_result(
            "close_issue",
            asdict(issue),
            resource_id=str(issue.id),
            resource_url=issue.html_url,
        )

    async def _reopen_issue(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Reopen a closed issue."""
        repo_name = self._get_repo_name(context)
        issue_number = context.input_data.get("issue_number")

        if not repo_name or not issue_number:
            return self._create_spec_error_result(
                "Repository name and issue_number required", "reopen_issue"
            )

        issue = await github.reopen_issue(installation_id, repo_name, int(issue_number))

        self.log_execution(context, f"✅ Reopened issue #{issue.number}")

        return self._create_spec_success_result(
            "reopen_issue",
            asdict(issue),
            resource_id=str(issue.id),
            resource_url=issue.html_url,
        )

    async def _list_issues(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """List issues in a repository."""
        repo_name = self._get_repo_name(context)
        if not repo_name:
            return self._create_spec_error_result("Repository name required", "list_issues")

        state = context.input_data.get("state", "open")
        labels = context.input_data.get("labels")
        assignee = context.input_data.get("assignee")

        issues = await github.list_issues(installation_id, repo_name, state, labels, assignee)

        self.log_execution(context, f"✅ Retrieved {len(issues)} issues")

        return self._create_spec_success_result(
            "list_issues",
            {"issues": [asdict(issue) for issue in issues], "count": len(issues)},
        )

    async def _add_issue_comment(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Add comment to an issue."""
        repo_name = self._get_repo_name(context)
        issue_number = context.input_data.get("issue_number")
        body = context.input_data.get("comment") or context.input_data.get("body", "")

        if not repo_name or not issue_number or not body:
            return self._create_spec_error_result(
                "Repository name, issue_number, and comment required", "add_issue_comment"
            )

        comment = await github.create_issue_comment(
            installation_id, repo_name, int(issue_number), body
        )

        self.log_execution(context, f"✅ Added comment to issue #{issue_number}")

        return self._create_spec_success_result(
            "add_issue_comment",
            asdict(comment),
            resource_id=str(comment.id),
            resource_url=comment.html_url,
        )

    async def _assign_issue(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Assign users to an issue."""
        repo_name = self._get_repo_name(context)
        issue_number = context.input_data.get("issue_number")
        assignees = context.input_data.get("assignees", [])

        if not repo_name or not issue_number or not assignees:
            return self._create_spec_error_result(
                "Repository name, issue_number, and assignees required", "assign_issue"
            )

        if not isinstance(assignees, list):
            assignees = [assignees]

        result = await github.assign_issue(installation_id, repo_name, int(issue_number), assignees)

        self.log_execution(context, f"✅ Assigned {len(assignees)} users to issue #{issue_number}")

        return self._create_spec_success_result("assign_issue", result)

    async def _add_issue_labels(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Add labels to an issue."""
        repo_name = self._get_repo_name(context)
        issue_number = context.input_data.get("issue_number")
        labels = context.input_data.get("labels", [])

        if not repo_name or not issue_number or not labels:
            return self._create_spec_error_result(
                "Repository name, issue_number, and labels required", "add_issue_labels"
            )

        if not isinstance(labels, list):
            labels = [labels]

        result_labels = await github.add_labels_to_issue(
            installation_id, repo_name, int(issue_number), labels
        )

        self.log_execution(context, f"✅ Added {len(labels)} labels to issue #{issue_number}")

        return self._create_spec_success_result(
            "add_issue_labels", {"labels": result_labels, "count": len(result_labels)}
        )

    # ============================================================================
    # Pull Request Operations
    # ============================================================================

    async def _create_pull_request(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Create a pull request."""
        repo_name = self._get_repo_name(context)
        title = context.input_data.get("title", "Workflow Generated PR")
        head = context.input_data.get("head")
        base = context.input_data.get("base", "main")
        body = context.input_data.get("body", "")

        if not repo_name or not head:
            return self._create_spec_error_result(
                "Repository name and head branch required",
                "create_pull_request",
                {"missing_parameters": ["owner", "repo", "head"]},
            )

        pr = await github.create_pull_request(installation_id, repo_name, title, head, base, body)

        self.log_execution(context, f"✅ Created PR #{pr.number} in {repo_name}")

        return self._create_spec_success_result(
            "create_pull_request",
            asdict(pr),
            resource_id=str(pr.id),
            resource_url=pr.html_url,
        )

    async def _update_pull_request(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Update a pull request."""
        repo_name = self._get_repo_name(context)
        pr_number = context.input_data.get("pr_number")

        if not repo_name or not pr_number:
            return self._create_spec_error_result(
                "Repository name and pr_number required", "update_pull_request"
            )

        title = context.input_data.get("title")
        body = context.input_data.get("body")
        state = context.input_data.get("state")

        pr = await github.update_pull_request(
            installation_id, repo_name, int(pr_number), title, body, state
        )

        self.log_execution(context, f"✅ Updated PR #{pr.number}")

        return self._create_spec_success_result(
            "update_pull_request",
            asdict(pr),
            resource_id=str(pr.id),
            resource_url=pr.html_url,
        )

    async def _merge_pull_request(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Merge a pull request."""
        repo_name = self._get_repo_name(context)
        pr_number = context.input_data.get("pr_number")

        if not repo_name or not pr_number:
            return self._create_spec_error_result(
                "Repository name and pr_number required", "merge_pull_request"
            )

        commit_title = context.input_data.get("commit_title")
        commit_message = context.input_data.get("commit_message")
        merge_method = context.input_data.get("merge_method", "merge")

        result = await github.merge_pull_request(
            installation_id, repo_name, int(pr_number), commit_title, commit_message, merge_method
        )

        self.log_execution(context, f"✅ Merged PR #{pr_number}")

        return self._create_spec_success_result("merge_pull_request", result)

    async def _list_pull_requests(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """List pull requests in a repository."""
        repo_name = self._get_repo_name(context)
        if not repo_name:
            return self._create_spec_error_result("Repository name required", "list_pull_requests")

        state = context.input_data.get("state", "open")
        prs = await github.list_pull_requests(installation_id, repo_name, state)

        self.log_execution(context, f"✅ Retrieved {len(prs)} pull requests")

        return self._create_spec_success_result(
            "list_pull_requests",
            {"pull_requests": [asdict(pr) for pr in prs], "count": len(prs)},
        )

    async def _add_pr_comment(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Add comment to a pull request."""
        repo_name = self._get_repo_name(context)
        pr_number = context.input_data.get("pr_number")
        body = context.input_data.get("comment") or context.input_data.get("body", "")

        if not repo_name or not pr_number or not body:
            return self._create_spec_error_result(
                "Repository name, pr_number, and comment required", "add_pr_comment"
            )

        comment = await github.create_pull_request_comment(
            installation_id, repo_name, int(pr_number), body
        )

        self.log_execution(context, f"✅ Added comment to PR #{pr_number}")

        return self._create_spec_success_result(
            "add_pr_comment",
            asdict(comment),
            resource_id=str(comment.id),
            resource_url=comment.html_url,
        )

    async def _request_pr_review(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Request reviewers for a pull request."""
        repo_name = self._get_repo_name(context)
        pr_number = context.input_data.get("pr_number")
        reviewers = context.input_data.get("reviewers", [])

        if not repo_name or not pr_number or not reviewers:
            return self._create_spec_error_result(
                "Repository name, pr_number, and reviewers required", "request_pr_review"
            )

        if not isinstance(reviewers, list):
            reviewers = [reviewers]

        team_reviewers = context.input_data.get("team_reviewers")

        result = await github.request_pull_request_reviewers(
            installation_id, repo_name, int(pr_number), reviewers, team_reviewers
        )

        self.log_execution(context, f"✅ Requested reviewers for PR #{pr_number}")

        return self._create_spec_success_result("request_pr_review", result)

    # ============================================================================
    # Repository Operations
    # ============================================================================

    async def _list_repositories(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """List repositories accessible to the installation."""
        repos = await github.list_repositories(installation_id)

        self.log_execution(context, f"✅ Retrieved {len(repos)} repositories")

        return self._create_spec_success_result(
            "list_repositories",
            {"repositories": [asdict(repo) for repo in repos], "count": len(repos)},
        )

    # ============================================================================
    # File Operations
    # ============================================================================

    async def _get_file_content(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Get file content from repository."""
        repo_name = self._get_repo_name(context)
        file_path = context.input_data.get("path")
        ref = context.input_data.get("ref", "main")

        if not repo_name or not file_path:
            return self._create_spec_error_result(
                "Repository name and path required",
                "get_file_content",
                {"missing_parameters": ["owner", "repo", "path"]},
            )

        file_content = await github.get_file_content(installation_id, repo_name, file_path, ref)

        self.log_execution(context, f"✅ Retrieved file {file_path}")

        return self._create_spec_success_result(
            "get_file_content",
            asdict(file_content),
            resource_id=file_content.sha,
            resource_url=file_content.download_url,
        )

    async def _create_or_update_file(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Create or update a file in the repository."""
        repo_name = self._get_repo_name(context)
        file_path = context.input_data.get("path")
        content = context.input_data.get("content", "")
        commit_message = context.input_data.get("commit_message", f"Update {file_path}")
        branch = context.input_data.get("branch", "main")
        sha = context.input_data.get("sha")  # Required for updates

        if not repo_name or not file_path:
            return self._create_spec_error_result(
                "Repository name and path required",
                "create_or_update_file",
                {"missing_parameters": ["owner", "repo", "path"]},
            )

        result = await github.create_or_update_file(
            installation_id, repo_name, file_path, content, commit_message, branch, sha
        )

        self.log_execution(context, f"✅ Created/updated file {file_path}")

        return self._create_spec_success_result("create_or_update_file", result)

    # ============================================================================
    # Branch Operations
    # ============================================================================

    async def _create_branch(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Create a new branch."""
        repo_name = self._get_repo_name(context)
        branch_name = context.input_data.get("branch") or context.input_data.get("branch_name")
        from_branch = context.input_data.get("from_branch", "main")

        if not repo_name or not branch_name:
            return self._create_spec_error_result(
                "Repository name and branch name required",
                "create_branch",
                {"missing_parameters": ["owner", "repo", "branch"]},
            )

        branch = await github.create_branch(installation_id, repo_name, branch_name, from_branch)

        self.log_execution(context, f"✅ Created branch {branch_name}")

        return self._create_spec_success_result(
            "create_branch",
            {
                "branch_name": branch.name,
                "commit_sha": branch.commit_sha,
                "protected": branch.protected,
            },
        )

    async def _delete_branch(
        self, context: NodeExecutionContext, github: GitHubSDK, installation_id: int
    ) -> NodeExecutionResult:
        """Delete a branch."""
        repo_name = self._get_repo_name(context)
        branch_name = context.input_data.get("branch") or context.input_data.get("branch_name")

        if not repo_name or not branch_name:
            return self._create_spec_error_result(
                "Repository name and branch name required",
                "delete_branch",
                {"missing_parameters": ["owner", "repo", "branch"]},
            )

        success = await github.delete_branch(installation_id, repo_name, branch_name)

        if success:
            self.log_execution(context, f"✅ Deleted branch {branch_name}")
            return self._create_spec_success_result(
                "delete_branch", {"deleted": True, "branch_name": branch_name}
            )
        else:
            return self._create_spec_error_result(
                f"Branch {branch_name} not found or could not be deleted",
                "delete_branch",
                {"reason": "branch_not_found_or_protected"},
            )


__all__ = ["GitHubExternalAction"]
