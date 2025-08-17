#!/usr/bin/env python3
"""
Test script for workflow_scheduler notification functionality
Tests all trigger types with mock data
"""

import asyncio
import logging
import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from shared.models.trigger import TriggerType
from workflow_scheduler.services.notification_service import NotificationService
from workflow_scheduler.triggers.cron_trigger import CronTrigger
from workflow_scheduler.triggers.manual_trigger import ManualTrigger

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_notification_service():
    """Test notification service directly"""
    print("🧪 Testing Notification Service...")

    notification_service = NotificationService()

    # Test different trigger types
    test_cases = [
        {
            "workflow_id": "test-workflow-001",
            "trigger_type": TriggerType.MANUAL.value,
            "trigger_data": {
                "user_id": "test_user",
                "confirmation": True,
                "triggered_at": "2025-01-28T12:00:00Z",
            },
        },
        {
            "workflow_id": "daily-report-workflow",
            "trigger_type": TriggerType.CRON.value,
            "trigger_data": {
                "cron_expression": "0 9 * * MON-FRI",
                "timezone": "America/New_York",
                "scheduled_time": "2025-01-28T09:00:00-05:00",
            },
        },
        {
            "workflow_id": "github-ci-workflow",
            "trigger_type": TriggerType.GITHUB.value,
            "trigger_data": {
                "event_type": "pull_request",
                "repository": {"full_name": "company/awesome-project"},
                "sender": {"login": "developer123"},
                "action": "opened",
                "pull_request": {"number": 42, "title": "Add new feature"},
            },
        },
        {
            "workflow_id": "webhook-integration",
            "trigger_type": TriggerType.WEBHOOK.value,
            "trigger_data": {
                "method": "POST",
                "path": "/webhook/webhook-integration",
                "remote_addr": "192.168.1.100",
                "headers": {"Content-Type": "application/json"},
                "body": {"event": "deployment", "status": "success"},
            },
        },
        {
            "workflow_id": "email-processor",
            "trigger_type": TriggerType.EMAIL.value,
            "trigger_data": {
                "sender": "customer@example.com",
                "subject": "Support Request: Login Issues",
                "body_text": "I'm having trouble logging into my account...",
                "attachments": [{"filename": "screenshot.png", "size": 1024}],
            },
        },
    ]

    for i, test_case in enumerate(test_cases):
        print(f"\n📧 Test {i+1}: {test_case['trigger_type']} trigger")

        try:
            result = await notification_service.send_trigger_notification(
                workflow_id=test_case["workflow_id"],
                trigger_type=test_case["trigger_type"],
                trigger_data=test_case["trigger_data"],
            )

            print(f"   ✅ Status: {result.status}")
            print(f"   📝 Message: {result.message}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Small delay between tests
        await asyncio.sleep(1)

    # Test health check
    print(f"\n🩺 Health Check:")
    health = await notification_service.health_check()
    for key, value in health.items():
        print(f"   {key}: {value}")


async def test_manual_trigger():
    """Test manual trigger end-to-end"""
    print(f"\n🔧 Testing Manual Trigger...")

    config = {"require_confirmation": True, "enabled": True}

    trigger = ManualTrigger("manual-test-workflow", config)

    try:
        # Start trigger
        started = await trigger.start()
        print(f"   Trigger started: {started}")

        # Execute manual trigger
        result = await trigger.trigger_manual("test_user", confirmation=True)
        print(f"   ✅ Status: {result.status}")
        print(f"   📝 Message: {result.message}")

        # Stop trigger
        stopped = await trigger.stop()
        print(f"   Trigger stopped: {stopped}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    finally:
        await trigger.cleanup()


async def main():
    """Run all tests"""
    print("🚀 Starting Workflow Scheduler Notification Tests")
    print("=" * 60)

    try:
        await test_notification_service()
        await test_manual_trigger()

        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("\n💡 Tips:")
        print("   - Configure SMTP credentials in .env to enable email sending")
        print("   - Check logs for detailed information")
        print("   - Email will be sent to z1771485029@gmail.com if SMTP is configured")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
