"""
Migration script to convert node configurations from schema format to value format.

This script fixes existing workflows in the database where node configurations
contain schema definitions (type, default, description) instead of actual values.

Example transformation:
BEFORE: {"timeout": {"type": "integer", "default": 30, "description": "..."}}
AFTER:  {"timeout": 30}
"""

import os
import sys
from typing import Any, Dict

from supabase import create_client


def extract_default_value(config_value: Any) -> Any:
    """Extract default value from configuration schema."""
    if isinstance(config_value, dict) and "default" in config_value:
        return config_value["default"]
    return config_value


def migrate_node_configurations(node: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate a single node's configurations from schema to values."""
    if not node.get("configurations"):
        return node

    migrated_configs = {}
    for key, value in node["configurations"].items():
        migrated_configs[key] = extract_default_value(value)

    node["configurations"] = migrated_configs
    return node


def migrate_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate all nodes in a workflow."""
    if not workflow.get("nodes"):
        return workflow

    migrated_nodes = []
    for node in workflow["nodes"]:
        migrated_nodes.append(migrate_node_configurations(node))

    workflow["nodes"] = migrated_nodes
    return workflow


def main():
    """Run the migration on all workflows in the database."""
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY")

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SECRET_KEY must be set")
        sys.exit(1)

    print(f"🔌 Connecting to Supabase: {supabase_url}")
    supabase = create_client(supabase_url, supabase_key)

    # Fetch all workflows
    print("📥 Fetching workflows...")
    response = supabase.table("workflows").select("*").execute()
    workflows = response.data

    print(f"📊 Found {len(workflows)} workflows")

    migrated_count = 0
    skipped_count = 0

    for workflow in workflows:
        workflow_id = workflow["id"]
        # Support both 'definition' and 'workflow_data' fields
        definition = workflow.get("definition") or workflow.get("workflow_data")

        if not definition or not isinstance(definition, dict):
            print(f"⏭️  Skipping workflow {workflow_id}: No definition or workflow_data")
            skipped_count += 1
            continue

        # Check if migration is needed
        needs_migration = False
        for node in definition.get("nodes", []):
            for config_value in node.get("configurations", {}).values():
                if isinstance(config_value, dict) and "default" in config_value:
                    needs_migration = True
                    break
            if needs_migration:
                break

        if not needs_migration:
            print(f"✅ Workflow {workflow_id}: Already migrated")
            skipped_count += 1
            continue

        # Migrate the workflow
        print(f"🔄 Migrating workflow {workflow_id}...")
        migrated_definition = migrate_workflow(definition)

        # Update in database (use the same field that was read)
        try:
            field_name = "workflow_data" if workflow.get("workflow_data") else "definition"
            supabase.table("workflows").update({field_name: migrated_definition}).eq(
                "id", workflow_id
            ).execute()
            print(f"✅ Migrated workflow {workflow_id}")
            migrated_count += 1
        except Exception as e:
            print(f"❌ Failed to migrate workflow {workflow_id}: {e}")

    print("\n" + "=" * 60)
    print(f"📊 Migration complete!")
    print(f"   - Migrated: {migrated_count}")
    print(f"   - Skipped: {skipped_count}")
    print(f"   - Total: {len(workflows)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
