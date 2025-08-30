"""
Workflow Service - 工作流CRUD操作服务.

This module implements workflow-related operations: Create, Read, Update, Delete, List.
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

# Add backend directory to Python path for shared models
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import (
    CreateWorkflowRequest,
    ListWorkflowsRequest,
    NodeTemplate,
    UpdateWorkflowRequest,
    WorkflowData,
)

from ..core.config import get_settings
from ..models import NodeTemplateModel, WorkflowModel
from ..utils.node_id_generator import NodeIdGenerator
from ..utils.workflow_validator import WorkflowValidator

logger = logging.getLogger(__name__)
settings = get_settings()


class WorkflowService:
    """Service for workflow CRUD operations."""

    def __init__(self, db_session: Session):
        self.logger = logger
        self.db = db_session
        self.validator = WorkflowValidator()

    def create_workflow_from_data(self, request: CreateWorkflowRequest) -> WorkflowData:
        """Create a new workflow from Pydantic model."""
        try:
            self.logger.info(f"Creating workflow: {request.name}")

            # DEBUG: Log the original request nodes
            print(f"🐛 DEBUG: create_workflow_from_data called with {len(request.nodes)} nodes")
            for i, node in enumerate(request.nodes):
                print(
                    f"🐛 DEBUG: Original request node {i}: id='{node.id}', type='{node.type}', subtype='{node.subtype}'"
                )

            workflow_id = str(uuid.uuid4())
            now = int(datetime.now().timestamp())

            # Convert nodes to dict for processing
            nodes_data = [node.dict() for node in request.nodes]

            # DEBUG: Log nodes after dict conversion
            print(f"🐛 DEBUG: After dict conversion:")
            for i, node in enumerate(nodes_data):
                print(
                    f"🐛 DEBUG: Dict node {i}: id='{node.get('id')}', type='{node.get('type')}', subtype='{node.get('subtype')}')"
                )

            # Ensure all nodes have unique IDs
            nodes_data = NodeIdGenerator.ensure_unique_node_ids(nodes_data)

            # Handle connections early - support both name and ID references
            connections_data = request.connections if request.connections else {}
            self.logger.info(
                f"Original connections data from request: {json.dumps(connections_data, ensure_ascii=False)}"
            )

            # Create name to ID mapping for all nodes
            name_to_id_mapping = NodeIdGenerator.create_name_to_id_mapping(nodes_data)
            node_ids = {node["id"] for node in nodes_data}

            # Resolve any name-based references to IDs BEFORE validation
            connections_data = NodeIdGenerator.resolve_connection_references(
                connections_data, name_to_id_mapping, node_ids
            )
            self.logger.info(
                f"Resolved connections to use IDs: {json.dumps(connections_data, ensure_ascii=False)}"
            )

            # Convert nodes back to NodeData objects for validation
            from shared.models import NodeData

            print(f"🐛 DEBUG: About to recreate NodeData objects from nodes_data")
            temp_nodes = []
            for i, node_data in enumerate(nodes_data):
                print(
                    f"🐛 DEBUG: Creating NodeData from node_data {i}: subtype='{node_data.get('subtype')}'"
                )
                temp_node = NodeData(**node_data)
                print(f"🐛 DEBUG: Created NodeData object {i}: subtype='{temp_node.subtype}'")
                temp_nodes.append(temp_node)

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

            workflow_data = WorkflowData(
                id=workflow_id,
                name=request.name,
                description=request.description,
                nodes=nodes,
                connections=connections_data,
                settings=request.settings,
                static_data=request.static_data,
                tags=request.tags,
                active=True,
                created_at=now,
                updated_at=now,
                version="1.0.0",
            )

            self.logger.info(
                f"WorkflowData connections after creation: {workflow_data.connections}"
            )
            self.logger.info(f"WorkflowData connections type: {type(workflow_data.connections)}")
            workflow_dict = workflow_data.dict()
            self.logger.info(f"WorkflowData dict connections: {workflow_dict.get('connections')}")
            self.logger.info(f"Full workflow_dict: {json.dumps(workflow_dict, ensure_ascii=False)}")

            db_workflow = WorkflowModel(
                id=workflow_id,
                user_id=request.user_id,
                name=request.name,
                description=request.description,
                active=True,
                workflow_data=workflow_data.dict(),
                created_at=now,
                updated_at=now,
                version="1.0.0",
                tags=request.tags,
                session_id=request.session_id,
            )
            self.db.add(db_workflow)
            self.db.commit()

            self.logger.info(f"Workflow created successfully: {workflow_id}")
            return workflow_data
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error creating workflow: {str(e)}")
            raise

    def get_workflow(self, workflow_id: str, user_id: str) -> Optional[WorkflowData]:
        """Get a workflow by ID."""
        try:
            self.logger.info(f"Getting workflow: {workflow_id}")

            db_workflow = (
                self.db.query(WorkflowModel)
                .filter(WorkflowModel.id == workflow_id, WorkflowModel.user_id == user_id)
                .first()
            )

            if not db_workflow:
                return None

            return WorkflowData(**db_workflow.workflow_data)
        except Exception as e:
            self.logger.error(f"Error getting workflow: {str(e)}")
            raise

    def update_workflow_from_data(
        self, workflow_id: str, user_id: str, update_data: UpdateWorkflowRequest
    ) -> WorkflowData:
        """Update an existing workflow from Pydantic model."""
        try:
            self.logger.info(f"Updating workflow: {workflow_id}")

            db_workflow = (
                self.db.query(WorkflowModel)
                .filter(WorkflowModel.id == workflow_id, WorkflowModel.user_id == user_id)
                .first()
            )

            if not db_workflow:
                raise Exception("Workflow not found")

            workflow_data = WorkflowData(**db_workflow.workflow_data)

            update_dict = update_data.dict(exclude_unset=True)

            # If nodes are being updated, ensure unique IDs
            if "nodes" in update_dict and update_dict["nodes"]:
                nodes_data = [
                    node.dict() if hasattr(node, "dict") else node for node in update_dict["nodes"]
                ]

                # Ensure all nodes have unique IDs
                nodes_data = NodeIdGenerator.ensure_unique_node_ids(nodes_data)

                # Check if any IDs were changed
                original_nodes = update_dict["nodes"]
                id_mapping = {}

                for i, original_node in enumerate(original_nodes):
                    orig_id = (
                        original_node.id
                        if hasattr(original_node, "id")
                        else original_node.get("id")
                    )
                    if orig_id and nodes_data[i]["id"] != orig_id:
                        id_mapping[orig_id] = nodes_data[i]["id"]
                        self.logger.info(
                            f"Node ID changed during update: {orig_id} -> {nodes_data[i]['id']}"
                        )

                # Update connections if IDs changed
                if id_mapping and "connections" in update_dict:
                    connections_data = update_dict["connections"]
                    if hasattr(connections_data, "dict"):
                        connections_data = connections_data.dict()
                    update_dict["connections"] = NodeIdGenerator.update_connection_references(
                        connections_data, id_mapping
                    )

                # Convert nodes back to proper format
                from shared.models import NodeData

                update_dict["nodes"] = [NodeData(**node_data) for node_data in nodes_data]

            for key, value in update_dict.items():
                if hasattr(workflow_data, key):
                    setattr(workflow_data, key, value)

            workflow_data.updated_at = int(datetime.now().timestamp())

            db_workflow.name = workflow_data.name
            db_workflow.description = workflow_data.description
            db_workflow.active = workflow_data.active
            db_workflow.workflow_data = workflow_data.dict()
            db_workflow.updated_at = workflow_data.updated_at
            db_workflow.tags = workflow_data.tags
            if update_data.session_id:
                db_workflow.session_id = update_data.session_id

            self.db.commit()

            self.logger.info(f"Workflow updated successfully: {workflow_id}")
            return workflow_data
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error updating workflow: {str(e)}")
            raise

    def delete_workflow(self, workflow_id: str, user_id: str) -> bool:
        """Delete a workflow."""
        try:
            self.logger.info(f"Deleting workflow: {workflow_id}")

            result = (
                self.db.query(WorkflowModel)
                .filter(WorkflowModel.id == workflow_id, WorkflowModel.user_id == user_id)
                .delete()
            )

            if result == 0:
                raise Exception("Workflow not found")

            self.db.commit()
            self.logger.info(f"Workflow deleted successfully: {workflow_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error deleting workflow: {str(e)}")
            raise

    def list_workflows(self, request: ListWorkflowsRequest) -> Tuple[List[WorkflowData], int]:
        """List workflows for a user."""
        try:
            self.logger.info(f"Listing workflows for user: {request.user_id}")

            query = self.db.query(WorkflowModel).filter(WorkflowModel.user_id == request.user_id)

            if request.active_only:
                query = query.filter(WorkflowModel.active == True)

            if request.tags:
                for tag in request.tags:
                    query = query.filter(WorkflowModel.tags.contains([tag]))

            total_count = query.count()

            query = query.order_by(WorkflowModel.updated_at.desc())

            if request.limit > 0:
                query = query.limit(request.limit)
            if request.offset > 0:
                query = query.offset(request.offset)

            db_workflows = query.all()

            # Filter out workflows with validation errors
            workflows = []
            for db_workflow in db_workflows:
                try:
                    workflow = WorkflowData(**db_workflow.workflow_data)
                    workflows.append(workflow)
                except Exception as e:
                    self.logger.warning(
                        f"Skipping workflow {db_workflow.id} due to validation error: {str(e)}"
                    )
                    # Optionally log more details about the invalid workflow
                    workflow_data = db_workflow.workflow_data if hasattr(db_workflow, 'workflow_data') else {}
                    workflow_name = workflow_data.get('name', 'Unknown') if isinstance(workflow_data, dict) else 'Unknown'
                    self.logger.debug(
                        f"Invalid workflow details - ID: {db_workflow.id}, "
                        f"Name: {workflow_name}, "
                        f"User: {db_workflow.user_id}"
                    )

            # Adjust total count to reflect only valid workflows
            # Note: This gives accurate count for current page but total_count might be higher
            return workflows, total_count
        except Exception as e:
            self.logger.error(f"Error listing workflows: {str(e)}")
            raise

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
