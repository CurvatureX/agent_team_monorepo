"""
Supabase-based Workflow Service - 工作流CRUD操作服务.

This module implements workflow-related operations using Supabase SDK instead of SQLAlchemy.
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# Add backend directory to Python path for shared models
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import (
    CreateWorkflowRequest,
    ListWorkflowsRequest,
    NodeTemplate,
    UpdateWorkflowRequest,
    WorkflowData,
    WorkflowMetadata,
)

from ..core.config import get_settings
from ..utils.node_id_generator import NodeIdGenerator
from ..utils.workflow_validator import WorkflowValidator
from .supabase_repository import SupabaseWorkflowRepository

logger = logging.getLogger(__name__)
settings = get_settings()


class SupabaseWorkflowService:
    """Service for workflow CRUD operations using Supabase SDK."""

    def __init__(self, access_token: Optional[str] = None):
        self.logger = logger
        self.repository = SupabaseWorkflowRepository(access_token)
        self.validator = WorkflowValidator()

    async def create_workflow_from_data(self, request: CreateWorkflowRequest) -> WorkflowData:
        """Create a new workflow from Pydantic model using Supabase."""
        try:
            self.logger.info(f"Creating workflow: {request.name}")

            workflow_id = str(uuid.uuid4())
            now = datetime.now()
            # Convert to Unix timestamp in milliseconds for BIGINT columns
            now_timestamp = int(now.timestamp() * 1000)

            self.logger.debug(f"Processing {len(request.nodes)} nodes for workflow creation")

            # Convert nodes to dict for processing
            nodes_data = [node.dict() for node in request.nodes]

            # Ensure all nodes have unique IDs
            nodes_data = NodeIdGenerator.ensure_unique_node_ids(nodes_data)

            # Process connections and resolve node references
            connections_data = self._process_workflow_connections(request, nodes_data)

            # Convert nodes back to NodeData objects for validation
            from shared.models import NodeData

            temp_nodes = [NodeData(**node_data) for node_data in nodes_data]

            # Validate workflow before saving
            validation_result = self.validator.validate_workflow_structure(
                {
                    "name": request.name,
                    "nodes": [node.dict() for node in temp_nodes],
                    "connections": connections_data,
                    "settings": request.settings.dict() if request.settings else {},
                },
                validate_node_parameters=True,
            )

            if not validation_result.get("valid", True):
                validation_errors = validation_result.get("errors", [])
                error_message = f"Workflow validation failed: {'; '.join(validation_errors)}"
                self.logger.error(error_message)
                raise ValueError(error_message)

            validation_warnings = validation_result.get("warnings", [])
            if validation_warnings:
                self.logger.warning(
                    f"Workflow validation warnings: {'; '.join(validation_warnings)}"
                )

            # Prepare workflow data for Supabase
            workflow_data = {
                "id": workflow_id,
                "user_id": request.user_id,
                "session_id": getattr(request, "session_id", None),
                "name": request.name,
                "description": request.description or "",
                "version": getattr(request, "version", 1),
                "active": True,
                "tags": request.tags or [],
                "deployment_status": "DRAFT",
                "deployed_at": None,
                "latest_execution_status": None,
                "latest_execution_time": None,
                "latest_execution_id": None,
                "icon_url": getattr(request, "icon_url", None),
                "created_at": now_timestamp,
                "updated_at": now_timestamp,
                "workflow_data": {
                    "nodes": [node.dict() for node in temp_nodes],
                    "connections": connections_data,
                    "settings": request.settings.dict() if request.settings else {},
                },
            }

            # Create workflow in Supabase
            created_workflow = await self.repository.create_workflow(workflow_data)

            if not created_workflow:
                raise ValueError("Failed to create workflow in database")

            # Convert back to WorkflowData
            workflow_data = self._dict_to_workflow_data(created_workflow)
            if workflow_data is None:
                raise ValueError("Created workflow has invalid data structure (no nodes)")
            return workflow_data

        except Exception as e:
            self.logger.error(f"Error creating workflow: {e}")
            raise

    async def get_workflow_by_id(self, workflow_id: str) -> Optional[WorkflowData]:
        """Get a workflow by ID using Supabase."""
        try:
            workflow_dict = await self.repository.get_workflow(workflow_id)

            if not workflow_dict:
                return None

            workflow_data = self._dict_to_workflow_data(workflow_dict)
            if workflow_data is None:
                self.logger.error(f"Workflow {workflow_id} has invalid data structure (no nodes)")
                return None

            return workflow_data

        except Exception as e:
            self.logger.error(f"Error getting workflow {workflow_id}: {e}")
            return None

    async def update_workflow_from_data(
        self, workflow_id: str, user_id: str, update_data: UpdateWorkflowRequest
    ) -> Optional[WorkflowData]:
        """Update a workflow using Supabase."""
        try:
            self.logger.info(f"Updating workflow {workflow_id}")

            # Prepare update data
            # Convert to Unix timestamp in milliseconds for BIGINT column
            update_dict = {"updated_at": int(datetime.now().timestamp() * 1000)}

            # Update basic fields if provided
            if update_data.name is not None:
                update_dict["name"] = update_data.name
            if update_data.description is not None:
                update_dict["description"] = update_data.description
            if update_data.tags is not None:
                update_dict["tags"] = update_data.tags
            if update_data.settings is not None:
                # Update settings in workflow_data
                current_workflow = await self.repository.get_workflow(workflow_id)
                if current_workflow and current_workflow.get("workflow_data"):
                    workflow_data = current_workflow["workflow_data"]
                    workflow_data["settings"] = update_data.settings.dict() if update_data.settings else {}
                    update_dict["workflow_data"] = workflow_data

            # Handle nodes and connections update
            if update_data.nodes is not None:
                nodes_data = [node.dict() for node in update_data.nodes]
                nodes_data = NodeIdGenerator.ensure_unique_node_ids(nodes_data)

                connections_data = {}
                if update_data.connections is not None:
                    connections_data = update_data.connections
                else:
                    # Try to preserve existing connections if only nodes are updated
                    current_workflow = await self.repository.get_workflow(workflow_id)
                    if current_workflow and current_workflow.get("workflow_data"):
                        connections_data = current_workflow["workflow_data"].get("connections", {})

                # Validate updated workflow
                from shared.models import NodeData

                temp_nodes = [NodeData(**node_data) for node_data in nodes_data]

                validation_result = self.validator.validate_workflow_structure(
                    {
                        "name": update_data.name or "Updated Workflow",
                        "nodes": [node.dict() for node in temp_nodes],
                        "connections": connections_data,
                        "settings": update_data.settings.dict() if update_data.settings else {},
                    },
                    validate_node_parameters=True,
                )

                if not validation_result.get("valid", True):
                    validation_errors = validation_result.get("errors", [])
                    error_message = f"Workflow validation failed: {'; '.join(validation_errors)}"
                    self.logger.error(error_message)
                    raise ValueError(error_message)

                # Update workflow_data
                current_workflow = await self.repository.get_workflow(workflow_id)
                if current_workflow and current_workflow.get("workflow_data"):
                    workflow_data = current_workflow["workflow_data"]
                else:
                    workflow_data = {}

                workflow_data.update(
                    {
                        "nodes": [node.dict() for node in temp_nodes],
                        "connections": connections_data,
                        "settings": update_data.settings.dict() if update_data.settings else workflow_data.get("settings", {}),
                    }
                )

                update_dict["workflow_data"] = workflow_data

            # Update workflow in Supabase
            updated_workflow = await self.repository.update_workflow(workflow_id, update_dict)

            if not updated_workflow:
                return None

            workflow_data = self._dict_to_workflow_data(updated_workflow)
            if workflow_data is None:
                self.logger.error(
                    f"Updated workflow {workflow_id} has invalid data structure (no nodes)"
                )
                return None
            return workflow_data

        except Exception as e:
            self.logger.error(f"Error updating workflow {workflow_id}: {e}")
            raise

    async def delete_workflow(self, workflow_id: str, user_id: str) -> bool:
        """Delete a workflow using Supabase."""
        try:
            return await self.repository.delete_workflow(workflow_id)
        except Exception as e:
            self.logger.error(f"Error deleting workflow {workflow_id}: {e}")
            raise

    async def list_workflows(
        self,
        active_only: bool = False,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[WorkflowMetadata], int]:
        """List workflows using Supabase."""
        try:
            workflows, total_count = await self.repository.list_workflows(
                active_only=active_only, tags=tags, limit=limit, offset=offset
            )

            # Convert to WorkflowMetadata objects
            workflow_metadata = [WorkflowMetadata(**workflow) for workflow in workflows]

            return workflow_metadata, total_count

        except Exception as e:
            self.logger.error(f"Error listing workflows: {e}")
            raise

    def _process_workflow_connections(
        self, request: CreateWorkflowRequest, nodes_data: List[dict]
    ) -> dict:
        """Process and resolve workflow connections."""
        # This is a simplified version - the original method has more complex logic
        # You may need to import the full implementation from the original service
        connections_data = {}

        if hasattr(request, "connections") and request.connections:
            connections_data = request.connections

        return connections_data

    def _dict_to_workflow_data(self, workflow_dict: dict) -> Optional[WorkflowData]:
        """Convert dictionary from Supabase to WorkflowData object."""
        try:
            # Extract workflow_data JSON field
            workflow_data = workflow_dict.get("workflow_data", {})
            nodes_data = workflow_data.get("nodes", [])
            connections_data = workflow_data.get("connections", {})
            settings_data = workflow_data.get("settings", {})

            # Convert nodes to NodeData objects
            from shared.models import NodeData

            nodes = [NodeData(**node_data) for node_data in nodes_data]

            # Validate that workflow has nodes - return None for invalid workflows
            if not nodes:
                self.logger.error(
                    f"Workflow {workflow_dict['id']} has no nodes - invalid workflow data"
                )
                return None

            # Handle null tags from database
            tags = workflow_dict.get("tags")
            if tags is None:
                tags = []

            # Create WorkflowData object
            return WorkflowData(
                id=workflow_dict["id"],
                user_id=workflow_dict["user_id"],
                session_id=workflow_dict.get("session_id"),
                name=workflow_dict["name"],
                description=workflow_dict.get("description", ""),
                version=workflow_dict.get("version", 1),
                active=workflow_dict.get("active", True),
                tags=tags,
                nodes=nodes,
                connections=connections_data,
                settings=settings_data,
                created_at=workflow_dict.get("created_at"),
                updated_at=workflow_dict.get("updated_at"),
                icon_url=workflow_dict.get("icon_url"),  # Add missing icon_url field
            )

        except Exception as e:
            self.logger.error(f"Error converting workflow dict to WorkflowData: {e}")
            raise
