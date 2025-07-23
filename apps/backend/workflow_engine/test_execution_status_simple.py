#!/usr/bin/env python3
"""
Simple execution status test
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

import grpc
from proto import execution_pb2
from proto import execution_pb2_grpc

def test_execution_status_simple():
    """Simple execution status test"""
    print("🧪 Simple Execution Status Test")
    print("=" * 40)
    
    # Connect to gRPC server
    channel = grpc.insecure_channel('localhost:50051')
    stub = execution_pb2_grpc.ExecutionServiceStub(channel)
    
    # Use a known execution ID from our previous tests
    execution_id = "b98426f6-9dc4-4f16-9b29-e67759f6e110"
    
    try:
        print(f"📋 Testing execution status for: {execution_id}")
        
        # Create status request
        status_request = execution_pb2.GetExecutionStatusRequest(
            execution_id=execution_id
        )
        
        print("📋 Sending GetExecutionStatus request...")
        
        # Call the service
        status_response = stub.GetExecutionStatus(status_request)
        
        print("📋 Response received!")
        print(f"  Found: {status_response.found}")
        print(f"  Message: {status_response.message}")
        
        if status_response.found:
            execution = status_response.execution
            print(f"  Execution ID: {execution.execution_id}")
            print(f"  Workflow ID: {execution.workflow_id}")
            print(f"  Status: {execution.status}")
            print(f"  Mode: {execution.mode}")
            print(f"  Triggered by: {execution.triggered_by}")
            print(f"  Start time: {execution.start_time}")
            print(f"  End time: {execution.end_time}")
            print(f"  Metadata: {dict(execution.metadata)}")
        
        print("✅ Test completed successfully!")
        
    except grpc.RpcError as e:
        print(f"❌ gRPC Error: {e.code()}: {e.details()}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        channel.close()

if __name__ == "__main__":
    test_execution_status_simple() 