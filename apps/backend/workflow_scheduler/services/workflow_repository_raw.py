"""
Raw SQL Workflow Repository - Uses raw SQL to avoid prepared statement conflicts with pgbouncer
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import asyncpg

from workflow_scheduler.core.config import settings
from shared.logging_config import get_logger

logger = get_logger(__name__)


class RawSQLWorkflowRepository:
    """Repository using raw SQL to avoid prepared statement conflicts"""

    def __init__(self):
        # Parse database URL to get connection parameters
        self.database_url = settings.database_url

    async def _get_connection(self):
        """Get a raw asyncpg connection without prepared statements"""
        # Create connection directly with asyncpg to avoid SQLAlchemy issues
        return await asyncpg.connect(
            self.database_url,
            command_timeout=30,
            server_settings={"application_name": "workflow_scheduler_raw"},
        )

    async def get_workflow_by_id(self, workflow_id: str) -> Optional[Dict]:
        """Get workflow by ID using raw SQL"""
        try:
            conn = await self._get_connection()
            try:
                # Handle both string and UUID workflow_id
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return None
                else:
                    workflow_uuid = workflow_id

                # Use execute with string interpolation to avoid prepared statements
                query = f"""
                    SELECT id, name, deployment_status, deployed_at, deployed_by,
                           deployment_version, deployment_config, created_at, updated_at
                    FROM workflows
                    WHERE id = '{workflow_uuid}'
                """

                row = await conn.fetchrow(query)

                if row:
                    logger.info(f"Found workflow: {workflow_id}")
                    return dict(row)
                else:
                    logger.warning(f"Workflow not found: {workflow_id}")
                    return None

            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"Error getting workflow {workflow_id}: {e}", exc_info=True)
            return None

    async def update_workflow_deployment_status(
        self,
        workflow_id: str,
        deployment_status: str,
        deployed_at: Optional[datetime] = None,
        deployed_by: Optional[str] = None,
        undeployed_at: Optional[datetime] = None,
        deployment_config: Optional[Dict] = None,
        increment_version: bool = False,
    ) -> bool:
        """Update workflow deployment fields using raw SQL"""
        try:
            conn = await self._get_connection()
            try:
                # Handle both string and UUID workflow_id
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return False
                else:
                    workflow_uuid = workflow_id

                # Get current version if we need to increment it
                if increment_version:
                    current_version_query = (
                        f"SELECT deployment_version FROM workflows WHERE id = '{workflow_uuid}'"
                    )
                    current_version = await conn.fetchval(current_version_query)
                    new_version = (current_version or 0) + 1
                else:
                    new_version = None

                # Build dynamic UPDATE query using string formatting to avoid prepared statements
                set_clauses = [
                    f"deployment_status = '{deployment_status}'",
                    f"updated_at = '{datetime.now(timezone.utc)}'",
                ]

                if deployed_at:
                    set_clauses.append(f"deployed_at = '{deployed_at}'")

                if undeployed_at:
                    set_clauses.append(f"undeployed_at = '{undeployed_at}'")

                if deployed_by:
                    try:
                        deployed_by_uuid = UUID(deployed_by)
                        set_clauses.append(f"deployed_by = '{deployed_by_uuid}'")
                    except ValueError:
                        logger.warning(f"Invalid deployed_by UUID format: {deployed_by}")

                if deployment_config:
                    import json

                    config_json = json.dumps(deployment_config)
                    set_clauses.append(f"deployment_config = '{config_json}'::jsonb")

                if new_version is not None:
                    set_clauses.append(f"deployment_version = {new_version}")

                query = (
                    f"UPDATE workflows SET {', '.join(set_clauses)} WHERE id = '{workflow_uuid}'"
                )

                result = await conn.execute(query)

                # Extract number of affected rows from result
                affected_rows = int(result.split()[-1]) if result.startswith("UPDATE") else 0

                if affected_rows > 0:
                    logger.info(
                        f"Updated workflow deployment status: {workflow_id} -> {deployment_status}"
                    )
                    return True
                else:
                    logger.warning(f"No workflow found to update: {workflow_id}")
                    return False

            finally:
                await conn.close()

        except Exception as e:
            logger.error(
                f"Error updating workflow deployment status {workflow_id}: {e}", exc_info=True
            )
            return False

    async def create_deployment_history_record(
        self,
        workflow_id: str,
        deployment_action: str,
        from_status: str,
        to_status: str,
        deployment_version: int,
        triggered_by: Optional[str] = None,
        deployment_config: Optional[Dict] = None,
        error_message: Optional[str] = None,
        deployment_logs: Optional[Dict] = None,
    ) -> bool:
        """Create a deployment history record using raw SQL"""
        try:
            conn = await self._get_connection()
            try:
                # Handle both string and UUID workflow_id
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return False
                else:
                    workflow_uuid = workflow_id

                # Handle triggered_by UUID
                triggered_by_uuid = None
                if triggered_by:
                    try:
                        triggered_by_uuid = UUID(triggered_by)
                    except ValueError:
                        logger.warning(f"Invalid triggered_by UUID format: {triggered_by}")

                import json

                current_time = datetime.now(timezone.utc)
                deployment_config_json = json.dumps(deployment_config or {})
                deployment_logs_json = json.dumps(deployment_logs or {})

                query = f"""
                    INSERT INTO workflow_deployment_history
                    (workflow_id, deployment_action, from_status, to_status, deployment_version,
                     triggered_by, deployment_config, error_message, deployment_logs, started_at, completed_at)
                    VALUES ('{workflow_uuid}', '{deployment_action}', '{from_status}', '{to_status}', {deployment_version},
                            {f"'{triggered_by_uuid}'" if triggered_by_uuid else "NULL"}, '{deployment_config_json}'::jsonb,
                            {f"'{error_message}'" if error_message else "NULL"}, '{deployment_logs_json}'::jsonb,
                            '{current_time}', {f"'{current_time}'" if error_message is None else "NULL"})
                """

                await conn.execute(query)

                logger.info(
                    f"Created deployment history record: {workflow_id} - {deployment_action}"
                )
                return True

            finally:
                await conn.close()

        except Exception as e:
            logger.error(
                f"Error creating deployment history record {workflow_id}: {e}", exc_info=True
            )
            return False

    async def update_deployment_history_completion(
        self,
        workflow_id: str,
        deployment_action: str,
        error_message: Optional[str] = None,
        deployment_logs: Optional[Dict] = None,
    ) -> bool:
        """Update the most recent deployment history record with completion info using raw SQL"""
        try:
            conn = await self._get_connection()
            try:
                # Handle both string and UUID workflow_id
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return False
                else:
                    workflow_uuid = workflow_id

                # Find the most recent incomplete record for this workflow and action
                find_query = f"""
                    SELECT id FROM workflow_deployment_history
                    WHERE workflow_id = '{workflow_uuid}' AND deployment_action = '{deployment_action}' AND completed_at IS NULL
                    ORDER BY started_at DESC
                    LIMIT 1
                """

                history_id = await conn.fetchval(find_query)

                if history_id:
                    # Update completion info using string formatting
                    import json

                    current_time = datetime.now(timezone.utc)
                    set_clauses = [f"completed_at = '{current_time}'"]

                    if error_message:
                        set_clauses.append(f"error_message = '{error_message}'")

                    if deployment_logs:
                        logs_json = json.dumps(deployment_logs)
                        set_clauses.append(f"deployment_logs = '{logs_json}'::jsonb")

                    update_query = f"""
                        UPDATE workflow_deployment_history
                        SET {', '.join(set_clauses)}
                        WHERE id = '{history_id}'
                    """

                    await conn.execute(update_query)

                    logger.info(
                        f"Updated deployment history completion: {workflow_id} - {deployment_action}"
                    )
                    return True
                else:
                    logger.warning(
                        f"No incomplete deployment history found for {workflow_id} - {deployment_action}"
                    )
                    return False

            finally:
                await conn.close()

        except Exception as e:
            logger.error(
                f"Error updating deployment history completion {workflow_id}: {e}", exc_info=True
            )
            return False

    async def get_deployment_history(
        self, workflow_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get deployment history for a workflow using raw SQL"""
        try:
            conn = await self._get_connection()
            try:
                # Handle both string and UUID workflow_id
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return []
                else:
                    workflow_uuid = workflow_id

                query = f"""
                    SELECT id, workflow_id, deployment_action, from_status, to_status,
                           deployment_version, triggered_by, deployment_config,
                           error_message, deployment_logs, started_at, completed_at
                    FROM workflow_deployment_history
                    WHERE workflow_id = '{workflow_uuid}'
                    ORDER BY started_at DESC
                    LIMIT {limit}
                """

                rows = await conn.fetch(query)

                return [dict(row) for row in rows]

            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"Error getting deployment history for {workflow_id}: {e}", exc_info=True)
            return []
