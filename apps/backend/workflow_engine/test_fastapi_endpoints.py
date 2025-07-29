#!/usr/bin/env python3
"""
Test script for FastAPI endpoints.
Tests the migrated workflow_engine FastAPI endpoints locally.
"""

import asyncio
import json
import time
from typing import Any, Dict

import httpx

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_123"

# Sample workflow data
SAMPLE_WORKFLOW = {
    "name": "Test Email Processing Workflow",
    "description": "A test workflow for processing emails with AI",
    "nodes": [
        {
            "id": "trigger_1",
            "name": "Email Trigger",
            "type": "trigger",
            "subtype": "email",
            "position": {"x": 100, "y": 100},
            "parameters": {"trigger_type": "email", "email_filter": "*.@company.com"},
            "disabled": False,
            "on_error": "continue",
        },
        {
            "id": "ai_agent_1",
            "name": "AI Email Analyzer",
            "type": "ai_agent",
            "subtype": "text_analysis",
            "position": {"x": 300, "y": 100},
            "parameters": {
                "agent_type": "text_analyzer",
                "prompt": "Analyze this email for sentiment and extract key information",
                "model": "gpt-3.5-turbo",
            },
            "disabled": False,
            "on_error": "stop",
        },
        {
            "id": "action_1",
            "name": "Send Notification",
            "type": "action",
            "subtype": "notification",
            "position": {"x": 500, "y": 100},
            "parameters": {
                "action_type": "send_notification",
                "channel": "slack",
                "message": "Email processed successfully",
            },
            "disabled": False,
            "on_error": "continue",
        },
    ],
    "connections": {"connections": {"trigger_1": ["ai_agent_1"], "ai_agent_1": ["action_1"]}},
    "settings": {
        "timeout": 300,
        "max_retries": 3,
        "retry_delay": 5,
        "parallel_execution": False,
        "error_handling": "stop",
        "execution_mode": "sequential",
        "variables": {},
    },
    "static_data": {"company": "Test Company", "department": "IT"},
    "tags": ["email", "ai", "automation", "test"],
    "user_id": TEST_USER_ID,
    "session_id": "test_session_123",
}


class WorkflowEngineTestClient:
    """Test client for Workflow Engine FastAPI endpoints."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def test_health_check(self) -> Dict[str, Any]:
        """Test the health check endpoint."""
        print("🏥 Testing health check endpoint...")

        response = await self.client.get(f"{self.base_url}/health")
        result = {
            "status_code": response.status_code,
            "response": response.json() if response.status_code < 500 else response.text,
            "success": response.status_code == 200,
        }

        print(f"   Status: {response.status_code}")
        print(f"   Success: {result['success']}")

        return result

    async def test_root_endpoint(self) -> Dict[str, Any]:
        """Test the root endpoint."""
        print("🏠 Testing root endpoint...")

        response = await self.client.get(f"{self.base_url}/")
        result = {
            "status_code": response.status_code,
            "response": response.json(),
            "success": response.status_code == 200,
        }

        print(f"   Status: {response.status_code}")
        print(f"   Service: {result['response'].get('service', 'Unknown')}")

        return result

    async def test_create_workflow(self) -> Dict[str, Any]:
        """Test creating a workflow."""
        print("📝 Testing create workflow endpoint...")

        response = await self.client.post(f"{self.base_url}/v1/workflows", json=SAMPLE_WORKFLOW)

        result = {
            "status_code": response.status_code,
            "response": response.json() if response.status_code < 500 else response.text,
            "success": response.status_code in [200, 201],
        }

        print(f"   Status: {response.status_code}")
        print(f"   Success: {result['success']}")

        if result["success"] and isinstance(result["response"], dict):
            workflow_id = result["response"].get("workflow", {}).get("id")
            if workflow_id:
                print(f"   Created workflow ID: {workflow_id}")
                result["workflow_id"] = workflow_id

        return result

    async def test_get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Test getting a workflow."""
        print(f"📖 Testing get workflow endpoint for ID: {workflow_id}")

        response = await self.client.get(
            f"{self.base_url}/v1/workflows/{workflow_id}", params={"user_id": TEST_USER_ID}
        )

        result = {
            "status_code": response.status_code,
            "response": response.json() if response.status_code < 500 else response.text,
            "success": response.status_code == 200,
        }

        print(f"   Status: {response.status_code}")
        print(f"   Success: {result['success']}")

        if result["success"] and isinstance(result["response"], dict):
            found = result["response"].get("found", False)
            print(f"   Found: {found}")

        return result

    async def test_list_workflows(self) -> Dict[str, Any]:
        """Test listing workflows."""
        print("📋 Testing list workflows endpoint...")

        response = await self.client.get(
            f"{self.base_url}/v1/workflows",
            params={"user_id": TEST_USER_ID, "limit": 10, "offset": 0},
        )

        result = {
            "status_code": response.status_code,
            "response": response.json() if response.status_code < 500 else response.text,
            "success": response.status_code == 200,
        }

        print(f"   Status: {response.status_code}")
        print(f"   Success: {result['success']}")

        if result["success"] and isinstance(result["response"], dict):
            total_count = result["response"].get("total_count", 0)
            print(f"   Total workflows: {total_count}")

        return result

    async def test_validate_workflow(self) -> Dict[str, Any]:
        """Test workflow validation."""
        print("✅ Testing workflow validation endpoint...")

        # Create a simple workflow for validation
        validation_workflow = {
            "id": "test_validation",
            "name": "Validation Test Workflow",
            "description": "A simple workflow for testing validation",
            "nodes": SAMPLE_WORKFLOW["nodes"][:2],  # Just first 2 nodes
            "connections": {"connections": {"trigger_1": ["ai_agent_1"]}},
            "settings": SAMPLE_WORKFLOW["settings"],
            "static_data": {},
            "tags": ["validation", "test"],
            "active": True,
        }

        response = await self.client.post(
            f"{self.base_url}/v1/workflows/validate",
            json={"workflow": validation_workflow, "strict_mode": True},
        )

        result = {
            "status_code": response.status_code,
            "response": response.json() if response.status_code < 500 else response.text,
            "success": response.status_code == 200,
        }

        print(f"   Status: {response.status_code}")
        print(f"   Success: {result['success']}")

        if result["success"] and isinstance(result["response"], dict):
            validation_result = result["response"].get("validation_result", {})
            is_valid = validation_result.get("valid", False)
            errors = validation_result.get("errors", [])
            warnings = validation_result.get("warnings", [])

            print(f"   Valid: {is_valid}")
            print(f"   Errors: {len(errors)}")
            print(f"   Warnings: {len(warnings)}")

        return result

    async def test_execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Test workflow execution."""
        print(f"🚀 Testing workflow execution for ID: {workflow_id}")

        response = await self.client.post(
            f"{self.base_url}/v1/workflows/{workflow_id}/execute",
            json={
                "workflow_id": workflow_id,
                "user_id": TEST_USER_ID,
                "input_data": {
                    "email_content": "Test email content for processing",
                    "sender": "test@company.com",
                },
                "execution_options": {"priority": "normal", "timeout_override": 600},
            },
        )

        result = {
            "status_code": response.status_code,
            "response": response.json() if response.status_code < 500 else response.text,
            "success": response.status_code in [200, 201],
        }

        print(f"   Status: {response.status_code}")
        print(f"   Success: {result['success']}")

        if result["success"] and isinstance(result["response"], dict):
            execution_id = result["response"].get("execution_id")
            if execution_id:
                print(f"   Execution ID: {execution_id}")
                result["execution_id"] = execution_id

        return result

    async def test_get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Test getting execution status."""
        print(f"📊 Testing execution status for ID: {execution_id}")

        response = await self.client.get(
            f"{self.base_url}/v1/workflows/executions/{execution_id}/status",
            params={"user_id": TEST_USER_ID},
        )

        result = {
            "status_code": response.status_code,
            "response": response.json() if response.status_code < 500 else response.text,
            "success": response.status_code == 200,
        }

        print(f"   Status: {response.status_code}")
        print(f"   Success: {result['success']}")

        if result["success"] and isinstance(result["response"], dict):
            found = result["response"].get("found", False)
            if found:
                execution = result["response"].get("execution", {})
                status = execution.get("status", "unknown")
                progress = execution.get("progress_percentage", 0)
                print(f"   Execution Status: {status}")
                print(f"   Progress: {progress}%")

        return result


