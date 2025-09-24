"""
GitHub OAuth2 Client for workflow integration.

This provides GitHub OAuth2 authentication compatible with the BaseSDK pattern.
"""

import os
from typing import Any, Dict, Optional

from ..base import APIResponse, BaseSDK, OAuth2Config
from .exceptions import GitHubAuthError, GitHubError, GitHubRateLimitError


class GitHubOAuth2SDK(BaseSDK):
    """GitHub SDK client with OAuth2 authentication."""

    @property
    def base_url(self) -> str:
        return "https://api.github.com"

    @property
    def supported_operations(self) -> Dict[str, str]:
        ops = {
            "create_issue": "Create new issue in repository",
            "create_pull_request": "Create new pull request",
            "add_comment": "Add comment to issue or PR",
            "close_issue": "Close an issue",
            "merge_pr": "Merge a pull request",
            "list_issues": "List repository issues",
            "get_issue": "Get issue details",
            "list_repos": "List user repositories",
            "get_repo": "Get repository details",
            "create_branch": "Create new branch",
            "get_file": "Get file content",
            "create_file": "Create file in repository",
            "update_file": "Update existing file",
            "get_user": "Get authenticated user info",
        }
        # MCP-aligned aliases
        ops.update(
            {
                "github_create_issue": ops["create_issue"],
                "github_create_pull_request": ops["create_pull_request"],
                "github_add_comment": ops["add_comment"],
                "github_close_issue": ops["close_issue"],
                "github_merge_pr": ops["merge_pr"],
                "github_list_issues": ops["list_issues"],
                "github_get_issue": ops["get_issue"],
                "github_list_repos": ops["list_repos"],
                "github_get_repo": ops["get_repo"],
                "github_create_branch": ops["create_branch"],
                "github_get_file": ops["get_file"],
                "github_create_file": ops["create_file"],
                "github_update_file": ops["update_file"],
                "github_get_user": ops["get_user"],
            }
        )
        return ops

    def get_oauth2_config(self) -> OAuth2Config:
        """Get GitHub OAuth2 configuration."""
        return OAuth2Config(
            client_id=os.getenv("GITHUB_CLIENT_ID", ""),
            client_secret=os.getenv("GITHUB_CLIENT_SECRET", ""),
            auth_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            revoke_url="https://github.com/settings/connections/applications/{client_id}",
            scopes=["repo", "user:email", "read:user", "write:repo_hook"],
            redirect_uri=os.getenv(
                "GITHUB_REDIRECT_URI", "http://localhost:8002/api/v1/oauth2/github/callback"
            ),
        )

    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate GitHub credentials."""
        return "access_token" in credentials and bool(credentials["access_token"])

    async def call_operation(
        self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> APIResponse:
        """Execute GitHub API operation."""
        if not self.validate_credentials(credentials):
            return APIResponse(
                success=False,
                error="Invalid credentials: missing access_token",
                provider="github",
                operation=operation,
            )

        if operation not in self.supported_operations:
            return APIResponse(
                success=False,
                error=f"Unsupported operation: {operation}",
                provider="github",
                operation=operation,
            )

        try:
            # Route to specific operation handler
            handler_map = {
                "create_issue": self._create_issue,
                "create_pull_request": self._create_pull_request,
                "add_comment": self._add_comment,
                "close_issue": self._close_issue,
                "merge_pr": self._merge_pr,
                "list_issues": self._list_issues,
                "get_issue": self._get_issue,
                "list_repos": self._list_repos,
                "get_repo": self._get_repo,
                "create_branch": self._create_branch,
                "get_file": self._get_file,
                "create_file": self._create_file,
                "update_file": self._update_file,
                "get_user": self._get_user,
            }
            alias = {
                "github_create_issue": "create_issue",
                "github_create_pull_request": "create_pull_request",
                "github_add_comment": "add_comment",
                "github_close_issue": "close_issue",
                "github_merge_pr": "merge_pr",
                "github_list_issues": "list_issues",
                "github_get_issue": "get_issue",
                "github_list_repos": "list_repos",
                "github_get_repo": "get_repo",
                "github_create_branch": "create_branch",
                "github_get_file": "get_file",
                "github_create_file": "create_file",
                "github_update_file": "update_file",
                "github_get_user": "get_user",
            }
            op = alias.get(operation, operation)
            handler = handler_map[op]
            result = await handler(parameters, credentials)

            return APIResponse(success=True, data=result, provider="github", operation=operation)

        except GitHubAuthError as e:
            return APIResponse(
                success=False, error=str(e), provider="github", operation=operation, status_code=401
            )
        except GitHubRateLimitError as e:
            return APIResponse(
                success=False, error=str(e), provider="github", operation=operation, status_code=429
            )
        except Exception as e:
            self.logger.error(f"GitHub {operation} failed: {str(e)}")
            return APIResponse(success=False, error=str(e), provider="github", operation=operation)

    async def _create_issue(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create new issue in repository."""
        repository = parameters.get("repository")
        title = parameters.get("title")
        body = parameters.get("body", "")
        labels = parameters.get("labels", [])

        if not repository or not title:
            raise GitHubError("Missing required parameters: repository and title")

        # Parse owner/repo
        if "/" not in repository:
            raise GitHubError("Repository must be in 'owner/repo' format")
        owner, repo = repository.split("/", 1)

        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        headers = self._prepare_headers(credentials)

        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels

        response = await self.make_http_request("POST", url, headers=headers, json_data=payload)

        if not (200 <= response.status_code < 300):
            self._handle_error(response)

        issue_data = response.json()

        return {
            "issue_id": issue_data.get("id"),
            "issue_number": issue_data.get("number"),
            "title": issue_data.get("title"),
            "html_url": issue_data.get("html_url"),
            "state": issue_data.get("state"),
            "created_at": issue_data.get("created_at"),
        }

    async def _create_pull_request(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create new pull request."""
        repository = parameters.get("repository")
        title = parameters.get("title")
        head = parameters.get("head")  # branch to merge from
        base = parameters.get("base", "main")  # branch to merge to
        body = parameters.get("body", "")

        if not repository or not title or not head:
            raise GitHubError("Missing required parameters: repository, title, and head")

        # Parse owner/repo
        if "/" not in repository:
            raise GitHubError("Repository must be in 'owner/repo' format")
        owner, repo = repository.split("/", 1)

        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        headers = self._prepare_headers(credentials)

        payload = {"title": title, "head": head, "base": base, "body": body}

        response = await self.make_http_request("POST", url, headers=headers, json_data=payload)

        if not (200 <= response.status_code < 300):
            self._handle_error(response)

        pr_data = response.json()

        return {
            "pr_id": pr_data.get("id"),
            "pr_number": pr_data.get("number"),
            "title": pr_data.get("title"),
            "html_url": pr_data.get("html_url"),
            "state": pr_data.get("state"),
            "created_at": pr_data.get("created_at"),
            "mergeable": pr_data.get("mergeable"),
        }

    async def _list_issues(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """List repository issues."""
        repository = parameters.get("repository")
        state = parameters.get("state", "open")  # open, closed, all
        per_page = min(int(parameters.get("per_page", 30)), 100)

        if not repository:
            raise GitHubError("Missing required parameter: repository")

        # Parse owner/repo
        if "/" not in repository:
            raise GitHubError("Repository must be in 'owner/repo' format")
        owner, repo = repository.split("/", 1)

        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        headers = self._prepare_headers(credentials)

        params = {"state": state, "per_page": per_page}

        response = await self.make_http_request("GET", url, headers=headers, params=params)

        if not (200 <= response.status_code < 300):
            self._handle_error(response)

        issues_data = response.json()

        # Filter out pull requests (GitHub API includes PRs in issues)
        issues = [
            {
                "id": issue.get("id"),
                "number": issue.get("number"),
                "title": issue.get("title"),
                "body": issue.get("body"),
                "state": issue.get("state"),
                "html_url": issue.get("html_url"),
                "created_at": issue.get("created_at"),
                "updated_at": issue.get("updated_at"),
                "labels": [label.get("name") for label in issue.get("labels", [])],
            }
            for issue in issues_data
            if not issue.get("pull_request")  # Exclude pull requests
        ]

        return {"issues": issues, "total_count": len(issues)}

    async def _get_user(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get authenticated user info."""
        url = f"{self.base_url}/user"
        headers = self._prepare_headers(credentials)

        response = await self.make_http_request("GET", url, headers=headers)

        if not (200 <= response.status_code < 300):
            self._handle_error(response)

        user_data = response.json()

        return {
            "id": user_data.get("id"),
            "login": user_data.get("login"),
            "name": user_data.get("name"),
            "email": user_data.get("email"),
            "avatar_url": user_data.get("avatar_url"),
            "html_url": user_data.get("html_url"),
            "public_repos": user_data.get("public_repos"),
            "followers": user_data.get("followers"),
            "following": user_data.get("following"),
        }

    async def _test_connection_impl(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """GitHub specific connection test."""
        try:
            user_info = await self._get_user({}, credentials)
            return {
                "credentials_valid": True,
                "github_access": True,
                "user_login": user_info.get("login"),
                "user_name": user_info.get("name"),
            }
        except Exception as e:
            return {"credentials_valid": False, "error": str(e)}

    def _prepare_headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """Prepare GitHub API headers."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AgentTeam-Workflow-Engine/1.0",
        }

        if "access_token" in credentials:
            headers["Authorization"] = f"Bearer {credentials['access_token']}"

        return headers

    def _handle_error(self, response) -> None:
        """Handle HTTP error responses."""
        if response.status_code == 401:
            raise GitHubAuthError("Authentication failed")
        elif response.status_code == 403:
            error_data = response.json() if response.content else {}
            if "rate limit" in str(error_data).lower():
                raise GitHubRateLimitError("Rate limit exceeded")
            else:
                raise GitHubAuthError("Forbidden - insufficient permissions")
        elif response.status_code == 404:
            raise GitHubError("Repository or resource not found")
        elif response.status_code == 422:
            error_data = response.json() if response.content else {}
            raise GitHubError(f"Validation error: {error_data}")
        elif 400 <= response.status_code < 500:
            raise GitHubError(f"Client error: {response.status_code}")
        elif 500 <= response.status_code < 600:
            raise GitHubError(f"Server error: {response.status_code}")
        else:
            raise GitHubError(f"Unexpected error: {response.status_code}")

    # Placeholder methods for other operations - can be implemented as needed
    async def _add_comment(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Add comment to issue or PR."""
        raise NotImplementedError("Add comment not yet implemented")

    async def _close_issue(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Close an issue."""
        raise NotImplementedError("Close issue not yet implemented")

    async def _merge_pr(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Merge a pull request."""
        raise NotImplementedError("Merge PR not yet implemented")

    async def _get_issue(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get issue details."""
        raise NotImplementedError("Get issue not yet implemented")

    async def _list_repos(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """List user repositories."""
        raise NotImplementedError("List repos not yet implemented")

    async def _get_repo(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get repository details."""
        raise NotImplementedError("Get repo not yet implemented")

    async def _create_branch(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create new branch."""
        raise NotImplementedError("Create branch not yet implemented")

    async def _get_file(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get file content."""
        raise NotImplementedError("Get file not yet implemented")

    async def _create_file(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create file in repository."""
        raise NotImplementedError("Create file not yet implemented")

    async def _update_file(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Update existing file."""
        raise NotImplementedError("Update file not yet implemented")
