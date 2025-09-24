#!/usr/bin/env python3
"""
Integration test for manual workflow trigger
"""
import json
import os
import sys

import requests

# Configuration
SUPABASE_URL = "https://mkrczzgjeduruwxpanbj.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_GDldaQkfc6tfJ2aEOx_H3w_rq2Tc5G3"
TEST_USER_EMAIL = "daming.lu@starmates.ai"
TEST_USER_PASSWORD = "test.1234!"
WORKFLOW_ID = "e30c8316-c4fc-41ee-b3b8-36958d5ccdfc"

API_GATEWAY_URL = "http://localhost:8000/api/v1"
WORKFLOW_ENGINE_URL = "http://localhost:8002"


def get_jwt_token():
    """Get JWT token from Supabase"""
    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("access_token")
    except Exception as e:
        print(f"❌ Error getting JWT token: {e}")
        return None


def test_workflow_engine_direct():
    """Test workflow engine execute endpoint directly"""
    print("🔧 Testing Workflow Engine Execute Endpoint Directly...")

    jwt_token = get_jwt_token()
    if not jwt_token:
        print("❌ Could not get JWT token")
        return False

    print(f"✅ JWT token obtained: {jwt_token[:20]}...")

    # Test direct execution
    payload = {
        "workflow_id": WORKFLOW_ID,
        "trigger_data": {
            "trigger_type": "manual_trigger",
            "execution_id": "exec_integration_test_123",
            "triggered_at": "2025-09-14T08:00:00.000Z",
        },
        "user_id": "7ba36345-a2bb-4ec9-a001-bb46d79d629d",
    }

    try:
        response = requests.post(
            f"{WORKFLOW_ENGINE_URL}/v1/workflows/{WORKFLOW_ID}/execute",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {jwt_token}"},
            json=payload,
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            execution_id = data.get("execution_id")
            print(f"✅ Workflow execution started successfully!")
            print(f"   Execution ID: {execution_id}")
            print(f"   Status: {data.get('status')}")
            print(f"   Message: {data.get('message')}")
            return True
        else:
            print(f"❌ Workflow engine execution failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error testing workflow engine: {e}")
        return False


def test_manual_trigger_via_api_gateway():
    """Test manual invocation via API Gateway with parameters"""
    print("\n🌐 Testing Manual Invocation via API Gateway...")

    jwt_token = get_jwt_token()
    if not jwt_token:
        print("❌ Could not get JWT token")
        return False

    # First, try to get the workflow to find trigger nodes
    try:
        workflow_response = requests.get(
            f"{API_GATEWAY_URL}/app/workflows/{WORKFLOW_ID}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        if workflow_response.status_code != 200:
            print(f"❌ Could not get workflow: {workflow_response.status_code}")
            return False

        workflow_data = workflow_response.json()
        workflow = workflow_data.get("workflow")
        if not workflow:
            print("❌ No workflow data returned")
            return False

        # Find the first trigger node (likely slack_trigger_1)
        trigger_node_id = None
        for node in workflow.get("nodes", []):
            if node.get("type") == "TRIGGER" and node.get("subtype") in ["SLACK", "slack"]:
                trigger_node_id = node.get("id")
                break

        if not trigger_node_id:
            print("❌ No trigger node found in workflow")
            return False

        print(f"✅ Found trigger node: {trigger_node_id}")

    except Exception as e:
        print(f"❌ Error getting workflow: {e}")
        return False

    # Now test manual invocation with parameters
    payload = {
        "parameters": {
            "message": "Integration test message",
            "channel_name": "general",
            "user_id": "U7TESTUSER",
            "event_type": "message",
        },
        "description": "Integration test invocation",
    }

    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/app/workflows/{WORKFLOW_ID}/triggers/{trigger_node_id}/manual-invoke",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {jwt_token}"},
            json=payload,
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Manual invocation successful!")
            print(f"   Execution ID: {data.get('execution_id')}")
            print(f"   Status: {data.get('status')}")
            return True
        else:
            print(f"❌ Manual invocation failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error testing manual invocation: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Starting Integration Tests...")
    print("=" * 50)

    # Test 1: Direct workflow engine
    success1 = test_workflow_engine_direct()

    # Test 2: Via API Gateway
    success2 = test_manual_trigger_via_api_gateway()

    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   Workflow Engine Direct: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"   Manual Invocation via API: {'✅ PASS' if success2 else '❌ FAIL'}")

    if success1 and success2:
        print("\n🎉 All integration tests PASSED!")
        sys.exit(0)
    else:
        print("\n💥 Some integration tests FAILED!")
        sys.exit(1)
