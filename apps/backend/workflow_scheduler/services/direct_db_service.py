"""
Direct Database Service - Uses raw SQL connections to bypass SQLAlchemy prepared statement issues
"""

import asyncio
import logging
import socket
import time
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID

import asyncpg

from shared.models.workflow_new import WorkflowDeploymentStatus as DeploymentStatus
from workflow_scheduler.core.config import settings

logger = logging.getLogger(__name__)


class DirectDBService:
    """Direct database operations using raw asyncpg to bypass SQLAlchemy issues"""

    def __init__(self):
        self.database_url = settings.database_url
        self.pool: Optional[asyncpg.Pool] = None
        self._pool_initialized = False

    @staticmethod
    def _normalize_deployment_status(status: Optional[str]) -> str:
        """
        Normalize incoming deployment status values to align with the
        database constraint on workflows.deployment_status.

        Allowed values (per latest migration): 'pending', 'deployed', 'failed', 'undeployed'.
        Map legacy/uppercase values to the allowed set to avoid constraint violations.
        """
        if not status:
            return "pending"

        s = str(status).strip()
        # Try enum by name or value
        try:
            return DeploymentStatus[s.upper()].value
        except Exception:
            pass
        try:
            return DeploymentStatus(s).value
        except Exception:
            pass

        # Legacy mappings for transitional states
        mapping = {
            "DRAFT": DeploymentStatus.PENDING.value,
            "DEPLOYING": DeploymentStatus.PENDING.value,
            "UNDEPLOYING": DeploymentStatus.PENDING.value,
            "DEPRECATED": DeploymentStatus.UNDEPLOYED.value,
            "DEPLOYMENT_FAILED": DeploymentStatus.FAILED.value,
        }

        return mapping.get(s.upper(), DeploymentStatus.PENDING.value)

    async def initialize(self):
        """Initialize the database connection pool - call once on service startup"""
        if not self._pool_initialized:
            await self._initialize_pool()
            logger.info("🔌 DirectDBService initialized successfully")

    async def _initialize_pool(self):
        """Initialize connection pool if not already done"""
        if self._pool_initialized:
            return

        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Initializing database connection pool (attempt {attempt + 1}/{max_retries})"
                )
                self.pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=2,
                    max_size=8,
                    command_timeout=30,
                    statement_cache_size=0,  # Disable prepared statements for pgbouncer compatibility
                    server_settings={"application_name": "workflow_scheduler_direct"},
                )
                logger.info("✅ Database connection pool initialized successfully")
                self._pool_initialized = True
                return
            except (OSError, socket.gaierror, asyncpg.ConnectionError, asyncpg.InterfaceError) as e:
                error_str = str(e).lower()
                # Classify network vs other errors like workflow engine
                if any(
                    keyword in error_str
                    for keyword in [
                        "ssl",
                        "eof",
                        "connection",
                        "timeout",
                        "dns",
                        "resolve",
                        "name resolution",
                        "temporary failure",
                        "network",
                    ]
                ):
                    logger.warning(
                        f"⚠️ Network connection attempt {attempt + 1} failed: {type(e).__name__}: {e}"
                    )
                    if attempt < max_retries - 1:
                        logger.info(
                            f"Retrying database pool initialization in {retry_delay} seconds..."
                        )
                        time.sleep(
                            retry_delay
                        )  # Use sync sleep like workflow engine for network issues
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(
                            f"❌ All {max_retries} database pool initialization attempts failed"
                        )
                        raise
                else:
                    # Non-network error - re-raise immediately
                    logger.error(
                        f"❌ Database pool initialization failed with non-network error: {e}"
                    )
                    raise

    async def _get_connection(self):
        """Get a database connection from pool with fallback to direct connection"""
        # Initialize pool if not already done (fallback for backwards compatibility)
        if not self._pool_initialized:
            await self._initialize_pool()

        if self.pool:
            # Use pool connection (preferred)
            return self.pool.acquire()
        else:
            # Fallback to direct connection
            logger.warning("Using fallback direct connection (pool unavailable)")
            return await asyncpg.connect(
                self.database_url,
                command_timeout=30,
                statement_cache_size=0,
                server_settings={"application_name": "workflow_scheduler_direct_fallback"},
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
            # Use pool connection with context manager
            async with self.pool.acquire() as conn:
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
                    try:
                        current_version_result = await conn.fetchval(
                            "SELECT deployment_version FROM workflows WHERE id = $1",
                            workflow_uuid,
                        )
                        current_version = (current_version_result or 0) + 1
                    except Exception as e:
                        if 'column "deployment_version" does not exist' in str(e):
                            logger.warning("deployment_version column missing, adding it now...")
                            try:
                                await conn.execute(
                                    "ALTER TABLE workflows ADD COLUMN deployment_version INTEGER NOT NULL DEFAULT 1"
                                )
                                logger.info("✅ Added deployment_version column successfully")
                                # Now try again to get the version
                                current_version_result = await conn.fetchval(
                                    "SELECT deployment_version FROM workflows WHERE id = $1",
                                    workflow_uuid,
                                )
                                current_version = (current_version_result or 0) + 1
                            except Exception as add_error:
                                logger.error(
                                    f"Failed to add deployment_version column: {add_error}"
                                )
                                current_version = 1
                        else:
                            logger.error(f"Error getting deployment_version: {e}")
                            current_version = 1

                # Normalize status to satisfy DB constraint
                normalized_status = self._normalize_deployment_status(deployment_status)

                # Build the UPDATE query dynamically
                set_clauses = ["deployment_status = $2", "updated_at = $3"]
                params = [
                    workflow_uuid,
                    normalized_status,
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
                        f"✅ Updated workflow deployment status: {workflow_id} -> {normalized_status}"
                    )
                    return True
                else:
                    logger.warning(f"❌ No workflow found to update: {workflow_id}")
                    return False

        except Exception as e:
            logger.error(
                f"❌ Error updating workflow deployment status {workflow_id}: {e}",
                exc_info=True,
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
            # Use pool connection with context manager
            async with self.pool.acquire() as conn:
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

        except Exception as e:
            logger.error(
                f"❌ Error creating deployment history record {workflow_id}: {e}",
                exc_info=True,
            )
            return False

    async def get_workflow_current_status(self, workflow_id: str) -> Optional[Dict]:
        """Get current workflow deployment status"""
        try:
            # Use pool connection with context manager
            async with self.pool.acquire() as conn:
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

        except Exception as e:
            logger.error(f"Error getting workflow status {workflow_id}: {e}", exc_info=True)
            return None

    async def create_or_update_workflow(
        self,
        workflow_id: str,
        workflow_spec: Dict,
        user_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> bool:
        """Create or update a workflow record in the database"""
        try:
            # Use pool connection with context manager
            async with self.pool.acquire() as conn:
                # Validate workflow_id format
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return False
                else:
                    workflow_uuid = workflow_id

                # Extract metadata from workflow_spec
                metadata = workflow_spec.get("metadata", {})
                workflow_name = name or metadata.get("name", "Untitled Workflow")
                workflow_user_id = user_id or metadata.get("created_by")

                # Convert user_id to UUID if it's a string
                user_uuid = None
                if workflow_user_id:
                    try:
                        user_uuid = (
                            UUID(workflow_user_id)
                            if isinstance(workflow_user_id, str)
                            else workflow_user_id
                        )
                    except ValueError:
                        logger.warning(f"Invalid user_id format: {workflow_user_id}")
                        user_uuid = None

                # Use UPSERT to create or update the workflow record
                upsert_query = """
                    INSERT INTO workflows (
                        id,
                        user_id,
                        name,
                        workflow_data,
                        deployment_status,
                        deployment_version,
                        deployment_config,
                        created_at,
                        updated_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9
                    )
                    ON CONFLICT (id)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        workflow_data = EXCLUDED.workflow_data,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id
                """

                import json

                now_timestamp = int(datetime.now(timezone.utc).timestamp())

                result = await conn.fetchval(
                    upsert_query,
                    workflow_uuid,
                    user_uuid,
                    workflow_name,
                    json.dumps(workflow_spec),
                    DeploymentStatus.PENDING.value,  # Default deployment status
                    1,  # Default deployment version
                    json.dumps({}),  # Default deployment config
                    now_timestamp,
                    now_timestamp,
                )

                if result:
                    logger.info(f"✅ Created/updated workflow record: {workflow_id}")
                    return True
                else:
                    logger.warning(f"❌ Failed to create/update workflow record: {workflow_id}")
                    return False

        except Exception as e:
            logger.error(
                f"❌ Error creating/updating workflow {workflow_id}: {e}",
                exc_info=True,
            )
            return False

    async def get_workflow_by_id(self, workflow_id: str) -> Optional[Dict]:
        """Get a workflow record from the database by ID"""
        try:
            # Use pool connection with context manager
            async with self.pool.acquire() as conn:
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
                    SELECT id, user_id, name, workflow_data, deployment_status,
                           deployment_version, deployment_config, created_at, updated_at
                    FROM workflows
                    WHERE id = $1
                """

                row = await conn.fetchrow(query, workflow_uuid)

                if row:
                    return dict(row)
                else:
                    logger.warning(f"Workflow not found: {workflow_id}")
                    return None

        except Exception as e:
            logger.error(f"Error getting workflow {workflow_id}: {e}", exc_info=True)
            return None

    async def test_connection(self) -> bool:
        """Test database connection and pool health"""
        try:
            await self._initialize_pool()
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            return False

    async def close_pool(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Database connection pool closed")
            self._pool_initialized = False
