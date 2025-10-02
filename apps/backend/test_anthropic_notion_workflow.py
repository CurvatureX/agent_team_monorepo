"""
Integration test: Manual Trigger → Anthropic Claude → Notion External Action

This workflow demonstrates:
1. Manual trigger to start the workflow
2. Anthropic Claude AI agent to generate task information
3. Notion External Action to create a task in a Notion database
"""

import json
import os
import time

import requests

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "test@123.com")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "123456")

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jzcgmzipaiwesyyzixfh.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "sb_publishable_WQbXbSJYrg-3YPW4Htx0Aw_ha3LND8z")

# Notion credentials
NOTION_ACCESS_TOKEN = "ntn_Y29841984278cT45JYtg0JKVUGiJ4m8Yas96xNCmvuI43v"
NOTION_DATABASE_ID = "27c0b1df-411b-81fa-ac40-ca8f7b697a0b"  # Tasks database


def get_auth_token():
    """Get authentication token for the test user."""
    print(f"🔐 Getting auth token for user: {TEST_USER_EMAIL}")

    auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"

    response = requests.post(
        auth_url,
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
    )

    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user_id = data.get("user", {}).get("id")
        print(f"✅ Got auth token: {token[:20]}...")
        print(f"   User ID: {user_id}")
        return token, user_id
    else:
        print(f"❌ Failed to get auth token: {response.status_code}")
        print(f"   Response: {response.text}")
        return None, None


def store_notion_oauth_token(auth_token, user_id):
    """Store Notion OAuth token in the database for the user."""
    print("\n🔑 Storing Notion OAuth token in database...")

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

    # First, check if token already exists for this user and provider
    check_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/oauth_tokens?user_id=eq.{user_id}&provider=eq.notion&limit=1",
        headers=headers,
    )

    if check_response.status_code == 200:
        existing_tokens = check_response.json()

        if existing_tokens:
            # Token exists - update it
            token_id = existing_tokens[0]["id"]
            print(f"   Found existing token (ID: {token_id}), updating...")

            update_data = {
                "access_token": NOTION_ACCESS_TOKEN,
                "updated_at": "now()",
            }

            update_response = requests.patch(
                f"{SUPABASE_URL}/rest/v1/oauth_tokens?id=eq.{token_id}",
                headers=headers,
                json=update_data,
            )

            if update_response.status_code in [200, 204]:
                print(f"✅ Notion OAuth token updated successfully")
                return True
            else:
                print(f"⚠️  Failed to update token: {update_response.status_code}")
                return False
        else:
            # No token exists - create new one
            print(f"   No existing token found, creating new one...")

            token_data = {
                "user_id": user_id,
                "provider": "notion",
                "access_token": NOTION_ACCESS_TOKEN,
                "expires_at": None,
                "refresh_token": None,
            }

            create_response = requests.post(
                f"{SUPABASE_URL}/rest/v1/oauth_tokens",
                headers=headers,
                json=token_data,
            )

            if create_response.status_code in [200, 201]:
                print(f"✅ Notion OAuth token created successfully")
                return True
            else:
                print(f"⚠️  Failed to create token: {create_response.status_code}")
                print(f"   Response: {create_response.text}")
                return False
    else:
        print(f"❌ Failed to check for existing tokens: {check_response.status_code}")
        return False


