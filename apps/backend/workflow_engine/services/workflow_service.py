"""
Workflow Service - Workflow CRUD operations service.

This module implements workflow-related operations using Supabase SDK.
Migrated from old workflow engine structure to new flat architecture.
"""

import json
import logging

# Import from shared models instead of local models
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Use relative imports for the new flat structure
from config import get_settings

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))
from shared.models.workflow import NodeData, WorkflowData, WorkflowMetadata

from .supabase_repository import SupabaseWorkflowRepository

logger = logging.getLogger(__name__)
settings = get_settings()


# Import full-featured utilities
from utils.node_id_generator import NodeIdGenerator
from utils.workflow_validator import WorkflowValidator


# Minimal models for compatibility with old interface
class CreateWorkflowRequest:
    """Minimal CreateWorkflowRequest for compatibility"""

    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "")
        self.description = kwargs.get("description", "")
        self.user_id = kwargs.get("user_id", "")
        self.session_id = kwargs.get("session_id")
        self.nodes = kwargs.get("nodes", [])
        self.connections = kwargs.get("connections", {})
        self.settings = kwargs.get("settings", {})
        self.tags = kwargs.get("tags", [])
        self.version = kwargs.get("version", 1)
        self.icon_url = kwargs.get("icon_url")
        self.static_data = kwargs.get("static_data", {})


class UpdateWorkflowRequest:
    """Minimal UpdateWorkflowRequest for compatibility"""

    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.description = kwargs.get("description")
        self.nodes = kwargs.get("nodes")
        self.connections = kwargs.get("connections")
        self.settings = kwargs.get("settings")
        self.tags = kwargs.get("tags")


