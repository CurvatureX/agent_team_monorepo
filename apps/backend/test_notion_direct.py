"""
Direct test of AI-powered Notion External Action Node.

This test directly imports and executes the Notion External Action runner
without relying on deployed services.
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

# Add backend to path
sys.path.insert(0, "/Users/jingweizhang/Workspace/agent_team_monorepo/apps/backend")

from shared.models import TriggerInfo
from shared.models.workflow import Node
from workflow_engine_v2.core.context import NodeExecutionContext
from workflow_engine_v2.runners.external_actions.notion_external_action import NotionExternalAction

# Notion credentials
NOTION_TOKEN = "ntn_Y29841984278cT45JYtg0JKVUGiJ4m8Yas96xNCmvuI43v"
NOTION_PAGE_ID = "27f0b1df411b80acaa54c4cba158a1f9"

# AI API keys (from environment)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


async def test_ai_notion_action():
    """Test the AI-powered Notion External Action directly."""
    print("=" * 60)
    print("🧪 Direct Test: AI-Powered Notion External Action")
    print("=" * 60)

    # Create node with configurations
    node = Node(
        id="notion_ai_node",
        name="AI_Notion_Action",
        description="AI-powered Notion operations",
        type="EXTERNAL_ACTION",
        subtype="NOTION",
        configurations={
            "notion_token": NOTION_TOKEN,
            "page_config": {
                "parent": {},
                "properties": {},
                "children": [],
                "icon": {},
                "cover": {},
            },
        },
        input_params={
            "instruction": "",
            "context": {},
        },
        output_params={
            "success": False,
            "resource_id": "",
            "resource_url": "",
            "error_message": "",
        },
    )

    # Create trigger info (manual trigger)
    import time

    trigger = TriggerInfo(
        trigger_type="MANUAL",
        trigger_subtype="MANUAL",
        trigger_data={
            "instruction": "Clean up the documen",
            "page_id": NOTION_PAGE_ID,
        },
        timestamp=int(time.time() * 1000),  # Current timestamp in milliseconds
    )

    # Create execution context
    context = NodeExecutionContext(
        node=node,
        input_data={
            "instruction": "Delete all content blocks from this page to clean it up completely",
            "context": {
                "page_id": NOTION_PAGE_ID,
            },
        },
        trigger=trigger,
        metadata={
            "execution_id": "test-exec-123",
            "user_id": "test-user-123",
        },
    )

    # Initialize the Notion External Action runner
    print("\n📝 Initializing Notion External Action runner...")
    action = NotionExternalAction()

    # Override get_oauth_token to return our test token directly
    async def mock_get_oauth_token(ctx):
        return NOTION_TOKEN

    action.get_oauth_token = mock_get_oauth_token

    # Set API keys for AI
    if ANTHROPIC_API_KEY:
        action._anthropic_api_key = ANTHROPIC_API_KEY
        print(f"✅ Anthropic API key configured: {ANTHROPIC_API_KEY[:20]}...")
    elif OPENAI_API_KEY:
        action._openai_api_key = OPENAI_API_KEY
        print(f"✅ OpenAI API key configured: {OPENAI_API_KEY[:20]}...")
    else:
        print("❌ No AI API key found! Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
        return

    print(f"✅ Notion token configured: {NOTION_TOKEN[:20]}...")

    # Execute the action
    print("\n🚀 Executing AI-powered Notion action...")
    print(f"   Instruction: {context.input_data['instruction'][:80]}...")
    print(f"   Page ID: {NOTION_PAGE_ID}")

    try:
        result = await action.execute(context)

        print("\n📊 Execution Result:")
        print(f"   Status: {result.status}")
        print(f"   Result type: {type(result)}")
        print(f"   Result attributes: {dir(result)}")

        # Get outputs (could be in output_data or outputs)
        print(f"   Has 'outputs' attr: {hasattr(result, 'outputs')}")
        print(f"   output_data: {result.output_data}")

        if hasattr(result, "outputs"):
            print(f"   outputs attr: {result.outputs}")
            outputs = result.outputs
        else:
            outputs = result.output_data

        print(f"   Outputs type: {type(outputs)}")
        print(
            f"   Success: {outputs.get('success', False) if isinstance(outputs, dict) else 'N/A'}"
        )

        print(f"\n📄 Full Outputs:")
        print(json.dumps(outputs, indent=4))

        if result.error_message:
            print(f"\n   Error: {result.error_message}")
            if result.error_details:
                print(f"   Error Details: {json.dumps(result.error_details, indent=4)}")

        # Print AI execution telemetry
        execution_metadata = outputs.get("execution_metadata", {})
        if "ai_execution" in execution_metadata:
            ai_exec = execution_metadata["ai_execution"]
            print(f"\n🤖 AI Execution Telemetry:")
            print(f"   Rounds Executed: {ai_exec.get('rounds_executed', 0)}")
            print(f"   Completed: {ai_exec.get('completed', False)}")

            if ai_exec.get("rounds"):
                print(f"\n   📋 Execution Rounds:")
                for round_data in ai_exec["rounds"]:
                    print(f"\n   Round {round_data.get('round_num')}:")
                    print(f"      Phase: {round_data.get('phase')}")
                    print(f"      Decision: {round_data.get('decision_text', '')[:100]}...")
                    print(f"      API Success: {round_data.get('api_success', False)}")
                    print(f"      Duration: {round_data.get('duration_ms', 0)}ms")

        # Print discovered resources
        if "discovered_resources" in execution_metadata:
            print(f"\n🔍 Discovered Resources:")
            print(json.dumps(execution_metadata["discovered_resources"], indent=4))

        # Print resource ID and URL
        if outputs.get("resource_id"):
            print(f"\n✅ Resource Created:")
            print(f"   ID: {outputs.get('resource_id')}")
            print(f"   URL: {outputs.get('resource_url', 'N/A')}")

        print("\n" + "=" * 60)
        print("✅ Test completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during execution: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Check for required API keys
    if not ANTHROPIC_API_KEY and not OPENAI_API_KEY:
        print("❌ ERROR: No AI API key found!")
        print("   Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable")
        sys.exit(1)

    # Run the test
    asyncio.run(test_ai_notion_action())
