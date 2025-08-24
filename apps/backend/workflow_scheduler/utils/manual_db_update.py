#!/usr/bin/env python3
"""
Manual Database Update Utility
Bypasses SQLAlchemy to directly update workflow deployment status using psycopg2
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import UUID

# Add the parent directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)

from workflow_scheduler.core.config import settings


def get_db_connection():
    """Get a direct psycopg2 connection"""
    # Parse the database URL to get connection parameters
    url = settings.database_url

    # Create connection with psycopg2 (synchronous, no prepared statements by default)
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


def update_workflow_deployment_status(workflow_id: str, status: str = "DEPLOYED"):
    """Update workflow deployment status using direct SQL"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Validate workflow_id format
                try:
                    workflow_uuid = UUID(workflow_id)
                except ValueError:
                    print(f"❌ Invalid workflow ID format: {workflow_id}")
                    return False

                # Get current timestamp as Unix timestamp for updated_at
                current_time = datetime.now(timezone.utc)
                current_timestamp = int(current_time.timestamp())

                # Update workflow deployment status
                update_query = """
                    UPDATE workflows
                    SET deployment_status = %s,
                        deployed_at = %s,
                        deployment_version = deployment_version + 1,
                        updated_at = %s
                    WHERE id = %s
                """

                cur.execute(
                    update_query,
                    (status, current_time, current_timestamp, workflow_uuid),
                )
                affected_rows = cur.rowcount

                if affected_rows > 0:
                    print(f"✅ Updated workflow {workflow_id} status to {status}")

                    # Create deployment history record
                    history_query = """
                        INSERT INTO workflow_deployment_history
                        (workflow_id, deployment_action, from_status, to_status, deployment_version,
                         deployment_config, started_at, completed_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """

                    cur.execute(
                        history_query,
                        (
                            workflow_uuid,
                            "DEPLOY",
                            "DRAFT",
                            status,
                            cur.execute(
                                "SELECT deployment_version FROM workflows WHERE id = %s",
                                (workflow_uuid,),
                            )
                            or 1,
                            '{"manual_update": true}',
                            current_time,
                            current_time,
                        ),
                    )

                    print(f"✅ Created deployment history record for {workflow_id}")
                    return True
                else:
                    print(f"❌ No workflow found with ID: {workflow_id}")
                    return False

    except Exception as e:
        print(f"❌ Error updating workflow {workflow_id}: {e}")
        return False


def list_workflows():
    """List workflows and their current deployment status"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, deployment_status, deployed_at, deployment_version
                    FROM workflows
                    ORDER BY created_at DESC
                    LIMIT 10
                """
                )

                workflows = cur.fetchall()

                print("📋 Recent Workflows:")
                print("-" * 80)
                for workflow in workflows:
                    deployed_str = (
                        workflow["deployed_at"].strftime("%Y-%m-%d %H:%M:%S")
                        if workflow["deployed_at"]
                        else "Never"
                    )
                    print(f"ID: {workflow['id']}")
                    print(f"Name: {workflow['name']}")
                    print(f"Status: {workflow['deployment_status']}")
                    print(f"Deployed: {deployed_str}")
                    print(f"Version: {workflow['deployment_version']}")
                    print("-" * 80)

    except Exception as e:
        print(f"❌ Error listing workflows: {e}")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Manual Database Update Utility")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List workflows command
    list_parser = subparsers.add_parser("list", help="List recent workflows")

    # Update workflow command
    update_parser = subparsers.add_parser("update", help="Update workflow deployment status")
    update_parser.add_argument("workflow_id", help="Workflow ID to update")
    update_parser.add_argument(
        "--status",
        default="DEPLOYED",
        choices=["DEPLOYED", "DRAFT", "DEPLOYMENT_FAILED"],
        help="Deployment status to set",
    )

    args = parser.parse_args()

    if args.command == "list":
        list_workflows()
    elif args.command == "update":
        success = update_workflow_deployment_status(args.workflow_id, args.status)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
