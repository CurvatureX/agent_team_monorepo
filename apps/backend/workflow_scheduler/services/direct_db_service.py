"""
Direct Database Service - Uses raw SQL connections to bypass SQLAlchemy prepared statement issues
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID

import asyncpg

from workflow_scheduler.core.config import settings
from shared.logging_config import get_logger

logger = get_logger(__name__)


class DirectDBService:
    """Direct database operations using raw asyncpg to bypass SQLAlchemy issues"""

    def __init__(self):
        self.database_url = settings.database_url

    async def _get_connection(self):
        """Get a raw asyncpg connection"""
        return await asyncpg.connect(
            self.database_url,
            command_timeout=30,
            statement_cache_size=0,  # Disable prepared statements for pgbouncer compatibility
            server_settings={"application_name": "workflow_scheduler_direct"},
        )

    async def update_workflow_deployment_status(
        self,
        workflow_id: str,
        deployment_status: str,
        deployed_at: Optional[datetime] = None,
        undeployed_at: Optional[datetime] = None,
        deployment_config: Optional[Dict] = None,
        increment_version: bool = False,
    ) -> bool:
        """Update workflow deployment status using raw SQL"""
        try:
            conn = await self._get_connection()
            try:
                # Validate workflow_id format
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return False
                else:
                    workflow_uuid = workflow_id

                # Get current version if we need to increment it
                current_version = 1
                if increment_version:
                    current_version_result = await conn.fetchval(
                        "SELECT deployment_version FROM workflows WHERE id = $1", workflow_uuid
                    )
                    current_version = (current_version_result or 0) + 1

                # Build the UPDATE query dynamically
                set_clauses = ["deployment_status = $2", "updated_at = $3"]
                params = [
                    workflow_uuid,
                    deployment_status,
                    int(datetime.now(timezone.utc).timestamp()),  # Unix timestamp for bigint field
                ]
                param_index = 4

                if deployed_at:
                    set_clauses.append(f"deployed_at = ${param_index}")
                    params.append(deployed_at)
                    param_index += 1

                if undeployed_at:
                    set_clauses.append(f"undeployed_at = ${param_index}")
                    params.append(undeployed_at)
                    param_index += 1

                if deployment_config:
                    import json

                    set_clauses.append(f"deployment_config = ${param_index}")
                    params.append(json.dumps(deployment_config))  # Convert dict to JSON string
                    param_index += 1

                if increment_version:
                    set_clauses.append(f"deployment_version = ${param_index}")
                    params.append(current_version)
                    param_index += 1

                query = f"UPDATE workflows SET {', '.join(set_clauses)} WHERE id = $1"

                result = await conn.execute(query, *params)

                # Extract number of affected rows
                affected_rows = int(result.split()[-1]) if result.startswith("UPDATE") else 0

                if affected_rows > 0:
                    logger.info(
                        f"✅ Updated workflow deployment status: {workflow_id} -> {deployment_status}"
                    )
                    return True
                else:
                    logger.warning(f"❌ No workflow found to update: {workflow_id}")
                    return False

            finally:
                await conn.close()

        except Exception as e:
            logger.error(
                f"❌ Error updating workflow deployment status {workflow_id}: {e}", exc_info=True
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
                # Validate workflow_id format
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

                current_time = datetime.now(timezone.utc)

                query = """
                    INSERT INTO workflow_deployment_history
                    (workflow_id, deployment_action, from_status, to_status, deployment_version,
                     triggered_by, deployment_config, error_message, deployment_logs, started_at, completed_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """

                import json

                await conn.execute(
                    query,
                    workflow_uuid,
                    deployment_action,
                    from_status,
                    to_status,
                    deployment_version,
                    triggered_by_uuid,
                    json.dumps(deployment_config or {}),  # Convert dict to JSON string
                    error_message,
                    json.dumps(deployment_logs or {}),  # Convert dict to JSON string
                    current_time,
                    current_time if error_message is None else None,
                )

                logger.info(
                    f"✅ Created deployment history record: {workflow_id} - {deployment_action}"
                )
                return True

            finally:
                await conn.close()

        except Exception as e:
            logger.error(
                f"❌ Error creating deployment history record {workflow_id}: {e}", exc_info=True
            )
            return False

    async def get_workflow_current_status(self, workflow_id: str) -> Optional[Dict]:
        """Get current workflow deployment status"""
        try:
            conn = await self._get_connection()
            try:
                # Validate workflow_id format
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return None
                else:
                    workflow_uuid = workflow_id

                query = """
                    SELECT deployment_status, deployment_version, deployed_at, undeployed_at, deployment_config
                    FROM workflows
                    WHERE id = $1
                """

                row = await conn.fetchrow(query, workflow_uuid)

                if row:
                    return dict(row)
                else:
                    logger.warning(f"Workflow not found: {workflow_id}")
                    return None

            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"Error getting workflow status {workflow_id}: {e}", exc_info=True)
            return None
