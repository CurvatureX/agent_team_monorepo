import fnmatch
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import jwt
from github import Github, GithubIntegration

from shared.models.node_enums import TriggerSubtype
from shared.models.trigger import ExecutionResult, TriggerStatus
from workflow_scheduler.core.config import settings
from workflow_scheduler.triggers.base import BaseTrigger

# Import our GitHub SDK for enhanced functionality
try:
    from shared.sdks.github_sdk import GitHubSDK

    GITHUB_SDK_AVAILABLE = True
except ImportError:
    GITHUB_SDK_AVAILABLE = False
    logging.warning("GitHub SDK not available, using basic PyGithub client")

logger = logging.getLogger(__name__)


class GitHubTrigger(BaseTrigger):
    """GitHub App-based trigger for repository events"""

    def __init__(self, workflow_id: str, trigger_config: Dict[str, Any]):
        super().__init__(workflow_id, trigger_config)

        self.installation_id = trigger_config.get("github_app_installation_id")
        self.repository = trigger_config.get("repository")
        self.event_config = trigger_config.get("event_config", {})
        self.author_filter = trigger_config.get("author_filter")
        self.ignore_bots = trigger_config.get("ignore_bots", True)
        self.require_signature_verification = trigger_config.get(
            "require_signature_verification", True
        )

        # Extract events from event_config for backward compatibility
        self.events = list(self.event_config.keys()) if self.event_config else []

        # GitHub App configuration
        self.app_id = settings.github_app_id
        self.private_key = settings.github_app_private_key
        self.webhook_secret = settings.github_webhook_secret

        if not all([self.installation_id, self.repository, self.app_id, self.private_key]):
            raise ValueError("GitHub App configuration incomplete")

        # GitHub clients
        self._integration: Optional[GithubIntegration] = None
        self._github_client: Optional[Github] = None
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
        self._github_sdk: Optional[GitHubSDK] = None

    @property
    def trigger_type(self) -> str:
        return TriggerSubtype.GITHUB.value

    async def start(self) -> bool:
        """Start the GitHub trigger (initialize GitHub App integration)"""
        try:
            if not self.enabled:
                logger.info(f"GitHub trigger for workflow {self.workflow_id} is disabled")
                self.status = TriggerStatus.PAUSED
                return True

            # Initialize GitHub App integration
            self._integration = GithubIntegration(
                integration_id=int(self.app_id), private_key=self.private_key
            )

            # Initialize GitHub SDK if available
            if GITHUB_SDK_AVAILABLE:
                try:
                    self._github_sdk = GitHubSDK(app_id=self.app_id, private_key=self.private_key)
                    logger.info(f"GitHub SDK initialized for workflow {self.workflow_id}")
                except Exception as e:
                    logger.warning(
                        f"Failed to initialize GitHub SDK: {e}, falling back to PyGithub"
                    )

            # Test access token generation
            access_token = await self._get_access_token()
            if not access_token:
                logger.error(f"Failed to get GitHub access token for workflow {self.workflow_id}")
                self.status = TriggerStatus.ERROR
                return False

            self.status = TriggerStatus.ACTIVE
            logger.info(
                f"GitHub trigger started for workflow {self.workflow_id} on repo {self.repository}"
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to start GitHub trigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )
            self.status = TriggerStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Stop the GitHub trigger"""
        try:
            self.status = TriggerStatus.STOPPED
            self._access_token = None
            self._token_expires_at = None

            # Clean up GitHub SDK
            if self._github_sdk:
                try:
                    await self._github_sdk.close()
                except Exception as e:
                    logger.warning(f"Error closing GitHub SDK: {e}")
                finally:
                    self._github_sdk = None

            logger.info(f"GitHub trigger stopped for workflow {self.workflow_id}")

            return True

        except Exception as e:
            logger.error(
                f"Failed to stop GitHub trigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )
            return False

    async def process_github_event(
        self, event_type: str, payload: Dict[str, Any]
    ) -> Optional[ExecutionResult]:
        """
        Process GitHub webhook event

        Args:
            event_type: GitHub event type (push, pull_request, etc.)
            payload: GitHub webhook payload

        Returns:
            ExecutionResult if workflow was triggered, None if filtered out
        """
        try:
            if not self.enabled:
                logger.debug(f"GitHub trigger for workflow {self.workflow_id} is disabled")
                return None

            if self.status != TriggerStatus.ACTIVE:
                logger.warning(
                    f"GitHub trigger for workflow {self.workflow_id} is not active: {self.status.value}"
                )
                return None

            # Check if event type is in our filter
            if self.events and event_type not in self.events:
                logger.debug(
                    f"Event type {event_type} not in filter for workflow {self.workflow_id}"
                )
                return None

            # Validate repository
            repo_name = payload.get("repository", {}).get("full_name", "")
            if repo_name != self.repository:
                logger.debug(
                    f"Repository {repo_name} does not match {self.repository} for workflow {self.workflow_id}"
                )
                return None

            # Apply advanced filters
            if not await self._matches_advanced_filters(event_type, payload):
                logger.debug(
                    f"Event filtered out by advanced filters for workflow {self.workflow_id}"
                )
                return None

            # Enhance event data with repository context
            enhanced_data = await self._enhance_event_data(event_type, payload)

            # Trigger workflow
            result = await self._trigger_workflow(enhanced_data)

            if result.status == "started":
                logger.info(
                    f"GitHub trigger executed successfully for workflow {self.workflow_id}: {result.execution_id}"
                )
            else:
                logger.warning(
                    f"GitHub trigger execution had issues for workflow {self.workflow_id}: {result.message}"
                )

            return result

        except Exception as e:
            error_msg = f"Error processing GitHub event for workflow {self.workflow_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return ExecutionResult(
                status="error",
                message=error_msg,
                trigger_data={"event_type": event_type, "repository": self.repository},
            )

    async def _matches_advanced_filters(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Apply advanced filtering logic using new event_config structure"""
        try:
            # Bot filter (global)
            if self.ignore_bots:
                sender = payload.get("sender", {})
                if sender.get("type") == "Bot" or "[bot]" in sender.get("login", "").lower():
                    logger.debug(f"Ignoring bot event from {sender.get('login')}")
                    return False

            # Global author filter
            if self.author_filter:
                author = self._get_event_author(event_type, payload)
                if author and not re.match(self.author_filter, author):
                    logger.debug(f"Author {author} does not match filter {self.author_filter}")
                    return False

            # Event-specific filters from event_config
            event_filters = self.event_config.get(event_type, {})
            if not event_filters:
                # If no specific config for this event, allow it (backward compatibility)
                return True

            # Apply event-specific filters
            return await self._apply_event_specific_filters(event_type, payload, event_filters)

        except Exception as e:
            logger.error(f"Error in advanced filtering: {e}", exc_info=True)
            return False

    async def _apply_event_specific_filters(
        self, event_type: str, payload: Dict[str, Any], filters: Dict[str, Any]
    ) -> bool:
        """Apply filters specific to the event type"""

        # Branch filter
        if "branches" in filters and event_type in ["push", "pull_request"]:
            if event_type == "push":
                ref = payload.get("ref", "")
                branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ""
            elif event_type == "pull_request":
                branch = payload.get("pull_request", {}).get("base", {}).get("ref", "")

            if branch and branch not in filters["branches"]:
                logger.debug(f"Branch {branch} not in filter {filters['branches']}")
                return False

        # Action filter
        if "actions" in filters:
            action = payload.get("action", "")
            if action not in filters["actions"]:
                logger.debug(f"Action {action} not in filter {filters['actions']}")
                return False

        # Label filter (for issues and PRs)
        if "labels" in filters and event_type in ["issues", "pull_request"]:
            event_labels = []
            if event_type == "issues":
                event_labels = [
                    label["name"] for label in payload.get("issue", {}).get("labels", [])
                ]
            elif event_type == "pull_request":
                event_labels = [
                    label["name"] for label in payload.get("pull_request", {}).get("labels", [])
                ]

            if not any(label in event_labels for label in filters["labels"]):
                logger.debug(
                    f"No matching labels found. Event labels: {event_labels}, Filter: {filters['labels']}"
                )
                return False

        # Draft PR handling
        if "draft_handling" in filters and event_type == "pull_request":
            pr = payload.get("pull_request", {})
            is_draft = pr.get("draft", False)

            if filters["draft_handling"] == "ignore" and is_draft:
                logger.debug("Ignoring draft PR")
                return False
            elif filters["draft_handling"] == "only" and not is_draft:
                logger.debug("Only accepting draft PRs")
                return False

        # Path filter (for push and PR events)
        if "paths" in filters and event_type in ["push", "pull_request"]:
            changed_files = await self._get_changed_files(event_type, payload)
            if not self._files_match_patterns(changed_files, filters["paths"]):
                logger.debug(f"No changed files match path patterns {filters['paths']}")
                return False

        # Authors filter (event-specific, different from global author_filter)
        if "authors" in filters:
            author = self._get_event_author(event_type, payload)
            if author and author not in filters["authors"]:
                logger.debug(f"Author {author} not in allowed authors {filters['authors']}")
                return False

        # Review state filter (for pull_request_review events)
        if "states" in filters and event_type == "pull_request_review":
            review_state = payload.get("review", {}).get("state", "")
            if review_state not in filters["states"]:
                logger.debug(f"Review state {review_state} not in filter {filters['states']}")
                return False

        # Workflow filter (for workflow_run events)
        if "workflows" in filters and event_type == "workflow_run":
            workflow_path = payload.get("workflow_run", {}).get("path", "")
            if workflow_path not in filters["workflows"]:
                logger.debug(f"Workflow path {workflow_path} not in filter {filters['workflows']}")
                return False

        # Conclusion filter (for workflow_run and workflow_job events)
        if "conclusions" in filters and event_type in ["workflow_run", "workflow_job"]:
            conclusion = payload.get(event_type, {}).get("conclusion", "")
            if conclusion not in filters["conclusions"]:
                logger.debug(f"Conclusion {conclusion} not in filter {filters['conclusions']}")
                return False

        # Ref type filter (for create/delete events)
        if "ref_types" in filters and event_type in ["create", "delete"]:
            ref_type = payload.get("ref_type", "")
            if ref_type not in filters["ref_types"]:
                logger.debug(f"Ref type {ref_type} not in filter {filters['ref_types']}")
                return False

        return True

    def _get_event_author(self, event_type: str, payload: Dict[str, Any]) -> Optional[str]:
        """Extract author from event payload"""
        if event_type == "push":
            commits = payload.get("commits", [])
            return commits[0]["author"]["name"] if commits else None
        elif event_type in ["pull_request", "issues"]:
            return payload.get(event_type.replace("_", ""), {}).get("user", {}).get("login")
        else:
            return payload.get("sender", {}).get("login")

    async def _get_changed_files(self, event_type: str, payload: Dict[str, Any]) -> List[str]:
        """Get list of changed files from event"""
        try:
            if event_type == "push":
                # For push events, get files from commits
                files = set()
                for commit in payload.get("commits", []):
                    files.update(commit.get("added", []))
                    files.update(commit.get("modified", []))
                    files.update(commit.get("removed", []))
                return list(files)

            elif event_type == "pull_request":
                # For PR events, we need to call GitHub API to get changed files
                access_token = await self._get_access_token()
                if not access_token:
                    return []

                pr_number = payload.get("pull_request", {}).get("number")
                if not pr_number:
                    return []

                # Call GitHub API to get PR files
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"https://api.github.com/repos/{self.repository}/pulls/{pr_number}/files",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Accept": "application/vnd.github.v3+json",
                        },
                    )

                    if response.status_code == 200:
                        files_data = response.json()
                        return [file_info["filename"] for file_info in files_data]

            return []

        except Exception as e:
            logger.error(f"Error getting changed files: {e}", exc_info=True)
            return []

    def _files_match_patterns(self, files: List[str], patterns: List[str]) -> bool:
        """Check if any files match the given patterns"""
        for file in files:
            for pattern in patterns:
                if fnmatch.fnmatch(file, pattern):
                    return True
        return False

    async def _enhance_event_data(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance event data with additional repository context"""
        try:
            enhanced_data = {
                "trigger_type": self.trigger_type,
                "event_type": event_type,
                "action": payload.get("action"),
                "repository": payload.get("repository", {}),
                "sender": payload.get("sender", {}),
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat(),
                "installation_id": self.installation_id,
            }

            # Add event-specific enhancements
            if event_type == "pull_request":
                pr_context = await self._get_pr_context(payload)
                if pr_context:
                    enhanced_data["pr_context"] = pr_context

            elif event_type == "push":
                commit_contexts = await self._get_commit_contexts(payload)
                if commit_contexts:
                    enhanced_data["commit_contexts"] = commit_contexts

            return enhanced_data

        except Exception as e:
            logger.error(f"Error enhancing event data: {e}", exc_info=True)
            return {
                "trigger_type": self.trigger_type,
                "event_type": event_type,
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _get_pr_context(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get additional PR context using GitHub API"""
        try:
            pr_number = payload.get("pull_request", {}).get("number")
            if not pr_number:
                return None

            # Use GitHub SDK if available for enhanced functionality
            if self._github_sdk and GITHUB_SDK_AVAILABLE:
                try:
                    # Get comprehensive PR context using our SDK
                    pr_data = await self._github_sdk.get_pull_request(
                        self.installation_id, self.repository, pr_number
                    )

                    pr_files = await self._github_sdk.get_pull_request_files(
                        self.installation_id, self.repository, pr_number
                    )

                    pr_comments = await self._github_sdk.list_pull_request_comments(
                        self.installation_id, self.repository, pr_number
                    )

                    # Try to get PR diff
                    pr_diff = None
                    try:
                        pr_diff = await self._github_sdk.get_pull_request_diff(
                            self.installation_id, self.repository, pr_number
                        )
                    except Exception as e:
                        logger.debug(f"Could not get PR diff: {e}")

                    return {
                        "pr_details": pr_data.dict(),
                        "files": pr_files,
                        "comments": [comment.dict() for comment in pr_comments],
                        "diff": pr_diff,
                        "source": "github_sdk",
                    }

                except Exception as e:
                    logger.warning(
                        f"GitHub SDK failed to get PR context, falling back to httpx: {e}"
                    )

            # Fallback to direct API calls
            access_token = await self._get_access_token()
            if not access_token:
                return None

            async with httpx.AsyncClient() as client:
                # Get PR details
                pr_response = await client.get(
                    f"https://api.github.com/repos/{self.repository}/pulls/{pr_number}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )

                pr_context = {
                    "pr_details": pr_response.json() if pr_response.status_code == 200 else None,
                    "source": "direct_api",
                }

                # Get PR files
                files_response = await client.get(
                    f"https://api.github.com/repos/{self.repository}/pulls/{pr_number}/files",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )

                pr_context["files"] = (
                    files_response.json() if files_response.status_code == 200 else []
                )

                return pr_context

        except Exception as e:
            logger.error(f"Error getting PR context: {e}", exc_info=True)
            return None

    async def _get_commit_contexts(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get additional commit contexts using GitHub API"""
        try:
            access_token = await self._get_access_token()
            if not access_token:
                return []

            commit_contexts = []

            for commit in payload.get("commits", []):
                commit_sha = commit.get("id")
                if not commit_sha:
                    continue

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"https://api.github.com/repos/{self.repository}/commits/{commit_sha}",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Accept": "application/vnd.github.v3+json",
                        },
                    )

                    if response.status_code == 200:
                        commit_contexts.append(response.json())

            return commit_contexts

        except Exception as e:
            logger.error(f"Error getting commit contexts: {e}", exc_info=True)
            return []

    async def _get_access_token(self) -> Optional[str]:
        """Get GitHub App access token"""
        try:
            # Check if current token is still valid
            current_time = time.time()
            if (
                self._access_token
                and self._token_expires_at
                and current_time < self._token_expires_at - 60
            ):
                return self._access_token

            # Generate new token
            if not self._integration:
                return None

            token_data = self._integration.get_access_token(int(self.installation_id))
            self._access_token = token_data.token

            # Tokens expire in 1 hour, we'll refresh 1 minute early
            self._token_expires_at = current_time + 3540  # 59 minutes

            return self._access_token

        except Exception as e:
            logger.error(f"Error getting GitHub access token: {e}", exc_info=True)
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Return health status of the GitHub trigger"""
        base_health = await super().health_check()

        github_health = {
            **base_health,
            "repository": self.repository,
            "installation_id": self.installation_id,
            "events": self.events,
            "has_access_token": self._access_token is not None,
            "token_expires_soon": False,
            "github_sdk_available": GITHUB_SDK_AVAILABLE,
            "using_github_sdk": self._github_sdk is not None,
        }

        # Check token expiration
        if self._token_expires_at:
            time_until_expiry = self._token_expires_at - time.time()
            github_health["token_expires_soon"] = time_until_expiry < 300  # 5 minutes

        return github_health
