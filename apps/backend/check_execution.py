#!/usr/bin/env python3
"""
Check execution status and logs
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

# Execution IDs from the recent test
EXECUTION_ID_1 = "befc91c6-79a0-4a42-ae92-7df12abe4771"
EXECUTION_ID_2 = "0381821f-0eb9-4a91-9e83-8142ffe2a606"


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


def check_execution_status(execution_id, jwt_token):
    """Check execution status"""
    try:
        print(f"\n🔍 Checking execution status: {execution_id}")
        response = requests.get(
            f"{WORKFLOW_ENGINE_URL}/v1/executions/{execution_id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error checking execution: {e}")
        return False


def check_execution_logs(execution_id, jwt_token):
    """Check execution logs"""
    try:
        print(f"\n📋 Checking execution logs: {execution_id}")
        response = requests.get(
            f"{WORKFLOW_ENGINE_URL}/v1/workflows/executions/{execution_id}/logs",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Logs: {json.dumps(data, indent=2)}")
        else:
            print(f"Error Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error checking logs: {e}")
        return False


def main():
    print("🔍 Checking Execution Status and Logs...")
    print("=" * 50)

    jwt_token = get_jwt_token()
    if not jwt_token:
        print("❌ Could not get JWT token")
        return

    print(f"✅ JWT token obtained")

    # Check both executions
    for execution_id in [EXECUTION_ID_1, EXECUTION_ID_2]:
        check_execution_status(execution_id, jwt_token)
        check_execution_logs(execution_id, jwt_token)


if __name__ == "__main__":
    main()
