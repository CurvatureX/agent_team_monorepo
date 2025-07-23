#!/usr/bin/env python3
"""
Simple Session ID Test
简单的session_id测试
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

import grpc
from proto import workflow_service_pb2
from proto import workflow_service_pb2_grpc
from proto import workflow_pb2

def test_simple_session():
    """Simple session_id test"""
    print("🧪 Simple Session ID Test")
    print("=" * 30)
    
    # Connect to gRPC server
    channel = grpc.insecure_channel('localhost:50051')
    stub = workflow_service_pb2_grpc.WorkflowServiceStub(channel)
    
    # Test user ID and session ID
    user_id = "00000000-0000-0000-0000-000000000123"
    session_id = "6e9e76ae-cbee-4f31-a3cd-432a8c31355d"
    
    try:
        # Create a simple workflow with session_id
        print(f"Creating workflow with session_id: {session_id}")
        
        # Create workflow settings
        settings = workflow_pb2.WorkflowSettings(
            timezone="UTC",
            save_execution_progress=True,
            save_manual_executions=True,
            timeout=300,
            error_policy=workflow_pb2.ErrorPolicy.STOP_WORKFLOW,
            caller_policy=workflow_pb2.CallerPolicy.WORKFLOW_MAIN
        )
        
        # Create a simple trigger node
        trigger_node = workflow_pb2.Node(
            id="trigger-1",
            name="Simple Session Trigger",
            type=workflow_pb2.NodeType.TRIGGER_NODE,
            subtype=workflow_pb2.NodeSubtype.TRIGGER_MANUAL,
            position=workflow_pb2.Position(x=100, y=100),
            parameters={}
        )
        
        # Create connections map
        connections = workflow_pb2.ConnectionsMap()
        
        # Create workflow request with session_id
        create_request = workflow_service_pb2.CreateWorkflowRequest(
            name="Simple Session Workflow",
            description="A simple workflow for testing session_id",
            nodes=[trigger_node],
            connections=connections,
            settings=settings,
            static_data={},
            tags=["test", "simple", "session"],
            user_id=user_id,
            session_id=session_id
        )
        
        create_response = stub.CreateWorkflow(create_request)
        if create_response.success:
            workflow_id = create_response.workflow.id
            print(f"✅ Workflow created: {workflow_id}")
            print(f"   Session ID: {create_response.workflow.session_id}")
            
            # Test get workflow
            print(f"\nGetting workflow: {workflow_id}")
            get_request = workflow_service_pb2.GetWorkflowRequest(
                workflow_id=workflow_id,
                user_id=user_id
            )
            
            get_response = stub.GetWorkflow(get_request)
            if get_response.found:
                print(f"✅ Workflow retrieved")
                print(f"   Session ID: {get_response.workflow.session_id}")
            else:
                print(f"❌ Workflow not found")
                
        else:
            print(f"❌ Failed to create workflow: {create_response.message}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        channel.close()

if __name__ == "__main__":
    test_simple_session() 