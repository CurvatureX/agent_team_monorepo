"""Main GitHub SDK client."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .auth import GitHubAuth
from .exceptions import (
    GitHubAuthError,
    GitHubError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
)
from .issues import IssueMixin
from .models import (
    Branch,
    Comment,
    Commit,
    FileContent,
    GitHubUser,
    Installation,
    Issue,
    PullRequest,
    Repository,
)
from .pulls import PullRequestMixin


class GitHubSDK(PullRequestMixin, IssueMixin):
    """Main GitHub SDK client for GitHub App operations."""

    def __init__(self, app_id: str, private_key: str, base_url: str = "https://api.github.com"):
        self.app_id = app_id
        self.base_url = base_url
        self.auth = GitHubAuth(app_id, private_key)
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "AI-Workflow-Teams-SDK/1.0.0",
            },
        )

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _handle_response_error(self, response: httpx.Response, context: str = ""):
        """Handle HTTP response errors and convert to appropriate exceptions."""
        if response.status_code == 401:
            raise GitHubAuthError(f"Authentication failed: {context}")
        elif response.status_code == 403:
            if "rate limit" in response.text.lower():
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                raise GitHubRateLimitError(
                    f"Rate limit exceeded: {context}", reset_time=reset_time, status_code=403
                )
            else:
                raise GitHubPermissionError(f"Permission denied: {context}")
        elif response.status_code == 404:
            raise GitHubNotFoundError(f"Resource not found: {context}")
        elif response.status_code >= 400:
            try:
                error_data = response.json()
            except:
                error_data = {}

            raise GitHubError(
                f"GitHub API error: {context}",
                status_code=response.status_code,
                response_data=error_data,
            )

    async def get_installation_token(self, installation_id: int) -> str:
        """Get installation access token."""
        # Check cache first
        cached_token = self.auth.get_cached_installation_token(installation_id)
        if cached_token:
            return cached_token

        # Generate new token
        jwt_token = self.auth.generate_jwt_token()

        response = await self._client.post(
            f"{self.base_url}/app/installations/{installation_id}/access_tokens",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        if response.status_code != 201:
            self._handle_response_error(
                response, f"Getting installation token for {installation_id}"
            )

        token_data = response.json()

        # Cache the token
        self.auth.cache_installation_token(
            installation_id, token_data["token"], token_data["expires_at"]
        )

        return token_data["token"]

    async def _make_authenticated_request(
        self, method: str, url: str, installation_id: int, **kwargs
    ) -> httpx.Response:
        """Make an authenticated request using installation token."""
        token = await self.get_installation_token(installation_id)

        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"token {token}"
        kwargs["headers"] = headers

        response = await self._client.request(method, url, **kwargs)
        return response

    # Repository operations

    async def list_repositories(self, installation_id: int) -> List[Repository]:
        """List repositories accessible to the installation."""
        response = await self._make_authenticated_request(
            "GET", f"{self.base_url}/installation/repositories", installation_id
        )

        if response.status_code != 200:
            self._handle_response_error(response, "Listing repositories")

        data = response.json()
        return [Repository(**repo) for repo in data["repositories"]]

    async def get_repository(self, installation_id: int, repo_name: str) -> Repository:
        """Get repository details."""
        response = await self._make_authenticated_request(
            "GET", f"{self.base_url}/repos/{repo_name}", installation_id
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Getting repository {repo_name}")

        return Repository(**response.json())

    async def get_file_content(
        self, installation_id: int, repo_name: str, file_path: str, ref: str = "main"
    ) -> FileContent:
        """Get file content from repository."""
        response = await self._make_authenticated_request(
            "GET",
            f"{self.base_url}/repos/{repo_name}/contents/{file_path}",
            installation_id,
            params={"ref": ref},
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Getting file {file_path} from {repo_name}")

        data = response.json()

        # Decode content if base64 encoded
        content = data["content"]
        if data["encoding"] == "base64":
            import base64

            content = base64.b64decode(content).decode("utf-8")

        return FileContent(
            path=data["path"],
            content=content,
            encoding=data["encoding"],
            size=data["size"],
            sha=data["sha"],
            download_url=data["download_url"],
        )

    async def create_or_update_file(
        self,
        installation_id: int,
        repo_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str = "main",
        sha: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update a file in the repository."""
        import base64

        payload = {
            "message": commit_message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }

        if sha:  # Update existing file
            payload["sha"] = sha

        response = await self._make_authenticated_request(
            "PUT",
            f"{self.base_url}/repos/{repo_name}/contents/{file_path}",
            installation_id,
            json=payload,
        )

        if response.status_code not in [200, 201]:
            self._handle_response_error(response, f"Creating/updating file {file_path}")

        return response.json()

    async def create_branch(
        self, installation_id: int, repo_name: str, branch_name: str, from_branch: str = "main"
    ) -> Branch:
        """Create a new branch."""
        # Get the SHA of the source branch
        response = await self._make_authenticated_request(
            "GET", f"{self.base_url}/repos/{repo_name}/git/ref/heads/{from_branch}", installation_id
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Getting reference for branch {from_branch}")

        source_sha = response.json()["object"]["sha"]

        # Create new branch
        payload = {"ref": f"refs/heads/{branch_name}", "sha": source_sha}

        response = await self._make_authenticated_request(
            "POST", f"{self.base_url}/repos/{repo_name}/git/refs", installation_id, json=payload
        )

        if response.status_code != 201:
            self._handle_response_error(response, f"Creating branch {branch_name}")

        return Branch(name=branch_name, commit_sha=source_sha, protected=False)

    async def delete_branch(self, installation_id: int, repo_name: str, branch_name: str) -> bool:
        """Delete a branch."""
        response = await self._make_authenticated_request(
            "DELETE",
            f"{self.base_url}/repos/{repo_name}/git/refs/heads/{branch_name}",
            installation_id,
        )

        if response.status_code == 204:
            return True
        elif response.status_code == 404:
            return False  # Branch doesn't exist
        else:
            self._handle_response_error(response, f"Deleting branch {branch_name}")
            return False

    # Pull Request operations (will be implemented in separate file)
    # Issue operations (will be implemented in separate file)
    # Additional utility methods
