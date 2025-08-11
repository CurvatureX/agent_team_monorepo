"""
Trigger Index Manager for workflow_scheduler

This service manages the trigger indexing system for fast reverse lookup and matching.
It handles registration, updates, and cleanup of trigger index entries.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.trigger import TriggerSpec, TriggerType
from shared.models.trigger_index import GitHubInstallation, TriggerIndex
from workflow_scheduler.core.config import settings
from workflow_scheduler.core.database import async_session_factory

from shared.logging_config import get_logger
logger = get_logger(__name__)


class TriggerIndexManager:
    """
    Manager for trigger indexing system

    This class handles the creation, update, and deletion of trigger index entries
    for fast event routing and matching.
    """

    def __init__(self):
        """Initialize the TriggerIndexManager with database session"""
        # Use centralized async database configuration
        self.session_factory = async_session_factory

    async def register_workflow_triggers(
        self, workflow_id: str, trigger_specs: List[TriggerSpec], deployment_status: str = "active"
    ) -> bool:
        """
        Register all triggers for a workflow in the index

        Args:
            workflow_id: Workflow identifier
            trigger_specs: List of trigger specifications
            deployment_status: Status of the deployment ('active', 'paused', 'stopped')

        Returns:
            bool: True if all triggers registered successfully
        """
        try:
            logger.info(f"Registering {len(trigger_specs)} triggers for workflow {workflow_id}")

            async with self.session_factory() as session:
                # First, remove any existing triggers for this workflow
                await self._remove_workflow_triggers(session, workflow_id)

                # Register each trigger spec
                for spec in trigger_specs:
                    success = await self._register_single_trigger(
                        session, workflow_id, spec, deployment_status
                    )
                    if not success:
                        logger.error(
                            f"Failed to register trigger {spec.subtype} for workflow {workflow_id}"
                        )
                        await session.rollback()
                        return False

                await session.commit()
                logger.info(f"Successfully registered all triggers for workflow {workflow_id}")
                return True

        except Exception as e:
            logger.error(
                f"Error registering triggers for workflow {workflow_id}: {e}", exc_info=True
            )
            return False

    async def unregister_workflow_triggers(self, workflow_id: str) -> bool:
        """
        Unregister all triggers for a workflow from the index

        Args:
            workflow_id: Workflow identifier

        Returns:
            bool: True if successfully unregistered
        """
        try:
            logger.info(f"Unregistering triggers for workflow {workflow_id}")

            async with self.session_factory() as session:
                success = await self._remove_workflow_triggers(session, workflow_id)
                await session.commit()

                if success:
                    logger.info(f"Successfully unregistered triggers for workflow {workflow_id}")
                return success

        except Exception as e:
            logger.error(
                f"Error unregistering triggers for workflow {workflow_id}: {e}", exc_info=True
            )
            return False

    async def update_trigger_status(self, workflow_id: str, status: str) -> bool:
        """
        Update deployment status for all triggers of a workflow

        Args:
            workflow_id: Workflow identifier
            status: New status ('active', 'paused', 'stopped')

        Returns:
            bool: True if successfully updated
        """
        try:
            logger.info(f"Updating trigger status for workflow {workflow_id} to {status}")

            async with self.session_factory() as session:
                # Update all triggers for this workflow
                query = (
                    session.query(TriggerIndex)
                    .filter(TriggerIndex.workflow_id == uuid.UUID(workflow_id))
                    .update({"deployment_status": status, "updated_at": datetime.utcnow()})
                )

                result = await session.execute(query)
                updated_count = result.rowcount
                await session.commit()

                logger.info(
                    f"Updated {updated_count} triggers for workflow {workflow_id} to status {status}"
                )
                return updated_count > 0

        except Exception as e:
            logger.error(
                f"Error updating trigger status for workflow {workflow_id}: {e}", exc_info=True
            )
            return False

    async def get_workflow_triggers(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get all indexed triggers for a workflow

        Args:
            workflow_id: Workflow identifier

        Returns:
            List of trigger information dictionaries
        """
        try:
            async with self.session_factory() as session:
                query = session.query(TriggerIndex).filter(
                    TriggerIndex.workflow_id == uuid.UUID(workflow_id)
                )

                result = await session.execute(query)
                triggers = result.scalars().all()

                trigger_info = []
                for trigger in triggers:
                    trigger_info.append(
                        {
                            "id": str(trigger.id),
                            "workflow_id": str(trigger.workflow_id),
                            "trigger_type": trigger.trigger_type,
                            "trigger_config": trigger.trigger_config,
                            "deployment_status": trigger.deployment_status,
                            "created_at": trigger.created_at.isoformat(),
                            "updated_at": trigger.updated_at.isoformat(),
                            # Type-specific fields
                            "cron_expression": trigger.cron_expression,
                            "webhook_path": trigger.webhook_path,
                            "email_filter": trigger.email_filter,
                            "github_repository": trigger.github_repository,
                            "github_events": trigger.github_events,
                            "github_installation_id": trigger.github_installation_id,
                        }
                    )

                return trigger_info

        except Exception as e:
            logger.error(f"Error getting triggers for workflow {workflow_id}: {e}", exc_info=True)
            return []

    async def register_github_installation(
        self,
        installation_id: int,
        account_id: int,
        account_login: str,
        account_type: str,
        repositories: List[Dict[str, Any]],
        permissions: Dict[str, str],
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Register a GitHub App installation for access management

        Args:
            installation_id: GitHub installation ID
            account_id: GitHub account ID
            account_login: GitHub account login name
            account_type: 'User' or 'Organization'
            repositories: List of accessible repositories
            permissions: Installation permissions
            user_id: Associated user ID (optional)

        Returns:
            bool: True if successfully registered
        """
        try:
            logger.info(f"Registering GitHub installation {installation_id} for {account_login}")

            async with self.session_factory() as session:
                # Check if installation already exists
                existing_query = session.query(GitHubInstallation).filter(
                    GitHubInstallation.installation_id == installation_id
                )

                result = await session.execute(existing_query)
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing installation
                    existing.account_id = account_id
                    existing.account_login = account_login
                    existing.account_type = account_type
                    existing.repositories = repositories
                    existing.permissions = permissions
                    existing.user_id = uuid.UUID(user_id) if user_id else None
                    existing.updated_at = datetime.utcnow()

                    logger.info(f"Updated existing GitHub installation {installation_id}")
                else:
                    # Create new installation
                    installation = GitHubInstallation(
                        user_id=uuid.UUID(user_id) if user_id else None,
                        installation_id=installation_id,
                        account_id=account_id,
                        account_login=account_login,
                        account_type=account_type,
                        repositories=repositories,
                        permissions=permissions,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )

                    session.add(installation)
                    logger.info(f"Created new GitHub installation {installation_id}")

                await session.commit()
                return True

        except Exception as e:
            logger.error(
                f"Error registering GitHub installation {installation_id}: {e}", exc_info=True
            )
            return False

    async def get_github_installations(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get GitHub installations, optionally filtered by user

        Args:
            user_id: Optional user ID to filter by

        Returns:
            List of installation information
        """
        try:
            async with self.session_factory() as session:
                query = session.query(GitHubInstallation)

                if user_id:
                    query = query.filter(GitHubInstallation.user_id == uuid.UUID(user_id))

                result = await session.execute(query)
                installations = result.scalars().all()

                installation_info = []
                for installation in installations:
                    installation_info.append(
                        {
                            "id": str(installation.id),
                            "user_id": str(installation.user_id) if installation.user_id else None,
                            "installation_id": installation.installation_id,
                            "account_id": installation.account_id,
                            "account_login": installation.account_login,
                            "account_type": installation.account_type,
                            "repositories": installation.repositories,
                            "permissions": installation.permissions,
                            "access_token_expires_at": installation.access_token_expires_at.isoformat()
                            if installation.access_token_expires_at
                            else None,
                            "created_at": installation.created_at.isoformat(),
                            "updated_at": installation.updated_at.isoformat(),
                        }
                    )

                return installation_info

        except Exception as e:
            logger.error(f"Error getting GitHub installations: {e}", exc_info=True)
            return []

    async def get_index_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the trigger index

        Returns:
            Dictionary with index statistics
        """
        try:
            async with self.session_factory() as session:
                # Count triggers by type and status
                query = session.query(TriggerIndex)
                result = await session.execute(query)
                all_triggers = result.scalars().all()

                stats = {
                    "total_triggers": len(all_triggers),
                    "by_type": {},
                    "by_status": {},
                    "by_workflow": {},
                    "github_installations": 0,
                    "unique_repositories": set(),
                    "unique_webhook_paths": set(),
                }

                for trigger in all_triggers:
                    # Count by type
                    trigger_type = trigger.trigger_type
                    stats["by_type"][trigger_type] = stats["by_type"].get(trigger_type, 0) + 1

                    # Count by status
                    status = trigger.deployment_status
                    stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

                    # Count by workflow
                    workflow_id = str(trigger.workflow_id)
                    stats["by_workflow"][workflow_id] = stats["by_workflow"].get(workflow_id, 0) + 1

                    # Collect unique values
                    if trigger.github_repository:
                        stats["unique_repositories"].add(trigger.github_repository)
                    if trigger.webhook_path:
                        stats["unique_webhook_paths"].add(trigger.webhook_path)

                # Get GitHub installation count
                installations_query = session.query(GitHubInstallation)
                installations_result = await session.execute(installations_query)
                installations = installations_result.scalars().all()
                stats["github_installations"] = len(installations)

                # Convert sets to counts for JSON serialization
                stats["unique_repositories"] = len(stats["unique_repositories"])
                stats["unique_webhook_paths"] = len(stats["unique_webhook_paths"])

                return stats

        except Exception as e:
            logger.error(f"Error getting index statistics: {e}", exc_info=True)
            return {"error": str(e)}

    async def _register_single_trigger(
        self, session: AsyncSession, workflow_id: str, spec: TriggerSpec, deployment_status: str
    ) -> bool:
        """Register a single trigger specification in the index"""
        try:
            # Create trigger index entry
            trigger_index = TriggerIndex(
                workflow_id=uuid.UUID(workflow_id),
                trigger_type=spec.subtype.value,
                trigger_config=spec.parameters,
                deployment_status=deployment_status,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Set unified index_key for fast matching based on trigger type
            if spec.subtype == TriggerType.CRON:
                trigger_index.index_key = spec.parameters.get("cron_expression")

            elif spec.subtype == TriggerType.WEBHOOK:
                trigger_index.index_key = spec.parameters.get(
                    "webhook_path", f"/webhook/{workflow_id}"
                )

            elif spec.subtype == TriggerType.EMAIL:
                # Use primary email address or filter as index key
                trigger_index.index_key = spec.parameters.get("email_filter", "")

            elif spec.subtype == TriggerType.GITHUB:
                # Use repository name as primary index key
                trigger_index.index_key = spec.parameters.get("repository")

            elif spec.subtype == TriggerType.SLACK:
                # Use workspace_id as primary index key for Slack triggers
                trigger_index.index_key = spec.parameters.get("workspace_id", "")

            # TRIGGER_MANUAL doesn't need index_key (no fast lookup needed)

            session.add(trigger_index)

            logger.debug(
                f"Registered trigger {spec.subtype.value} for workflow {workflow_id} with index_key: {trigger_index.index_key}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error registering single trigger {spec.subtype.value}: {e}", exc_info=True
            )
            return False

    async def _remove_workflow_triggers(self, session: AsyncSession, workflow_id: str) -> bool:
        """Remove all trigger index entries for a workflow"""
        try:
            # Delete all triggers for this workflow
            delete_query = delete(TriggerIndex).where(
                TriggerIndex.workflow_id == uuid.UUID(workflow_id)
            )

            result = await session.execute(delete_query)
            deleted_count = result.rowcount

            logger.debug(
                f"Removed {deleted_count} trigger index entries for workflow {workflow_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error removing triggers for workflow {workflow_id}: {e}", exc_info=True)
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check health of trigger index manager"""
        try:
            async with self.session_factory() as session:
                # Test database connection
                result = await session.execute("SELECT COUNT(*) FROM trigger_index")
                trigger_count = result.scalar()

                return {
                    "service": "trigger_index_manager",
                    "database_connected": True,
                    "trigger_count": trigger_count,
                    "status": "healthy",
                }

        except Exception as e:
            logger.error(f"Trigger index manager health check failed: {e}")
            return {
                "service": "trigger_index_manager",
                "database_connected": False,
                "status": "unhealthy",
                "error": str(e),
            }
