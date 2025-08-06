"""Issue operations for GitHub SDK."""

from typing import Any, Dict, List, Optional

import httpx

from .exceptions import GitHubError
from .models import Comment, GitHubUser, Issue


class IssueMixin:
    """Mixin class for issue operations."""

    async def list_issues(
        self,
        installation_id: int,
        repo_name: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        sort: str = "created",
        direction: str = "desc",
    ) -> List[Issue]:
        """List issues for a repository."""
        params = {"state": state, "sort": sort, "direction": direction}

        if labels:
            params["labels"] = ",".join(labels)
        if assignee:
            params["assignee"] = assignee

        response = await self._make_authenticated_request(
            "GET", f"{self.base_url}/repos/{repo_name}/issues", installation_id, params=params
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Listing issues for {repo_name}")

        issues = []
        for issue_data in response.json():
            # Skip pull requests (GitHub API includes PRs in issues endpoint)
            if "pull_request" not in issue_data:
                issues.append(self._parse_issue(issue_data))

        return issues

    async def get_issue(self, installation_id: int, repo_name: str, issue_number: int) -> Issue:
        """Get a specific issue."""
        response = await self._make_authenticated_request(
            "GET", f"{self.base_url}/repos/{repo_name}/issues/{issue_number}", installation_id
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Getting issue #{issue_number} from {repo_name}")

        return self._parse_issue(response.json())

    async def create_issue(
        self,
        installation_id: int,
        repo_name: str,
        title: str,
        body: Optional[str] = None,
        assignees: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        milestone: Optional[int] = None,
    ) -> Issue:
        """Create a new issue."""
        payload = {"title": title}

        if body:
            payload["body"] = body
        if assignees:
            payload["assignees"] = assignees
        if labels:
            payload["labels"] = labels
        if milestone:
            payload["milestone"] = milestone

        response = await self._make_authenticated_request(
            "POST", f"{self.base_url}/repos/{repo_name}/issues", installation_id, json=payload
        )

        if response.status_code != 201:
            self._handle_response_error(response, f"Creating issue in {repo_name}")

        return self._parse_issue(response.json())

    async def update_issue(
        self,
        installation_id: int,
        repo_name: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        assignees: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
    ) -> Issue:
        """Update an issue."""
        payload = {}

        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if assignees is not None:
            payload["assignees"] = assignees
        if labels is not None:
            payload["labels"] = labels

        if not payload:
            raise ValueError("At least one field must be updated")

        response = await self._make_authenticated_request(
            "PATCH",
            f"{self.base_url}/repos/{repo_name}/issues/{issue_number}",
            installation_id,
            json=payload,
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Updating issue #{issue_number} in {repo_name}")

        return self._parse_issue(response.json())

    async def close_issue(self, installation_id: int, repo_name: str, issue_number: int) -> Issue:
        """Close an issue."""
        return await self.update_issue(installation_id, repo_name, issue_number, state="closed")

    async def reopen_issue(self, installation_id: int, repo_name: str, issue_number: int) -> Issue:
        """Reopen an issue."""
        return await self.update_issue(installation_id, repo_name, issue_number, state="open")

    async def add_labels_to_issue(
        self, installation_id: int, repo_name: str, issue_number: int, labels: List[str]
    ) -> List[str]:
        """Add labels to an issue."""
        response = await self._make_authenticated_request(
            "POST",
            f"{self.base_url}/repos/{repo_name}/issues/{issue_number}/labels",
            installation_id,
            json=labels,
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Adding labels to issue #{issue_number}")

        return [label["name"] for label in response.json()]

    async def remove_label_from_issue(
        self, installation_id: int, repo_name: str, issue_number: int, label: str
    ) -> bool:
        """Remove a label from an issue."""
        response = await self._make_authenticated_request(
            "DELETE",
            f"{self.base_url}/repos/{repo_name}/issues/{issue_number}/labels/{label}",
            installation_id,
        )

        return response.status_code == 200

    async def assign_issue(
        self, installation_id: int, repo_name: str, issue_number: int, assignees: List[str]
    ) -> Dict[str, Any]:
        """Assign users to an issue."""
        payload = {"assignees": assignees}

        response = await self._make_authenticated_request(
            "POST",
            f"{self.base_url}/repos/{repo_name}/issues/{issue_number}/assignees",
            installation_id,
            json=payload,
        )

        if response.status_code != 201:
            self._handle_response_error(response, f"Assigning users to issue #{issue_number}")

        return response.json()

    async def unassign_issue(
        self, installation_id: int, repo_name: str, issue_number: int, assignees: List[str]
    ) -> Dict[str, Any]:
        """Unassign users from an issue."""
        payload = {"assignees": assignees}

        response = await self._make_authenticated_request(
            "DELETE",
            f"{self.base_url}/repos/{repo_name}/issues/{issue_number}/assignees",
            installation_id,
            json=payload,
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Unassigning users from issue #{issue_number}")

        return response.json()

    async def list_issue_comments(
        self, installation_id: int, repo_name: str, issue_number: int
    ) -> List[Comment]:
        """List comments on an issue."""
        response = await self._make_authenticated_request(
            "GET",
            f"{self.base_url}/repos/{repo_name}/issues/{issue_number}/comments",
            installation_id,
        )

        if response.status_code != 200:
            self._handle_response_error(response, f"Getting comments for issue #{issue_number}")

        comments = []
        for comment_data in response.json():
            comments.append(self._parse_comment(comment_data))

        return comments

    async def create_issue_comment(
        self, installation_id: int, repo_name: str, issue_number: int, body: str
    ) -> Comment:
        """Create a comment on an issue."""
        payload = {"body": body}

        response = await self._make_authenticated_request(
            "POST",
            f"{self.base_url}/repos/{repo_name}/issues/{issue_number}/comments",
            installation_id,
            json=payload,
        )

        if response.status_code != 201:
            self._handle_response_error(response, f"Creating comment on issue #{issue_number}")

        return self._parse_comment(response.json())

    async def update_issue_comment(
        self, installation_id: int, repo_name: str, comment_id: int, body: str
    ) -> Comment:
        """Update an issue comment."""
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

    async def delete_issue_comment(
        self, installation_id: int, repo_name: str, comment_id: int
    ) -> bool:
        """Delete an issue comment."""
        response = await self._make_authenticated_request(
            "DELETE",
            f"{self.base_url}/repos/{repo_name}/issues/comments/{comment_id}",
            installation_id,
        )

        return response.status_code == 204

    def _parse_issue(self, data: Dict[str, Any]) -> Issue:
        """Parse GitHub API issue data into Issue model."""
        from datetime import datetime

        return Issue(
            id=data["id"],
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=data["state"],
            author=GitHubUser(**data["user"]),
            assignees=[GitHubUser(**u) for u in data.get("assignees", [])],
            labels=[label["name"] for label in data.get("labels", [])],
            milestone=data.get("milestone", {}).get("title") if data.get("milestone") else None,
            comments=data.get("comments", 0),
            html_url=data["html_url"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            closed_at=datetime.fromisoformat(data["closed_at"].replace("Z", "+00:00"))
            if data.get("closed_at")
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
