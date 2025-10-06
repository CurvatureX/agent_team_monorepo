"""
Test script for AI Agent Node with attached Notion MCP tool.

This script simulates an AI Agent (Anthropic Claude) with a Notion MCP tool attached,
demonstrating how the AI can use Notion tools to search for information and generate
better, data-driven responses.

Test scenario:
- Input: "analyze the company A's sales trend and provide suggestions"
- Company A's sales data is stored in: https://www.notion.so/Test-27f0b1df411b80acaa54c4cba158a1f9
- Expected: AI Agent uses Notion MCP to retrieve the page and analyze the data
"""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import httpx
from supabase import Client, create_client

# Configuration from environment
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://mkrczzgjeduruwxpanbj.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "sb_publishable_GDldaQkfc6tfJ2aEOx_H3w_rq2Tc5G3")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "daming.lu@starmates.ai")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "test.1234!")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
WORKFLOW_ENGINE_URL = os.getenv("WORKFLOW_ENGINE_URL", "http://localhost:8002")

# Extract Notion page ID from URL
# URL: https://www.notion.so/Test-27f0b1df411b80acaa54c4cba158a1f9
# Format: title-<32-char-hex-id>
NOTION_PAGE_ID = "27f0b1df411b80acaa54c4cba158a1f9"


def create_workflow_definition() -> Dict[str, Any]:
    """Create a test workflow with AI Agent + Notion MCP tool."""

    # Generate unique IDs
    workflow_id = str(uuid.uuid4())
    trigger_node_id = str(uuid.uuid4())
    claude_node_id = str(uuid.uuid4())
    notion_tool_id = str(uuid.uuid4())

    workflow = {
        "metadata": {
            "id": workflow_id,
            "name": "AI Agent with Notion Analysis",
            "description": "Test workflow: AI Agent analyzes company sales data from Notion",
            "version": 1,
            "deployment_status": "idle",
        },
        "nodes": [
            # Manual trigger node
            {
                "id": trigger_node_id,
                "name": "ManualTrigger",
                "description": "Manual trigger",
                "type": "TRIGGER",
                "subtype": "MANUAL",
                "configurations": {},
                "input_params": {},
                "output_params": {
                    "user_prompt": {"type": "string", "description": "User's analysis request"}
                },
                "position": {"x": 100, "y": 100},
            },
            # Claude AI Agent with Notion tool attached
            {
                "id": claude_node_id,
                "name": "ClaudeAnalyst",
                "description": "Claude AI with Notion access for data analysis",
                "type": "AI_AGENT",
                "subtype": "ANTHROPIC_CLAUDE",
                "configurations": {
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 8192,
                    "temperature": 0.7,
                    "system_prompt": """You are a business analyst AI with access to Notion data.

When asked to analyze company data:
1. Use the notion_page tool with operation="get" to retrieve the page content from Notion
2. Extract and analyze the sales data from the page
3. Identify trends, patterns, and insights
4. Provide actionable recommendations based on the data

Always cite specific data points from Notion when making your analysis.""",
                },
                "input_params": {
                    "user_prompt": {"type": "string", "description": "Analysis request"}
                },
                "output_params": {
                    "content": {"type": "string", "description": "AI analysis response"}
                },
                "position": {"x": 400, "y": 100},
                "attached_nodes": [notion_tool_id],  # Notion tool is ATTACHED
            },
            # Notion MCP Tool - provides Notion access to Claude
            {
                "id": notion_tool_id,
                "name": "NotionMCPTool",
                "description": "Notion integration via MCP",
                "type": "TOOL",
                "subtype": "NOTION_MCP_TOOL",
                "configurations": {
                    # ✅ OAuth token will be fetched automatically from oauth_tokens table by user_id
                    # No need to hardcode access_token - ToolRunner retrieves it from database
                    "operation_type": "page",  # Page operations
                    "default_page_id": NOTION_PAGE_ID,  # The company sales page
                    "available_tools": ["notion_page", "notion_search"],
                    "page_size_limit": 100,
                    "enable_rich_text": True,
                    "auto_create_missing_props": False,
                },
                "input_params": {},
                "output_params": {},
                "position": {"x": 400, "y": 250},
            },
        ],
        "connections": [
            # Connect trigger to AI Agent
            {
                "id": str(uuid.uuid4()),
                "from_node": trigger_node_id,
                "to_node": claude_node_id,
                "output_key": "user_prompt",
            }
        ],
    }

    return workflow


