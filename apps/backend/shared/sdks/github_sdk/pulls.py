"""Pull request operations for GitHub SDK."""

from typing import Any, Dict, List, Optional

import httpx

from .exceptions import GitHubError
from .models import Comment, GitHubUser, PullRequest


class PullRequestMixin:
    """Mixin class for pull request operations."""

    async def list_pull_requests(
        self,
        installation_id: int,
        repo_name: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc",
    ) -> List[PullRequest]:
        """List pull requests for a repository."""
        response = await self._make_authenticated_request(
            "GET",
            f"{self.base_url}/repos/{repo_name}/pulls",
            installation_id,
            params={"state": state, "sort": sort, "direction": direction},
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Listing PRs for {repo_name}")

        prs = []
        for pr_data in response.json():
            prs.append(self._parse_pull_request(pr_data))

        return prs

    async def get_pull_request(
        self, installation_id: int, repo_name: str, pr_number: int
    ) -> PullRequest:
        """Get a specific pull request."""
        response = await self._make_authenticated_request(
            "GET", f"{self.base_url}/repos/{repo_name}/pulls/{pr_number}", installation_id
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Getting PR #{pr_number} from {repo_name}")

        return self._parse_pull_request(response.json())

    async def create_pull_request(
        self,
        installation_id: int,
        repo_name: str,
        title: str,
        head_branch: str,
        base_branch: str = "main",
        body: Optional[str] = None,
        draft: bool = False,
    ) -> PullRequest:
        """Create a new pull request."""
        payload = {"title": title, "head": head_branch, "base": base_branch, "draft": draft}

        if body:
            payload["body"] = body

        response = await self._make_authenticated_request(
            "POST", f"{self.base_url}/repos/{repo_name}/pulls", installation_id, json=payload
        )

        if response.status_code != 201:
            self._handle_response_error(response, f"Creating PR in {repo_name}")

        return self._parse_pull_request(response.json())

    async def update_pull_request(
        self,
        installation_id: int,
        repo_name: str,
        pr_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
    ) -> PullRequest:
        """Update a pull request."""
        payload = {}

        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state

        if not payload:
            raise ValueError("At least one field must be updated")

        response = await self._make_authenticated_request(
            "PATCH",
            f"{self.base_url}/repos/{repo_name}/pulls/{pr_number}",
            installation_id,
            json=payload,
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Updating PR #{pr_number} in {repo_name}")

        return self._parse_pull_request(response.json())

    async def merge_pull_request(
        self,
        installation_id: int,
        repo_name: str,
        pr_number: int,
        commit_title: Optional[str] = None,
        commit_message: Optional[str] = None,
        merge_method: str = "merge",  # "merge", "squash", "rebase"
    ) -> Dict[str, Any]:
        """Merge a pull request."""
        payload = {"merge_method": merge_method}

        if commit_title:
            payload["commit_title"] = commit_title
        if commit_message:
            payload["commit_message"] = commit_message

        response = await self._make_authenticated_request(
            "PUT",
            f"{self.base_url}/repos/{repo_name}/pulls/{pr_number}/merge",
            installation_id,
            json=payload,
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Merging PR #{pr_number} in {repo_name}")

        return response.json()

    async def get_pull_request_diff(
        self, installation_id: int, repo_name: str, pr_number: int
    ) -> str:
        """Get pull request diff."""
        response = await self._make_authenticated_request(
            "GET",
            f"{self.base_url}/repos/{repo_name}/pulls/{pr_number}",
            installation_id,
            headers={"Accept": "application/vnd.github.v3.diff"},
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Getting diff for PR #{pr_number}")

        return response.text

    async def get_pull_request_files(
        self, installation_id: int, repo_name: str, pr_number: int
    ) -> List[Dict[str, Any]]:
        """Get files changed in a pull request."""
        response = await self._make_authenticated_request(
            "GET", f"{self.base_url}/repos/{repo_name}/pulls/{pr_number}/files", installation_id
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Getting files for PR #{pr_number}")

        return response.json()

    async def list_pull_request_comments(
        self, installation_id: int, repo_name: str, pr_number: int
    ) -> List[Comment]:
        """List comments on a pull request."""
        response = await self._make_authenticated_request(
            "GET", f"{self.base_url}/repos/{repo_name}/issues/{pr_number}/comments", installation_id
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Getting comments for PR #{pr_number}")

        comments = []
        for comment_data in response.json():
            comments.append(self._parse_comment(comment_data))

        return comments

    async def create_pull_request_comment(
        self, installation_id: int, repo_name: str, pr_number: int, body: str
    ) -> Comment:
        """Create a comment on a pull request."""
        payload = {"body": body}

        response = await self._make_authenticated_request(
            "POST",
            f"{self.base_url}/repos/{repo_name}/issues/{pr_number}/comments",
            installation_id,
            json=payload,
        )

        if response.status_code != 201:
            self._handle_response_error(response, f"Creating comment on PR #{pr_number}")

        return self._parse_comment(response.json())

    async def update_pull_request_comment(
        self, installation_id: int, repo_name: str, comment_id: int, body: str
    ) -> Comment:
        """Update a pull request comment."""
        payload = {"body": body}

        response = await self._make_authenticated_request(
            "PATCH",
            f"{self.base_url}/repos/{repo_name}/issues/comments/{comment_id}",
            installation_id,
            json=payload,
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Updating comment {comment_id}")

        return self._parse_comment(response.json())

    async def delete_pull_request_comment(
        self, installation_id: int, repo_name: str, comment_id: int
    ) -> bool:
        """Delete a pull request comment."""
        response = await self._make_authenticated_request(
            "DELETE",
            f"{self.base_url}/repos/{repo_name}/issues/comments/{comment_id}",
            installation_id,
        )

        return response.status_code == 204

    async def request_pull_request_reviewers(
        self,
        installation_id: int,
        repo_name: str,
        pr_number: int,
        reviewers: List[str],
        team_reviewers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Request reviewers for a pull request."""
        payload = {"reviewers": reviewers}

        if team_reviewers:
            payload["team_reviewers"] = team_reviewers

        response = await self._make_authenticated_request(
            "POST",
            f"{self.base_url}/repos/{repo_name}/pulls/{pr_number}/requested_reviewers",
            installation_id,
            json=payload,
        )

        if response.status_code != 201:
            self._handle_response_error(response, f"Requesting reviewers for PR #{pr_number}")

        return response.json()

    def _parse_pull_request(self, data: Dict[str, Any]) -> PullRequest:
        """Parse GitHub API pull request data into PullRequest model."""
        from datetime import datetime

        return PullRequest(
            id=data["id"],
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=data["state"],
            draft=data.get("draft", False),
            merged=data.get("merged", False),
            mergeable=data.get("mergeable"),
            author=GitHubUser(**data["user"]),
            assignees=[GitHubUser(**u) for u in data.get("assignees", [])],
            reviewers=[GitHubUser(**u) for u in data.get("requested_reviewers", [])],
            head_branch=data["head"]["ref"],
            head_sha=data["head"]["sha"],
            base_branch=data["base"]["ref"],
            base_sha=data["base"]["sha"],
            html_url=data["html_url"],
            diff_url=data["diff_url"],
            patch_url=data["patch_url"],
            commits=data.get("commits", 0),
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
            changed_files=data.get("changed_files", 0),
            labels=[label["name"] for label in data.get("labels", [])],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            closed_at=datetime.fromisoformat(data["closed_at"].replace("Z", "+00:00"))
            if data.get("closed_at")
            else None,
            merged_at=datetime.fromisoformat(data["merged_at"].replace("Z", "+00:00"))
            if data.get("merged_at")
            else None,
        )

    def _parse_comment(self, data: Dict[str, Any]) -> Comment:
        """Parse GitHub API comment data into Comment model."""
        from datetime import datetime

        return Comment(
            id=data["id"],
            body=data["body"],
            author=GitHubUser(**data["user"]),
            html_url=data["html_url"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
        )
