"""
Supabase-based repository for workflow operations with RLS support.
Replaces direct PostgreSQL connection to leverage Row Level Security.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from supabase import Client, create_client

logger = logging.getLogger(__name__)


class SupabaseWorkflowRepository:
    """Repository for workflow operations using Supabase client with RLS support."""

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize Supabase client with optional user access token for RLS.

        Args:
            access_token: JWT token for RLS user context. If None, uses service role.
        """
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.access_token = access_token
        self.use_rls = access_token is not None

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
                        "Could not set Authorization header, falling back to session-based auth"
                    )
                    self.client.auth.set_session(access_token, access_token)
        else:
            # For service role, use service key
            service_key = os.getenv("SUPABASE_SECRET_KEY")
            if not service_key:
                raise ValueError("SUPABASE_SECRET_KEY must be configured")
            self.client: Client = create_client(self.supabase_url, service_key)

        logger.info(
            f"✅ Supabase client initialized with {'RLS (user token)' if self.use_rls else 'service role'}"
        )

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
                f"✅ Retrieved {len(workflows)} workflows (total: {total_count}) via Supabase RLS"
            )
            return workflows, total_count

        except Exception as e:
            logger.error(f"❌ Error listing workflows via Supabase: {e}")
            raise

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a single workflow by ID using RLS."""
        try:
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
                logger.info(f"✅ Retrieved workflow {workflow_id} via Supabase RLS")
            else:
                logger.info(f"❌ Workflow {workflow_id} not found or not accessible")

            return workflow

        except Exception as e:
            logger.error(f"❌ Error getting workflow {workflow_id} via Supabase: {e}")
            return None

    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new workflow using RLS."""
        try:
            response = self.client.table("workflows").insert(workflow_data).execute()

            if response.data:
                created_workflow = response.data[0]
                logger.info(f"✅ Created workflow {created_workflow['id']} via Supabase RLS")
                return created_workflow
            else:
                logger.error("❌ Failed to create workflow - no data returned")
                return None

        except Exception as e:
            logger.error(f"❌ Error creating workflow via Supabase: {e}")
            raise

    async def update_workflow(
        self, workflow_id: str, workflow_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a workflow using RLS."""
        try:
            response = (
                self.client.table("workflows").update(workflow_data).eq("id", workflow_id).execute()
            )

            if response.data:
                updated_workflow = response.data[0]
                logger.info(f"✅ Updated workflow {workflow_id} via Supabase RLS")
                return updated_workflow
            else:
                logger.error(
                    f"❌ Failed to update workflow {workflow_id} - not found or not accessible"
                )
                return None

        except Exception as e:
            logger.error(f"❌ Error updating workflow {workflow_id} via Supabase: {e}")
            raise

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow using RLS."""
        try:
            response = self.client.table("workflows").delete().eq("id", workflow_id).execute()

            if response.data:
                logger.info(f"✅ Deleted workflow {workflow_id} via Supabase RLS")
                return True
            else:
                logger.error(
                    f"❌ Failed to delete workflow {workflow_id} - not found or not accessible"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Error deleting workflow {workflow_id} via Supabase: {e}")
            raise

    # Workflow Execution operations
    async def create_execution(self, execution_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new workflow execution."""
        try:
            response = self.client.table("workflow_executions").insert(execution_data).execute()

            if response.data:
                created_execution = response.data[0]
                logger.info(
                    f"✅ Created execution {created_execution['execution_id']} (DB ID: {created_execution['id']}) via Supabase"
                )
                return created_execution
            else:
                logger.error("❌ Failed to create execution - no data returned")
                return None

        except Exception as e:
            logger.error(f"❌ Error creating execution via Supabase: {e}")
            raise

    async def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get a single execution by ID."""
        try:
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
            logger.error(f"❌ Error getting execution {execution_id} via Supabase: {e}")
            return None

    async def update_execution(
        self, execution_id: str, execution_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an execution."""
        try:
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
            logger.error(f"❌ Error updating execution {execution_id} via Supabase: {e}")
            raise

    async def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List workflow executions with optional filters."""
        try:
            query = self.client.table("workflow_executions").select("*", count="exact")

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

            logger.info(
                f"✅ Retrieved {len(executions)} executions (total: {total_count}) via Supabase"
            )
            return executions, total_count

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
