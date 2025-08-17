#!/usr/bin/env python3
"""
Debug script to test workflow update with detailed logging
"""
import asyncio
import json
import httpx
from pydantic import ValidationError

# Import the shared models
import sys
from pathlib import Path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from shared.models.workflow import UpdateWorkflowRequest, NodeData, PositionData, WorkflowSettingsData

async def test_minimal_update():
    """Test with minimal update payload"""
    print("\n=== Testing Minimal Update ===")
    
    workflow_id = "44b2f8a9-d3f5-46b9-9b88-94a9ea21e36f"
    user_id = "00000000-0000-0000-0000-000000000117"
    
    # Test 1: Just update name
    print("\n1. Testing name-only update:")
    minimal_payload = {
        "workflow_id": workflow_id,
        "user_id": user_id,
        "name": "Updated Workflow Name"
    }
    
    try:
        # Validate with Pydantic model
        request = UpdateWorkflowRequest(**minimal_payload)
        print(f"✅ Pydantic validation passed")
        print(f"   Model dump: {request.model_dump(exclude_none=True)}")
    except ValidationError as e:
        print(f"❌ Pydantic validation failed: {e}")
        return

    # Test direct to workflow-engine
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                f"http://localhost:8002/v1/workflows/{workflow_id}",
                json=minimal_payload
            )
            print(f"   Direct to workflow-engine: {response.status_code}")
            if response.status_code != 200:
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")

async def test_full_update():
    """Test with full update payload from file"""
    print("\n=== Testing Full Update ===")
    
    workflow_id = "44b2f8a9-d3f5-46b9-9b88-94a9ea21e36f"
    user_id = "00000000-0000-0000-0000-000000000117"
    
    # Load the test payload
    with open("/tmp/workflow_update.json", "r") as f:
        payload_data = json.load(f)
    
    # Add required fields
    payload_data["workflow_id"] = workflow_id
    payload_data["user_id"] = user_id
    
    print("\n2. Testing full update with nodes:")
    print(f"   Nodes: {len(payload_data.get('nodes', []))}")
    print(f"   Connections: {list(payload_data.get('connections', {}).keys())}")
    
    try:
        # Validate with Pydantic model
        request = UpdateWorkflowRequest(**payload_data)
        print(f"✅ Pydantic validation passed")
        
        # Get the serialized data
        serialized = request.model_dump(exclude_none=True)
        print(f"\n   Serialized fields: {list(serialized.keys())}")
        
    except ValidationError as e:
        print(f"❌ Pydantic validation failed: {e}")
        for error in e.errors():
            print(f"   - {error['loc']}: {error['msg']}")
        return

    # Test direct to workflow-engine
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.put(
                f"http://localhost:8002/v1/workflows/{workflow_id}",
                json=serialized
            )
            print(f"\n   Direct to workflow-engine: {response.status_code}")
            if response.status_code != 200:
                print(f"   Response: {response.text}")
                try:
                    error_json = response.json()
                    print(f"   Error detail: {json.dumps(error_json, indent=2)}")
                except:
                    pass
        except Exception as e:
            print(f"   Error: {e}")

async def test_api_gateway_update():
    """Test through API Gateway"""
    print("\n=== Testing Through API Gateway ===")
    
    workflow_id = "44b2f8a9-d3f5-46b9-9b88-94a9ea21e36f"
    
    # Load the test payload
    with open("/tmp/workflow_update.json", "r") as f:
        payload_data = json.load(f)
    
    # Don't include workflow_id or user_id in the body
    # API Gateway will add them
    
    print("\n3. Testing API Gateway update:")
    
    # Need auth token for API Gateway
    auth_token = "your-auth-token-here"  # Replace with actual token
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.put(
                f"http://localhost:8001/api/app/workflows/{workflow_id}",
                json=payload_data,
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json"
                }
            )
            print(f"   API Gateway response: {response.status_code}")
            if response.status_code != 200:
                print(f"   Response: {response.text}")
                try:
                    error_json = response.json()
                    print(f"   Error detail: {json.dumps(error_json, indent=2)}")
                except:
                    pass
        except Exception as e:
            print(f"   Error: {e}")

async def validate_payload_structure():
    """Validate the payload structure matches Pydantic models"""
    print("\n=== Validating Payload Structure ===")
    
    with open("/tmp/workflow_update.json", "r") as f:
        payload_data = json.load(f)
    
    # Check nodes
    if "nodes" in payload_data:
        print(f"\nValidating {len(payload_data['nodes'])} nodes:")
        for i, node_data in enumerate(payload_data["nodes"]):
            try:
                node = NodeData(**node_data)
                print(f"   ✅ Node {i} ({node.id}): Valid")
            except ValidationError as e:
                print(f"   ❌ Node {i}: Invalid - {e}")
    
    # Check settings
    if "settings" in payload_data:
        print(f"\nValidating settings:")
        try:
            settings = WorkflowSettingsData(**payload_data["settings"])
            print(f"   ✅ Settings: Valid")
        except ValidationError as e:
            print(f"   ❌ Settings: Invalid - {e}")

async def main():
    """Run all tests"""
    await validate_payload_structure()
    await test_minimal_update()
    await test_full_update()
    # await test_api_gateway_update()  # Uncomment if you have auth token

if __name__ == "__main__":
    asyncio.run(main())