class WorkflowService:
    """Service for workflow CRUD operations using Supabase SDK."""

    def __init__(self, access_token: Optional[str] = None):
        self.logger = logger
        self.repository = SupabaseWorkflowRepository(access_token)
        self.validator = WorkflowValidator()

    async def create_workflow_from_data(self, request: CreateWorkflowRequest) -> WorkflowData:
        """Create a new workflow from request data using Supabase."""
        try:
            self.logger.info(f"Creating workflow: {request.name}")

            workflow_id = str(uuid.uuid4())
            now = datetime.now()

            self.logger.debug(f"Processing {len(request.nodes)} nodes for workflow creation")

            # Convert nodes to dict for processing
            if hasattr(request.nodes[0], "dict"):
                nodes_data = [node.dict() for node in request.nodes]
            else:
                nodes_data = request.nodes

            # Ensure all nodes have unique IDs
            nodes_data = NodeIdGenerator.ensure_unique_node_ids(nodes_data)

            # Process connections and resolve node references
            connections_data = self._process_workflow_connections(request, nodes_data)

            # Convert nodes to NodeData objects for validation
            temp_nodes = []
            for node_data in nodes_data:
                if isinstance(node_data, dict):
                    temp_nodes.append(NodeData(**node_data))
                else:
                    temp_nodes.append(node_data)

            # Validate workflow before saving
            validation_result = self.validator.validate_workflow_structure(
                {
                    "name": request.name,
                    "nodes": [
                        node.dict() if hasattr(node, "dict") else node for node in temp_nodes
                    ],
                    "connections": connections_data,
                    "settings": request.settings,
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
            workflow_data_dict = {
                "id": workflow_id,
                "user_id": request.user_id,
                "session_id": getattr(request, "session_id", None),
                "name": request.name,
                "description": request.description or "",
                "version": getattr(request, "version", 1),
                "active": True,
                "tags": request.tags or [],
                "deployment_status": "draft",
                "deployed_at": None,
                "latest_execution_status": None,
                "latest_execution_time": None,
                "latest_execution_id": None,
                "icon_url": getattr(request, "icon_url", None),
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "workflow_data": {
                    "nodes": [
                        node.dict() if hasattr(node, "dict") else node for node in temp_nodes
                    ],
                    "connections": connections_data,
                    "settings": request.settings or {},
                    "static_data": getattr(request, "static_data", {}),
                },
            }

            # Create workflow in Supabase
            created_workflow = await self.repository.create_workflow(workflow_data_dict)

            if not created_workflow:
                raise ValueError("Failed to create workflow in database")

            # Convert back to WorkflowData
            workflow_data = self._dict_to_workflow_data(created_workflow)
            if workflow_data is None:
                raise ValueError("Created workflow has invalid data structure (no nodes)")

            self.logger.info(f"Workflow created successfully: {workflow_id}")
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
            update_dict = {"updated_at": datetime.now().isoformat()}

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
                    workflow_data["settings"] = update_data.settings
                    update_dict["workflow_data"] = workflow_data

            # Handle nodes and connections update
            if update_data.nodes is not None:
                if hasattr(update_data.nodes[0], "dict"):
                    nodes_data = [node.dict() for node in update_data.nodes]
                else:
                    nodes_data = update_data.nodes
                nodes_data = NodeIdGenerator.ensure_unique_node_ids(nodes_data)

                connections_data = {}
                if update_data.connections is not None:
                    connections_data = update_data.connections
                else:
                    # Try to preserve existing connections if only nodes are updated
                    current_workflow = await self.repository.get_workflow(workflow_id)
                    if current_workflow and current_workflow.get("workflow_data"):
                        connections_data = current_workflow["workflow_data"].get("connections", {})

                # Convert nodes to NodeData objects for validation
                temp_nodes = []
                for node_data in nodes_data:
                    if isinstance(node_data, dict):
                        temp_nodes.append(NodeData(**node_data))
                    else:
                        temp_nodes.append(node_data)

                # Validate updated workflow
                validation_result = self.validator.validate_workflow_structure(
                    {
                        "name": update_data.name or "Updated Workflow",
                        "nodes": [
                            node.dict() if hasattr(node, "dict") else node for node in temp_nodes
                        ],
                        "connections": connections_data,
                        "settings": update_data.settings or {},
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
                        "nodes": [
                            node.dict() if hasattr(node, "dict") else node for node in temp_nodes
                        ],
                        "connections": connections_data,
                        "settings": update_data.settings or workflow_data.get("settings", {}),
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

    def _dict_to_workflow_data(self, workflow_dict: dict) -> Optional[WorkflowData]:
        """Convert dictionary from Supabase to WorkflowData object."""
        try:
            # Extract workflow_data JSON field
            workflow_data = workflow_dict.get("workflow_data", {})
            nodes_data = workflow_data.get("nodes", [])
            connections_data = workflow_data.get("connections", {})
            settings_data = workflow_data.get("settings", {})

            # Convert nodes to NodeData objects
            nodes = []
            for node_data in nodes_data:
                if isinstance(node_data, dict):
                    nodes.append(NodeData(**node_data))
                else:
                    nodes.append(node_data)

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
                static_data=workflow_data.get("static_data", {}),
                created_at=workflow_dict.get("created_at"),
                updated_at=workflow_dict.get("updated_at"),
                icon_url=workflow_dict.get("icon_url"),
                # Add metadata fields
                deployment_status=workflow_dict.get("deployment_status"),
                deployed_at=workflow_dict.get("deployed_at"),
                latest_execution_status=workflow_dict.get("latest_execution_status"),
                latest_execution_time=workflow_dict.get("latest_execution_time"),
                latest_execution_id=workflow_dict.get("latest_execution_id"),
            )

        except Exception as e:
            self.logger.error(f"Error converting workflow dict to WorkflowData: {e}")
            raise

    def _process_workflow_connections(
        self, request: CreateWorkflowRequest, nodes_data: List[dict]
    ) -> dict:
        """Process and resolve workflow connections, supporting both name and ID references."""
        connections_data = request.connections if request.connections else {}
        self.logger.debug(f"Processing {len(connections_data)} connections")

        # Create name to ID mapping for all nodes
        name_to_id_mapping = NodeIdGenerator.create_name_to_id_mapping(nodes_data)
        node_ids = {node["id"] for node in nodes_data}

        # Resolve any name-based references to IDs BEFORE validation
        resolved_connections = NodeIdGenerator.resolve_connection_references(
            connections_data, name_to_id_mapping, node_ids
        )

        self.logger.debug("Successfully resolved connection references to node IDs")
        return resolved_connections

    def list_all_node_templates(
        self, category_filter: Optional[str] = None, include_system_templates: bool = True
    ) -> List[Dict[str, Any]]:
        """List all available node templates."""
        try:
            self.logger.info("Listing node templates (simplified for new structure)")

            # Return a simple list of templates - in the new structure this would be handled
            # by a dedicated node specs service or similar
            return []

        except Exception as e:
            self.logger.error(f"Error listing node templates: {str(e)}")
            raise
