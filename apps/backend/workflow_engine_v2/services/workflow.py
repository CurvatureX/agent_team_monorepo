"""Workflow service (v2) for creating, validating, and retrieving workflows.

Stores workflows in-memory (can be swapped for DB-backed repo later).
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.db_models import WorkflowDB
from shared.models.supabase import create_supabase_client

# Use absolute imports
from shared.models.workflow import Workflow, WorkflowMetadata
from workflow_engine_v2.core.spec import coerce_node_to_v2, get_spec
from workflow_engine_v2.core.validation import validate_workflow


class WorkflowServiceV2:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        # Initialize Supabase client for database persistence
        try:
            self.supabase = create_supabase_client()
            self.logger.info("✅ Supabase client initialized for workflow persistence")
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to initialize Supabase client: {e}")
            self.supabase = None
            raise Exception("Supabase client is required for workflow operations")

    def create_workflow(
        self,
        *,
        workflow_id: str,
        name: str,
        created_by: str,
        created_time_ms: int,
        nodes: List[Dict],
        connections: List[Dict],
        triggers: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> Workflow:
        # Generate icon URL using shared utility
        icon_url = metadata.get("icon_url") if metadata else None
        if not icon_url:
            try:
                from shared.utils.icon_utils import generate_random_icon_url

                icon_url = generate_random_icon_url()
            except Exception as e:
                self.logger.warning(f"Failed to generate icon URL: {e}, using None")
                icon_url = None

        meta = WorkflowMetadata(
            id=workflow_id,
            name=name,
            created_time=created_time_ms,
            created_by=created_by,
            icon_url=icon_url,
        )

        # Convert user dictionaries to Node objects, preserving their data exactly
        from shared.models.workflow import Connection, Node

        v2_nodes = []
        for n in nodes:
            # Create Node object from user dict - Pydantic will handle conversion
            node = Node(**n)
            v2_nodes.append(node)

        v2_connections = []
        for c in connections:
            # Create Connection object from user dict
            conn = Connection(
                id=c["id"],
                from_node=c["from_node"],
                to_node=c["to_node"],
                output_key=c.get("output_key", "result"),
                conversion_function=c.get("conversion_function"),
            )
            v2_connections.append(conn)

        wf = Workflow(
            metadata=meta,
            nodes=v2_nodes,
            connections=v2_connections,  # type: ignore
            triggers=triggers or [],
        )

        # Validate workflow with dictionary-based nodes
        validate_workflow(wf)

        # Save directly to database
        self.logger.info(f"🔄 Saving workflow {workflow_id} to database...")
        try:
            self._save_to_database(wf, created_by, created_time_ms)
            self.logger.info(f"✅ Workflow {workflow_id} saved to database")
        except Exception as e:
            self.logger.error(f"❌ Failed to save workflow {workflow_id} to database: {e}")
            # Import full traceback for debugging
            import traceback

            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise e

        return wf

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow from database by ID."""
        if not self.supabase:
            self.logger.error("Supabase client not available")
            return None

        try:
            result = (
                self.supabase.table("workflows")
                .select("workflow_data, user_id")
                .eq("id", workflow_id)
                .eq("active", True)
                .execute()
            )
            if result.data:
                workflow_data = result.data[0].get("workflow_data")
                if workflow_data:
                    # Debug: Log the actual workflow data structure
                    self.logger.info(f"🔍 Raw workflow_data structure: {workflow_data}")

                    # Fix missing fields in workflow_data for Pydantic validation
                    if "metadata" in workflow_data:
                        metadata = workflow_data["metadata"]
                        # Ensure required fields exist with proper types
                        if "created_time" not in metadata:
                            metadata["created_time"] = metadata.get("created_time_ms", 0)
                        if "created_by" not in metadata:
                            metadata["created_by"] = metadata.get("created_by", "unknown")
                        if "version" in metadata and isinstance(metadata["version"], int):
                            metadata["version"] = str(metadata["version"])
                        workflow_data["metadata"] = metadata

                    return Workflow(**workflow_data)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get workflow {workflow_id}: {e}")
            return None

    def get_workflow_with_user_id(self, workflow_id: str) -> Optional[Tuple[Workflow, str]]:
        """Get workflow from database by ID along with user_id."""
        if not self.supabase:
            self.logger.error("Supabase client not available")
            return None

        try:
            result = (
                self.supabase.table("workflows")
                .select("workflow_data, user_id")
                .eq("id", workflow_id)
                .eq("active", True)
                .execute()
            )
            if result.data:
                workflow_data = result.data[0].get("workflow_data")
                user_id = result.data[0].get("user_id")
                if workflow_data and user_id:
                    # Fix missing fields in workflow_data for Pydantic validation
                    if "metadata" in workflow_data:
                        metadata = workflow_data["metadata"]
                        # Ensure required fields exist with proper types
                        if "created_time" not in metadata:
                            metadata["created_time"] = metadata.get("created_time_ms", 0)
                        if "created_by" not in metadata:
                            metadata["created_by"] = metadata.get("created_by", "unknown")
                        if "version" in metadata and isinstance(metadata["version"], int):
                            metadata["version"] = str(metadata["version"])
                        workflow_data["metadata"] = metadata

                    return (Workflow(**workflow_data), user_id)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get workflow {workflow_id} with user_id: {e}")
            return None

    def validate(self, wf: Workflow) -> None:
        validate_workflow(wf)

    def list_workflows(self, access_token: Optional[str] = None) -> List[Workflow]:
        """
        List active workflows from database.

        Args:
            access_token: JWT token for RLS filtering. If provided, uses RLS to filter by user.
                         If None, uses service role (admin mode - returns all workflows).
        """
        try:
            # Create RLS-enabled client if access token is provided
            if access_token:
                from shared.models.supabase import create_user_supabase_client

                supabase_client = create_user_supabase_client(access_token)
                if not supabase_client:
                    self.logger.error("Failed to create RLS-enabled Supabase client")
                    return []
                self.logger.info("🔐 Using RLS-enabled Supabase client for list_workflows")
            else:
                # Use service role client (admin mode)
                if not self.supabase:
                    self.logger.error("Supabase client not available")
                    return []
                supabase_client = self.supabase
                self.logger.info(
                    "👑 Using service role Supabase client for list_workflows (admin mode)"
                )

            result = (
                supabase_client.table("workflows")
                .select("workflow_data")
                .eq("active", True)
                .execute()
            )
            workflows = []
            for row in result.data:
                workflow_data = row.get("workflow_data")
                if workflow_data:
                    try:
                        workflows.append(Workflow(**workflow_data))
                    except Exception as e:
                        self.logger.warning(f"Failed to parse workflow data: {e}")

            self.logger.info(f"✅ Listed {len(workflows)} workflows")
            return workflows
        except Exception as e:
            self.logger.error(f"Failed to list workflows: {e}")
            return []

    def update_workflow(self, workflow: Workflow) -> Workflow:
        """Update existing workflow in database."""
        validate_workflow(workflow)

        if not self.supabase:
            raise Exception("Supabase client not available")

        try:
            update_data = {
                "name": workflow.metadata.name,
                "description": workflow.metadata.description,
                "version": workflow.metadata.version,
                "workflow_data": workflow.model_dump(),
                "tags": workflow.metadata.tags or [],
                "updated_at": int(time.time() * 1000),
            }

            result = (
                self.supabase.table("workflows")
                .update(update_data)
                .eq("id", workflow.metadata.id)
                .execute()
            )
            self.logger.info(f"✅ Workflow {workflow.metadata.id} updated in database")
            return workflow
        except Exception as e:
            self.logger.error(f"Failed to update workflow {workflow.metadata.id}: {e}")
            raise e

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete workflow from database (soft delete by setting active=false)."""
        if not self.supabase:
            self.logger.error("Supabase client not available")
            return False

        try:
            result = (
                self.supabase.table("workflows")
                .update({"active": False})
                .eq("id", workflow_id)
                .execute()
            )
            if result.data:
                self.logger.info(f"✅ Workflow {workflow_id} deleted (deactivated)")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete workflow {workflow_id}: {e}")
            return False

    # Import/Export helpers
    def export_workflow(self, workflow_id: str) -> Dict:
        wf = self.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")
        return wf.model_dump()

    def import_workflow(self, data: Dict) -> Workflow:
        """Import workflow from data and save to database."""
        wf = Workflow(**data)
        validate_workflow(wf)

        # Save to database
        try:
            self._save_to_database(wf, wf.metadata.created_by, wf.metadata.created_time)
            return wf
        except Exception as e:
            self.logger.error(f"Failed to import workflow: {e}")
            raise e

    def save_to_file(self, workflow_id: str, path: str) -> None:
        wf = self.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(wf.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    def load_from_file(self, path: str) -> Workflow:
        p = Path(path)
        raw = json.loads(p.read_text(encoding="utf-8"))
        return self.import_workflow(raw)

    def _save_to_database(self, workflow: Workflow, created_by: str, created_time_ms: int) -> None:
        """Save workflow to Supabase database for other services to access."""
        if not self.supabase:
            raise Exception("Supabase client not available")

        # Base workflow data with only guaranteed columns
        workflow_data = {
            "id": workflow.metadata.id,
            "user_id": created_by,
            "name": workflow.metadata.name,
            "description": workflow.metadata.description,
            "version": workflow.metadata.version,
            "active": True,
            "workflow_data": workflow.model_dump(),  # Store entire new workflow as JSON
            "tags": workflow.metadata.tags or [],
            "created_at": created_time_ms,
            "updated_at": int(time.time() * 1000),
        }

        # Add optional columns if they exist in schema (handle missing columns gracefully)
        # Import enums to use instead of hardcoded strings
        from shared.models.execution_new import ExecutionStatus
        from shared.models.workflow import WorkflowDeploymentStatus

        optional_columns = {
            "deployment_status": WorkflowDeploymentStatus.UNDEPLOYED.value,  # Default state (never deployed)
            "latest_execution_status": ExecutionStatus.IDLE.value,  # Always start as IDLE (never executed)
            "latest_execution_time": None,  # No execution yet
            "latest_execution_id": None,
            "icon_url": workflow.metadata.icon_url,
        }

        # We'll add these one by one and remove any that cause schema errors
        for col_name, col_value in optional_columns.items():
            workflow_data[col_name] = col_value

        def attempt_insert(data: Dict[str, Any]):
            return self.supabase.table("workflows").insert(data).execute()

        try:
            # Insert workflow into database
            result = attempt_insert(workflow_data)
            self.logger.info(
                f"💾 Successfully inserted workflow {workflow.metadata.id} into database"
            )
            return result
        except Exception as e:
            error_message = str(e)
            if "valid_deployment_status" in error_message:
                self.logger.warning("Deployment status 'pending' not accepted; retrying with legacy value 'DRAFT'")
                workflow_data["deployment_status"] = WorkflowDeploymentStatus.DRAFT.value
                try:
                    result = attempt_insert(workflow_data)
                    self.logger.info(
                        f"💾 Successfully inserted workflow {workflow.metadata.id} into database with fallback status"
                    )
                    return result
                except Exception as deployment_error:
                    deployment_error_message = str(deployment_error)
                    if "valid_deployment_status" in deployment_error_message:
                        self.logger.warning("Deployment status still rejected; removing column entirely for compatibility")
                        workflow_data.pop("deployment_status", None)
                        result = attempt_insert(workflow_data)
                        self.logger.info(
                            f"💾 Successfully inserted workflow {workflow.metadata.id} into database without deployment status"
                        )
                        return result
                    error_message = deployment_error_message
                    e = deployment_error
            # Check if it's a schema error (missing columns)
            if "Could not find" in error_message and "column" in error_message:
                self.logger.warning(f"⚠️ Schema error, retrying with basic columns only: {e}")
                # Retry with only the basic columns that should exist
                basic_workflow_data = {
                    "id": workflow.metadata.id,
                    "user_id": created_by,
                    "name": workflow.metadata.name,
                    "description": workflow.metadata.description,
                    "version": workflow.metadata.version,
                    "active": True,
                    "workflow_data": workflow.model_dump(),  # Store entire new workflow as JSON
                    "tags": workflow.metadata.tags or [],
                    "created_at": created_time_ms,
                    "updated_at": int(time.time() * 1000),
                }
                try:
                    result = attempt_insert(basic_workflow_data)
                    self.logger.info(
                        f"💾 Successfully inserted workflow {workflow.metadata.id} with basic schema"
                    )
                    return result
                except Exception as e2:
                    self.logger.error(f"❌ Failed even with basic schema: {e2}")
                    raise e2
            # Check if it's a duplicate key error (workflow already exists)
            elif "duplicate key" in error_message.lower() or "already exists" in error_message.lower():
                self.logger.info(
                    f"📝 Workflow {workflow.metadata.id} already exists, updating instead"
                )
                # Update existing workflow with basic data
                basic_update_data = {
                    "name": workflow.metadata.name,
                    "description": workflow.metadata.description,
                    "version": workflow.metadata.version,
                    "active": True,
                    "workflow_data": workflow.model_dump(),
                    "tags": workflow.metadata.tags or [],
                    "updated_at": int(time.time() * 1000),
                }
                result = (
                    self.supabase.table("workflows")
                    .update(basic_update_data)
                    .eq("id", workflow.metadata.id)
                    .execute()
                )
                self.logger.info(
                    f"✏️ Successfully updated workflow {workflow.metadata.id} in database"
                )
                return result
            else:
                raise e


__all__ = ["WorkflowServiceV2"]