def create_anthropic_notion_workflow(auth_token):
    """Create a workflow: Manual Trigger → Anthropic Claude → Notion Action."""
    print("\n📝 Creating Anthropic + Notion workflow...")

    workflow = {
        "name": "AI_Task_Generator",
        "description": "Generate task ideas with Claude and create them in Notion",
        "metadata": {
            "name": "AI Task Generator",
            "description": "Uses Claude to generate task ideas and creates them in Notion",
            "version": "1.0",
            "tags": ["ai", "notion", "productivity"],
            "icon_url": "https://dtijyicuvv7hy.cloudfront.net/11.png",
        },
        "nodes": [
            {
                "id": "manual_trigger",
                "name": "Manual_Trigger",
                "description": "Start workflow manually",
                "type": "TRIGGER",
                "subtype": "MANUAL",
                "configurations": {},
                "input_params": {},
                "output_params": {
                    "topic": "",
                    "context": "",
                },
                "input_ports": [],
                "output_ports": [
                    {
                        "id": "main",
                        "name": "main",
                        "data_type": "dict",
                        "required": False,
                        "description": "Manual trigger output",
                        "max_connections": -1,
                    }
                ],
            },
            {
                "id": "claude_agent",
                "name": "Claude_Task_Generator",
                "description": "Generate task information using Claude",
                "type": "AI_AGENT",
                "subtype": "ANTHROPIC_CLAUDE",
                "configurations": {
                    "model": "claude-3-5-sonnet-20241022",
                    "system_prompt": 'You are a productivity expert. Generate ONE actionable task based on the topic provided. Return ONLY a JSON object with these exact fields: {"task_name": "...", "priority": "High|Medium|Low", "due_date": "YYYY-MM-DD", "tags": ["tag1", "tag2"]}. No additional text or explanation.',
                    "temperature": 0.7,
                    "max_tokens": 200,
                },
                "input_params": {"user_prompt": ""},
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
                "id": "notion_action",
                "name": "Notion_Task_Creator",
                "description": "Create task in Notion database",
                "type": "EXTERNAL_ACTION",
                "subtype": "NOTION",
                "configurations": {
                    "notion_token": NOTION_ACCESS_TOKEN,
                    "action_type": "create_page",
                    "database_id": NOTION_DATABASE_ID,
                },
                "input_params": {
                    "title": "",
                    "content": "",
                },
                "output_params": {
                    "success": False,
                    "page_id": "",
                    "page_url": "",
                },
                "input_ports": [
                    {
                        "id": "main",
                        "name": "main",
                        "data_type": "dict",
                        "required": True,
                        "description": "Task data to create",
                    }
                ],
                "output_ports": [
                    {
                        "id": "main",
                        "name": "main",
                        "data_type": "dict",
                        "required": True,
                        "description": "Creation result",
                    }
                ],
            },
        ],
        "connections": [
            {
                "id": "conn_trigger_to_claude",
                "from_node": "manual_trigger",
                "to_node": "claude_agent",
                "from_port": "main",
                "to_port": "main",
                "conversion_function": """def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    topic = input_data.get("topic", "workflow automation")
    context = input_data.get("context", "")
    prompt = f"Generate a task about: {topic}"
    if context:
        prompt += f"\\nContext: {context}"
    return {"user_prompt": prompt}""",
            },
            {
                "id": "conn_claude_to_notion",
                "from_node": "claude_agent",
                "to_node": "notion_action",
                "from_port": "main",
                "to_port": "main",
                "conversion_function": """def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    import json

    # Extract Claude's response - it's in "content" field, not "response"
    response_text = input_data.get("content", "{}")

    # Parse JSON response from Claude
    try:
        task_data = json.loads(response_text)
        task_name = task_data.get("task_name", "AI Generated Task")
        priority = task_data.get("priority", "Medium")
        due_date = task_data.get("due_date", "2025-10-15")
        tags = ", ".join(task_data.get("tags", ["ai-generated"]))
    except Exception as e:
        # Fallback if parsing fails
        task_name = "AI Generated Task"
        priority = "Medium"
        due_date = "2025-10-15"
        tags = "ai-generated"

    # Format for Notion - simple title and content
    title = task_name
    content = f"Priority: {priority}\\nDue Date: {due_date}\\nTags: {tags}"

    return {"title": title, "content": content}""",
            },
        ],
        "triggers": ["manual_trigger"],
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

        # Handle nested response structure: {"workflow": {...}}
        workflow_data = result.get("workflow", result.get("data", result))

        workflow_id = workflow_data.get("id")
        workflow_name = workflow_data.get("metadata", {}).get("name") or workflow_data.get("name")
        workflow_status = workflow_data.get("deployment_status")

        print(f"\n   Workflow ID: {workflow_id}")
        print(f"   Name: {workflow_name}")
        print(f"   Status: {workflow_status}")

        return workflow_data
    else:
        print(f"❌ Failed to create workflow")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def trigger_workflow_execution(auth_token, workflow_id):
    """Trigger the workflow with initial data."""
    print(f"\n🚀 Triggering workflow execution: {workflow_id}")

    execution_data = {
        "inputs": {
            "topic": "implement user authentication feature",
            "context": "High priority security enhancement for the application",
        },
        "settings": {
            "start_from_node": None,
            "skip_trigger_validation": False,
        },
    }

    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{API_BASE_URL}/api/v1/app/workflows/{workflow_id}/execute",
        headers=headers,
        json=execution_data,
        timeout=60,
    )

    print(f"📊 Execution Response Status: {response.status_code}")

    if response.status_code in [200, 201]:
        result = response.json()
        print(f"✅ Workflow execution triggered!")
        print(f"   Execution ID: {result.get('execution_id')}")
        print(f"\n📄 Full response:")
        print(json.dumps(result, indent=2))
        return result
    else:
        print(f"❌ Failed to trigger workflow")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def delete_workflow(auth_token, workflow_id):
    """Delete the test workflow."""
    print(f"\n🗑️  Deleting workflow: {workflow_id}")

    headers = {
        "Authorization": f"Bearer {auth_token}",
    }

    response = requests.delete(
        f"{API_BASE_URL}/api/v1/app/workflows/{workflow_id}",
        headers=headers,
        timeout=30,
    )

    if response.status_code in [200, 204]:
        print(f"✅ Workflow deleted successfully")
        return True
    else:
        print(f"❌ Failed to delete workflow: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 Testing Anthropic Claude + Notion Integration")
    print(f"📍 API URL: {API_BASE_URL}")
    print("=" * 60)

    # Get authentication token
    auth_token, user_id = get_auth_token()
    if not auth_token or not user_id:
        print("\n❌ ERROR: Could not get auth token. Cannot continue.")
        return

    # Store Notion OAuth token in database
    if not store_notion_oauth_token(auth_token, user_id):
        print("\n⚠️  Warning: Could not store OAuth token, but continuing...")

    # Create the workflow
    workflow = create_anthropic_notion_workflow(auth_token)
    if not workflow:
        print("\n❌ ERROR: Could not create workflow.")
        return

    workflow_id = workflow.get("id")

    # Try to trigger the workflow execution
    print("\n" + "=" * 60)
    print("⏸️  Workflow created. Ready to test execution.")
    print("=" * 60)

    # Auto-execute for testing (set to False for interactive mode)
    AUTO_EXECUTE = os.getenv("AUTO_EXECUTE", "true").lower() == "true"

    if AUTO_EXECUTE:
        print("\n🔹 Auto-triggering workflow execution...")
        execution = trigger_workflow_execution(auth_token, workflow_id)
        if execution:
            print("\n✅ Workflow execution completed!")
            print("   Check your Notion database for the new task.")
    else:
        user_input = input("\n🔹 Trigger workflow execution? (y/n): ")
        if user_input.lower() == "y":
            execution = trigger_workflow_execution(auth_token, workflow_id)
            if execution:
                print("\n✅ Workflow execution completed!")
                print("   Check your Notion database for the new task.")

    # Ask if user wants to clean up
    print("\n" + "=" * 60)

    AUTO_CLEANUP = os.getenv("AUTO_CLEANUP", "false").lower() == "true"

    if AUTO_CLEANUP:
        print("🔹 Auto-cleaning up test workflow...")
        delete_workflow(auth_token, workflow_id)
        print("\n✅ Cleanup complete!")
    else:
        print(f"\n💡 Workflow preserved with ID: {workflow_id}")
        print("   You can manually delete it later if needed.")
        print("   Set AUTO_CLEANUP=true to auto-delete test workflows.")

    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
