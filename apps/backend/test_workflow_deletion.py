#!/usr/bin/env python3
"""
Test script for workflow deletion with CASCADE constraints.

Usage:
    python test_workflow_deletion.py create      # Create test workflow with related data
    python test_workflow_deletion.py verify      # Verify related data exists
    python test_workflow_deletion.py delete      # Delete workflow and verify CASCADE
    python test_workflow_deletion.py cleanup     # Clean up any leftover test data
"""

import os
import sys
import uuid
from datetime import datetime

from shared.models.supabase import create_supabase_client

# Test workflow ID (consistent across runs)
TEST_WORKFLOW_ID = "00000000-0000-0000-0000-000000000001"


def create_test_workflow():
    """Create a test workflow with related data in multiple tables."""
    print("🔧 Creating test workflow with related data...")

    supabase = create_supabase_client()

    try:
        # 1. Create workflow
        workflow_data = {
            "id": TEST_WORKFLOW_ID,
            "user_id": "7ba36345-a2bb-4ec9-a001-bb46d79d629d",  # Test user
            "name": "Test Workflow for Deletion",
            "description": "This workflow tests CASCADE deletion",
            "active": True,
            "workflow_data": {
                "metadata": {
                    "id": TEST_WORKFLOW_ID,
                    "name": "Test Workflow for Deletion",
                    "description": "This workflow tests CASCADE deletion",
                    "created_time": int(datetime.now().timestamp() * 1000),
                    "created_by": "7ba36345-a2bb-4ec9-a001-bb46d79d629d",
                },
                "nodes": [],
                "connections": [],
                "triggers": [],
            },
            "created_at": int(datetime.now().timestamp() * 1000),
            "updated_at": int(datetime.now().timestamp() * 1000),
        }

        result = supabase.table("workflows").insert(workflow_data).execute()
        print(f"✅ Created workflow: {TEST_WORKFLOW_ID}")

        # 2. Create trigger_index record
        trigger_data = {
            "workflow_id": TEST_WORKFLOW_ID,
            "trigger_type": "TRIGGER_MANUAL",
            "trigger_subtype": "MANUAL",
            "trigger_config": {"type": "manual"},
            "deployment_status": "active",
        }
        supabase.table("trigger_index").insert(trigger_data).execute()
        print("✅ Created trigger_index record")

        # 3. Create workflow_execution record
        execution_data = {
            "execution_id": str(uuid.uuid4()),
            "workflow_id": TEST_WORKFLOW_ID,
            "status": "SUCCESS",
            "mode": "MANUAL",
            "start_time": int(datetime.now().timestamp() * 1000),
            "end_time": int(datetime.now().timestamp() * 1000),
        }
        supabase.table("workflow_executions").insert(execution_data).execute()
        print("✅ Created workflow_execution record")

        # 4. Create human_interaction record (if table exists)
        try:
            interaction_data = {
                "workflow_id": TEST_WORKFLOW_ID,
                "node_id": "test_node",
                "interaction_type": "approval",
                "channel_type": "slack",
                "status": "pending",
                "request_data": {"question": "Test approval?"},
                "timeout_at": datetime.now().isoformat(),
            }
            supabase.table("human_interactions").insert(interaction_data).execute()
            print("✅ Created human_interaction record")
        except Exception as e:
            print(f"⚠️  Could not create human_interaction: {e}")

        print("\n✅ Test workflow and related data created successfully!")
        print(f"Workflow ID: {TEST_WORKFLOW_ID}")

    except Exception as e:
        print(f"❌ Error creating test workflow: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def verify_test_data():
    """Verify that test workflow and related data exist."""
    print("🔍 Verifying test workflow and related data...")

    supabase = create_supabase_client()

    try:
        # Check workflow exists
        workflow_result = (
            supabase.table("workflows").select("id").eq("id", TEST_WORKFLOW_ID).execute()
        )
        workflow_exists = len(workflow_result.data) > 0
        print(f"{'✅' if workflow_exists else '❌'} Workflow exists: {workflow_exists}")

        # Check trigger_index records
        trigger_result = (
            supabase.table("trigger_index")
            .select("id", count="exact")
            .eq("workflow_id", TEST_WORKFLOW_ID)
            .execute()
        )
        trigger_count = (
            trigger_result.count if hasattr(trigger_result, "count") else len(trigger_result.data)
        )
        print(f"{'✅' if trigger_count > 0 else '❌'} trigger_index records: {trigger_count}")

        # Check workflow_executions records
        exec_result = (
            supabase.table("workflow_executions")
            .select("id", count="exact")
            .eq("workflow_id", TEST_WORKFLOW_ID)
            .execute()
        )
        exec_count = exec_result.count if hasattr(exec_result, "count") else len(exec_result.data)
        print(f"{'✅' if exec_count > 0 else '❌'} workflow_executions records: {exec_count}")

        # Check human_interactions records (if table exists)
        try:
            interaction_result = (
                supabase.table("human_interactions")
                .select("id", count="exact")
                .eq("workflow_id", TEST_WORKFLOW_ID)
                .execute()
            )
            interaction_count = (
                interaction_result.count
                if hasattr(interaction_result, "count")
                else len(interaction_result.data)
            )
            print(
                f"{'✅' if interaction_count > 0 else '❌'} human_interactions records: {interaction_count}"
            )
        except Exception:
            print("⚠️  human_interactions table not available")

        if not workflow_exists:
            print(
                "\n⚠️  Test workflow not found. Run 'python test_workflow_deletion.py create' first."
            )
            sys.exit(1)

        print("\n✅ Verification complete!")

    except Exception as e:
        print(f"❌ Error verifying test data: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def delete_test_workflow():
    """Delete test workflow and verify CASCADE deletion."""
    print("🗑️  Deleting test workflow...")

    supabase = create_supabase_client()

    try:
        # Count records before deletion
        print("\n📊 Before deletion:")
        verify_test_data()

        # Delete the workflow
        print(f"\n🗑️  Deleting workflow {TEST_WORKFLOW_ID}...")
        result = supabase.table("workflows").delete().eq("id", TEST_WORKFLOW_ID).execute()

        if result.data:
            print("✅ Workflow deleted successfully")
        else:
            print("⚠️  Workflow not found or already deleted")
            return

        # Verify CASCADE deletion
        print("\n📊 After deletion (verifying CASCADE):")

        # Check workflow is gone
        workflow_result = (
            supabase.table("workflows").select("id").eq("id", TEST_WORKFLOW_ID).execute()
        )
        workflow_exists = len(workflow_result.data) > 0
        print(
            f"{'❌ FAILED' if workflow_exists else '✅ SUCCESS'} Workflow deleted: {not workflow_exists}"
        )

        # Check trigger_index records CASCADE deleted
        trigger_result = (
            supabase.table("trigger_index")
            .select("id")
            .eq("workflow_id", TEST_WORKFLOW_ID)
            .execute()
        )
        trigger_count = len(trigger_result.data)
        print(
            f"{'❌ FAILED' if trigger_count > 0 else '✅ SUCCESS'} trigger_index CASCADE deleted: {trigger_count == 0} (count: {trigger_count})"
        )

        # Check workflow_executions CASCADE deleted
        exec_result = (
            supabase.table("workflow_executions")
            .select("id")
            .eq("workflow_id", TEST_WORKFLOW_ID)
            .execute()
        )
        exec_count = len(exec_result.data)
        print(
            f"{'❌ FAILED' if exec_count > 0 else '✅ SUCCESS'} workflow_executions CASCADE deleted: {exec_count == 0} (count: {exec_count})"
        )

        # Check human_interactions CASCADE deleted (if table exists)
        try:
            interaction_result = (
                supabase.table("human_interactions")
                .select("id")
                .eq("workflow_id", TEST_WORKFLOW_ID)
                .execute()
            )
            interaction_count = len(interaction_result.data)
            print(
                f"{'❌ FAILED' if interaction_count > 0 else '✅ SUCCESS'} human_interactions CASCADE deleted: {interaction_count == 0} (count: {interaction_count})"
            )
        except Exception:
            print("⚠️  human_interactions table not available")

        print("\n✅ Deletion test complete!")

        if trigger_count > 0 or exec_count > 0:
            print(
                "\n❌ CASCADE deletion FAILED! Foreign key constraints may not be set up correctly."
            )
            print(
                "   Run the migration: supabase/migrations/20251007000001_add_cascade_delete_constraints.sql"
            )
            sys.exit(1)
        else:
            print("\n✅ CASCADE deletion working correctly!")

    except Exception as e:
        print(f"❌ Error during deletion test: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def cleanup():
    """Clean up any leftover test data."""
    print("🧹 Cleaning up test data...")

    supabase = create_supabase_client()

    try:
        # Delete from all related tables first (if CASCADE constraints don't exist)
        tables = [
            "human_interactions",
            "trigger_index",
            "workflow_executions",
            "workflows",
        ]

        for table in tables:
            try:
                result = (
                    supabase.table(table)
                    .delete()
                    .eq("workflow_id" if table != "workflows" else "id", TEST_WORKFLOW_ID)
                    .execute()
                )
                if result.data:
                    print(f"✅ Cleaned up {table}: {len(result.data)} records")
            except Exception as e:
                print(f"⚠️  Could not clean up {table}: {e}")

        print("\n✅ Cleanup complete!")

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        create_test_workflow()
    elif command == "verify":
        verify_test_data()
    elif command == "delete":
        delete_test_workflow()
    elif command == "cleanup":
        cleanup()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
