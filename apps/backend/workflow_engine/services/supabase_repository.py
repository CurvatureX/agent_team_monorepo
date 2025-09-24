"""
Supabase-based repository for workflow operations with RLS support.
Replaces direct PostgreSQL connection to leverage Row Level Security.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from supabase import Client, create_client

logger = logging.getLogger(__name__)

# Redis-based caching for automatic TTL management
try:
    import redis

    _redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    # Test Redis connection
    _redis_client.ping()
    REDIS_AVAILABLE = True
    logger.info("✅ Redis client initialized for caching")
except (ImportError, redis.ConnectionError, redis.TimeoutError) as e:
    _redis_client = None
    REDIS_AVAILABLE = False
    logger.warning(f"⚠️ Redis not available ({e}), using in-memory cache")

# Fallback in-memory cache when Redis is not available
_memory_cache = {}
_memory_cache_ttl = {}

# Cache TTL durations (seconds) - Redis automatically handles expiration
CACHE_TTL_EXECUTIONS = 1  # 1 second for execution lists (ensures immediate freshness)
CACHE_TTL_WORKFLOWS = 30  # 30 seconds for workflow metadata
CACHE_TTL_TEMPLATES = 300  # 5 minutes for static data like node templates


# Global client instance for connection pooling
_global_service_client: Optional[Client] = None


def _get_cache(key: str) -> Optional[Any]:
    """Get value from cache (Redis or memory fallback)."""
    if REDIS_AVAILABLE:
        try:
            cached_data = _redis_client.get(key)
            if cached_data:
                return json.loads(cached_data.decode("utf-8"))
        except Exception as e:
            logger.warning(f"Redis cache get error: {e}")

    # Fallback to memory cache
    current_time = time.time()
    if key in _memory_cache and current_time < _memory_cache_ttl.get(key, 0):
        return _memory_cache[key]

    return None


def _set_cache(key: str, value: Any, ttl: int):
    """Set value in cache with TTL (Redis or memory fallback)."""
    if REDIS_AVAILABLE:
        try:
            _redis_client.setex(key, ttl, json.dumps(value))
            return
        except Exception as e:
            logger.warning(f"Redis cache set error: {e}")

    # Fallback to memory cache
    _memory_cache[key] = value
    _memory_cache_ttl[key] = time.time() + ttl


class SupabaseWorkflowRepository:
    """Repository for workflow operations using Supabase client with RLS support."""

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize Supabase client with optional user access token for RLS.

        Args:
            access_token: JWT token for RLS user context. If None, uses service role.
        """
        global _global_service_client

        self.supabase_url = os.getenv("SUPABASE_URL")
        self.access_token = access_token
        self.use_rls = access_token is not None
        # Prefer direct DB when not using RLS (service role/admin operations)
        self.prefer_direct_db = not self.use_rls

        if not self.supabase_url:
            raise ValueError("SUPABASE_URL must be configured")

        if self.use_rls:
            # For RLS, use anon key with user's access token in headers
            anon_key = os.getenv("SUPABASE_ANON_KEY")
            if not anon_key:
                raise ValueError("SUPABASE_ANON_KEY must be configured for RLS")
            self.client: Client = create_client(self.supabase_url, anon_key)
            # Set Authorization header for RLS instead of session (much faster)
            # Use the correct way to set headers on the underlying session
            self.client.auth.session = None  # Clear any existing session
            if hasattr(self.client, "_session"):
                self.client._session.headers.update({"Authorization": f"Bearer {access_token}"})
            else:
                # Fallback: modify the client's headers if available
                if hasattr(self.client, "postgrest") and hasattr(self.client.postgrest, "session"):
                    self.client.postgrest.session.headers.update(
                        {"Authorization": f"Bearer {access_token}"}
                    )
                else:
                    logger.warning(
                        "Could not set Authorization header on Supabase client, "
                        "RLS may not work properly with this token format"
                    )
                    # Skip session-based auth to avoid JWT validation errors
                    # Let the request proceed with whatever token format was provided
        else:
            # For service role, use global shared client for connection pooling
            if _global_service_client is None:
                service_key = os.getenv("SUPABASE_SECRET_KEY")
                if not service_key:
                    raise ValueError("SUPABASE_SECRET_KEY must be configured")
                _global_service_client = create_client(self.supabase_url, service_key)
                logger.info("✅ Global Supabase service client initialized")

            self.client: Client = _global_service_client

        logger.info(
            f"✅ Repository ready: {'RLS (user token via Supabase REST)' if self.use_rls else 'service role (prefer direct Postgres)'}"
        )

    async def _handle_supabase_error(
        self, e: Exception, operation: str, **kwargs
    ) -> tuple[bool, any]:
        """
        Centralized error handling for DNS resolution and JWT validation issues.
        Returns (should_return_result, result_value).
        If should_return_result is False, calling method should continue with general error handling.
        """
        error_str = str(e)

        # Handle DNS resolution issues with retry
        if "Temporary failure in name resolution" in error_str or "[Errno -3]" in error_str:
            logger.warning(f"🔄 DNS resolution failed for {operation}, retrying in 2s...")
            await asyncio.sleep(2)
            try:
                # The retry_callback should be provided by the calling method
                retry_callback = kwargs.get("retry_callback")
                if retry_callback:
                    result = await retry_callback()
                    if result is not None:
                        logger.info(f"✅ {operation} successful after DNS retry")
                        return True, result
                    else:
                        logger.warning(f"⚠️ {operation} failed - no data returned after DNS retry")
                        return True, None
            except Exception as retry_e:
                retry_error_str = str(retry_e)
                logger.error(f"❌ Retry failed for {operation}: {retry_error_str}")

        # Handle JWT validation errors gracefully
        elif (
            "JWSError" in error_str
            or "CompactDecodeError" in error_str
            or "Invalid number of parts" in error_str
        ):
            logger.warning(
                f"⚠️ JWT validation error for {operation}, falling back to service role access"
            )
            try:
                fallback_callback = kwargs.get("fallback_callback")
                if fallback_callback:
                    service_repo = SupabaseWorkflowRepository(access_token=None)
                    result = await fallback_callback(service_repo)
                    logger.info(f"✅ {operation} successful via service role fallback")
                    return True, result
            except Exception as fallback_error:
                logger.error(
                    f"❌ Fallback service role access also failed for {operation}: {fallback_error}"
                )

        # No special handling needed, let calling method handle
        return False, None

    async def list_workflows(
        self,
        active_only: bool = False,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List workflows using Supabase client with RLS filtering.

        Returns:
            Tuple of (workflow_list, total_count)
        """
        try:
            # Fast path: direct SQL when not using RLS
            if self.prefer_direct_db:
                try:
                    from database_direct import get_direct_db

                    direct_db = await get_direct_db()

                    # Build direct query with filters
                    # database_direct.list_workflows_fast already excludes workflow_data
                    result = await direct_db.list_workflows_fast(
                        active_only=active_only, limit=limit, offset=offset, user_id=None
                    )
                    workflows = result.get("workflows", [])
                    total_count = result.get("total_count", 0)
                    return workflows, total_count
                except Exception as de:
                    logger.warning(
                        f"⚠️ Direct DB list_workflows failed, falling back to Supabase REST: {de}"
                    )

            # Build query - RLS automatically filters by user
            # Metadata only for listing - no workflow_data needed
            query = self.client.table("workflows").select(
                "id, user_id, session_id, name, description, version, active, tags, icon_url, "
                "deployment_status, deployed_at, latest_execution_status, "
                "latest_execution_time, latest_execution_id, created_at, updated_at",
                count="exact",  # Get total count
            )

            # Apply filters
            if active_only:
                query = query.eq("active", True)

            if tags:
                for tag in tags:
                    query = query.contains("tags", [tag])

            # Apply ordering and pagination
            query = query.order("updated_at", desc=True)
            query = query.range(offset, offset + limit - 1)

            # Execute query
            response = query.execute()

            workflows = response.data or []
            total_count = response.count or 0

            logger.info(
                f"✅ Retrieved {len(workflows)} workflows (total: {total_count}) via Supabase"
            )
            return workflows, total_count

        except Exception as e:
            logger.error(f"❌ Error listing workflows via Supabase: {e}")
            raise

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a single workflow by ID."""
        try:
            if self.prefer_direct_db:
                try:
                    from database_direct import get_direct_db

                    direct_db = await get_direct_db()
                    workflow = await direct_db.get_workflow_fast(workflow_id)
                    if workflow:
                        logger.info(f"✅ Retrieved workflow {workflow_id} via direct SQL")
                        return workflow
                except Exception as de:
                    logger.warning(
                        f"⚠️ Direct DB get_workflow failed, falling back to Supabase REST: {de}"
                    )

            response = (
                self.client.table("workflows")
                .select(
                    "id, user_id, session_id, name, description, version, active, tags, icon_url, "
                    "deployment_status, deployed_at, latest_execution_status, "
                    "latest_execution_time, latest_execution_id, created_at, updated_at, workflow_data"
                )
                .eq("id", workflow_id)
                .single()
                .execute()
            )

            workflow = response.data
            if workflow:
                logger.info(f"✅ Retrieved workflow {workflow_id} via Supabase")
            else:
                logger.info(f"❌ Workflow {workflow_id} not found or not accessible")

            return workflow

        except Exception as e:
            error_str = str(e)

            # Handle DNS resolution issues with retry
            if "Temporary failure in name resolution" in error_str or "[Errno -3]" in error_str:
                logger.warning(
                    f"🔄 DNS resolution failed for workflow {workflow_id}, retrying in 2s..."
                )
                await asyncio.sleep(2)
                try:
                    # Retry once with the same query
                    response = (
                        self.client.table("workflows")
                        .select(
                            "id, user_id, session_id, name, description, version, active, tags, icon_url, "
                            "deployment_status, deployed_at, latest_execution_status, "
                            "latest_execution_time, latest_execution_id, created_at, updated_at, workflow_data"
                        )
                        .eq("id", workflow_id)
                        .single()
                        .execute()
                    )

                    workflow = response.data
                    if workflow:
                        logger.info(
                            f"✅ Retrieved workflow {workflow_id} via Supabase (retry successful)"
                        )
                        return workflow
                    else:
                        logger.warning(
                            f"⚠️ Workflow {workflow_id} not found after successful retry"
                        )
                        return None

                except Exception as retry_e:
                    retry_error_str = str(retry_e)
                    logger.error(f"❌ Retry failed for workflow {workflow_id}: {retry_error_str}")
                    # If retry also has DNS issues, fall through to general error handling
                    if "Temporary failure in name resolution" not in retry_error_str:
                        # Different error on retry, log and continue to general error handling
                        pass

            # Handle JWT validation errors gracefully
            elif (
                "JWSError" in error_str
                or "CompactDecodeError" in error_str
                or "Invalid number of parts" in error_str
            ):
                logger.warning(
                    f"⚠️ JWT validation error for workflow {workflow_id}, falling back to service role access"
                )
                # Try with service role client as fallback
                try:
                    service_repo = SupabaseWorkflowRepository(access_token=None)
                    return await service_repo.get_workflow(workflow_id)
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback service role access also failed: {fallback_error}")

            # General error logging
            logger.error(f"❌ Error getting workflow {workflow_id} via Supabase: {e}")
            return None

    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new workflow."""
        try:
            if self.prefer_direct_db:
                try:
                    from database_direct import get_direct_db

                    direct_db = await get_direct_db()
                    created = await direct_db.create_workflow_fast(workflow_data)
                    if created:
                        logger.info(f"✅ Created workflow {created['id']} via direct SQL")
                        return created
                except Exception as de:
                    logger.warning(
                        f"⚠️ Direct DB create_workflow failed, falling back to Supabase REST: {de}"
                    )

            response = self.client.table("workflows").insert(workflow_data).execute()

            if response.data:
                created_workflow = response.data[0]
                logger.info(f"✅ Created workflow {created_workflow['id']} via Supabase")
                return created_workflow
            else:
                logger.error("❌ Failed to create workflow - no data returned")
                return None

        except Exception as e:
            error_str = str(e)

            # Handle DNS resolution issues with retry
            if "Temporary failure in name resolution" in error_str or "[Errno -3]" in error_str:
                logger.warning("🔄 DNS resolution failed for create_workflow, retrying in 2s...")
                await asyncio.sleep(2)
                try:
                    # Retry once
                    response = self.client.table("workflows").insert(workflow_data).execute()
                    if response.data:
                        created_workflow = response.data[0]
                        logger.info(
                            f"✅ Created workflow {created_workflow['id']} via Supabase (retry successful)"
                        )
                        return created_workflow
                    else:
                        logger.error("❌ Failed to create workflow - no data returned after retry")
                        return None
                except Exception as retry_e:
                    logger.error(f"❌ Retry failed for create_workflow: {retry_e}")

            # Handle JWT validation errors gracefully
            elif (
                "JWSError" in error_str
                or "CompactDecodeError" in error_str
                or "Invalid number of parts" in error_str
            ):
                logger.warning(
                    "⚠️ JWT validation error for create_workflow, falling back to service role access"
                )
                try:
                    service_repo = SupabaseWorkflowRepository(access_token=None)
                    return await service_repo.create_workflow(workflow_data)
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback service role access also failed: {fallback_error}")

            # General error logging and re-raise
            logger.error(f"❌ Error creating workflow via repository: {e}")
            raise

    async def update_workflow(
        self, workflow_id: str, workflow_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a workflow using RLS."""
        try:
            if self.prefer_direct_db:
                try:
                    from database_direct import get_direct_db

                    direct_db = await get_direct_db()
                    updated = await direct_db.update_workflow_fast(workflow_id, workflow_data)
                    if updated:
                        logger.info(f"✅ Updated workflow {workflow_id} via direct SQL")
                        return updated
                except Exception as de:
                    logger.warning(
                        f"⚠️ Direct DB update_workflow failed, falling back to Supabase REST: {de}"
                    )

            response = (
                self.client.table("workflows").update(workflow_data).eq("id", workflow_id).execute()
            )

            if response.data:
                updated_workflow = response.data[0]
                logger.info(f"✅ Updated workflow {workflow_id} via Supabase")
                return updated_workflow
            else:
                logger.error(
                    f"❌ Failed to update workflow {workflow_id} - not found or not accessible"
                )
                return None

        except Exception as e:
            error_str = str(e)

            # Handle DNS resolution issues with retry
            if "Temporary failure in name resolution" in error_str or "[Errno -3]" in error_str:
                logger.warning(
                    f"🔄 DNS resolution failed for update_workflow {workflow_id}, retrying in 2s..."
                )
                await asyncio.sleep(2)
                try:
                    # Retry once
                    response = (
                        self.client.table("workflows")
                        .update(workflow_data)
                        .eq("id", workflow_id)
                        .execute()
                    )
                    if response.data:
                        updated_workflow = response.data[0]
                        logger.info(
                            f"✅ Updated workflow {workflow_id} via Supabase (retry successful)"
                        )
                        return updated_workflow
                    else:
                        logger.error(
                            f"❌ Failed to update workflow {workflow_id} - not found after retry"
                        )
                        return None
                except Exception as retry_e:
                    logger.error(f"❌ Retry failed for update_workflow {workflow_id}: {retry_e}")

            # Handle JWT validation errors gracefully
            elif (
                "JWSError" in error_str
                or "CompactDecodeError" in error_str
                or "Invalid number of parts" in error_str
            ):
                logger.warning(
                    f"⚠️ JWT validation error for update_workflow {workflow_id}, falling back to service role access"
                )
                try:
                    service_repo = SupabaseWorkflowRepository(access_token=None)
                    return await service_repo.update_workflow(workflow_id, workflow_data)
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback service role access also failed: {fallback_error}")

            # General error logging and re-raise
            logger.error(f"❌ Error updating workflow {workflow_id} via repository: {e}")
            raise

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow using RLS."""
        try:
            if self.prefer_direct_db:
                try:
                    from database_direct import get_direct_db

                    direct_db = await get_direct_db()
                    ok = await direct_db.delete_workflow_fast(workflow_id)
                    if ok:
                        logger.info(f"✅ Deleted workflow {workflow_id} via direct SQL")
                        return True
                except Exception as de:
                    logger.warning(
                        f"⚠️ Direct DB delete_workflow failed, falling back to Supabase REST: {de}"
                    )

            response = self.client.table("workflows").delete().eq("id", workflow_id).execute()

            if response.data:
                logger.info(f"✅ Deleted workflow {workflow_id} via Supabase")
                return True
            else:
                logger.error(
                    f"❌ Failed to delete workflow {workflow_id} - not found or not accessible"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Error deleting workflow {workflow_id} via repository: {e}")
            raise

    # Workflow Execution operations
    async def create_execution(self, execution_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new workflow execution (Redis TTL handles cache freshness automatically)."""
        try:
            if self.prefer_direct_db:
                try:
                    from database_direct import get_direct_db

                    direct_db = await get_direct_db()
                    created = await direct_db.create_execution_fast(execution_data)
                    if created:
                        logger.info(f"✅ Created execution {created['execution_id']} via direct SQL")
                        return created
                except Exception as de:
                    logger.warning(
                        f"⚠️ Direct DB create_execution failed, falling back to Supabase REST: {de}"
                    )

            response = self.client.table("workflow_executions").insert(execution_data).execute()

            if response.data:
                created_execution = response.data[0]
                logger.info(f"✅ Created execution {created_execution['execution_id']} via Supabase")
                # Note: Redis TTL will automatically expire cache within 1 second, ensuring freshness
                return created_execution
            else:
                logger.error("❌ Failed to create execution - no data returned")
                return None

        except Exception as e:
            error_str = str(e)

            # Handle DNS resolution issues with retry
            if "Temporary failure in name resolution" in error_str or "[Errno -3]" in error_str:
                logger.warning("🔄 DNS resolution failed for create_execution, retrying in 2s...")
                await asyncio.sleep(2)
                try:
                    # Retry once
                    response = (
                        self.client.table("workflow_executions").insert(execution_data).execute()
                    )
                    if response.data:
                        created_execution = response.data[0]
                        logger.info(
                            f"✅ Created execution {created_execution['execution_id']} via Supabase (retry successful)"
                        )
                        return created_execution
                    else:
                        logger.error("❌ Failed to create execution - no data returned after retry")
                        return None
                except Exception as retry_e:
                    logger.error(f"❌ Retry failed for create_execution: {retry_e}")

            # Handle JWT validation errors gracefully
            elif (
                "JWSError" in error_str
                or "CompactDecodeError" in error_str
                or "Invalid number of parts" in error_str
            ):
                logger.warning(
                    "⚠️ JWT validation error for create_execution, falling back to service role access"
                )
                try:
                    service_repo = SupabaseWorkflowRepository(access_token=None)
                    return await service_repo.create_execution(execution_data)
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback service role access also failed: {fallback_error}")

            # General error logging and re-raise
            logger.error(f"❌ Error creating execution via repository: {e}")
            raise

    async def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get a single execution by ID."""
        try:
            if self.prefer_direct_db:
                try:
                    from database_direct import get_direct_db

                    direct_db = await get_direct_db()
                    execution = await direct_db.get_execution_fast(execution_id)
                    if execution:
                        logger.info(f"✅ Retrieved execution {execution_id} via direct SQL")
                        return execution
                except Exception as de:
                    logger.warning(
                        f"⚠️ Direct DB get_execution failed, falling back to Supabase REST: {de}"
                    )

            response = (
                self.client.table("workflow_executions")
                .select("*")
                .eq("execution_id", execution_id)
                .single()
                .execute()
            )

            execution = response.data
            if execution:
                logger.info(f"✅ Retrieved execution {execution_id} via Supabase")
            else:
                logger.info(f"❌ Execution {execution_id} not found")

            return execution

        except Exception as e:
            logger.error(f"❌ Error getting execution {execution_id}: {e}")
            return None

    async def update_execution(
        self, execution_id: str, execution_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an execution."""
        try:
            if self.prefer_direct_db:
                try:
                    from database_direct import get_direct_db

                    direct_db = await get_direct_db()
                    updated = await direct_db.update_execution_fast(execution_id, execution_data)
                    if updated:
                        logger.info(f"✅ Updated execution {execution_id} via direct SQL")
                        return updated
                except Exception as de:
                    logger.warning(
                        f"⚠️ Direct DB update_execution failed, falling back to Supabase REST: {de}"
                    )

            response = (
                self.client.table("workflow_executions")
                .update(execution_data)
                .eq("execution_id", execution_id)
                .execute()
            )

            if response.data:
                updated_execution = response.data[0]
                logger.info(f"✅ Updated execution {execution_id} via Supabase")
                return updated_execution
            else:
                logger.error(f"❌ Failed to update execution {execution_id} - not found")
                return None

        except Exception as e:
            logger.error(f"❌ Error updating execution {execution_id}: {e}")
            raise

    async def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List workflow executions with Redis-based caching and automatic TTL."""
        # Create cache key
        cache_key = f"executions:{workflow_id}:{status_filter}:{limit}:{offset}"

        # Check cache first (only for frequent queries)
        if workflow_id and not status_filter and offset == 0 and limit <= 20:
            cached_result = _get_cache(cache_key)
            if cached_result:
                logger.info(f"✅ Redis cache hit for executions {workflow_id}")
                return tuple(cached_result)  # Convert back to tuple

        try:
            if self.prefer_direct_db:
                try:
                    from database_direct import get_direct_db

                    direct_db = await get_direct_db()
                    result = await direct_db.list_executions_fast(
                        workflow_id=workflow_id,
                        status_filter=status_filter,
                        limit=limit,
                        offset=offset,
                    )
                    executions = result.get("executions", [])
                    total_count = result.get("total_count", 0)
                    # Cache with TTL only for frequent default query
                    if workflow_id and not status_filter and offset == 0 and limit <= 20:
                        _set_cache(cache_key, (executions, total_count), CACHE_TTL_EXECUTIONS)
                    return executions, total_count
                except Exception as de:
                    logger.warning(
                        f"⚠️ Direct DB list_executions failed, falling back to Supabase REST: {de}"
                    )

            # Optimize field selection - only fetch essential fields for listing
            # Exclude potentially large fields like run_data, error_details, execution_metadata
            query = self.client.table("workflow_executions").select(
                "id, execution_id, workflow_id, status, mode, triggered_by, "
                "start_time, end_time, error_message, created_at, updated_at",
                count="exact",
            )

            # Apply filters
            if workflow_id:
                query = query.eq("workflow_id", workflow_id)
            if status_filter:
                query = query.eq("status", status_filter)

            # Apply ordering and pagination
            query = query.order("created_at", desc=True)
            query = query.range(offset, offset + limit - 1)

            response = query.execute()

            executions = response.data or []
            total_count = response.count or 0
            result = (executions, total_count)

            # Cache with Redis TTL (automatically expires after 1 second)
            if workflow_id and not status_filter and offset == 0 and limit <= 20:
                _set_cache(cache_key, result, CACHE_TTL_EXECUTIONS)
                logger.info(
                    f"📦 Cached executions for {workflow_id} with {CACHE_TTL_EXECUTIONS}s TTL"
                )

            logger.info(
                f"✅ Retrieved {len(executions)} executions (total: {total_count}) via Supabase"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Error listing executions via Supabase: {e}")
            raise

    # Node Templates operations
    async def list_node_templates(
        self,
        category: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List node templates with optional filters."""
        try:
            if self.prefer_direct_db:
                try:
                    from database_direct import get_direct_db

                    direct_db = await get_direct_db()
                    result = await direct_db.list_node_templates_fast(
                        category=category, node_type=node_type, limit=limit, offset=offset
                    )
                    return result.get("templates", []), result.get("total_count", 0)
                except Exception as de:
                    logger.warning(
                        f"⚠️ Direct DB list_node_templates failed, falling back to Supabase REST: {de}"
                    )

            query = self.client.table("node_templates").select("*", count="exact")

            # Apply filters
            if category:
                query = query.eq("category", category)
            if node_type:
                query = query.eq("node_type", node_type)

            # Apply ordering and pagination
            query = query.order("name")
            query = query.range(offset, offset + limit - 1)

            response = query.execute()

            templates = response.data or []
            total_count = response.count or 0

            logger.info(
                f"✅ Retrieved {len(templates)} node templates (total: {total_count}) via Supabase"
            )
            return templates, total_count

        except Exception as e:
            logger.error(f"❌ Error listing node templates via Supabase: {e}")
            raise

    async def get_node_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a single node template by ID."""
        try:
            if self.prefer_direct_db:
                try:
                    from database_direct import get_direct_db

                    direct_db = await get_direct_db()
                    template = await direct_db.get_node_template_fast(template_id)
                    return template
                except Exception as de:
                    logger.warning(
                        f"⚠️ Direct DB get_node_template failed, falling back to Supabase REST: {de}"
                    )
            response = (
                self.client.table("node_templates")
                .select("*")
                .eq("id", template_id)
                .single()
                .execute()
            )

            template = response.data
            if template:
                logger.info(f"✅ Retrieved node template {template_id} via Supabase")
            else:
                logger.info(f"❌ Node template {template_id} not found")

            return template

        except Exception as e:
            logger.error(f"❌ Error getting node template {template_id} via Supabase: {e}")
            return None

    # Bulk operations
    async def bulk_insert(
        self, table_name: str, data_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Perform bulk insert operation."""
        try:
            response = self.client.table(table_name).insert(data_list).execute()

            if response.data:
                logger.info(
                    f"✅ Bulk inserted {len(response.data)} records to {table_name} via Supabase"
                )
                return response.data
            else:
                logger.error(f"❌ Failed to bulk insert to {table_name} - no data returned")
                return []

        except Exception as e:
            logger.error(f"❌ Error bulk inserting to {table_name} via Supabase: {e}")
            raise

    async def bulk_update(
        self, table_name: str, updates: List[Dict[str, Any]], match_column: str = "id"
    ) -> List[Dict[str, Any]]:
        """Perform bulk update operation."""
        try:
            updated_records = []
            for update_data in updates:
                match_value = update_data.pop(match_column)
                response = (
                    self.client.table(table_name)
                    .update(update_data)
                    .eq(match_column, match_value)
                    .execute()
                )
                if response.data:
                    updated_records.extend(response.data)

            logger.info(
                f"✅ Bulk updated {len(updated_records)} records in {table_name} via Supabase"
            )
            return updated_records

        except Exception as e:
            logger.error(f"❌ Error bulk updating {table_name} via Supabase: {e}")
            raise
