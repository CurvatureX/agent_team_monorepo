"""
Workflow Data Migration Script

Migrates existing workflow records from old format to align with the latest
data model defined in shared/models/workflow_new.py and shared/node_specs/.

Key Changes:
1. Convert old "parameters" field to new "configurations" field
2. Add missing required fields: description, input_params, output_params
3. Remove legacy fields: disabled, notes, webhooks, credentials, retry_policy, type_version, on_error
4. Convert connections format from nested structure to flat list with Connection model
5. Validate against node specifications in NODE_SPECS_REGISTRY
6. Add proper metadata fields per WorkflowMetadata model

Usage:
    python migrate_workflows.py --dry-run  # Preview changes without applying
    python migrate_workflows.py --execute  # Apply migrations to database
    python migrate_workflows.py --workflow-id <uuid>  # Migrate specific workflow
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import ValidationError

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.models import Connection, Node, Workflow, WorkflowMetadata, WorkflowStatistics
from shared.models.node_enums import NodeType
from shared.node_specs import NODE_SPECS_REGISTRY, get_node_spec

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class WorkflowMigration:
    """Handles migration of workflow data from old format to new format."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }

    def migrate_node(self, old_node: Dict[str, Any]) -> Optional[Node]:
        """
        Migrate a single node from old format to new format.

        Old format:
        {
            "id": "node_id",
            "name": "Node Name",
            "type": "TRIGGER",
            "subtype": "SLACK",
            "parameters": {...},  # OLD: configuration data
            "disabled": false,
            "on_error": "continue",
            "notes": {},
            "webhooks": [],
            "credentials": {},
            "retry_policy": null,
            "type_version": 1,
            "position": {"x": 100, "y": 100}
        }

        New format:
        {
            "id": "node_id",
            "name": "Node Name",
            "description": "Node description",  # NEW: required
            "type": "TRIGGER",
            "subtype": "SLACK",
            "configurations": {...},  # NEW: renamed from parameters
            "input_params": {...},  # NEW: runtime input parameters
            "output_params": {...},  # NEW: runtime output parameters
            "position": {"x": 100, "y": 100}
        }
        """
        try:
            node_id = old_node.get("id")
            node_type = old_node.get("type")
            node_subtype = old_node.get("subtype")

            # Get node spec for validation and defaults
            node_spec = get_node_spec(node_type, node_subtype)
            if not node_spec:
                logger.warning(
                    f"No node spec found for {node_type}.{node_subtype}, node_id={node_id}"
                )

            # Generate description from node spec or use default
            description = node_spec.description if node_spec else f"{node_type} {node_subtype} node"

            # Migrate parameters -> configurations
            configurations = old_node.get("parameters", {})

            # Initialize input_params and output_params from node spec defaults
            input_params = {}
            output_params = {}
            if node_spec:
                # Use default_input_params if available, otherwise derive from input_params schema
                if hasattr(node_spec, "default_input_params") and node_spec.default_input_params:
                    input_params = node_spec.default_input_params.copy()
                elif hasattr(node_spec, "input_params") and node_spec.input_params:
                    input_params = self._derive_defaults_from_schema(node_spec.input_params)

                # Use default_output_params if available, otherwise derive from output_params schema
                if hasattr(node_spec, "default_output_params") and node_spec.default_output_params:
                    output_params = node_spec.default_output_params.copy()
                elif hasattr(node_spec, "output_params") and node_spec.output_params:
                    output_params = self._derive_defaults_from_schema(node_spec.output_params)

            # Sanitize node name - remove spaces as per Node model validation
            node_name = old_node.get("name", "").replace(" ", "_")

            # Build new node data
            new_node_data = {
                "id": node_id,
                "name": node_name,
                "description": description,
                "type": node_type,
                "subtype": node_subtype,
                "configurations": configurations,
                "input_params": input_params,
                "output_params": output_params,
                "position": old_node.get("position"),
            }

            # Validate and create Node instance
            new_node = Node(**new_node_data)
            logger.debug(f"Successfully migrated node: {node_id}")
            return new_node

        except ValidationError as e:
            logger.error(f"Validation error migrating node {old_node.get('id')}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error migrating node {old_node.get('id')}: {e}")
            return None

    def _derive_defaults_from_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Derive default runtime values from parameter schema definitions."""
        defaults = {}
        try:
            for key, spec in schema.items():
                if isinstance(spec, dict) and "default" in spec:
                    defaults[key] = spec["default"]
        except Exception as e:
            logger.warning(f"Error deriving defaults from schema: {e}")
        return defaults

    def migrate_connections(
        self, old_connections: Dict[str, Any], node_ids: List[str]
    ) -> List[Connection]:
        """
        Migrate connections from old nested format to new flat format.

        Old format:
        {
            "source_node": {
                "connection_types": {
                    "main": {
                        "connections": [
                            {"node": "target_node", "type": "main", "index": 0}
                        ]
                    },
                    "true": {
                        "connections": [
                            {"node": "target_node", "type": "main", "index": 0}
                        ]
                    }
                }
            }
        }

        New format:
        [
            {
                "id": "conn_1",
                "from_node": "source_node",
                "to_node": "target_node",
                "output_key": "result",  # or "true", "false" for conditional nodes
                "conversion_function": "def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return input_data"
            }
        ]
        """
        new_connections = []
        connection_counter = 0
        node_id_set = set(node_ids)

        try:
            for source_node_id, connection_data in old_connections.items():
                if source_node_id not in node_id_set:
                    logger.warning(f"Skipping connection from unknown node: {source_node_id}")
                    continue

                connection_types = connection_data.get("connection_types", {})
                for output_type, connections_info in connection_types.items():
                    connections_list = connections_info.get("connections", [])

                    for conn in connections_list:
                        target_node = conn.get("node")
                        if target_node not in node_id_set:
                            logger.warning(f"Skipping connection to unknown node: {target_node}")
                            continue

                        # Map old connection types to new output_key
                        # "main" -> "result"
                        # "true"/"false" -> keep as is (for conditional nodes)
                        if output_type == "main":
                            output_key = "result"
                        else:
                            output_key = output_type

                        # Default passthrough conversion function
                        conversion_function = (
                            "def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: "
                            "return input_data"
                        )

                        connection_counter += 1
                        new_connection = Connection(
                            id=f"conn_{connection_counter}",
                            from_node=source_node_id,
                            to_node=target_node,
                            output_key=output_key,
                            conversion_function=conversion_function,
                        )
                        new_connections.append(new_connection)

            logger.debug(f"Migrated {len(new_connections)} connections")
            return new_connections

        except Exception as e:
            logger.error(f"Error migrating connections: {e}")
            return []

    def migrate_workflow(self, workflow_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Migrate a complete workflow record.

        Returns updated workflow_data to be saved, or None if migration failed.
        """
        try:
            workflow_id = workflow_record.get("id")
            workflow_data = workflow_record.get("workflow_data", {})

            logger.info(f"Migrating workflow: {workflow_id} - {workflow_record.get('name')}")

            # Extract old data
            old_nodes = workflow_data.get("nodes", [])
            old_connections = workflow_data.get("connections", {})
            old_settings = workflow_data.get("settings", {})

            # Migrate nodes
            new_nodes = []
            for old_node in old_nodes:
                new_node = self.migrate_node(old_node)
                if new_node:
                    new_nodes.append(new_node)
                else:
                    logger.warning(
                        f"Failed to migrate node {old_node.get('id')} in workflow {workflow_id}"
                    )

            if not new_nodes:
                logger.error(f"No valid nodes after migration for workflow {workflow_id}")
                return None

            # Extract node IDs
            node_ids = [node.id for node in new_nodes]

            # Migrate connections
            new_connections = self.migrate_connections(old_connections, node_ids)

            # Identify triggers (nodes with type TRIGGER)
            triggers = [node.id for node in new_nodes if node.type == NodeType.TRIGGER]

            # Build WorkflowMetadata
            created_at = workflow_record.get("created_at")
            updated_at = workflow_record.get("updated_at")
            current_time_ms = int(datetime.now().timestamp() * 1000)

            metadata = WorkflowMetadata(
                id=str(workflow_id),
                name=workflow_record.get("name", "Untitled Workflow"),
                icon_url=workflow_record.get("icon_url"),
                description=workflow_record.get("description", ""),
                deployment_status=workflow_record.get("deployment_status", "DRAFT"),
                last_execution_status=None,
                last_execution_time=None,
                tags=workflow_record.get("tags", []),
                created_time=created_at if created_at else current_time_ms,
                parent_workflow=None,
                statistics=WorkflowStatistics(),
                version=workflow_record.get("version", "1.0"),
                created_by=str(workflow_record.get("user_id", "")),
                updated_by=str(workflow_record.get("user_id", "")),
            )

            # Build complete Workflow object
            workflow = Workflow(
                metadata=metadata,
                nodes=new_nodes,
                connections=new_connections,
                triggers=triggers,
            )

            # Convert to dict for storage
            new_workflow_data = workflow.model_dump(mode="json")

            logger.info(
                f"Successfully migrated workflow {workflow_id}: "
                f"{len(new_nodes)} nodes, {len(new_connections)} connections, "
                f"{len(triggers)} triggers"
            )

            return new_workflow_data

        except Exception as e:
            logger.error(f"Error migrating workflow {workflow_record.get('id')}: {e}")
            return None

    def execute_migration(self, workflow_id: Optional[str] = None, limit: Optional[int] = None):
        """
        Execute the migration process.

        Args:
            workflow_id: Optional specific workflow ID to migrate
            limit: Optional limit on number of workflows to migrate
        """
        try:
            # Import database connection
            from supabase import create_client

            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SECRET_KEY")

            if not supabase_url or not supabase_key:
                raise ValueError("SUPABASE_URL and SUPABASE_SECRET_KEY must be set")

            client = create_client(supabase_url, supabase_key)

            # Fetch workflows to migrate
            query = client.table("workflows").select("*")

            if workflow_id:
                query = query.eq("id", workflow_id)

            if limit:
                query = query.limit(limit)

            response = query.execute()
            workflows = response.data

            if not workflows:
                logger.warning("No workflows found to migrate")
                return

            self.stats["total"] = len(workflows)
            logger.info(f"Found {len(workflows)} workflows to migrate")

            # Migrate each workflow
            for workflow_record in workflows:
                try:
                    new_workflow_data = self.migrate_workflow(workflow_record)

                    if new_workflow_data:
                        if self.dry_run:
                            logger.info(f"[DRY RUN] Would update workflow {workflow_record['id']}")
                            logger.debug(
                                f"[DRY RUN] New data: {json.dumps(new_workflow_data, indent=2)[:500]}..."
                            )
                            self.stats["success"] += 1
                        else:
                            # Update workflow in database
                            update_response = (
                                client.table("workflows")
                                .update(
                                    {
                                        "workflow_data": new_workflow_data,
                                        "updated_at": int(datetime.now().timestamp() * 1000),
                                    }
                                )
                                .eq("id", workflow_record["id"])
                                .execute()
                            )

                            if update_response.data:
                                logger.info(
                                    f"Successfully updated workflow {workflow_record['id']}"
                                )
                                self.stats["success"] += 1
                            else:
                                logger.error(f"Failed to update workflow {workflow_record['id']}")
                                self.stats["failed"] += 1
                    else:
                        logger.error(f"Migration failed for workflow {workflow_record['id']}")
                        self.stats["failed"] += 1

                except Exception as e:
                    logger.error(
                        f"Error processing workflow {workflow_record.get('id')}: {e}",
                        exc_info=True,
                    )
                    self.stats["failed"] += 1

            # Print summary
            logger.info("\n" + "=" * 50)
            logger.info("Migration Summary:")
            logger.info(f"Total workflows: {self.stats['total']}")
            logger.info(f"Successfully migrated: {self.stats['success']}")
            logger.info(f"Failed: {self.stats['failed']}")
            logger.info(f"Skipped: {self.stats['skipped']}")
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"Fatal error during migration: {e}", exc_info=True)
            raise


def main():
    parser = argparse.ArgumentParser(description="Migrate workflow data to new format")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without applying them (default: True)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the migration (overrides --dry-run)",
    )
    parser.add_argument(
        "--workflow-id",
        type=str,
        help="Migrate a specific workflow by ID",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of workflows to migrate",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine if this is a dry run
    dry_run = not args.execute

    if dry_run:
        logger.info("=" * 50)
        logger.info("DRY RUN MODE - No changes will be applied")
        logger.info("=" * 50)
    else:
        logger.warning("=" * 50)
        logger.warning("EXECUTION MODE - Changes will be applied to database")
        logger.warning("=" * 50)
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Migration cancelled")
            return

    migration = WorkflowMigration(dry_run=dry_run)
    migration.execute_migration(workflow_id=args.workflow_id, limit=args.limit)


if __name__ == "__main__":
    main()
