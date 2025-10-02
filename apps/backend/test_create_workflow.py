"""
Test script to create an example workflow via the API Gateway.

This creates a simple workflow:
WEBHOOK TRIGGER → AI AGENT (Generate Joke) → SLACK ACTION (Send Joke)
"""

import json
import os
import time

import requests

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "daming.lu@starmates.ai")

# Supabase credentials for authentication
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jzcgmzipaiwesyyzixfh.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "sb_publishable_WQbXbSJYrg-3YPW4Htx0Aw_ha3LND8z")


def get_auth_token():
    """Get authentication token for the test user."""
    print(f"🔐 Getting auth token for user: {TEST_USER_EMAIL}")

    # Get password from environment variable
    test_password = os.getenv("TEST_USER_PASSWORD")
    if not test_password:
        print("❌ TEST_USER_PASSWORD environment variable not set")
        return None

    # Try to get token from Supabase directly
    auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"

    print(f"📡 Requesting token from: {auth_url}")
    print(f"   Email: {TEST_USER_EMAIL}")
    print(f"   Password: {'*' * len(test_password)}")

    response = requests.post(
        auth_url,
        json={"email": TEST_USER_EMAIL, "password": test_password},
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
    )

    print(f"📊 Auth response status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"✅ Got auth token: {token[:20]}...")
        return token
    else:
        print(f"❌ Failed to get auth token: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def create_test_workflow(auth_token):
    """Create a test workflow via the API."""
    print("\n📝 Creating test workflow...")

    # Define the workflow
    workflow = {
        "name": "Simple Joke Generator",
        "description": "Generate a joke and send it to Slack",
        "metadata": {
            "name": "Simple Joke Generator",
            "description": "Generate a joke and send it to Slack",
            "version": "1.0",
            "tags": ["test", "joke", "slack"],
            "icon_url": "https://dtijyicuvv7hy.cloudfront.net/11.png",
        },
        "nodes": [
            {
                "id": "webhook_trigger",
                "name": "Webhook_Trigger",
                "description": "Receives webhook requests",
                "type": "TRIGGER",
                "subtype": "WEBHOOK",
                "configurations": {
                    "webhook_path": "/joke-webhook",
                    "allowed_methods": ["POST"],
                    "authentication": "none",
                    "response_format": "json",
                },
                "input_params": {},
                "output_params": {
                    "headers": {},
                    "body": {},
                    "query_params": {},
                    "method": "",
                    "path": "",
                },
                "input_ports": [],
                "output_ports": [
                    {
                        "id": "main",
                        "name": "main",
                        "data_type": "dict",
                        "required": False,
                        "description": "Webhook request data",
                        "max_connections": -1,
                        "validation_schema": None,
                    }
                ],
            },
            {
                "id": "ai_joke_generator",
                "name": "AI_Joke_Generator",
                "description": "Generates a funny joke using AI",
                "type": "AI_AGENT",
                "subtype": "OPENAI_CHATGPT",
                "configurations": {
                    "model": "gpt-4o-mini",
                    "system_prompt": "You are a professional comedian. Generate a short, clean, funny joke. Respond with just the joke text, no explanation or preamble.",
                    "temperature": 0.9,
                    "max_tokens": 150,
                },
                "input_params": {"user_prompt": "Generate a joke"},
                "output_params": {"response": "", "model": "", "tokens_used": 0},
                "input_ports": [
                    {
                        "id": "main",
                        "name": "main",
                        "data_type": "dict",
                        "required": True,
                        "description": "AI agent input",
                    }
                ],
                "output_ports": [
                    {
                        "id": "main",
                        "name": "main",
                        "data_type": "dict",
                        "required": True,
                        "description": "AI agent output",
                    }
                ],
            },
            {
                "id": "slack_sender",
                "name": "Slack_Message_Sender",
                "description": "Sends the joke to Slack",
                "type": "EXTERNAL_ACTION",
                "subtype": "SLACK",
                "configurations": {
                    "action_type": "send_message",
                    "channel": "jokes",
                },
                "input_params": {"message": "", "channel": "jokes"},
                "output_params": {"success": False, "message_ts": ""},
                "input_ports": [
                    {
                        "id": "main",
                        "name": "main",
                        "data_type": "dict",
                        "required": True,
                        "description": "Message to send",
                    }
                ],
                "output_ports": [
                    {
                        "id": "main",
                        "name": "main",
                        "data_type": "dict",
                        "required": True,
                        "description": "Send result",
                    }
                ],
            },
        ],
        "connections": [
            {
                "id": "conn_webhook_to_ai",
                "from_node": "webhook_trigger",
                "to_node": "ai_joke_generator",
                "from_port": "main",
                "to_port": "main",
                "conversion_function": 'def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:\n    return {"user_prompt": "Generate a random funny joke"}',
            },
            {
                "id": "conn_ai_to_slack",
                "from_node": "ai_joke_generator",
                "to_node": "slack_sender",
                "from_port": "main",
                "to_port": "main",
                "conversion_function": 'def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:\n    joke = input_data.get("response", "No joke generated")\n    return {"message": f"🎭 Joke of the moment:\\n\\n{joke}"}',
            },
        ],
        "triggers": ["webhook_trigger"],
        "active": True,
        "version": "1.0",
    }

    # Make the API request
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{API_BASE_URL}/api/v1/app/workflows/",
        headers=headers,
        json=workflow,
        timeout=30,
    )

    print(f"\n📊 Response Status: {response.status_code}")

    if response.status_code in [200, 201]:
        result = response.json()
        print(f"✅ Workflow created successfully!")
        print(f"   Workflow ID: {result.get('id')}")
        print(f"   Name: {result.get('name')}")
        print(f"   Status: {result.get('deployment_status')}")
        print(f"\n📄 Full response:")
        print(json.dumps(result, indent=2))
        return result
    else:
        print(f"❌ Failed to create workflow")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 Testing Workflow Creation API")
    print(f"📍 API URL: {API_BASE_URL}")
    print("=" * 60)

    # Get authentication token
    auth_token = get_auth_token()

    if not auth_token:
        print("\n❌ ERROR: Could not get auth token. Cannot continue.")
        print("   Please ensure:")
        print("   1. TEST_USER_EMAIL is set correctly")
        print("   2. TEST_USER_PASSWORD is set correctly")
        print("   3. The user exists in Supabase")
        return

    # Create the workflow
    workflow = create_test_workflow(auth_token)

    if workflow:
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Test failed")
        print("=" * 60)


if __name__ == "__main__":
    main()
