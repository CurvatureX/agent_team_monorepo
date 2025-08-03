#!/usr/bin/env python3
"""
Test script to debug workflow listing through API Gateway
"""

import httpx
import json
import asyncio
from datetime import datetime

# Configuration
API_GATEWAY_URL = "http://localhost:8000"
WORKFLOW_ENGINE_URL = "http://localhost:8002"
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6InZydnZmclVOdi9HUXFRT2oiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL21rcmN6emdqZWR1cnV3eHBhbmJqLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3YmEzNjM0NS1hMmJiLTRlYzktYTAwMS1iYjQ2ZDc5ZDYyOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU0MjAxMTc2LCJpYXQiOjE3NTQxOTc1NzYsImVtYWlsIjoiZGFtaW5nLmx1QHN0YXJtYXRlcy5haSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzU0MTk3NTc2fV0sInNlc3Npb25faWQiOiJjNjhiZjA4YS05YWY5LTQ5MWYtODkzYy1jZDA5NGNiMmEyYjYiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.O6LNKKJa053tLggrJlLv9YXsA_KmzQEZBXzbi7EKDD8"

# Extract user ID from JWT
import base64
jwt_parts = JWT_TOKEN.split('.')
payload = json.loads(base64.urlsafe_b64decode(jwt_parts[1] + '=='))
USER_ID_FROM_JWT = payload['sub']
print(f"User ID from JWT: {USER_ID_FROM_JWT}")


async def test_workflow_listing():
    async with httpx.AsyncClient() as client:
        print("\n=== Testing Workflow Listing ===")
        
        # 1. Test direct workflow engine access
        print("\n1. Direct workflow engine access:")
        try:
            response = await client.get(
                f"{WORKFLOW_ENGINE_URL}/v1/workflows",
                params={
                    "user_id": USER_ID_FROM_JWT,
                    "active_only": True,
                    "limit": 50,
                    "offset": 0
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Total workflows: {data.get('total_count', 0)}")
                print(f"Workflows returned: {len(data.get('workflows', []))}")
                if data.get('workflows'):
                    print("\nFirst workflow:")
                    print(json.dumps(data['workflows'][0], indent=2))
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
        
        # 2. Test API Gateway access (correct endpoint)
        print("\n2. API Gateway access (correct endpoint):")
        try:
            response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/app/workflows/",
                headers={
                    "Authorization": f"Bearer {JWT_TOKEN}"
                },
                params={
                    "active_only": True
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Total workflows: {data.get('total_count', 0)}")
                print(f"Workflows returned: {len(data.get('workflows', []))}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
        
        # 3. Test with different user_id parameters
        print("\n3. Testing with test user ID:")
        test_user_id = "00000000-0000-0000-0000-000000000123"
        try:
            response = await client.get(
                f"{WORKFLOW_ENGINE_URL}/v1/workflows",
                params={
                    "user_id": test_user_id,
                    "active_only": True
                }
            )
            print(f"Direct engine with test user ID: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Workflows for test user: {data.get('total_count', 0)}")
        except Exception as e:
            print(f"Error: {e}")
        
        # 4. Create a test workflow for the JWT user
        print(f"\n4. Creating a test workflow for user {USER_ID_FROM_JWT}:")
        try:
            test_workflow = {
                "name": f"Test Workflow {datetime.now().isoformat()}",
                "description": "Test workflow created for debugging",
                "nodes": [
                    {
                        "id": "trigger_1",
                        "type": "TRIGGER_NODE",
                        "subtype": "TRIGGER_MANUAL",
                        "name": "Manual Trigger",
                        "position": {"x": 0, "y": 0},
                        "parameters": {}
                    }
                ],
                "connections": {},
                "settings": {},
                "static_data": {},
                "tags": ["test"],
                "user_id": USER_ID_FROM_JWT
            }
            
            response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/app/workflows/",
                headers={
                    "Authorization": f"Bearer {JWT_TOKEN}",
                    "Content-Type": "application/json"
                },
                json=test_workflow
            )
            print(f"Create workflow status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Created workflow ID: {data.get('workflow', {}).get('id')}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error creating workflow: {e}")
        
        # 5. Re-test listing after creation
        print("\n5. Re-testing workflow listing after creation:")
        try:
            response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/app/workflows/",
                headers={
                    "Authorization": f"Bearer {JWT_TOKEN}"
                },
                params={
                    "active_only": True
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Total workflows: {data.get('total_count', 0)}")
                print(f"Workflows returned: {len(data.get('workflows', []))}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_workflow_listing())