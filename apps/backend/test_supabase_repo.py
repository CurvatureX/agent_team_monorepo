#!/usr/bin/env python3
"""
Test script for SupabaseWorkflowRepository to debug RLS workflow listing
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set environment variables
os.environ[
    "DATABASE_URL"
] = "postgresql://postgres.mkrczzgjeduruwxpanbj:Starmates2025%40@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
os.environ["SUPABASE_URL"] = "https://mkrczzgjeduruwxpanbj.supabase.co"
os.environ["SUPABASE_SECRET_KEY"] = "sb_secret_XzUlnp099wqPe1fvVggyOg_-a83ZFHY"
os.environ["SUPABASE_ANON_KEY"] = "sb_publishable_GDldaQkfc6tfJ2aEOx_H3w_rq2Tc5G3"

# JWT token for user 7ba36345-a2bb-4ec9-a001-bb46d79d629d
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6InZydnZmclVOdi9HUXFRT2oiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL21rcmN6emdqZWR1cnV3eHBhbmJqLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3YmEzNjM0NS1hMmJiLTRlYzktYTAwMS1iYjQ2ZDc5ZDYyOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU3NjUyNzgzLCJpYXQiOjE3NTc2NDkxODMsImVtYWlsIjoiZGFtaW5nLmx1QHN0YXJtYXRlcy5haSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzU3NjQ5MTgzfV0sInNlc3Npb25faWQiOiI5MmIzMzQyYi0zMWRlLTQ0OGMtYWQ2NC1kNjNkNjY3NzBhMTkiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.CUzxSl7hvbigGb7-EUZty5zTcuZyLN1LCpO3_1E48AI"


async def test_supabase_repo():
    """Test SupabaseWorkflowRepository directly"""
    print("🔍 Testing SupabaseWorkflowRepository...")

    try:
        # Import supabase repository directly
        import sys

        sys.path.insert(
            0, "/Users/jingweizhang/Workspace/agent_team_monorepo/apps/backend/workflow_engine"
        )
        from workflow_engine.services.supabase_repository import SupabaseWorkflowRepository

        print("✅ Import successful")

        # Test with JWT token (RLS)
        print(f"🔑 Creating repo with JWT token for RLS...")
        repo = SupabaseWorkflowRepository(access_token=JWT_TOKEN)
        print("✅ Repository created")

        # Test list_workflows
        print("📋 Calling list_workflows...")
        workflows, total_count = await repo.list_workflows(
            active_only=False, tags=[], limit=10, offset=0
        )

        print(f"✅ Query successful!")
        print(f"📊 Found {len(workflows)} workflows (total: {total_count})")

        for i, workflow in enumerate(workflows):
            print(f"  {i+1}. {workflow.get('name', 'Unknown')} ({workflow.get('id', 'No ID')})")

        if len(workflows) == 0:
            print("⚠️  No workflows returned - checking RLS policies...")

            # Test with service role (no RLS)
            print("🔓 Testing with service role (bypassing RLS)...")
            service_repo = SupabaseWorkflowRepository(access_token=None)
            service_workflows, service_total = await service_repo.list_workflows(
                active_only=False, tags=[], limit=10, offset=0
            )
            print(
                f"📊 Service role found {len(service_workflows)} workflows (total: {service_total})"
            )

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_supabase_repo())
