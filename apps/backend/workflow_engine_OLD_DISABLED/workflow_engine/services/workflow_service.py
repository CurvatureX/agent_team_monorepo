"""
Workflow Service - 工作流CRUD操作服务.

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


class WorkflowService:
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

            # Validate workflow before saving - validator expects dict, not objects
            validation_result = self.validator.validate_workflow_structure(
                {
                    "name": request.name,
                    "nodes": [node.dict() for node in temp_nodes],  # Convert to dict for validator
                    "connections": connections_data,  # Use resolved connections with IDs
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

            # Check if any IDs were changed (for connection updates)
            original_ids = {node.id: node.id for node in request.nodes if node.id}
            new_ids = {node["id"]: node["id"] for node in nodes_data}
            id_changed = False
            id_mapping = {}

            for i, original_node in enumerate(request.nodes):
                if original_node.id and nodes_data[i]["id"] != original_node.id:
                    id_changed = True
                    id_mapping[original_node.id] = nodes_data[i]["id"]
                    self.logger.info(
                        f"Node ID changed: {original_node.id} -> {nodes_data[i]['id']}"
                    )

            # If any IDs were changed during generation, update the connections
            if id_changed and connections_data:
                connections_data = NodeIdGenerator.update_connection_references(
                    connections_data, id_mapping
                )
                self.logger.info("Updated connection references after ID changes")

            # Convert nodes back to NodeData objects
            from shared.models import NodeData

            nodes = [NodeData(**node_data) for node_data in nodes_data]

            # 先打印 connections_data 的内容
            self.logger.info(f"connections_data before WorkflowData creation: {connections_data}")
            self.logger.info(f"connections_data type: {type(connections_data)}")

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
                    "nodes": [node.dict() for node in nodes],
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
                nodes_data = [node.dict() for node in update_data.nodes]
                nodes_data = NodeIdGenerator.ensure_unique_node_ids(nodes_data)

                # Check if any IDs were changed
                id_mapping = {}
                for i, original_node in enumerate(update_data.nodes):
                    orig_id = original_node.id
                    if orig_id and nodes_data[i]["id"] != orig_id:
                        id_mapping[orig_id] = nodes_data[i]["id"]
                        self.logger.info(
                            f"Node ID changed during update: {orig_id} -> {nodes_data[i]['id']}"
                        )

                connections_data = {}
                if update_data.connections is not None:
                    connections_data = update_data.connections
                    # Update connections if IDs changed
                    if id_mapping:
                        connections_data = NodeIdGenerator.update_connection_references(
                            connections_data, id_mapping
                        )
                else:
                    # Try to preserve existing connections if only nodes are updated
                    current_workflow = await self.repository.get_workflow(workflow_id)
                    if current_workflow and current_workflow.get("workflow_data"):
                        connections_data = current_workflow["workflow_data"].get("connections", {})
                        # Update connections if IDs changed
                        if id_mapping:
                            connections_data = NodeIdGenerator.update_connection_references(
                                connections_data, id_mapping
                            )

                # Validate updated workflow
                from shared.models import NodeData

                temp_nodes = [NodeData(**node_data) for node_data in nodes_data]

                validation_result = self.validator.validate_workflow_structure(
                    {
                        "name": update_data.name or "Updated Workflow",
                        "nodes": [node.dict() for node in temp_nodes],
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
                        "nodes": [node.dict() for node in temp_nodes],
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
    ) -> List[NodeTemplate]:
        """List all available node templates using node specs."""
        try:
            self.logger.info("Listing node templates from node specs (database deprecated)")

            # Import here to avoid circular imports
            from shared.services.node_specs_api_service import get_node_specs_api_service

            # Use the new node specs service instead of database
            specs_service = get_node_specs_api_service()
            templates = specs_service.list_all_node_templates(
                category_filter=category_filter, include_system_templates=include_system_templates
            )

            self.logger.info(f"Retrieved {len(templates)} templates from node specs")
            return templates

        except Exception as e:
            self.logger.error(f"Error listing node templates: {str(e)}")
            raise
