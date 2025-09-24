"""
Trigger Index Manager for workflow_scheduler

This service manages the trigger indexing system for fast reverse lookup and matching.
It handles registration, updates, and cleanup of trigger index entries.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.models.trigger import TriggerSpec, TriggerType
from workflow_scheduler.core.config import settings

logger = logging.getLogger(__name__)


class TriggerIndexManager:
    """
    Manager for trigger indexing system

    This class handles the creation, update, and deletion of trigger index entries
    for fast event routing and matching.
    """

    def __init__(self):
        """Initialize the TriggerIndexManager using Supabase client"""
        # All database operations now use Supabase client directly
        pass

    async def register_workflow_triggers(
        self,
        workflow_id: str,
        trigger_specs: List[TriggerSpec],
        deployment_status: str = "active",
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

            # First, remove any existing triggers for this workflow using Supabase
            logger.info(f"Removing existing triggers for workflow {workflow_id}")
            await self._remove_workflow_triggers(workflow_id)

            # Register each trigger spec using Supabase
            for spec in trigger_specs:
                logger.info(f"Registering {spec.subtype} trigger for workflow {workflow_id}")
                success = await self._register_single_trigger(workflow_id, spec, deployment_status)
                if not success:
                    logger.error(
                        f"Failed to register trigger {spec.subtype} for workflow {workflow_id}"
                    )
                    return False

            logger.info(
                f"Successfully registered all {len(trigger_specs)} triggers for workflow {workflow_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error registering triggers for workflow {workflow_id}: {e}",
                exc_info=True,
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

            success = await self._remove_workflow_triggers(workflow_id)

            if success:
                logger.info(f"Successfully unregistered triggers for workflow {workflow_id}")
            return success

        except Exception as e:
            logger.error(
                f"Error unregistering triggers for workflow {workflow_id}: {e}",
                exc_info=True,
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
            from workflow_scheduler.core.supabase_client import get_supabase_client

            client = get_supabase_client()
            if not client:
                logger.error("Supabase client not available")
                return False

            logger.info(f"Updating trigger status for workflow {workflow_id} to {status}")

            # Handle workflow_id - it might not be a valid UUID
            try:
                workflow_uuid = str(uuid.UUID(workflow_id))
            except ValueError:
                # If not a valid UUID, use the string as-is
                logger.warning(f"Workflow ID '{workflow_id}' is not a valid UUID, using as string")
                workflow_uuid = workflow_id

            # Update all triggers for this workflow using Supabase
            update_data = {
                "deployment_status": status,
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = (
                client.table("trigger_index")
                .update(update_data)
                .eq("workflow_id", workflow_uuid)
                .execute()
            )

            updated_count = len(response.data) if response.data else 0

            logger.info(
                f"Updated {updated_count} triggers for workflow {workflow_id} to status {status}"
            )
            return updated_count > 0

        except Exception as e:
            logger.error(
                f"Error updating trigger status for workflow {workflow_id}: {e}",
                exc_info=True,
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
            from workflow_scheduler.core.supabase_client import get_supabase_client

            client = get_supabase_client()

            # Query triggers using Supabase
            response = (
                client.table("trigger_index").select("*").eq("workflow_id", workflow_id).execute()
            )

            trigger_info = []

            for trigger_record in response.data:
                trigger_info.append(
                    {
                        "id": str(trigger_record["id"]),
                        "workflow_id": str(trigger_record["workflow_id"]),
                        "trigger_type": trigger_record["trigger_type"],
                        "trigger_config": trigger_record["trigger_config"],
                        "deployment_status": trigger_record["deployment_status"],
                        "created_at": trigger_record["created_at"],
                        "updated_at": trigger_record["updated_at"],
                        "index_key": trigger_record.get("index_key"),
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

            from workflow_scheduler.core.supabase_client import get_supabase_client

            client = get_supabase_client()
            if not client:
                logger.error("❌ Supabase client not available")
                return False

            # Prepare installation data
            now = datetime.utcnow().isoformat()
            installation_data = {
                "user_id": user_id if user_id else None,
                "installation_id": installation_id,
                "account_id": account_id,
                "account_login": account_login,
                "account_type": account_type,
                "repositories": repositories,
                "permissions": permissions,
                "created_at": now,
                "updated_at": now,
            }

            # Check if installation already exists
            existing = (
                client.table("github_installations")
                .select("*")
                .eq("installation_id", installation_id)
                .execute()
            )

            if existing.data:
                # Update existing installation
                update_data = {
                    "account_id": account_id,
                    "account_login": account_login,
                    "account_type": account_type,
                    "repositories": repositories,
                    "permissions": permissions,
                    "user_id": user_id if user_id else None,
                    "updated_at": now,
                }

                result = (
                    client.table("github_installations")
                    .update(update_data)
                    .eq("installation_id", installation_id)
                    .execute()
                )

                if result.data:
                    logger.info(f"✅ Updated existing GitHub installation {installation_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to update GitHub installation {installation_id}")
                    return False
            else:
                # Create new installation
                result = client.table("github_installations").insert(installation_data).execute()

                if result.data:
                    logger.info(f"✅ Created new GitHub installation {installation_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to create GitHub installation {installation_id}")
                    return False

        except Exception as e:
            logger.error(
                f"Error registering GitHub installation {installation_id}: {e}",
                exc_info=True,
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
            from workflow_scheduler.core.supabase_client import get_supabase_client

            logger.info(f"📨 Getting GitHub installations for user_id: {user_id}")

            client = get_supabase_client()
            if not client:
                logger.error("❌ Supabase client not available")
                return []

            # Build query
            query = client.table("github_installations").select("*")

            if user_id:
                query = query.eq("user_id", user_id)

            result = query.execute()

            if result.data:
                logger.info(f"✅ Retrieved {len(result.data)} GitHub installations")

                # Transform data to match expected format
                installation_info = []
                for installation in result.data:
                    installation_info.append(
                        {
                            "id": installation.get("id"),
                            "user_id": installation.get("user_id"),
                            "installation_id": installation.get("installation_id"),
                            "account_id": installation.get("account_id"),
                            "account_login": installation.get("account_login"),
                            "account_type": installation.get("account_type"),
                            "repositories": installation.get("repositories", []),
                            "permissions": installation.get("permissions", {}),
                            "access_token_expires_at": installation.get("access_token_expires_at"),
                            "created_at": installation.get("created_at"),
                            "updated_at": installation.get("updated_at"),
                        }
                    )

                return installation_info
            else:
                logger.info("📋 No GitHub installations found")
                return []

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
            from workflow_scheduler.core.supabase_client import get_supabase_client

            logger.info("📨 Getting index statistics")

            client = get_supabase_client()
            if not client:
                logger.error("❌ Supabase client not available")
                return {"error": "Supabase client not available"}

            # Get all triggers
            triggers_result = client.table("trigger_index").select("*").execute()
            all_triggers = triggers_result.data if triggers_result.data else []

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
                trigger_type = trigger.get("trigger_type")
                if trigger_type:
                    stats["by_type"][trigger_type] = stats["by_type"].get(trigger_type, 0) + 1

                # Count by status
                status = trigger.get("deployment_status")
                if status:
                    stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

                # Count by workflow
                workflow_id = trigger.get("workflow_id")
                if workflow_id:
                    workflow_id_str = str(workflow_id)
                    stats["by_workflow"][workflow_id_str] = (
                        stats["by_workflow"].get(workflow_id_str, 0) + 1
                    )

                # Collect unique values
                github_repository = trigger.get("github_repository")
                if github_repository:
                    stats["unique_repositories"].add(github_repository)

                webhook_path = trigger.get("webhook_path")
                if webhook_path:
                    stats["unique_webhook_paths"].add(webhook_path)

            # Get GitHub installation count
            installations_result = client.table("github_installations").select("id").execute()
            installations = installations_result.data if installations_result.data else []
            stats["github_installations"] = len(installations)

            # Convert sets to counts for JSON serialization
            stats["unique_repositories"] = len(stats["unique_repositories"])
            stats["unique_webhook_paths"] = len(stats["unique_webhook_paths"])

            logger.info(f"✅ Generated index statistics: {stats['total_triggers']} triggers")
            return stats

        except Exception as e:
            logger.error(f"Error getting index statistics: {e}", exc_info=True)
            return {"error": str(e)}

    async def _register_single_trigger(
        self,
        workflow_id: str,
        spec: TriggerSpec,
        deployment_status: str,
    ) -> bool:
        """Register a single trigger specification in the index using Supabase client"""
        try:
            from workflow_scheduler.core.supabase_client import get_supabase_client

            client = get_supabase_client()
            if not client:
                logger.error("Supabase client not available")
                return False

            # Handle workflow_id - it might not be a valid UUID
            try:
                workflow_uuid = str(uuid.UUID(workflow_id))
            except ValueError:
                # If not a valid UUID, use the string as-is
                logger.warning(f"Workflow ID '{workflow_id}' is not a valid UUID, using as string")
                workflow_uuid = workflow_id

            # Check if trigger already exists for this workflow
            existing_response = (
                client.table("trigger_index")
                .select("*")
                .eq("workflow_id", workflow_uuid)
                .eq("trigger_type", spec.subtype.value)
                .execute()
            )

            existing_trigger = existing_response.data[0] if existing_response.data else None

            if existing_trigger:
                # Calculate index_key for the update
                index_key = ""
                if spec.subtype == TriggerType.CRON:
                    index_key = spec.parameters.get("cron_expression", "")
                elif spec.subtype == TriggerType.WEBHOOK:
                    index_key = spec.parameters.get("webhook_path", f"/webhook/{workflow_id}")
                elif spec.subtype == TriggerType.EMAIL:
                    index_key = spec.parameters.get("email_filter", "")
                elif spec.subtype == TriggerType.GITHUB:
                    index_key = spec.parameters.get("repository", "")
                elif spec.subtype == TriggerType.SLACK:
                    # Update workspace_id from auto-resolved OAuth token
                    workspace_id = spec.parameters.get("workspace_id") or spec.parameters.get(
                        "team_id"
                    )
                    index_key = workspace_id or ""

                    # Log helpful information for debugging
                    if not workspace_id:
                        logger.error(
                            f"No workspace_id found for Slack trigger in workflow {workflow_id}. "
                            f"This indicates the deployment service failed to auto-resolve workspace_id from user's OAuth token. "
                            f"Available parameters: {list(spec.parameters.keys())}"
                        )
                    else:
                        logger.info(
                            f"Updated Slack trigger with auto-resolved workspace_id '{workspace_id}' for workflow {workflow_id}"
                        )

                # Update existing trigger using Supabase
                update_data = {
                    "trigger_config": spec.parameters,
                    "deployment_status": deployment_status,
                    "updated_at": datetime.utcnow().isoformat(),
                    "index_key": index_key,
                }

                # Note: trigger-specific data is stored in trigger_config JSONB field
                # No additional fields needed - all data is in trigger_config and index_key

                update_response = (
                    client.table("trigger_index")
                    .update(update_data)
                    .eq("id", existing_trigger["id"])
                    .execute()
                )

                if update_response.data:
                    logger.info(
                        f"Updated existing trigger {spec.subtype.value} for workflow {workflow_id} with index_key: '{index_key}'"
                    )
                    return True
                else:
                    logger.error(
                        f"Failed to update existing trigger {spec.subtype.value} for workflow {workflow_id}"
                    )
                    return False

            # Create new trigger index entry using Supabase
            now = datetime.utcnow().isoformat()

            # Calculate index_key for fast matching based on trigger type
            index_key = ""
            if spec.subtype == TriggerType.CRON:
                index_key = spec.parameters.get("cron_expression", "")
            elif spec.subtype == TriggerType.WEBHOOK:
                index_key = spec.parameters.get("webhook_path", f"/webhook/{workflow_id}")
            elif spec.subtype == TriggerType.EMAIL:
                index_key = spec.parameters.get("email_filter", "")
            elif spec.subtype == TriggerType.GITHUB:
                index_key = spec.parameters.get("repository", "")
            elif spec.subtype == TriggerType.SLACK:
                # Use workspace_id as primary index key for Slack triggers
                # workspace_id should always be auto-resolved from user's OAuth token during deployment
                workspace_id = spec.parameters.get("workspace_id") or spec.parameters.get("team_id")
                index_key = workspace_id or ""

                # Log helpful information for debugging
                if not workspace_id:
                    logger.error(
                        f"No workspace_id found for Slack trigger in workflow {workflow_id}. "
                        f"This indicates the deployment service failed to auto-resolve workspace_id from user's OAuth token. "
                        f"Available parameters: {list(spec.parameters.keys())}"
                    )
                else:
                    logger.info(
                        f"Using auto-resolved workspace_id '{workspace_id}' for Slack trigger index_key"
                    )

            # Prepare trigger data for insertion
            trigger_data = {
                "workflow_id": workflow_uuid,
                "trigger_type": spec.subtype.value,
                "trigger_config": spec.parameters,
                "deployment_status": deployment_status,
                "created_at": now,
                "updated_at": now,
                "index_key": index_key,
            }

            # Note: trigger-specific data is stored in trigger_config JSONB field
            # index_key is calculated above for fast lookup
            # No additional fields needed - all data is in trigger_config

            # Insert new trigger using Supabase
            insert_response = client.table("trigger_index").insert(trigger_data).execute()

            if insert_response.data:
                logger.info(
                    f"Created new trigger {spec.subtype.value} for workflow {workflow_id} with index_key: '{index_key}'"
                )
                return True
            else:
                logger.error(
                    f"Failed to create new trigger {spec.subtype.value} for workflow {workflow_id}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error registering single trigger {spec.subtype.value}: {e}",
                exc_info=True,
            )
            return False

    async def _remove_workflow_triggers(self, workflow_id: str) -> bool:
        """Remove all trigger index entries for a workflow using Supabase client"""
        try:
            from workflow_scheduler.core.supabase_client import get_supabase_client

            client = get_supabase_client()
            if not client:
                logger.error("Supabase client not available")
                return False

            # Handle workflow_id - it might not be a valid UUID
            try:
                workflow_uuid = str(uuid.UUID(workflow_id))
            except ValueError:
                # If not a valid UUID, use the string as-is
                logger.warning(f"Workflow ID '{workflow_id}' is not a valid UUID, using as string")
                workflow_uuid = workflow_id

            # Delete all triggers for this workflow using Supabase client
            response = (
                client.table("trigger_index").delete().eq("workflow_id", workflow_uuid).execute()
            )

            deleted_count = len(response.data) if response.data else 0

            logger.info(f"Removed {deleted_count} trigger index entries for workflow {workflow_id}")
            return True

        except Exception as e:
            logger.error(
                f"Error removing triggers for workflow {workflow_id}: {e}",
                exc_info=True,
            )
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check health of trigger index manager using Supabase client"""
        try:
            from workflow_scheduler.core.supabase_client import get_supabase_client

            client = get_supabase_client()

            # Test database connection by counting triggers
            response = client.table("trigger_index").select("count").execute()
            trigger_count = len(response.data) if response.data else 0

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
