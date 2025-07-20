#!/usr/bin/env python3
"""
Test Workflow CRUD operations via gRPC
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

def test_workflow_crud():
    """Test Workflow CRUD operations"""
    print("🧪 Testing Workflow CRUD Operations")
    print("=" * 50)
    
    # Connect to gRPC server
    channel = grpc.insecure_channel('localhost:50051')
    stub = workflow_service_pb2_grpc.WorkflowServiceStub(channel)
    
    # Test user ID
    user_id = "00000000-0000-0000-0000-000000000123"
    
    try:
        # Step 1: List existing workflows
        print("\n📋 Step 1: List existing workflows")
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
        except grpc.RpcError as e:
            print(f"❌ Error listing workflows: {e.details()}")
            return
        
        # Step 2: Create a simple workflow
        print("\n📋 Step 2: Create a simple workflow")
        
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
            name="Start Trigger",
            type=workflow_pb2.NodeType.TRIGGER_NODE,
            subtype=workflow_pb2.NodeSubtype.TRIGGER_MANUAL,
            position=workflow_pb2.Position(x=100, y=100),
            parameters={}
        )
        
        # Create connections map
        connections = workflow_pb2.ConnectionsMap()
        
        # Create workflow request
        create_request = workflow_service_pb2.CreateWorkflowRequest(
            name="Test CRUD Workflow",
            description="A simple workflow for testing CRUD operations",
            nodes=[trigger_node],
            connections=connections,
            settings=settings,
            static_data={},
            tags=["test", "crud", "simple"],
            user_id=user_id
        )
        
        try:
            create_response = stub.CreateWorkflow(create_request)
            if create_response.success:
                workflow_id = create_response.workflow.id
                print(f"✅ Workflow created successfully: {workflow_id}")
                print(f"   Name: {create_response.workflow.name}")
                print(f"   Tags: {list(create_response.workflow.tags)}")
            else:
                print(f"❌ Failed to create workflow: {create_response.message}")
                return
        except grpc.RpcError as e:
            print(f"❌ Error creating workflow: {e.details()}")
            return
        
        # Step 3: Get the created workflow
        print("\n📋 Step 3: Get the created workflow")
        get_request = workflow_service_pb2.GetWorkflowRequest(
            workflow_id=workflow_id,
            user_id=user_id
        )
        
        try:
            get_response = stub.GetWorkflow(get_request)
            if get_response.found:
                print(f"✅ Workflow retrieved successfully")
                print(f"   Name: {get_response.workflow.name}")
                print(f"   Description: {get_response.workflow.description}")
                print(f"   Active: {get_response.workflow.active}")
                print(f"   Tags: {list(get_response.workflow.tags)}")
            else:
                print(f"❌ Workflow not found: {get_response.message}")
        except grpc.RpcError as e:
            print(f"❌ Error getting workflow: {e.details()}")
        
        # Step 4: Update the workflow
        print("\n📋 Step 4: Update the workflow")
        
        # Create an action node for update
        action_node = workflow_pb2.Node(
            id="action-1",
            name="Test Action",
            type=workflow_pb2.NodeType.ACTION_NODE,
            subtype=workflow_pb2.NodeSubtype.ACTION_SEND_HTTP_REQUEST,
            position=workflow_pb2.Position(x=300, y=100),
            parameters={
                "url": "https://api.example.com/test",
                "method": "GET"
            }
        )
        
        update_request = workflow_service_pb2.UpdateWorkflowRequest(
            workflow_id=workflow_id,
            name="Updated CRUD Workflow",
            description="Updated description for testing",
            nodes=[trigger_node, action_node],
            connections=connections,
            settings=settings,
            static_data={"test_key": "test_value"},
            tags=["test", "crud", "updated"],
            active=True,
            user_id=user_id
        )
        
        try:
            update_response = stub.UpdateWorkflow(update_request)
            if update_response.success:
                print(f"✅ Workflow updated successfully")
                print(f"   New name: {update_response.workflow.name}")
                print(f"   New description: {update_response.workflow.description}")
                print(f"   Node count: {len(update_response.workflow.nodes)}")
                print(f"   Updated tags: {list(update_response.workflow.tags)}")
            else:
                print(f"❌ Failed to update workflow: {update_response.message}")
        except grpc.RpcError as e:
            print(f"❌ Error updating workflow: {e.details()}")
        
        # Step 5: List workflows again to see the updated one
        print("\n📋 Step 5: List workflows after update")
        try:
            list_response = stub.ListWorkflows(list_request)
            print(f"✅ Found {list_response.total_count} workflows")
            for workflow in list_response.workflows:
                print(f"   - {workflow.id}: {workflow.name} (Active: {workflow.active})")
                if workflow.id == workflow_id:
                    print(f"     Tags: {list(workflow.tags)}")
        except grpc.RpcError as e:
            print(f"❌ Error listing workflows: {e.details()}")
        
        # Step 6: Delete the workflow
        print("\n📋 Step 6: Delete the workflow")
        delete_request = workflow_service_pb2.DeleteWorkflowRequest(
            workflow_id=workflow_id,
            user_id=user_id
        )
        
        try:
            delete_response = stub.DeleteWorkflow(delete_request)
            if delete_response.success:
                print(f"✅ Workflow deleted successfully")
            else:
                print(f"❌ Failed to delete workflow: {delete_response.message}")
        except grpc.RpcError as e:
            print(f"❌ Error deleting workflow: {e.details()}")
        
        # Step 7: Verify deletion
        print("\n📋 Step 7: Verify deletion")
        try:
            get_response = stub.GetWorkflow(get_request)
            if get_response.found:
                print(f"❌ Workflow still exists after deletion")
            else:
                print(f"✅ Workflow successfully deleted")
        except grpc.RpcError as e:
            print(f"❌ Error verifying deletion: {e.details()}")
        
        print("\n✅ Workflow CRUD test completed!")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        channel.close()

if __name__ == "__main__":
    test_workflow_crud() 