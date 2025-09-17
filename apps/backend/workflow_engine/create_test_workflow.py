#!/usr/bin/env python3
"""
Create a test workflow in the database for parameter validation testing.
"""

import json
import uuid

from database import Database


def create_test_workflow():
    db = Database()

    # Create a simple test workflow with an AI_AGENT_NODE that has missing parameters
    workflow_id = str(uuid.uuid4())

    workflow_definition = {
        "nodes": [
            {
                "id": "ai_node_1",
                "type": "AI_AGENT_NODE",
                "subtype": "openai",
                "parameters": {
                    "name": "Test AI Node",
                    # Missing required parameters: "system_prompt", "user_message"
                    "model_version": "gpt-4",
                },
                "connections": [],
            }
        ],
        "connections": [],
        "metadata": {
            "name": "Test Parameter Validation Workflow",
            "description": "Workflow to test parameter validation errors",
        },
    }

    # Insert workflow into database
    try:
        result = (
            db.client.table("workflows")
            .insert(
                {
                    "id": workflow_id,
                    "name": "Test Parameter Validation",
                    "description": "Test workflow for parameter validation",
                    "definition": json.dumps(workflow_definition),
                    "user_id": "test-user",
                    "is_active": True,
                }
            )
            .execute()
        )

        print(f"✅ Created test workflow: {workflow_id}")
        print(f"Workflow definition: {json.dumps(workflow_definition, indent=2)}")
        return workflow_id

    except Exception as e:
        print(f"❌ Failed to create workflow: {e}")
        return None


if __name__ == "__main__":
    workflow_id = create_test_workflow()
    if workflow_id:
        print(f"\n🎯 Use this workflow ID for testing: {workflow_id}")
        print("\nTest command:")
        print(
            f"""curl -X POST "http://localhost:8002/v1/workflows/{workflow_id}/execute" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "workflow_id": "{workflow_id}",
    "user_id": "test-user",
    "async_execution": false,
    "trigger_data": {{"message": "test parameter validation"}}
  }}'"""
        )
