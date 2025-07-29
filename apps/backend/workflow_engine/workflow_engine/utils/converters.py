"""
Data conversion utilities between Pydantic models and database models.
Helps migrate from protobuf to Pydantic while maintaining database compatibility.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from workflow_engine.workflow_engine.models.execution import ExecutionData, ExecutionStatus
from workflow_engine.workflow_engine.models.workflow import ConnectionsMapData, NodeData
from workflow_engine.workflow_engine.models.workflow import Workflow as WorkflowDBModel
from workflow_engine.workflow_engine.models.workflow import WorkflowData, WorkflowSettingsData


class WorkflowConverter:
    """Converter for workflow data between database and Pydantic models."""

    @staticmethod
    def db_to_pydantic(db_workflow: WorkflowDBModel) -> WorkflowData:
        """Convert database workflow model to Pydantic model."""
        try:
            # Extract workflow data from JSONB field
            workflow_data = db_workflow.workflow_data or {}

            # Convert nodes
            nodes = []
            for node_data in workflow_data.get("nodes", []):
                node = NodeData(
                    id=node_data.get("id", ""),
                    name=node_data.get("name", ""),
                    type=node_data.get("type", ""),
                    subtype=node_data.get("subtype"),
                    position={
                        "x": node_data.get("position", {}).get("x", 0),
                        "y": node_data.get("position", {}).get("y", 0),
                    },
                    parameters=node_data.get("parameters", {}),
                    disabled=node_data.get("disabled", False),
                    on_error=node_data.get("on_error", "continue"),
                )
                nodes.append(node)

            # Convert connections
            connections_data = workflow_data.get("connections", {})
            connections = ConnectionsMapData(connections=connections_data)

            # Convert settings
            settings_data = workflow_data.get("settings", {})
            settings = WorkflowSettingsData(
                timeout=settings_data.get("timeout", 300),
                max_retries=settings_data.get("max_retries", 3),
                retry_delay=settings_data.get("retry_delay", 5),
                parallel_execution=settings_data.get("parallel_execution", False),
                error_handling=settings_data.get("error_handling", "stop"),
                execution_mode=settings_data.get("execution_mode", "sequential"),
                variables=settings_data.get("variables", {}),
            )

            # Create Pydantic model
            return WorkflowData(
                id=str(db_workflow.id),
                name=str(db_workflow.name),
                description=str(db_workflow.description) if db_workflow.description else None,
                nodes=nodes,
                connections=connections,
                settings=settings,
                static_data=workflow_data.get("static_data", {}),
                tags=list(db_workflow.tags) if db_workflow.tags else [],
                active=bool(db_workflow.active),
                version=str(db_workflow.version) if hasattr(db_workflow, "version") else "1.0.0",
                created_at=int(db_workflow.created_at),
                updated_at=int(db_workflow.updated_at),
                session_id=str(db_workflow.session_id) if db_workflow.session_id else None,
            )

        except Exception as e:
            raise ValueError(f"Failed to convert database workflow to Pydantic: {str(e)}")

    @staticmethod
    def pydantic_to_db_data(workflow: WorkflowData, user_id: str) -> Dict[str, Any]:
        """Convert Pydantic workflow model to database-compatible data."""
        try:
            # Convert nodes to dict format
            nodes_data = []
            for node in workflow.nodes:
                node_data = {
                    "id": node.id,
                    "name": node.name,
                    "type": node.type,
                    "subtype": node.subtype,
                    "position": {"x": node.position.x, "y": node.position.y},
                    "parameters": dict(node.parameters),
                    "disabled": node.disabled,
                    "on_error": node.on_error,
                }
                nodes_data.append(node_data)

            # Convert settings to dict
            settings_data = {
                "timeout": workflow.settings.timeout,
                "max_retries": workflow.settings.max_retries,
                "retry_delay": workflow.settings.retry_delay,
                "parallel_execution": workflow.settings.parallel_execution,
                "error_handling": workflow.settings.error_handling,
                "execution_mode": workflow.settings.execution_mode,
                "variables": dict(workflow.settings.variables),
            }

            # Create workflow JSONB data
            workflow_data = {
                "nodes": nodes_data,
                "connections": workflow.connections.connections,
                "settings": settings_data,
                "static_data": dict(workflow.static_data),
                "version": workflow.version,
            }

            # Prepare database model data
            current_time = int(datetime.now().timestamp())

            db_data = {
                "id": workflow.id or str(uuid.uuid4()),
                "user_id": user_id,
                "name": workflow.name,
                "description": workflow.description,
                "active": workflow.active,
                "workflow_data": workflow_data,
                "tags": list(workflow.tags),
                "created_at": workflow.created_at or current_time,
                "updated_at": current_time,
                "session_id": workflow.session_id,
            }

            return db_data

        except Exception as e:
            raise ValueError(f"Failed to convert Pydantic workflow to database format: {str(e)}")

    @staticmethod
    def create_new_workflow_id() -> str:
        """Generate a new UUID for workflow."""
        return str(uuid.uuid4())


class ExecutionConverter:
    """Converter for execution data between different formats."""

    @staticmethod
    def create_execution_data(
        workflow_id: str,
        workflow_name: str,
        user_id: str,
        trigger_type: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> ExecutionData:
        """Create a new execution data record."""
        execution_id = str(uuid.uuid4())
        current_time = int(datetime.now().timestamp())

        return ExecutionData(
            id=execution_id,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            user_id=user_id,
            status=ExecutionStatus.PENDING,
            trigger_type=trigger_type,
            trigger_data={},
            input_data=input_data or {},
            output_data={},
            started_at=current_time,
            completed_at=None,
            execution_time_ms=None,
            node_executions=[],
            current_node_id=None,
            error_message=None,
            error_node_id=None,
            total_nodes=0,
            completed_nodes=0,
            progress_percentage=0.0,
            session_id=None,
            execution_context={},
        )


class ValidationHelper:
    """Helper utilities for data validation and conversion."""

    @staticmethod
    def validate_workflow_data(workflow_data: Dict[str, Any]) -> Dict[str, str]:
        """Validate workflow data and return validation errors."""
        errors = {}

        # Validate basic fields
        if not workflow_data.get("name", "").strip():
            errors["name"] = "Workflow name is required"

        if not workflow_data.get("nodes"):
            errors["nodes"] = "At least one node is required"

        # Validate nodes
        nodes = workflow_data.get("nodes", [])
        node_ids = set()

        for i, node in enumerate(nodes):
            node_id = node.get("id", "")
            if not node_id:
                errors[f"nodes[{i}].id"] = "Node ID is required"
            elif node_id in node_ids:
                errors[f"nodes[{i}].id"] = "Node ID must be unique"
            else:
                node_ids.add(node_id)

            if not node.get("name", "").strip():
                errors[f"nodes[{i}].name"] = "Node name is required"

            if not node.get("type", "").strip():
                errors[f"nodes[{i}].type"] = "Node type is required"

            # Validate position
            position = node.get("position", {})
            if not isinstance(position.get("x"), (int, float)):
                errors[f"nodes[{i}].position.x"] = "Position X must be a number"
            if not isinstance(position.get("y"), (int, float)):
                errors[f"nodes[{i}].position.y"] = "Position Y must be a number"

        # Validate connections
        connections = workflow_data.get("connections", {})
        if isinstance(connections, dict):
            for source_id, targets in connections.items():
                if source_id not in node_ids:
                    errors[f"connections.{source_id}"] = f"Source node {source_id} does not exist"

                if isinstance(targets, list):
                    for target_id in targets:
                        if target_id not in node_ids:
                            errors[
                                f"connections.{source_id}"
                            ] = f"Target node {target_id} does not exist"

        return errors

    @staticmethod
    def sanitize_user_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize user input data to prevent issues."""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Convert keys to strings and limit length
                clean_key = str(key)[:100]

                # Recursively sanitize nested dictionaries
                if isinstance(value, dict):
                    sanitized[clean_key] = ValidationHelper.sanitize_user_input(value)
                elif isinstance(value, list):
                    sanitized[clean_key] = [
                        ValidationHelper.sanitize_user_input(item)
                        if isinstance(item, dict)
                        else str(item)[:1000]
                        for item in value[:100]  # Limit list length
                    ]
                else:
                    # Convert to string and limit length
                    sanitized[clean_key] = str(value)[:1000]

            return sanitized

        return data

    @staticmethod
    def generate_unique_id(prefix: str = "") -> str:
        """Generate a unique ID with optional prefix."""
        unique_id = str(uuid.uuid4())
        return f"{prefix}_{unique_id}" if prefix else unique_id
