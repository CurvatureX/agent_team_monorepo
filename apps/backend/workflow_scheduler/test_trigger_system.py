#!/usr/bin/env python3
"""
Test script for the trigger indexing and event routing system

This script tests the core functionality of the workflow scheduler
trigger system including:
- Trigger indexing
- Event routing
- Testing mode notifications
"""

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the backend directory to the Python path so we can import our modules
sys.path.insert(0, "/Users/jingweizhang/Workspace/agent_team_monorepo/apps/backend")

from shared.models.node_enums import NodeType
from shared.models.trigger import TriggerSpec, TriggerType
from workflow_scheduler.services.event_router import EventRouter
from workflow_scheduler.services.trigger_index_manager import TriggerIndexManager


async def test_trigger_indexing():
    """Test trigger indexing functionality"""
    logger.info("🧪 Testing trigger indexing system...")

    # Create test workflow and trigger specs
    workflow_id = str(uuid.uuid4())

    trigger_specs = [
        TriggerSpec(
            node_type=NodeType.TRIGGER.value,
            subtype=TriggerType.GITHUB,
            parameters={
                "repository": "test-org/test-repo",
                "event_config": {
                    "push": {"branches": ["main", "develop"]},
                    "pull_request": {"actions": ["opened", "synchronize", "closed"]},
                },
                "github_app_installation_id": "12345",
            },
            enabled=True,
        ),
        TriggerSpec(
            node_type=NodeType.TRIGGER.value,
            subtype=TriggerType.WEBHOOK,
            parameters={"path": "/webhooks/test", "allowed_methods": ["POST"]},
            enabled=True,
        ),
        TriggerSpec(
            node_type=NodeType.TRIGGER.value,
            subtype=TriggerType.CRON,
            parameters={"cron_expression": "0 9 * * MON-FRI", "timezone": "UTC"},
            enabled=True,
        ),
    ]

    # Initialize trigger index manager
    trigger_index_manager = TriggerIndexManager()

    try:
        # Test 1: Register workflow triggers
        logger.info("📝 Test 1: Registering workflow triggers...")
        success = await trigger_index_manager.register_workflow_triggers(
            workflow_id, trigger_specs, deployment_status="active"
        )
        if success:
            logger.info("✅ Trigger registration successful")
        else:
            logger.error("❌ Trigger registration failed")
            return False

        # Test 2: Get workflow triggers
        logger.info("📝 Test 2: Retrieving workflow triggers...")
        indexed_triggers = await trigger_index_manager.get_workflow_triggers(workflow_id)
        logger.info(f"✅ Retrieved {len(indexed_triggers)} triggers")
        for trigger in indexed_triggers:
            logger.info(f"   - {trigger['trigger_type']}: {trigger['deployment_status']}")

        # Test 3: Update trigger status
        logger.info("📝 Test 3: Updating trigger status to paused...")
        success = await trigger_index_manager.update_trigger_status(workflow_id, "paused")
        if success:
            logger.info("✅ Trigger status update successful")
        else:
            logger.error("❌ Trigger status update failed")
            return False

        # Test 4: Get index statistics
        logger.info("📝 Test 4: Getting index statistics...")
        stats = await trigger_index_manager.get_index_statistics()
        logger.info(f"✅ Index statistics: {json.dumps(stats, indent=2)}")

        return True

    except Exception as e:
        logger.error(f"❌ Trigger indexing test failed: {e}", exc_info=True)
        return False

    finally:
        # Cleanup: Remove test triggers
        logger.info("🧹 Cleaning up test triggers...")
        await trigger_index_manager.unregister_workflow_triggers(workflow_id)


async def test_event_routing():
    """Test event routing functionality"""
    logger.info("🧪 Testing event routing system...")

    # Initialize event router
    event_router = EventRouter()

    try:
        # Test 1: GitHub event routing
        logger.info("📝 Test 1: Testing GitHub event routing...")
        github_payload = {
            "repository": {"full_name": "test-org/test-repo", "id": 123456789},
            "installation": {"id": 12345},
            "sender": {"login": "testuser"},
            "ref": "refs/heads/main",
            "commits": [
                {
                    "added": ["src/new_file.py"],
                    "modified": ["src/existing_file.py"],
                    "removed": [],
                }
            ],
        }

        github_matches = await event_router.route_github_event(
            event_type="push", delivery_id="test-delivery-123", payload=github_payload
        )

        logger.info(f"✅ GitHub routing found {len(github_matches)} matches")
        for match in github_matches:
            logger.info(f"   - Workflow: {match['workflow_id']}")

        # Test 2: Webhook event routing
        logger.info("📝 Test 2: Testing webhook event routing...")
        webhook_matches = await event_router.route_webhook_event(
            path="/webhooks/test",
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "TestAgent/1.0"},
            payload={"test": "data"},
            remote_addr="127.0.0.1",
        )

        logger.info(f"✅ Webhook routing found {len(webhook_matches)} matches")
        for match in webhook_matches:
            logger.info(f"   - Workflow: {match['workflow_id']}")

        # Test 3: Cron event routing
        logger.info("📝 Test 3: Testing cron event routing...")
        cron_matches = await event_router.route_cron_event(
            cron_expression="0 9 * * MON-FRI", timezone="UTC"
        )

        logger.info(f"✅ Cron routing found {len(cron_matches)} matches")
        for match in cron_matches:
            logger.info(f"   - Workflow: {match['workflow_id']}")

        # Test 4: Get routing statistics
        logger.info("📝 Test 4: Getting routing statistics...")
        routing_stats = await event_router.get_routing_stats()
        logger.info(f"✅ Routing statistics: {json.dumps(routing_stats, indent=2)}")

        return True

    except Exception as e:
        logger.error(f"❌ Event routing test failed: {e}", exc_info=True)
        return False


async def test_health_checks():
    """Test health checks for all components"""
    logger.info("🧪 Testing component health checks...")

    try:
        # Test trigger index manager health
        trigger_index_manager = TriggerIndexManager()
        health = await trigger_index_manager.health_check()
        logger.info(f"📊 TriggerIndexManager health: {health}")

        # Test event router health
        event_router = EventRouter()
        health = await event_router.health_check()
        logger.info(f"📊 EventRouter health: {health}")

        return True

    except Exception as e:
        logger.error(f"❌ Health check test failed: {e}", exc_info=True)
        return False


async def main():
    """Run all tests"""
    logger.info("🚀 Starting workflow scheduler trigger system tests...")

    start_time = datetime.now()

    # Run test suite
    tests = [
        ("Trigger Indexing", test_trigger_indexing),
        ("Event Routing", test_event_routing),
        ("Health Checks", test_health_checks),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        logger.info(f"\n🏃 Running {test_name} test...")
        try:
            success = await test_func()
            if success:
                logger.info(f"✅ {test_name} test PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} test FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} test FAILED with exception: {e}")
            failed += 1

    # Summary
    duration = datetime.now() - start_time
    logger.info(f"\n📊 Test Summary:")
    logger.info(f"   ✅ Passed: {passed}")
    logger.info(f"   ❌ Failed: {failed}")
    logger.info(f"   ⏱️  Duration: {duration.total_seconds():.2f}s")

    if failed == 0:
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.error(f"💥 {failed} test(s) failed!")
        return False


if __name__ == "__main__":
    import asyncio

    success = asyncio.run(main())
    sys.exit(0 if success else 1)