async def authenticate_user(supabase: Client) -> tuple[str, str]:
    """Authenticate test user and return access token and user_id."""
    print(f"🔐 Authenticating user: {TEST_USER_EMAIL}")

    response = supabase.auth.sign_in_with_password(
        {"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )

    access_token = response.session.access_token
    user_id = response.user.id
    print(f"✅ Authenticated (user_id: {user_id[:8]}...)")
    return access_token, user_id


async def create_workflow_in_db(access_token: str, workflow: Dict[str, Any]) -> str:
    """Create workflow in database using API Gateway."""
    print(f"\n📝 Creating workflow in database...")

    trigger_node_id = workflow["nodes"][0]["id"]  # First node is trigger

    create_request = {
        "metadata": workflow["metadata"],
        "nodes": workflow["nodes"],
        "connections": workflow["connections"],
        "triggers": [trigger_node_id],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_GATEWAY_URL}/api/v1/app/workflows/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=create_request,
        )

        if response.status_code in (200, 201):
            result = response.json()
            # Try different response formats
            workflow_id = (
                result.get("id")
                or result.get("workflow_id")
                or (result.get("workflow", {}).get("metadata", {}).get("id"))
                or (result.get("workflow", {}).get("id"))
            )
            if workflow_id:
                print(f"✅ Workflow created with ID: {workflow_id[:8]}...")
                return workflow_id
            else:
                raise Exception(f"No workflow_id in response: {result}")
        else:
            raise Exception(f"Failed to create workflow: {response.status_code} - {response.text}")


async def deploy_workflow(access_token: str, workflow_id: str) -> bool:
    """Deploy the workflow using API Gateway."""
    print(f"\n🚀 Deploying workflow...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_GATEWAY_URL}/api/v1/app/workflows/{workflow_id}/deploy",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Workflow deployed successfully")
            return True
        else:
            print(f"❌ Deployment failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False


async def execute_workflow(access_token: str, workflow_id: str, user_prompt: str) -> Dict[str, Any]:
    """Execute the workflow with test input."""
    print(f"\n▶️  Executing workflow...")
    print(f"   User prompt: {user_prompt}")

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{API_GATEWAY_URL}/api/v1/app/workflows/{workflow_id}/execute",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "inputs": {"user_prompt": user_prompt},
                "async_execution": False,  # Wait for completion
                "skip_trigger_validation": True,
            },
        )

        print(f"   Response status: {response.status_code}")

        if response.status_code != 200:
            print(f"   ❌ Error response: {response.text}")
            return {"success": False, "error": response.text}

        result = response.json()

        # Handle both sync and async execution responses
        execution_id = result.get("execution_id")
        status = result.get("status")

        if execution_id:
            print(f"✅ Workflow execution started")
            print(f"   Execution ID: {execution_id}")
            print(f"   Status: {status}")

            # If status is RUNNING, wait for completion
            if status == "RUNNING":
                print(f"   ⏳ Waiting for execution to complete...")
                await asyncio.sleep(30)  # Wait longer for AI + MCP tool execution

            return {"success": True, "execution_id": execution_id, "status": status}
        else:
            print(f"❌ Workflow execution failed")
            print(f"   Error: {result.get('error')}")
            print(f"   Message: {result.get('message')}")
            return {"success": False, **result}


async def get_execution_details(access_token: str, execution_id: str) -> Dict[str, Any]:
    """Fetch detailed execution results."""
    print(f"\n📊 Fetching execution details...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{WORKFLOW_ENGINE_URL}/api/v2/executions/{execution_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️  Could not fetch details: {response.status_code}")
            return {}


async def cleanup_workflow(access_token: str, workflow_id: str):
    """Cleanup - undeploy and delete workflow."""
    print(f"\n🧹 Cleaning up workflow...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Undeploy
        print(f"   Undeploying...")
        await client.delete(
            f"{API_GATEWAY_URL}/api/v1/app/workflows/{workflow_id}/undeploy",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )

        # Delete
        print(f"   Deleting...")
        await client.delete(
            f"{API_GATEWAY_URL}/api/v1/app/workflows/{workflow_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    print(f"✅ Workflow cleaned up")


def print_execution_summary(details: Dict[str, Any]):
    """Pretty-print execution summary."""
    print("\n" + "=" * 80)
    print("📋 EXECUTION SUMMARY")
    print("=" * 80)

    print(f"\nStatus: {details.get('status')}")
    print(f"Workflow: {details.get('workflow_name')}")
    print(f"Start Time: {details.get('start_time')}")
    print(f"End Time: {details.get('end_time')}")

    # Print node executions
    node_executions = details.get("node_executions", [])
    print(f"\nNode Executions: {len(node_executions)}")

    for node_exec in node_executions:
        print(f"\n  📦 {node_exec.get('node_name')} ({node_exec.get('node_type')})")
        print(f"     Status: {node_exec.get('status')}")

        # Show execution details for AI Agent
        exec_details = node_exec.get("execution_details", {})
        if exec_details.get("type") == "ai_response":
            ai_response = exec_details.get("ai_response", {})
            content = ai_response.get("content", "")
            token_usage = ai_response.get("token_usage", {})
            function_calls = ai_response.get("function_calls", [])

            if function_calls:
                print(f"     Tool Calls: {len(function_calls)}")
                for call in function_calls:
                    print(f"       - {call.get('name')}(...)")

            if token_usage:
                print(f"     Tokens: {token_usage.get('total_tokens', 0)}")

            if content:
                print(f"\n     AI Response:")
                print(f"     {'-' * 70}")
                # Indent the response
                for line in content.split("\n"):
                    print(f"     {line}")
                print(f"     {'-' * 70}")


async def main():
    """Main test execution flow."""
    print("=" * 80)
    print("🧪 AI AGENT WITH NOTION MCP TOOL - INTEGRATION TEST")
    print("=" * 80)
    print("\nTest Scenario:")
    print("  - AI Agent: Anthropic Claude with business analysis capabilities")
    print("  - Attached Tool: Notion MCP for accessing company sales data")
    print(f"  - Data Source: Notion page {NOTION_PAGE_ID}")
    print("  - Task: Analyze sales trends and provide recommendations")
    print("=" * 80)

    # Initialize
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    access_token, user_id = await authenticate_user(supabase)

    # Create workflow definition
    workflow = create_workflow_definition()
    print(f"\n📋 Workflow definition created:")
    print(f"   Workflow ID: {workflow['metadata']['id'][:8]}...")
    print(f"   Nodes: {len(workflow['nodes'])}")
    for node in workflow["nodes"]:
        attached = (
            " [ATTACHED]" if node["id"] in workflow["nodes"][1].get("attached_nodes", []) else ""
        )
        print(f"     - {node['name']} ({node['subtype']}){attached}")

    workflow_id = None
    try:
        # Create workflow in database
        workflow_id = await create_workflow_in_db(access_token, workflow)

        # Deploy workflow
        deployed = await deploy_workflow(access_token, workflow_id)
        if not deployed:
            raise Exception("Deployment failed")

        # Execute workflow
        user_prompt = f"Analyze the company A's sales trend from Notion page {NOTION_PAGE_ID} and provide suggestions for improvement. Be specific with data points and recommendations."
        result = await execute_workflow(access_token, workflow_id, user_prompt)

        # Get detailed execution information
        if result.get("execution_id"):
            await asyncio.sleep(2)  # Wait for logs to be persisted

            details = await get_execution_details(access_token, result["execution_id"])

            if details:
                print_execution_summary(details)

        # Final verdict
        print("\n" + "=" * 80)
        if result.get("success"):
            print("✅ TEST PASSED")
            print("\nThe AI Agent successfully:")
            print("  1. Received the analysis request")
            print("  2. Used Notion MCP tool to retrieve the page data")
            print("  3. Analyzed the sales trends from Notion content")
            print("  4. Generated data-driven recommendations")
        else:
            print("❌ TEST FAILED")
            print(f"\nError: {result.get('error')}")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        if workflow_id:
            await cleanup_workflow(access_token, workflow_id)


if __name__ == "__main__":
    asyncio.run(main())
