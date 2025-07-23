#!/usr/bin/env python3
"""
Test protobuf session_id field
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from proto import workflow_pb2

def test_proto_session_id():
    """Test protobuf session_id field"""
    print("🧪 Testing Protobuf Session ID Field")
    print("=" * 40)
    
    # Create a workflow protobuf message
    workflow = workflow_pb2.Workflow()
    workflow.id = "test-id"
    workflow.name = "Test Workflow"
    workflow.session_id = "6e9e76ae-cbee-4f31-a3cd-432a8c31355d"
    
    print(f"Workflow ID: {workflow.id}")
    print(f"Workflow Name: {workflow.name}")
    print(f"Session ID: {workflow.session_id}")
    
    # Check if session_id field exists
    print(f"Has session_id field: {workflow.HasField('session_id')}")
    
    # List all fields
    print("\nAll fields:")
    for field in workflow.DESCRIPTOR.fields:
        print(f"  {field.name}: {field.number}")

if __name__ == "__main__":
    test_proto_session_id() 