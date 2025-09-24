"""
Direct PostgreSQL Database Access for Performance-Critical Operations

This module provides direct PostgreSQL connections to bypass Supabase REST API overhead
for performance-critical operations like execution logs retrieval.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import asyncpg
from config import settings

logger = logging.getLogger(__name__)


class DirectPostgreSQLClient:
    """
    Direct PostgreSQL client for high-performance database operations
    Bypasses Supabase REST API layer for critical performance paths
    """

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.connection_url = self._build_direct_connection_url()

    def _build_direct_connection_url(self) -> str:
        """
        Build direct PostgreSQL connection URL from existing DATABASE_URL or Supabase URL
        Prefers DATABASE_URL if available, otherwise builds from Supabase URL
        """
        # First try to use existing DATABASE_URL
        database_url = getattr(settings, "database_url", None) or os.getenv("DATABASE_URL")
        if database_url and database_url.startswith("postgres"):
            logger.info("🔗 Using existing DATABASE_URL for direct connection")
            return database_url

        # Fallback: build from Supabase URL
        supabase_url = settings.supabase_url
        if not supabase_url:
            raise ValueError("Neither DATABASE_URL nor SUPABASE_URL configured")

        # Parse Supabase URL to extract project ID
        parsed = urlparse(supabase_url)
        if not parsed.hostname:
            raise ValueError(f"Invalid SUPABASE_URL: {supabase_url}")

        # Extract project ID from hostname (e.g., "mkrczzgjeduruwxpanbj.supabase.co")
        hostname_parts = parsed.hostname.split(".")
        if len(hostname_parts) < 3 or hostname_parts[1] != "supabase":
            raise ValueError(f"Invalid Supabase hostname format: {parsed.hostname}")

        project_id = hostname_parts[0]

        # Get database password from service key or environment
        db_password = os.getenv("SUPABASE_DB_PASSWORD") or settings.supabase_secret_key
        if not db_password:
            raise ValueError(
                "Database password not found. Set SUPABASE_DB_PASSWORD or ensure SUPABASE_SECRET_KEY is set"
            )

        # Build direct PostgreSQL connection URL
        # Supabase uses this format: postgres://postgres:[password]@db.[project].supabase.co:5432/postgres
        db_host = f"db.{project_id}.supabase.co"
        db_url = f"postgres://postgres:{db_password}@{db_host}:5432/postgres"

        logger.info(f"🔗 Direct PostgreSQL connection to: {db_host}")
        return db_url

    async def initialize_pool(self, max_connections: int = 10) -> bool:
        """Initialize connection pool with performance optimizations"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_url,
                min_size=3,
                max_size=max_connections,
                command_timeout=15,  # Faster timeout for quick queries
                server_settings={
                    "application_name": "workflow_engine_direct",
                    "jit": "off",  # Disable JIT for consistent performance
                    "shared_preload_libraries": "pg_stat_statements",
                    "work_mem": "4MB",  # Optimize for small result sets
                    "random_page_cost": "1.1",  # Assume SSD storage
                    "effective_cache_size": "128MB",
                },
            )
            logger.info("✅ Direct PostgreSQL pool initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize PostgreSQL pool: {e}")
            return False

    async def close_pool(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Direct PostgreSQL pool closed")

    async def test_connection(self) -> bool:
        """Test direct database connection"""
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                logger.info("✅ Direct PostgreSQL connection test successful")
                return result == 1
        except Exception as e:
            logger.error(f"❌ Direct PostgreSQL connection test failed: {e}")
            return False

    async def get_execution_logs_fast(
        self,
        execution_id: str,
        limit: int = 100,
        offset: int = 0,
        level: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get execution logs with direct SQL query for maximum performance
        Bypasses REST API layer completely
        """
        if not self.pool:
            raise Exception("Database pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                # Build efficient SQL query
                where_conditions = ["execution_id = $1"]
                params = [execution_id]
                param_count = 1

                if level:
                    param_count += 1
                    where_conditions.append(f"level = ${param_count}")
                    params.append(level.upper())

                if start_time:
                    param_count += 1
                    where_conditions.append(f"created_at >= ${param_count}")
                    params.append(start_time)

                if end_time:
                    param_count += 1
                    where_conditions.append(f"created_at <= ${param_count}")
                    params.append(end_time)

                where_clause = " AND ".join(where_conditions)

                # Optimized query with index hints and minimal data transfer
                logs_query = f"""
                    SELECT id, execution_id, node_id, level, message, created_at, step_number,
                           user_friendly_message, display_priority, log_category, event_type
                    FROM workflow_execution_logs
                    WHERE {where_clause}
                    ORDER BY created_at ASC
                    LIMIT ${param_count + 1} OFFSET ${param_count + 2}
                """

                # Add query plan optimization hint for small result sets
                if limit <= 100:
                    logs_query = f"/*+ IndexScan(workflow_execution_logs) */ {logs_query}"
                params.extend([limit + 1, offset])

                # Execute query
                rows = await conn.fetch(logs_query, *params)

                # Convert to dict format and handle pagination
                logs = [dict(row) for row in rows]
                has_more = len(logs) > limit
                if has_more:
                    logs = logs[:limit]  # Remove extra record

                # Estimate total count (avoid expensive COUNT query)
                estimated_total = offset + len(logs) + (100 if has_more else 0)

                # Log performance metrics
                logger.info(
                    f"✅ Direct SQL: Retrieved {len(logs)} logs for {execution_id} (estimated: {estimated_total})"
                )

                return {
                    "execution_id": execution_id,
                    "logs": logs,
                    "total_count": estimated_total,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "has_more": has_more,
                    },
                }

        except Exception as e:
            logger.error(f"❌ Direct SQL query failed: {e}")
            raise

    async def get_execution_logs_with_count(
        self,
        execution_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get execution logs with exact count using efficient SQL
        Uses window function for single query performance
        """
        if not self.pool:
            raise Exception("Database pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                # Single query with window function for count (using actual schema)
                query = """
                    SELECT
                        id, execution_id, node_id, level, message, created_at, step_number,
                        user_friendly_message, display_priority, log_category, event_type,
                        COUNT(*) OVER() as total_count
                    FROM workflow_execution_logs
                    WHERE execution_id = $1
                    ORDER BY created_at ASC
                    LIMIT $2 OFFSET $3
                """

                rows = await conn.fetch(query, execution_id, limit, offset)

                if not rows:
                    return {
                        "execution_id": execution_id,
                        "logs": [],
                        "total_count": 0,
                        "pagination": {"limit": limit, "offset": offset, "has_more": False},
                    }

                # Extract logs and total count
                logs = []
                total_count = 0
                for row in rows:
                    row_dict = dict(row)
                    total_count = row_dict.pop("total_count")  # Remove from individual log
                    logs.append(row_dict)

                has_more = (offset + len(logs)) < total_count

                logger.info(
                    f"✅ Direct SQL with count: Retrieved {len(logs)}/{total_count} logs for {execution_id}"
                )

                return {
                    "execution_id": execution_id,
                    "logs": logs,
                    "total_count": total_count,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "has_more": has_more,
                    },
                }

        except Exception as e:
            logger.error(f"❌ Direct SQL with count failed: {e}")
            raise

    async def list_workflows_fast(
        self,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List workflows using direct PostgreSQL connection for maximum performance
        Bypasses Supabase REST API layer completely
        """
        try:
            if not self.pool:
                raise Exception("Database pool not initialized")

            logger.info(
                f"🚀 Fast workflow listing (active_only={active_only}, limit={limit}, offset={offset})"
            )

            # Build SQL query with optional filters
            conditions = []
            params = []
            param_count = 0

            if active_only:
                param_count += 1
                conditions.append(f"active = ${param_count}")
                params.append(True)

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # Count query for pagination
            count_query = f"""
                SELECT COUNT(*) as total
                FROM workflows
                {where_clause}
            """

            # Main query with optimized field selection (exclude large workflow_data JSON)
            list_query = f"""
                SELECT
                    id, user_id, session_id, name, description, version, active, tags,
                    icon_url, deployment_status, deployed_at, latest_execution_status,
                    latest_execution_time, latest_execution_id, created_at, updated_at
                FROM workflows
                {where_clause}
                ORDER BY deployment_status DESC, updated_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """

            # Add limit and offset parameters
            params.extend([limit, offset])

            async with self.pool.acquire() as conn:
                # Get total count
                count_result = await conn.fetchrow(
                    count_query, *params[:-2]
                )  # Exclude limit/offset for count
                total_count = count_result["total"] if count_result else 0

                # Get workflows
                workflows_result = await conn.fetch(list_query, *params)

                # Convert to list of dicts and handle potential JSON fields
                workflows = []
                for row in workflows_result:
                    workflow_dict = dict(row)
                    # Handle tags array conversion
                    if workflow_dict.get("tags"):
                        workflow_dict["tags"] = list(workflow_dict["tags"])
                    workflows.append(workflow_dict)

                has_more = total_count > offset + limit

                logger.info(
                    f"✅ Direct SQL: Retrieved {len(workflows)} workflows (total: {total_count})"
                )

                return {
                    "workflows": workflows,
                    "total_count": total_count,
                    "has_more": has_more,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "has_more": has_more,
                    },
                }

        except Exception as e:
            logger.error(f"❌ Direct workflow listing failed: {e}")
            raise

    async def get_workflow_fast(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a single workflow by ID with direct SQL."""
        if not self.pool:
            raise Exception("Database pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT id, user_id, session_id, name, description, version, active, tags,
                           icon_url, deployment_status, deployed_at, latest_execution_status,
                           latest_execution_time, latest_execution_id, created_at, updated_at,
                           workflow_data
                    FROM workflows
                    WHERE id = $1
                    LIMIT 1
                """
                row = await conn.fetchrow(query, workflow_id)
                if not row:
                    return None

                workflow = dict(row)
                # Convert tags to plain list
                if workflow.get("tags") is not None:
                    workflow["tags"] = list(workflow["tags"])  # type: ignore[index]
                return workflow
        except Exception as e:
            logger.error(f"❌ Direct get_workflow failed: {e}")
            raise

    async def create_workflow_fast(self, workflow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new workflow with direct SQL and return the created row."""
        if not self.pool:
            raise Exception("Database pool not initialized")

        columns = [
            "id",
            "user_id",
            "session_id",
            "name",
            "description",
            "version",
            "active",
            "tags",
            "icon_url",
            "deployment_status",
            "deployed_at",
            "latest_execution_status",
            "latest_execution_time",
            "latest_execution_id",
            "created_at",
            "updated_at",
            "workflow_data",
        ]

        try:
            async with self.pool.acquire() as conn:
                placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
                query = f"""
                    INSERT INTO workflows ({', '.join(columns)})
                    VALUES ({placeholders})
                    RETURNING {', '.join(columns)}
                """
                values = [workflow_data.get(col) for col in columns]
                row = await conn.fetchrow(query, *values)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Direct create_workflow failed: {e}")
            raise

    async def update_workflow_fast(
        self, workflow_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a workflow by ID with direct SQL and return the updated row."""
        if not self.pool:
            raise Exception("Database pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                set_clauses = []
                params: List[Any] = []
                idx = 0
                for key, value in updates.items():
                    idx += 1
                    set_clauses.append(f"{key} = ${idx}")
                    params.append(value)

                if not set_clauses:
                    return await self.get_workflow_fast(workflow_id)

                idx += 1
                params.append(workflow_id)

                query = f"""
                    UPDATE workflows
                    SET {', '.join(set_clauses)}
                    WHERE id = ${idx}
                    RETURNING id, user_id, session_id, name, description, version, active, tags,
                              icon_url, deployment_status, deployed_at, latest_execution_status,
                              latest_execution_time, latest_execution_id, created_at, updated_at,
                              workflow_data
                """
                row = await conn.fetchrow(query, *params)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Direct update_workflow failed: {e}")
            raise

    async def delete_workflow_fast(self, workflow_id: str) -> bool:
        """Delete a workflow by ID with direct SQL."""
        if not self.pool:
            raise Exception("Database pool not initialized")
        try:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM workflows WHERE id = $1", workflow_id)
                # asyncpg returns a string like 'DELETE 1'
                return res.startswith("DELETE ") and res.split(" ")[-1] != "0"
        except Exception as e:
            logger.error(f"❌ Direct delete_workflow failed: {e}")
            raise

    async def create_execution_fast(
        self, execution_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Insert into workflow_executions and return created row."""
        if not self.pool:
            raise Exception("Database pool not initialized")

        columns = [
            "execution_id",
            "workflow_id",
            "status",
            "mode",
            "triggered_by",
            "start_time",
            "end_time",
            "run_data",
            "metadata",
            "execution_metadata",
            "error_message",
            "error_details",
        ]

        try:
            async with self.pool.acquire() as conn:
                placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
                query = f"""
                    INSERT INTO workflow_executions ({', '.join(columns)})
                    VALUES ({placeholders})
                    RETURNING *
                """
                values = [execution_data.get(col) for col in columns]
                row = await conn.fetchrow(query, *values)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Direct create_execution failed: {e}")
            raise

    async def get_execution_fast(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow execution by execution_id."""
        if not self.pool:
            raise Exception("Database pool not initialized")
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM workflow_executions WHERE execution_id = $1 LIMIT 1",
                    execution_id,
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Direct get_execution failed: {e}")
            raise

    async def update_execution_fast(
        self, execution_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update workflow execution by execution_id and return updated row."""
        if not self.pool:
            raise Exception("Database pool not initialized")
        try:
            async with self.pool.acquire() as conn:
                set_clauses = []
                params: List[Any] = []
                idx = 0
                for key, value in updates.items():
                    idx += 1
                    set_clauses.append(f"{key} = ${idx}")
                    params.append(value)
                if not set_clauses:
                    return await self.get_execution_fast(execution_id)
                idx += 1
                params.append(execution_id)
                query = f"""
                    UPDATE workflow_executions
                    SET {', '.join(set_clauses)}
                    WHERE execution_id = ${idx}
                    RETURNING *
                """
                row = await conn.fetchrow(query, *params)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Direct update_execution failed: {e}")
            raise

    async def list_executions_fast(
        self,
        workflow_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List workflow executions with exact count via direct SQL."""
        if not self.pool:
            raise Exception("Database pool not initialized")
        try:
            conditions = []
            params: List[Any] = []
            idx = 0
            if workflow_id:
                idx += 1
                conditions.append(f"workflow_id = ${idx}")
                params.append(workflow_id)
            if status_filter:
                idx += 1
                conditions.append(f"status = ${idx}")
                params.append(status_filter)
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            count_query = f"SELECT COUNT(*) AS total FROM workflow_executions {where_clause}"
            list_query = (
                f"SELECT id, execution_id, workflow_id, status, mode, triggered_by, "
                f"start_time, end_time, error_message, created_at, updated_at "
                f"FROM workflow_executions {where_clause} "
                f"ORDER BY created_at DESC LIMIT ${idx + 1} OFFSET ${idx + 2}"
            )
            params_with_pagination = params + [limit, offset]

            async with self.pool.acquire() as conn:
                count_row = await conn.fetchrow(count_query, *params)
                total_count = count_row["total"] if count_row else 0
                rows = await conn.fetch(list_query, *params_with_pagination)
                executions = [dict(r) for r in rows]
                return {"executions": executions, "total_count": total_count}
        except Exception as e:
            logger.error(f"❌ Direct list_executions failed: {e}")
            raise

    async def list_node_templates_fast(
        self,
        category: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List node templates with optional filters."""
        if not self.pool:
            raise Exception("Database pool not initialized")
        try:
            conditions = []
            params: List[Any] = []
            idx = 0
            if category:
                idx += 1
                conditions.append(f"category = ${idx}")
                params.append(category)
            if node_type:
                idx += 1
                conditions.append(f"node_type = ${idx}")
                params.append(node_type)
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            count_query = f"SELECT COUNT(*) AS total FROM node_templates {where_clause}"
            list_query = (
                f"SELECT * FROM node_templates {where_clause} ORDER BY name ASC "
                f"LIMIT ${idx + 1} OFFSET ${idx + 2}"
            )

            params_with_pagination = params + [limit, offset]

            async with self.pool.acquire() as conn:
                count_row = await conn.fetchrow(count_query, *params)
                total_count = count_row["total"] if count_row else 0
                rows = await conn.fetch(list_query, *params_with_pagination)
                templates = [dict(r) for r in rows]
                return {"templates": templates, "total_count": total_count}
        except Exception as e:
            logger.error(f"❌ Direct list_node_templates failed: {e}")
            raise

    async def get_node_template_fast(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a single node template by ID."""
        if not self.pool:
            raise Exception("Database pool not initialized")
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM node_templates WHERE id = $1 LIMIT 1", template_id
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Direct get_node_template failed: {e}")
            raise


# Global instance
_direct_db: Optional[DirectPostgreSQLClient] = None


async def get_direct_db() -> DirectPostgreSQLClient:
    """Get or create direct database client"""
    global _direct_db
    if _direct_db is None:
        _direct_db = DirectPostgreSQLClient()
        await _direct_db.initialize_pool()
    return _direct_db


async def close_direct_db():
    """Close direct database connection"""
    global _direct_db
    if _direct_db:
        await _direct_db.close_pool()
        _direct_db = None
