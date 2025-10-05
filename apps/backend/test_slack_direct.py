"""
Direct test script for Slack External Action using SDK.

Tests all supported Slack operations with real Slack API and validates
that output_data follows the node spec format from SLACK.py.

Usage:
    SLACK_ACCESS_TOKEN="xoxb-..." python test_slack_direct.py
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus, NodeExecutionResult, TriggerInfo
from shared.models.workflow import Node
from workflow_engine_v2.core.context import NodeExecutionContext
from workflow_engine_v2.runners.external_actions.slack_external_action import SlackExternalAction

# ============================================================================
# Configuration
# ============================================================================

SLACK_ACCESS_TOKEN = os.getenv("SLACK_ACCESS_TOKEN", "")
TEST_CHANNEL = "#webhook-test"  # Existing channel for testing
TEST_USER_ID = "U08492AUZP0"  # Replace with a real user ID from your workspace


# ============================================================================
# Output Validation (per node spec)
# ============================================================================


def validate_node_spec_output(output_data: dict, operation: str) -> bool:
    """
    Validate that output_data follows the SLACK.py node spec format.

    Required output_params per spec:
    - success: boolean
    - message_ts: string (Slack message timestamp)
    - channel_id: string
    - response_data: object (parsed Slack API response)
    - error_message: string
    - api_response: object (raw Slack API response)
    """
    required_fields = {
        "success": bool,
        "message_ts": str,
        "channel_id": str,
        "response_data": dict,
        "error_message": str,
        "api_response": dict,
    }

    print(f"\n📋 Validating output for operation: {operation}")
    all_valid = True

    for field, expected_type in required_fields.items():
        if field not in output_data:
            print(f"  ❌ Missing field: {field}")
            all_valid = False
        elif not isinstance(output_data[field], expected_type):
            print(
                f"  ❌ Wrong type for {field}: expected {expected_type.__name__}, "
                f"got {type(output_data[field]).__name__}"
            )
            all_valid = False
        else:
            print(f"  ✅ {field}: {expected_type.__name__}")

    if all_valid:
        print("  ✅ All output fields valid!")
    else:
        print("  ❌ Output validation failed!")

    return all_valid


# ============================================================================
# Test Helper
# ============================================================================


async def run_slack_test(
    test_name: str,
    operation: str,
    input_data: Dict[str, Any],
    configurations: Dict[str, Any] = None,
) -> NodeExecutionResult:
    """Run a single Slack operation test with validation."""
    print(f"\n{'='*80}")
    print(f"🧪 TEST: {test_name}")
    print(f"{'='*80}")
    print(f"Operation: {operation}")
    print(f"Input Data: {input_data}")

    # Create test action instance
    action = SlackExternalAction()

    # Override get_oauth_token to return our test token
    async def mock_get_oauth_token(context):
        return SLACK_ACCESS_TOKEN

    action.get_oauth_token = mock_get_oauth_token

    # Create test node with configurations
    default_configs = {
        "action_type": operation,
        "channel": TEST_CHANNEL,
        "bot_token": SLACK_ACCESS_TOKEN,
        "use_oauth": False,
    }
    if configurations:
        default_configs.update(configurations)

    node = Node(
        id=f"test-slack-{operation}",
        name=f"Test_Slack_{operation.replace('_', '-')}",  # No spaces allowed
        type="EXTERNAL_ACTION",
        subtype="SLACK",
        description=f"Test node for Slack {operation} operation",
        configurations=default_configs,
    )

    # Create execution context
    trigger = TriggerInfo(
        trigger_type="MANUAL",
        trigger_subtype="MANUAL",
        trigger_data={"test_operation": operation},
        timestamp=int(time.time() * 1000),
    )

    context = NodeExecutionContext(
        node=node,
        input_data=input_data,
        trigger=trigger,
        metadata={
            "execution_id": f"test-exec-slack-{operation}",
            "user_id": "test-user-001",
        },
    )

    # Execute the operation
    result = await action.execute(context)

    # Display results
    print(f"\n📊 Result Status: {result.status.value}")
    print(f"Output Data Keys: {list(result.output_data.keys())}")

    if result.status == ExecutionStatus.SUCCESS:
        print(f"✅ Operation succeeded!")
        print(f"Message TS: {result.output_data.get('message_ts')}")
        print(f"Channel ID: {result.output_data.get('channel_id')}")
        print(f"Response Data: {result.output_data.get('response_data')}")
    else:
        print(f"❌ Operation failed!")
        print(f"Error: {result.error_message}")
        if result.error_details:
            print(f"Error Details: {result.error_details}")

    # Validate output format
    output_valid = validate_node_spec_output(result.output_data, operation)
    if not output_valid:
        print("\n⚠️  WARNING: Output does not match node spec!")

    return result


# ============================================================================
# Test Cases
# ============================================================================


async def test_send_message():
    """Test 1: Send a simple text message."""
    result = await run_slack_test(
        test_name="Send Simple Text Message",
        operation="send_message",
        input_data={
            "message": f"🧪 SDK Test Message - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nTesting Slack SDK integration with node spec compliance.",
        },
    )
    return result


async def test_send_message_with_blocks():
    """Test 2: Send a rich message using Block Kit."""
    result = await run_slack_test(
        test_name="Send Rich Message with Blocks",
        operation="send_message",
        input_data={
            "message": "Test Alert",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚀 Workflow Test Alert",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Status:* Running\n*Time:* "
                        + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": "*Test Type:*\nSDK Integration"},
                        {"type": "mrkdwn", "text": "*Node Spec:*\nCompliant ✅"},
                    ],
                },
            ],
        },
    )
    return result


# Skipped: requires channels:read scope
# async def test_get_channel_info():
#     """Test 3: Get channel information."""
#     result = await run_slack_test(
#         test_name="Get Channel Info",
#         operation="get_channel_info",
#         input_data={
#             "channel_override": TEST_CHANNEL,
#         },
#     )
#     return result


# Skipped: requires users:read scope
# async def test_get_user_info():
#     """Test 4: Get user information."""
#     result = await run_slack_test(
#         test_name="Get User Info",
#         operation="get_user_info",
#         input_data={
#             "user_id": TEST_USER_ID,
#         },
#     )
#     return result


async def test_update_message():
    """Test 5: Update an existing message (requires message_ts from previous send)."""
    # First, send a message to get a message_ts
    send_result = await run_slack_test(
        test_name="Send Message (for Update Test)",
        operation="send_message",
        input_data={
            "message": "Original message - will be updated in 3 seconds...",
        },
    )

    if send_result.status != ExecutionStatus.SUCCESS:
        print("❌ Cannot test update_message - send_message failed")
        return send_result

    message_ts = send_result.output_data.get("message_ts")
    channel_id = send_result.output_data.get("channel_id")
    print(f"\n⏳ Waiting 3 seconds before updating message {message_ts}...")
    await asyncio.sleep(3)

    # Update the message with explicit channel_id
    result = await run_slack_test(
        test_name="Update Message",
        operation="update_message",
        input_data={
            "message_ts": message_ts,
            "channel": channel_id,  # Use actual channel ID
            "message": f"✅ UPDATED MESSAGE at {datetime.now().strftime('%H:%M:%S')} - SDK test successful!",
        },
    )
    return result


async def test_delete_message():
    """Test 6: Delete a message (requires message_ts from previous send)."""
    # First, send a message to get a message_ts
    send_result = await run_slack_test(
        test_name="Send Message (for Delete Test)",
        operation="send_message",
        input_data={
            "message": "This message will be deleted in 3 seconds...",
        },
    )

    if send_result.status != ExecutionStatus.SUCCESS:
        print("❌ Cannot test delete_message - send_message failed")
        return send_result

    message_ts = send_result.output_data.get("message_ts")
    channel_id = send_result.output_data.get("channel_id")
    print(f"\n⏳ Waiting 3 seconds before deleting message {message_ts}...")
    await asyncio.sleep(3)

    # Delete the message with explicit channel_id
    result = await run_slack_test(
        test_name="Delete Message",
        operation="delete_message",
        input_data={
            "message_ts": message_ts,
            "channel": channel_id,  # Use actual channel ID
        },
    )
    return result


async def test_create_channel():
    """Test 7: Create a new Slack channel."""
    channel_name = f"test-sdk-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    result = await run_slack_test(
        test_name="Create Channel",
        operation="create_channel",
        input_data={
            "channel_name": channel_name,
            "is_private": False,
        },
    )
    return result


# Skipped: requires channels:manage scope
# async def test_set_channel_topic():
#     """Test 8: Set channel topic."""
#     result = await run_slack_test(
#         test_name="Set Channel Topic",
#         operation="set_channel_topic",
#         input_data={
#             "topic": f"SDK Test Topic - Updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
#         },
#     )
#     return result


# Skipped: requires channels:manage scope
# async def test_invite_users():
#     """Test 9: Invite users to a channel."""
#     result = await run_slack_test(
#         test_name="Invite Users to Channel",
#         operation="invite_users",
#         input_data={
#             "user_ids": [TEST_USER_ID],
#         },
#     )
#     return result


async def test_send_thread_reply():
    """Test 10: Send a message as a thread reply."""
    # First, send a parent message
    parent_result = await run_slack_test(
        test_name="Send Parent Message (for Thread Test)",
        operation="send_message",
        input_data={
            "message": "🧵 Parent message - thread replies will follow",
        },
    )

    if parent_result.status != ExecutionStatus.SUCCESS:
        print("❌ Cannot test thread reply - parent message failed")
        return parent_result

    thread_ts = parent_result.output_data.get("message_ts")
    print(f"\n⏳ Waiting 2 seconds before sending thread reply...")
    await asyncio.sleep(2)

    # Send thread reply
    result = await run_slack_test(
        test_name="Send Thread Reply",
        operation="send_message",
        input_data={
            "message": "💬 This is a thread reply!",
        },
        configurations={
            "thread_ts": thread_ts,
        },
    )
    return result


# ============================================================================
# Main Test Runner
# ============================================================================


async def main():
    """Run all Slack operation tests."""
    print("=" * 80)
    print("🚀 Slack External Action SDK Test Suite")
    print("=" * 80)
    print(f"Test Channel: {TEST_CHANNEL}")
    print(f"Test User ID: {TEST_USER_ID}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)

    # Store results for summary
    results = {}

    # Run tests sequentially
    # Note: Some tests are skipped due to missing OAuth scopes:
    # - get_channel_info, get_user_info: require channels:read, users:read
    # - set_channel_topic, invite_users: require channels:manage
    test_functions = [
        ("Send Message", test_send_message),
        ("Send Blocks", test_send_message_with_blocks),
        ("Update Message", test_update_message),
        ("Delete Message", test_delete_message),
        ("Send Thread Reply", test_send_thread_reply),
    ]

    for test_name, test_func in test_functions:
        try:
            result = await test_func()
            results[test_name] = {
                "status": result.status.value,
                "success": result.status == ExecutionStatus.SUCCESS,
            }
        except Exception as e:
            print(f"\n❌ Test '{test_name}' raised exception: {e}")
            results[test_name] = {"status": "EXCEPTION", "success": False, "error": str(e)}

        # Small delay between tests
        await asyncio.sleep(1)

    # Print summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    success_count = sum(1 for r in results.values() if r.get("success"))
    total_count = len(results)

    for test_name, result in results.items():
        status_emoji = "✅" if result.get("success") else "❌"
        print(f"{status_emoji} {test_name}: {result['status']}")

    print("=" * 80)
    print(f"Total: {success_count}/{total_count} tests passed")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
