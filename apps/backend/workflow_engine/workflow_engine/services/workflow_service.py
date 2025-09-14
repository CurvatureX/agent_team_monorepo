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

# Import database models for deployment and execution data
from shared.models.db_models import WorkflowDeployment, WorkflowExecution

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

            workflow_id = str(uuid.uuid4())
            now = int(datetime.now().timestamp())

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

            self.logger.debug("Successfully created WorkflowData object with resolved connections")

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
        """Get a workflow by ID with deployment and execution metadata."""
        try:
            self.logger.info(f"Getting workflow: {workflow_id}")

            db_workflow = (
                self.db.query(WorkflowModel)
                .filter(WorkflowModel.id == workflow_id, WorkflowModel.user_id == user_id)
                .first()
            )

            if not db_workflow:
                return None

            # Create workflow with enhanced metadata (same as list_workflows)
            return self._create_workflow_data_with_metadata(db_workflow)
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
        """List workflows for a user with deployment and execution metadata."""
        import time

        start_time = time.time()
        try:
            self.logger.info(f"Listing workflows for user: {request.user_id}")

            # Build and execute query
            query_start = time.time()
            base_query = self._build_workflows_query(request)
            query_build_time = time.time() - query_start
            self.logger.info(f"⏱️ Query build time: {query_build_time:.3f}s")

            # Get total count using a separate count query for efficiency
            # NOTE: RLS automatically filters by user, no manual user_id filter needed
            count_start = time.time()
            count_query = self.db.query(WorkflowModel.id)
            if request.active_only:
                count_query = count_query.filter(WorkflowModel.active == True)
            if request.tags:
                for tag in request.tags:
                    count_query = count_query.filter(WorkflowModel.tags.contains([tag]))
            total_count = count_query.count()
            count_time = time.time() - count_start
            self.logger.info(f"⏱️ Count query time: {count_time:.3f}s (count: {total_count})")

            # Get paginated results
            data_start = time.time()
            db_workflows = self._apply_pagination_and_ordering(base_query, request).all()
            data_time = time.time() - data_start
            self.logger.info(f"⏱️ Data query time: {data_time:.3f}s (rows: {len(db_workflows)})")

            # Transform database models to domain models with metadata
            transform_start = time.time()
            workflows = self._transform_db_workflows_to_domain(db_workflows)
            transform_time = time.time() - transform_start
            self.logger.info(f"⏱️ Transform time: {transform_time:.3f}s")

            total_time = time.time() - start_time
            self.logger.info(
                f"⏱️ Total list_workflows time: {total_time:.3f}s - Retrieved {len(workflows)} workflows"
            )
            return workflows, total_count

        except Exception as e:
            self.logger.error(f"Error listing workflows: {str(e)}")
            raise

    def _build_workflows_query(self, request: ListWorkflowsRequest):
        """Build the base query for workflows with filters applied."""
        # CRITICAL: Select only specific columns to avoid loading the massive workflow_data JSONB field
        # NOTE: Relying on RLS (Row Level Security) for user filtering instead of manual user_id filter
        query = self.db.query(
            WorkflowModel.id,
            WorkflowModel.user_id,
            WorkflowModel.session_id,
            WorkflowModel.name,
            WorkflowModel.description,
            WorkflowModel.version,
            WorkflowModel.active,
            WorkflowModel.tags,
            WorkflowModel.deployment_status,
            WorkflowModel.deployed_at,
            WorkflowModel.latest_execution_status,
            WorkflowModel.latest_execution_time,
            WorkflowModel.latest_execution_id,
            WorkflowModel.created_at,
            WorkflowModel.updated_at
            # ❌ DELIBERATELY EXCLUDE: WorkflowModel.workflow_data (massive JSONB field)
        )

        # 🚀 REMOVED: Manual user_id filtering - RLS handles this automatically
        # ❌ OLD: query = query.filter(WorkflowModel.user_id == request.user_id)

        if request.active_only:
            query = query.filter(WorkflowModel.active == True)

        if request.tags:
            for tag in request.tags:
                query = query.filter(WorkflowModel.tags.contains([tag]))

        return query

    def _apply_pagination_and_ordering(self, query, request: ListWorkflowsRequest):
        """Apply ordering, limit, and offset to the query."""
        query = query.order_by(WorkflowModel.updated_at.desc())

        if request.limit > 0:
            query = query.limit(request.limit)
        if request.offset > 0:
            query = query.offset(request.offset)

        return query

    def _transform_db_workflows_to_domain(self, db_workflow_rows) -> List[WorkflowData]:
        """Transform database workflow rows to domain WorkflowData objects."""
        workflows = []

        for row in db_workflow_rows:
            try:
                # Create WorkflowData from selected metadata columns (workflow_data JSONB excluded for performance)
                workflow_dict = {
                    "id": str(row.id),
                    "user_id": str(row.user_id),
                    "session_id": str(row.session_id) if row.session_id else None,
                    "name": row.name,
                    "description": row.description,
                    "version": row.version,
                    "active": row.active,
                    "tags": row.tags or [],
                    "deployment_status": row.deployment_status,
                    "deployed_at": row.deployed_at.isoformat() if row.deployed_at else None,
                    "latest_execution_status": row.latest_execution_status,
                    "latest_execution_time": row.latest_execution_time.isoformat()
                    if row.latest_execution_time
                    else None,
                    "latest_execution_id": str(row.latest_execution_id)
                    if row.latest_execution_id
                    else None,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    # Required but empty for listing (actual data in workflow_data JSONB field we're not loading)
                    "nodes": [],
                    "connections": {},
                }

                workflow = WorkflowData(**workflow_dict)
                workflows.append(workflow)

            except Exception as e:
                # Fallback for problematic workflows
                self.logger.warning(f"Failed to create WorkflowData for {row.id}: {e}")
                try:
                    minimal_dict = {
                        "id": str(row.id),
                        "name": row.name or "Invalid Workflow",
                        "user_id": str(row.user_id),
                        "description": row.description or "",
                        "active": row.active,
                        "nodes": [],
                        "connections": {},
                        "tags": row.tags or [],
                    }
                    workflows.append(WorkflowData(**minimal_dict))
                except Exception:
                    # Skip completely broken workflows
                    self.logger.error(f"Completely failed to process workflow {row.id}, skipping")
                    continue

        return workflows

    def _create_workflow_data_with_metadata(self, db_workflow) -> WorkflowData:
        """Create WorkflowData object with enhanced deployment and execution metadata."""
        workflow_dict = db_workflow.workflow_data.copy()

        # Enhance with deployment metadata
        workflow_dict.update(self._extract_deployment_metadata(db_workflow))

        # Enhance with execution metadata
        workflow_dict.update(self._extract_execution_metadata(db_workflow))

        # Skip validation for performance during listing - just return the dict as WorkflowData
        # This avoids expensive validation of legacy workflow formats
        try:
            return WorkflowData(**workflow_dict)
        except Exception:
            # For invalid workflows, return a minimal WorkflowData object to avoid breaking the API
            # This preserves basic functionality while skipping problematic workflows
            basic_dict = {
                "id": workflow_dict.get("id", db_workflow.id),
                "name": workflow_dict.get("name", "Invalid Workflow"),
                "user_id": db_workflow.user_id,
                "description": workflow_dict.get(
                    "description", "Legacy workflow with validation issues"
                ),
                "active": False,  # Mark as inactive to prevent execution
                "nodes": [],
                "connections": {},
                "created_at": workflow_dict.get("created_at"),
                "updated_at": workflow_dict.get("updated_at"),
            }
            # Add metadata
            basic_dict.update(self._extract_deployment_metadata(db_workflow))
            basic_dict.update(self._extract_execution_metadata(db_workflow))

            return WorkflowData(**basic_dict)

    def _extract_deployment_metadata(self, db_workflow) -> dict:
        """Extract deployment metadata from database workflow model."""
        return {
            "deployment_status": db_workflow.deployment_status,
            "deployed_at": db_workflow.deployed_at.isoformat() if db_workflow.deployed_at else None,
        }

    def _extract_execution_metadata(self, db_workflow) -> dict:
        """Extract execution metadata from database workflow model."""
        return {
            "latest_execution_status": db_workflow.latest_execution_status,
            "latest_execution_time": db_workflow.latest_execution_time.isoformat()
            if db_workflow.latest_execution_time
            else None,
            "latest_execution_id": db_workflow.latest_execution_id,
        }

    def _log_invalid_workflow(self, db_workflow, error: Exception) -> None:
        """Log details about invalid workflows for debugging."""
        self.logger.warning(
            f"Skipping workflow {db_workflow.id} due to validation error: {str(error)}"
        )

        # Extract workflow name for better debugging
        workflow_data = getattr(db_workflow, "workflow_data", {})
        workflow_name = (
            workflow_data.get("name", "Unknown") if isinstance(workflow_data, dict) else "Unknown"
        )

        self.logger.debug(
            f"Invalid workflow details - ID: {db_workflow.id}, "
            f"Name: {workflow_name}, User: {db_workflow.user_id}"
        )

    def _process_workflow_connections(self, request, nodes_data) -> dict:
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
