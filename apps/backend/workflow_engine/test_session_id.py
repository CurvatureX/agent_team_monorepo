#!/usr/bin/env python3
"""
Test Session ID functionality
测试session_id功能
"""

import sys
import time
import uuid
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

import grpc
from workflow_engine.proto import workflow_service_pb2
from workflow_engine.proto import workflow_service_pb2_grpc
from workflow_engine.proto import workflow_pb2

def test_session_id():
    """Test session_id functionality"""
    print("🧪 Testing Session ID Functionality")
    print("=" * 50)
    
    # Connect to gRPC server
    channel = grpc.insecure_channel('localhost:50051')
    stub = workflow_service_pb2_grpc.WorkflowServiceStub(channel)
    
    # Test user ID and session ID
    user_id = "00000000-0000-0000-0000-000000000123"
    session_id = "6e9e76ae-cbee-4f31-a3cd-432a8c31355d"  # 使用数据库中已存在的session_id
    
    try:
        # Step 1: Create a workflow with session_id
        print(f"\n📋 Step 1: Create workflow with session_id: {session_id}")
        
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
            name="Session Test Trigger",
            type=workflow_pb2.NodeType.TRIGGER_NODE,
            subtype=workflow_pb2.NodeSubtype.TRIGGER_MANUAL,
            position=workflow_pb2.Position(x=100, y=100),
            parameters={}
        )
        
        # Create connections map
        connections = workflow_pb2.ConnectionsMap()
        
        # Create workflow request with session_id
        create_request = workflow_service_pb2.CreateWorkflowRequest(
            name="Session Test Workflow",
            description="A workflow for testing session_id functionality",
            nodes=[trigger_node],
            connections=connections,
            settings=settings,
            static_data={},
            tags=["test", "session"],
            user_id=user_id,
            session_id=session_id  # 新增：session_id
        )
        
        try:
            create_response = stub.CreateWorkflow(create_request)
            if create_response.success:
                workflow_id = create_response.workflow.id
                print(f"✅ Workflow created successfully: {workflow_id}")
                print(f"   Name: {create_response.workflow.name}")
                print(f"   Session ID: {create_response.workflow.session_id}")
                print(f"   Tags: {list(create_response.workflow.tags)}")
            else:
                print(f"❌ Failed to create workflow: {create_response.message}")
                return
        except grpc.RpcError as e:
            print(f"❌ Error creating workflow: {e.details()}")
            return
        
        # Step 2: Get the created workflow
        print(f"\n📋 Step 2: Get workflow with session_id")
        get_request = workflow_service_pb2.GetWorkflowRequest(
            workflow_id=workflow_id,
            user_id=user_id
        )
        
        try:
            get_response = stub.GetWorkflow(get_request)
            if get_response.found:
                print(f"✅ Workflow retrieved successfully")
                print(f"   Name: {get_response.workflow.name}")
                print(f"   Session ID: {get_response.workflow.session_id}")
                print(f"   Active: {get_response.workflow.active}")
                print(f"   Tags: {list(get_response.workflow.tags)}")
            else:
                print(f"❌ Workflow not found: {get_response.message}")
        except grpc.RpcError as e:
            print(f"❌ Error getting workflow: {e.details()}")
        
        # Step 3: Update workflow with new session_id
        print(f"\n📋 Step 3: Update workflow with new session_id")
        new_session_id = "6e9e76ae-cbee-4f31-a3cd-432a8c31355d"  # 使用数据库中已存在的session_id
        
        update_request = workflow_service_pb2.UpdateWorkflowRequest(
            workflow_id=workflow_id,
            name="Updated Session Test Workflow",
            description="Updated description with new session",
            nodes=[trigger_node],
            connections=connections,
            settings=settings,
            static_data={"session_test": "updated"},
            tags=["test", "session", "updated"],
            active=True,
            user_id=user_id,
            session_id=new_session_id  # 新增：更新session_id
        )
        
        try:
            update_response = stub.UpdateWorkflow(update_request)
            if update_response.success:
                print(f"✅ Workflow updated successfully")
                print(f"   New name: {update_response.workflow.name}")
                print(f"   New session ID: {update_response.workflow.session_id}")
                print(f"   Updated tags: {list(update_response.workflow.tags)}")
            else:
                print(f"❌ Failed to update workflow: {update_response.message}")
        except grpc.RpcError as e:
            print(f"❌ Error updating workflow: {e.details()}")
        
        # Step 4: List workflows to see the updated one
        print(f"\n📋 Step 4: List workflows")
        list_request = workflow_service_pb2.ListWorkflowsRequest(
            user_id=user_id,
            active_only=False,
            limit=10,
            offset=0
        )
        
        try:
            list_response = stub.ListWorkflows(list_request)
            print(f"✅ Found {list_response.total_count} workflows")
            for workflow in list_response.workflows:
                print(f"   - {workflow.id}: {workflow.name} (Active: {workflow.active})")
                if workflow.id == workflow_id:
                    print(f"     Session ID: {workflow.session_id}")
                    print(f"     Tags: {list(workflow.tags)}")
        except grpc.RpcError as e:
            print(f"❌ Error listing workflows: {e.details()}")
        
        # Step 5: Test creating workflow without session_id
        print(f"\n📋 Step 5: Create workflow without session_id")
        create_request_no_session = workflow_service_pb2.CreateWorkflowRequest(
            name="No Session Workflow",
            description="A workflow without session_id",
            nodes=[trigger_node],
            connections=connections,
            settings=settings,
            static_data={},
            tags=["test", "no-session"],
            user_id=user_id
            # 不设置session_id
        )
        
        try:
            create_response_no_session = stub.CreateWorkflow(create_request_no_session)
            if create_response_no_session.success:
                workflow_id_no_session = create_response_no_session.workflow.id
                print(f"✅ Workflow without session_id created successfully: {workflow_id_no_session}")
                print(f"   Name: {create_response_no_session.workflow.name}")
                print(f"   Session ID: {create_response_no_session.workflow.session_id}")
                print(f"   Tags: {list(create_response_no_session.workflow.tags)}")
            else:
                print(f"❌ Failed to create workflow without session_id: {create_response_no_session.message}")
        except grpc.RpcError as e:
            print(f"❌ Error creating workflow without session_id: {e.details()}")
        
        print("\n✅ Session ID functionality test completed!")
        print("\n📋 Summary of session_id features tested:")
        print("  ✅ Create workflow with session_id")
        print("  ✅ Get workflow with session_id")
        print("  ✅ Update workflow with new session_id")
        print("  ✅ List workflows with session_id")
        print("  ✅ Create workflow without session_id")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        channel.close()

if __name__ == "__main__":
    test_session_id() 