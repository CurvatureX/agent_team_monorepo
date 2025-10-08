#!/usr/bin/env python3
"""
Script to generate random icons for workflows that don't have icon_url set.

This script:
1. Connects to Supabase database
2. Finds workflows without icon_url (both in column and metadata)
3. Generates random icon URLs using the icon_utils module
4. Updates both the icon_url column and workflow_data.metadata.icon_url
"""

import os
import sys

# Add parent directory to path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from supabase import Client, create_client

from shared.utils.icon_utils import generate_random_icon_url


def get_supabase_client() -> Client:
    """Create and return a Supabase client with admin privileges."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY")

    if not supabase_url or not supabase_secret_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SECRET_KEY environment variables must be set")

    return create_client(supabase_url, supabase_secret_key)


def main():
    """Main function to generate and update workflow icons."""
    print("🎨 Starting workflow icon generation...")
    print()

    # Get Supabase client
    try:
        supabase = get_supabase_client()
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return 1

    # Query workflows without icon_url
    print("🔍 Fetching workflows without icon_url...")
    try:
        result = (
            supabase.table("workflows")
            .select("id, name, icon_url, workflow_data")
            .eq("active", True)
            .execute()
        )
        all_workflows = result.data
        print(f"📊 Found {len(all_workflows)} total active workflows")
    except Exception as e:
        print(f"❌ Failed to fetch workflows: {e}")
        return 1

    # Filter workflows that need icons
    workflows_needing_icons = []
    for workflow in all_workflows:
        workflow_id = workflow.get("id")
        icon_url = workflow.get("icon_url")
        workflow_data = workflow.get("workflow_data", {})
        metadata_icon_url = (
            workflow_data.get("metadata", {}).get("icon_url") if workflow_data else None
        )

        # Need icon if both column and metadata are null/empty
        if not icon_url and not metadata_icon_url:
            workflows_needing_icons.append(workflow)

    print(f"🎯 Found {len(workflows_needing_icons)} workflows needing icons")
    print()

    if not workflows_needing_icons:
        print("✅ All workflows already have icons!")
        return 0

    # Generate and update icons
    updated_count = 0
    failed_count = 0

    for workflow in workflows_needing_icons:
        workflow_id = workflow.get("id")
        workflow_name = workflow.get("name", "Unnamed")
        workflow_data = workflow.get("workflow_data", {})

        try:
            # Generate random icon URL
            icon_url = generate_random_icon_url()

            # Update workflow_data.metadata.icon_url
            if "metadata" not in workflow_data:
                workflow_data["metadata"] = {}
            workflow_data["metadata"]["icon_url"] = icon_url

            # Update database - both column and metadata
            supabase.table("workflows").update(
                {"icon_url": icon_url, "workflow_data": workflow_data}
            ).eq("id", workflow_id).execute()

            updated_count += 1
            print(f"✅ [{updated_count}/{len(workflows_needing_icons)}] Updated: {workflow_name}")
            print(f"   ID: {workflow_id}")
            print(f"   Icon: {icon_url}")
            print()

        except Exception as e:
            failed_count += 1
            print(f"❌ Failed to update workflow {workflow_id} ({workflow_name}): {e}")
            print()

    # Summary
    print("=" * 60)
    print("📊 Summary:")
    print(f"   Total workflows: {len(all_workflows)}")
    print(f"   Workflows needing icons: {len(workflows_needing_icons)}")
    print(f"   Successfully updated: {updated_count}")
    print(f"   Failed: {failed_count}")
    print("=" * 60)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
