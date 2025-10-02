"""
Event Router for fast trigger matching and workflow execution

This module implements the core trigger reverse lookup and matching mechanism
according to the workflow-scheduler architecture specification.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from shared.models.db_models import get_database_engine
from shared.models.node_enums import TriggerSubtype
from shared.models.trigger_index import GitHubWebhookEvent, TriggerIndex
from shared.models.workflow_new import WorkflowExecutionResponse
from workflow_scheduler.core.config import settings

logger = logging.getLogger(__name__)


class EventRouter:
    """
    Fast event router for trigger matching using database indexing

    This class implements the core "触发器反查和匹配机制" (trigger reverse lookup
    and matching mechanism) for optimized event processing.
    """

    def __init__(self):
        """Initialize the EventRouter with database session"""
        self.engine = get_database_engine(settings.database_url, echo=settings.debug)
        self.session_factory = sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def route_cron_event(
        self, cron_expression: str, timezone: str = "UTC"
    ) -> List[Dict[str, Any]]:
        """
        Route cron trigger events to matching workflows

        Args:
            cron_expression: Cron expression that triggered
            timezone: Timezone for the cron execution

        Returns:
            List of matching workflow information
        """
        try:
            logger.debug(f"Routing cron event: {cron_expression} (timezone: {timezone})")

            async with self.session_factory() as session:
                # Query for active cron triggers using unified index_key
                query = session.query(TriggerIndex).filter(
                    and_(
                        TriggerIndex.trigger_type == TriggerSubtype.CRON.value,
                        TriggerIndex.index_key == cron_expression,
                        TriggerIndex.deployment_status == "active",
                    )
                )

                result = await session.execute(query)
                matching_triggers = result.scalars().all()

                workflow_matches = []
                for trigger in matching_triggers:
                    workflow_matches.append(
                        {
                            "workflow_id": str(trigger.workflow_id),
                            "trigger_type": trigger.trigger_type,
                            "trigger_config": trigger.trigger_config,
                            "trigger_data": {
                                "cron_expression": cron_expression,
                                "timezone": timezone,
                                "execution_time": datetime.utcnow().isoformat(),
                            },
                        }
                    )

                logger.info(
                    f"Found {len(workflow_matches)} workflows matching cron: {cron_expression}"
                )
                return workflow_matches

        except Exception as e:
            logger.error(f"Error routing cron event {cron_expression}: {e}", exc_info=True)
            return []

    async def route_webhook_event(
        self,
        path: str,
        method: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        remote_addr: str,
    ) -> List[Dict[str, Any]]:
        """
        Route webhook events to matching workflows

        Args:
            path: Webhook URL path
            method: HTTP method
            headers: Request headers
            payload: Request payload
            remote_addr: Remote IP address

        Returns:
            List of matching workflow information
        """
        try:
            logger.debug(f"Routing webhook event: {method} {path}")

            async with self.session_factory() as session:
                # Query for active webhook triggers using unified index_key
                query = session.query(TriggerIndex).filter(
                    and_(
                        TriggerIndex.trigger_type == TriggerSubtype.WEBHOOK.value,
                        TriggerIndex.index_key == path,
                        TriggerIndex.deployment_status == "active",
                    )
                )

                result = await session.execute(query)
                matching_triggers = result.scalars().all()

                workflow_matches = []
                for trigger in matching_triggers:
                    # Additional validation based on trigger configuration
                    config = trigger.trigger_config or {}

                    # Check if HTTP method matches (if specified in config)
                    allowed_methods = config.get(
                        "allowed_methods", ["GET", "POST", "PUT", "DELETE", "PATCH"]
                    )
                    if method.upper() not in allowed_methods:
                        continue

                    workflow_matches.append(
                        {
                            "workflow_id": str(trigger.workflow_id),
                            "trigger_type": trigger.trigger_type,
                            "trigger_config": trigger.trigger_config,
                            "trigger_data": {
                                "path": path,
                                "method": method,
                                "headers": headers,
                                "payload": payload,
                                "remote_addr": remote_addr,
                                "received_at": datetime.utcnow().isoformat(),
                            },
                        }
                    )

                logger.info(
                    f"Found {len(workflow_matches)} workflows matching webhook: {method} {path}"
                )
                return workflow_matches

        except Exception as e:
            logger.error(f"Error routing webhook event {path}: {e}", exc_info=True)
            return []

    async def route_github_event(
        self,
        event_type: str,
        delivery_id: str,
        payload: Dict[str, Any],
        signature: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Route GitHub webhook events to matching workflows using unified index_key design

        Args:
            event_type: GitHub event type (push, pull_request, etc.)
            delivery_id: GitHub delivery ID
            payload: GitHub webhook payload
            signature: GitHub webhook signature

        Returns:
            List of matching workflow information
        """
        try:
            logger.debug(f"Routing GitHub event: {event_type} (delivery: {delivery_id})")

            # Store the webhook event for debugging and analysis
            await self._store_github_event(event_type, delivery_id, payload)

            async with self.session_factory() as session:
                # Extract repository information from payload
                repository_info = payload.get("repository", {})
                repo_full_name = repository_info.get("full_name", "")

                # 1. Fast lookup using unified index_key (repository name)
                query = session.query(TriggerIndex).filter(
                    and_(
                        TriggerIndex.trigger_type == TriggerSubtype.GITHUB.value,
                        TriggerIndex.index_key == repo_full_name,
                        TriggerIndex.deployment_status == "active",
                    )
                )

                result = await session.execute(query)
                candidate_triggers = result.scalars().all()

                # 2. Detailed matching using trigger_config
                workflow_matches = []
                for trigger in candidate_triggers:
                    if self._validate_github_trigger_detailed(trigger, event_type, payload):
                        workflow_matches.append(
                            {
                                "workflow_id": str(trigger.workflow_id),
                                "trigger_type": trigger.trigger_type,
                                "trigger_config": trigger.trigger_config,
                                "trigger_data": {
                                    "event_type": event_type,
                                    "delivery_id": delivery_id,
                                    "payload": payload,
                                    "signature": signature,
                                    "repository": repo_full_name,
                                    "received_at": datetime.utcnow().isoformat(),
                                },
                            }
                        )

                logger.info(
                    f"Found {len(workflow_matches)} workflows matching GitHub event: {event_type} from {repo_full_name}"
                )
                return workflow_matches

        except Exception as e:
            logger.error(f"Error routing GitHub event {event_type}: {e}", exc_info=True)
            return []

    async def route_email_event(
        self,
        sender: str,
        subject: str,
        body: str,
        recipients: List[str],
        headers: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        Route email events to matching workflows

        Args:
            sender: Email sender address
            subject: Email subject line
            body: Email body content
            recipients: List of recipient addresses
            headers: Email headers

        Returns:
            List of matching workflow information
        """
        try:
            logger.debug(f"Routing email event from: {sender}")

            async with self.session_factory() as session:
                # Query for active email triggers using unified index_key
                query = session.query(TriggerIndex).filter(
                    and_(
                        TriggerIndex.trigger_type == TriggerSubtype.EMAIL.value,
                        TriggerIndex.deployment_status == "active",
                    )
                )

                result = await session.execute(query)
                matching_triggers = result.scalars().all()

                workflow_matches = []
                for trigger in matching_triggers:
                    # Check if email matches the trigger filter
                    if await self._matches_email_filter(trigger, sender, subject, body, recipients):
                        workflow_matches.append(
                            {
                                "workflow_id": str(trigger.workflow_id),
                                "trigger_type": trigger.trigger_type,
                                "trigger_config": trigger.trigger_config,
                                "trigger_data": {
                                    "sender": sender,
                                    "subject": subject,
                                    "body": body,
                                    "recipients": recipients,
                                    "headers": headers,
                                    "received_at": datetime.utcnow().isoformat(),
                                },
                            }
                        )

                logger.info(
                    f"Found {len(workflow_matches)} workflows matching email from: {sender}"
                )
                return workflow_matches

        except Exception as e:
            logger.error(f"Error routing email event from {sender}: {e}", exc_info=True)
            return []

    async def route_slack_event(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Route Slack events to matching workflows using unified index_key design

        Args:
            event_data: Slack event data containing team_id, type, etc.

        Returns:
            List of matching workflow information
        """
        try:
            workspace_id = event_data.get("team_id", "")
            event_type = event_data.get("type", "")

            logger.debug(f"Routing Slack event: {event_type} from workspace {workspace_id}")

            async with self.session_factory() as session:
                # 1. Fast lookup using unified index_key (workspace_id)
                # Include both specific workspace and global triggers (empty/null workspace_id)
                query = session.query(TriggerIndex).filter(
                    and_(
                        TriggerIndex.trigger_type == TriggerSubtype.SLACK.value,
                        or_(
                            TriggerIndex.index_key == workspace_id,
                            TriggerIndex.index_key.is_(None),
                            TriggerIndex.index_key == "",
                        ),
                        TriggerIndex.deployment_status == "active",
                    )
                )

                result = await session.execute(query)
                candidate_triggers = result.scalars().all()

                # 2. Detailed matching using trigger_config
                workflow_matches = []
                for trigger in candidate_triggers:
                    if self._validate_slack_trigger_detailed(trigger, event_data):
                        workflow_matches.append(
                            {
                                "workflow_id": str(trigger.workflow_id),
                                "trigger_type": trigger.trigger_type,
                                "trigger_config": trigger.trigger_config,
                                "trigger_data": {
                                    "event_type": event_type,
                                    "workspace_id": workspace_id,
                                    "event_data": event_data,
                                    "received_at": datetime.utcnow().isoformat(),
                                },
                            }
                        )

                logger.info(
                    f"Found {len(workflow_matches)} workflows matching Slack event: {event_type} from workspace {workspace_id}"
                )
                return workflow_matches

        except Exception as e:
            logger.error(f"Error routing Slack event: {e}", exc_info=True)
            return []

    async def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics for monitoring and debugging

        Returns:
            Dictionary with routing statistics
        """
        try:
            async with self.session_factory() as session:
                # Count active triggers by type
                active_triggers_query = session.query(TriggerIndex).filter(
                    TriggerIndex.deployment_status == "active"
                )

                result = await session.execute(active_triggers_query)
                active_triggers = result.scalars().all()

                stats = {
                    "total_active_triggers": len(active_triggers),
                    "triggers_by_type": {},
                    "triggers_by_status": {},
                    "github_repositories": set(),
                    "webhook_paths": set(),
                }

                for trigger in active_triggers:
                    # Count by trigger type
                    trigger_type = trigger.trigger_type
                    stats["triggers_by_type"][trigger_type] = (
                        stats["triggers_by_type"].get(trigger_type, 0) + 1
                    )

                    # Count by status
                    status = trigger.deployment_status
                    stats["triggers_by_status"][status] = (
                        stats["triggers_by_status"].get(status, 0) + 1
                    )

                    # Collect GitHub repositories
                    if trigger.github_repository:
                        stats["github_repositories"].add(trigger.github_repository)

                    # Collect webhook paths
                    if trigger.webhook_path:
                        stats["webhook_paths"].add(trigger.webhook_path)

                # Convert sets to lists for JSON serialization
                stats["github_repositories"] = list(stats["github_repositories"])
                stats["webhook_paths"] = list(stats["webhook_paths"])

                return stats

        except Exception as e:
            logger.error(f"Error getting routing stats: {e}", exc_info=True)
            return {"error": str(e)}

    async def _store_github_event(
        self, event_type: str, delivery_id: str, payload: Dict[str, Any]
    ) -> None:
        """Store GitHub webhook event for debugging and analysis"""
        try:
            async with self.session_factory() as session:
                # Extract key information from payload
                installation_id = payload.get("installation", {}).get("id")
                repository_id = payload.get("repository", {}).get("id")

                webhook_event = GitHubWebhookEvent(
                    delivery_id=delivery_id,
                    event_type=event_type,
                    installation_id=installation_id,
                    repository_id=repository_id,
                    payload=payload,
                    created_at=datetime.utcnow(),
                )

                session.add(webhook_event)
                await session.commit()

                logger.debug(f"Stored GitHub webhook event: {delivery_id}")

        except Exception as e:
            logger.warning(f"Failed to store GitHub webhook event {delivery_id}: {e}")

    def _validate_github_trigger_detailed(
        self, trigger: TriggerIndex, event_type: str, payload: Dict[str, Any]
    ) -> bool:
        """Validate if GitHub event matches detailed trigger configuration"""
        try:
            config = trigger.trigger_config or {}

            # Check if event type is configured - support both old and new formats
            event_config = config.get("event_config", config.get("events", []))

            if isinstance(event_config, list):
                # Old array format: ["push", "pull_request"]
                allowed_events = event_config
                if allowed_events and event_type not in allowed_events:
                    return False
            elif isinstance(event_config, dict):
                # New object format: {"push": {...}, "pull_request": {...}}
                if event_type not in event_config:
                    return False

                # For pull_request events, check action filters
                if event_type == "pull_request":
                    event_filters = event_config.get(event_type, {})
                    expected_actions = event_filters.get("actions", [])
                    if expected_actions:
                        action = payload.get("action")
                        if action not in expected_actions:
                            return False
            else:
                # No event configuration or invalid format
                return False

            # Check branch filters for push and pull_request events
            if event_type == "push" and "branches" in config:
                ref = payload.get("ref", "")
                branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref

                branch_patterns = config["branches"]
                if isinstance(branch_patterns, str):
                    branch_patterns = [branch_patterns]

                # Simple wildcard matching (extend as needed)
                if not any(self._matches_pattern(branch, pattern) for pattern in branch_patterns):
                    return False

            elif event_type == "pull_request" and "branches" in config:
                # For PR events, check the base branch
                base_branch = payload.get("pull_request", {}).get("base", {}).get("ref", "")

                branch_patterns = config["branches"]
                if isinstance(branch_patterns, str):
                    branch_patterns = [branch_patterns]

                if not any(
                    self._matches_pattern(base_branch, pattern) for pattern in branch_patterns
                ):
                    return False

            # Check file path filters
            if "paths" in config:
                files_changed = []

                # Extract changed files based on event type
                if event_type == "push":
                    for commit in payload.get("commits", []):
                        files_changed.extend(commit.get("added", []))
                        files_changed.extend(commit.get("modified", []))
                        files_changed.extend(commit.get("removed", []))
                elif event_type == "pull_request":
                    # Would need additional API call to get PR files
                    # For now, allow PR events to pass path filter
                    pass

                if files_changed:  # Only apply filter if we have file data
                    file_patterns = config["paths"]
                    if isinstance(file_patterns, str):
                        file_patterns = [file_patterns]

                    # Check if any changed file matches the patterns
                    if not any(
                        self._matches_pattern(file_path, pattern)
                        for file_path in files_changed
                        for pattern in file_patterns
                    ):
                        return False

            # Check author filter
            if "author_filter" in config:
                author = payload.get("sender", {}).get("login", "")
                if not self._matches_pattern(author, config["author_filter"]):
                    return False

            # Check action filter (for pull_request events)
            if event_type == "pull_request" and "action_filter" in config:
                action = payload.get("action", "")
                allowed_actions = config["action_filter"]
                if isinstance(allowed_actions, str):
                    allowed_actions = [allowed_actions]
                if action not in allowed_actions:
                    return False

            return True

        except Exception as e:
            logger.warning(f"Error validating GitHub trigger: {e}")
            return True  # Default to allow if validation fails

    def _validate_slack_trigger_detailed(
        self, trigger: TriggerIndex, event_data: Dict[str, Any]
    ) -> bool:
        """Validate if Slack event matches detailed trigger configuration"""
        try:
            config = trigger.trigger_config or {}

            # Event type filter
            event_type = event_data.get("type", "")
            allowed_events = config.get("event_types", ["message", "app_mention"])
            if event_type not in allowed_events:
                return False

            # Channel filter
            channel_id = event_data.get("channel", "")
            if config.get("channel_filter"):
                if not self._matches_channel_pattern(channel_id, config["channel_filter"]):
                    return False

            # User filter
            user_id = event_data.get("user", "")
            if config.get("user_filter"):
                if not self._matches_pattern(user_id, config["user_filter"]):
                    return False

            # Bot filter
            if config.get("ignore_bots", True) and event_data.get("bot_id"):
                return False

            # Mention requirement
            if config.get("mention_required", False):
                if not self._event_has_bot_mention(event_data):
                    return False

            # Thread requirement
            if config.get("require_thread", False):
                if not event_data.get("thread_ts"):
                    return False

            # Command prefix filter (for message events)
            if event_type == "message" and config.get("command_prefix"):
                message_text = event_data.get("text", "")
                if not message_text.strip().startswith(config["command_prefix"]):
                    return False

            return True

        except Exception as e:
            logger.warning(f"Error validating Slack trigger: {e}")
            return True  # Default to allow if validation fails

    async def _matches_email_filter(
        self,
        trigger: TriggerIndex,
        sender: str,
        subject: str,
        body: str,
        recipients: List[str],
    ) -> bool:
        """Check if email matches trigger filter criteria"""
        try:
            email_filter = trigger.email_filter
            if not email_filter:
                return True  # No filter means match all

            config = trigger.trigger_config or {}

            # Check sender filter
            if "sender_filter" in config:
                sender_patterns = config["sender_filter"]
                if isinstance(sender_patterns, str):
                    sender_patterns = [sender_patterns]

                if not any(self._matches_pattern(sender, pattern) for pattern in sender_patterns):
                    return False

            # Check subject filter
            if "subject_filter" in config:
                subject_patterns = config["subject_filter"]
                if isinstance(subject_patterns, str):
                    subject_patterns = [subject_patterns]

                if not any(self._matches_pattern(subject, pattern) for pattern in subject_patterns):
                    return False

            # Check recipient filter
            if "recipient_filter" in config:
                recipient_patterns = config["recipient_filter"]
                if isinstance(recipient_patterns, str):
                    recipient_patterns = [recipient_patterns]

                # Check if any recipient matches any pattern
                if not any(
                    self._matches_pattern(recipient, pattern)
                    for recipient in recipients
                    for pattern in recipient_patterns
                ):
                    return False

            return True

        except Exception as e:
            logger.warning(f"Error matching email filter: {e}")
            return True  # Default to allow if matching fails

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Simple pattern matching with wildcard support"""
        if pattern == "*":
            return True

        if "*" not in pattern:
            return text == pattern

        # Simple wildcard matching - convert to regex-like behavior
        import re

        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(f"^{regex_pattern}$", text, re.IGNORECASE))

    def _matches_channel_pattern(self, channel_id: str, pattern: str) -> bool:
        """Match Slack channel ID against pattern"""
        try:
            if pattern.startswith("C"):  # Channel ID format
                return channel_id == pattern
            else:  # Treat as regex pattern
                import re

                return bool(re.match(pattern, channel_id))
        except Exception:
            return False

    def _event_has_bot_mention(self, event_data: Dict[str, Any]) -> bool:
        """Check if Slack event contains a bot mention"""
        try:
            # Check for app_mention event type
            if event_data.get("type") == "app_mention":
                return True

            # Check for direct mention in message text
            message_text = event_data.get("text", "")
            if "<@U" in message_text:  # Basic mention pattern
                return True

            # Check for mention in blocks (rich text format)
            blocks = event_data.get("blocks", [])
            for block in blocks:
                if self._block_contains_mention(block):
                    return True

            return False
        except Exception:
            return False

    def _block_contains_mention(self, block: dict) -> bool:
        """Check if a Slack block contains a mention"""
        try:
            if block.get("type") == "rich_text":
                elements = block.get("elements", [])
                for element in elements:
                    if element.get("type") == "rich_text_section":
                        text_elements = element.get("elements", [])
                        for text_elem in text_elements:
                            if text_elem.get("type") == "user" and text_elem.get("user_id"):
                                return True
            return False
        except Exception:
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check health of event router"""
        try:
            async with self.session_factory() as session:
                # Test database connection with a simple query
                result = await session.execute("SELECT 1")
                result.fetchone()

                return {
                    "service": "event_router",
                    "database_connected": True,
                    "status": "healthy",
                }

        except Exception as e:
            logger.error(f"Event router health check failed: {e}")
            return {
                "service": "event_router",
                "database_connected": False,
                "status": "unhealthy",
                "error": str(e),
            }