async def run_comprehensive_test():
    """Run comprehensive test suite for all endpoints."""
    print("🧪 Starting Workflow Engine FastAPI Tests")
    print("=" * 50)

    async with WorkflowEngineTestClient(BASE_URL) as client:
        test_results = {}

        try:
            # Test 1: Health Check
            test_results["health"] = await client.test_health_check()
            print()

            # Test 2: Root Endpoint
            test_results["root"] = await client.test_root_endpoint()
            print()

            # Test 3: Create Workflow
            test_results["create"] = await client.test_create_workflow()
            workflow_id = test_results["create"].get("workflow_id")
            print()

            # Test 4: Get Workflow (if creation succeeded)
            if workflow_id:
                test_results["get"] = await client.test_get_workflow(workflow_id)
                print()

            # Test 5: List Workflows
            test_results["list"] = await client.test_list_workflows()
            print()

            # Test 6: Validate Workflow
            test_results["validate"] = await client.test_validate_workflow()
            print()

            # Test 7: Execute Workflow (if creation succeeded)
            if workflow_id:
                test_results["execute"] = await client.test_execute_workflow(workflow_id)
                execution_id = test_results["execute"].get("execution_id")
                print()

                # Test 8: Get Execution Status (if execution started)
                if execution_id:
                    # Wait a moment for execution to start
                    await asyncio.sleep(1)
                    test_results["execution_status"] = await client.test_get_execution_status(
                        execution_id
                    )
                    print()

        except Exception as e:
            print(f"❌ Test suite failed with error: {str(e)}")
            return False

    # Print summary
    print("📊 Test Results Summary")
    print("=" * 50)

    total_tests = len(test_results)
    successful_tests = sum(1 for result in test_results.values() if result.get("success", False))

    for test_name, result in test_results.items():
        status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
        print(f"{test_name:20} {status}")

    print()
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    print(f"Success Rate: {successful_tests / total_tests * 100:.1f}%")

    return successful_tests == total_tests


async def quick_health_test():
    """Quick test to check if the server is running."""
    print("🏥 Quick Health Check")
    print("-" * 30)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BASE_URL}/health")

            if response.status_code == 200:
                print("✅ Server is running and healthy!")
                print(f"   Response: {response.json()}")
                return True
            else:
                print(f"❌ Server returned status {response.status_code}")
                print(f"   Response: {response.text}")
                return False

    except httpx.ConnectError:
        print("❌ Cannot connect to server")
        print(f"   Make sure the server is running on {BASE_URL}")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "health":
        # Quick health check
        success = asyncio.run(quick_health_test())
    else:
        # Full test suite
        success = asyncio.run(run_comprehensive_test())

    sys.exit(0 if success else 1)
