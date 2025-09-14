#!/usr/bin/env python3
"""
Get workflow definition to understand what nodes should execute
"""
import json
import os

import requests

# Configuration
SUPABASE_URL = "https://mkrczzgjeduruwxpanbj.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_GDldaQkfc6tfJ2aEOx_H3w_rq2Tc5G3"
TEST_USER_EMAIL = "daming.lu@starmates.ai"
TEST_USER_PASSWORD = "test.1234!"
WORKFLOW_ENGINE_URL = "http://localhost:8002"
WORKFLOW_ID = "e30c8316-c4fc-41ee-b3b8-36958d5ccdfc"


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


def get_workflow_definition():
    """Get workflow definition"""
    jwt_token = get_jwt_token()
    if not jwt_token:
        print("❌ Could not get JWT token")
        return

    print(f"🔍 Getting workflow definition: {WORKFLOW_ID}")

    try:
        response = requests.get(
            f"{WORKFLOW_ENGINE_URL}/v1/workflows/{WORKFLOW_ID}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Workflow Definition Retrieved")

            # Pretty print the workflow structure
            workflow = data.get("workflow", data)

            print(f"\n📋 Workflow Overview:")
            print(f"   Name: {workflow.get('name', 'N/A')}")
            print(f"   Description: {workflow.get('description', 'N/A')}")
            print(f"   Active: {workflow.get('active', False)}")

            # Check nodes
            nodes = workflow.get("nodes", [])
            print(f"\n🔧 Nodes ({len(nodes)} total):")

            for i, node in enumerate(nodes):
                node_type = node.get("type", "Unknown")
                node_subtype = node.get("subtype", "")
                node_id = node.get("id", f"node_{i}")
                node_name = node.get("name", node_id)

                print(f"   {i+1}. [{node_type}:{node_subtype}] {node_name} (id: {node_id})")

                # Show parameters for important nodes
                if node_type in ["TRIGGER", "AI_AGENT", "EXTERNAL_ACTION"]:
                    params = node.get("parameters", {})
                    if params:
                        print(f"      Parameters: {json.dumps(params, indent=8)}")

            # Check connections
            connections = workflow.get("connections", {})
            print(f"\n🔗 Connections:")
            if connections:
                print(json.dumps(connections, indent=2))
            else:
                print("   No connections defined")

            return workflow
        else:
            print(f"❌ Error Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error getting workflow: {e}")
        return None


if __name__ == "__main__":
    get_workflow_definition()
