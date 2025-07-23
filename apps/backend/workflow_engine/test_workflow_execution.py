#!/usr/bin/env python3
"""
Test Workflow Execution with Nodes
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
from workflow_engine.proto import execution_pb2

def test_workflow_execution():
    """Test workflow execution with nodes"""
    print("🧪 Testing Workflow Execution with Nodes")
    print("=" * 50)
    
    # Connect to gRPC server
    channel = grpc.insecure_channel('localhost:50051')
    stub = workflow_service_pb2_grpc.WorkflowServiceStub(channel)
    
    # Test user ID
    user_id = "00000000-0000-0000-0000-000000000123"
    
    try:
        # Step 1: Create a workflow with multiple nodes
        print("\n📋 Step 1: Create workflow with multiple nodes")
        
        # Create workflow settings
        settings = workflow_pb2.WorkflowSettings(
            timezone="UTC",
            save_execution_progress=True,
            save_manual_executions=True,
            timeout=300,
            error_policy=workflow_pb2.ErrorPolicy.STOP_WORKFLOW,
            caller_policy=workflow_pb2.CallerPolicy.WORKFLOW_MAIN
        )
        
        # Create nodes
        nodes = []
        
        # 1. Trigger Node
        trigger_node = workflow_pb2.Node(
            id="trigger-1",
            name="Manual Trigger",
            type=workflow_pb2.NodeType.TRIGGER_NODE,
            subtype=workflow_pb2.NodeSubtype.TRIGGER_MANUAL,
            position=workflow_pb2.Position(x=100, y=100),
            parameters={}
        )
        nodes.append(trigger_node)
        
        # 2. AI Agent Node
        ai_agent_node = workflow_pb2.Node(
            id="ai-agent-1",
            name="Task Analyzer",
            type=workflow_pb2.NodeType.AI_AGENT_NODE,
            subtype=workflow_pb2.NodeSubtype.AI_TASK_ANALYZER,
            position=workflow_pb2.Position(x=300, y=100),
            parameters={
                "model": "gpt-4",
                "temperature": "0.7",
                "max_tokens": "1000"
            }
        )
        nodes.append(ai_agent_node)
        
        # 3. Action Node
        action_node = workflow_pb2.Node(
            id="action-1",
            name="HTTP Request",
            type=workflow_pb2.NodeType.ACTION_NODE,
            subtype=workflow_pb2.NodeSubtype.ACTION_SEND_HTTP_REQUEST,
            position=workflow_pb2.Position(x=500, y=100),
            parameters={
                "url": "https://httpbin.org/get",
                "method": "GET",
                "headers": "{}"
            }
        )
        nodes.append(action_node)
        
        # Create connections
        connections = workflow_pb2.ConnectionsMap()
        
        # Connect trigger to AI agent
        trigger_connections = workflow_pb2.NodeConnections()
        main_connection_array = workflow_pb2.ConnectionArray()
        main_connection = workflow_pb2.Connection(
            node="Task Analyzer",
            type=workflow_pb2.ConnectionType.MAIN,
            index=0
        )
        main_connection_array.connections.append(main_connection)
        trigger_connections.connection_types["main"].CopyFrom(main_connection_array)
        connections.connections["Manual Trigger"].CopyFrom(trigger_connections)
        
        # Connect AI agent to action
        ai_connections = workflow_pb2.NodeConnections()
        ai_main_connection_array = workflow_pb2.ConnectionArray()
        ai_main_connection = workflow_pb2.Connection(
            node="HTTP Request",
            type=workflow_pb2.ConnectionType.MAIN,
            index=0
        )
        ai_main_connection_array.connections.append(ai_main_connection)
        ai_connections.connection_types["main"].CopyFrom(ai_main_connection_array)
        connections.connections["Task Analyzer"].CopyFrom(ai_connections)
        
        # Create workflow request
        create_request = workflow_service_pb2.CreateWorkflowRequest(
            name="Test Execution Workflow",
            description="A workflow with multiple nodes for testing execution",
            nodes=nodes,
            connections=connections,
            settings=settings,
            static_data={
                "test_data": "This is test data for execution",
                "environment": "development"
            },
            tags=["test", "execution", "nodes", "ai"],
            user_id=user_id
        )
        
        try:
            create_response = stub.CreateWorkflow(create_request)
            if create_response.success:
                workflow_id = create_response.workflow.id
                print(f"✅ Workflow created successfully: {workflow_id}")
                print(f"   Name: {create_response.workflow.name}")
                print(f"   Node count: {len(create_response.workflow.nodes)}")
                print(f"   Tags: {list(create_response.workflow.tags)}")
            else:
                print(f"❌ Failed to create workflow: {create_response.message}")
                return
        except grpc.RpcError as e:
            print(f"❌ Error creating workflow: {e.details()}")
            return
        
        # Step 2: Execute the workflow
        print("\n📋 Step 2: Execute the workflow")
        
        # Create execution request
        execution_request = execution_pb2.ExecuteWorkflowRequest(
            workflow_id=workflow_id,
            mode=execution_pb2.ExecutionMode.MANUAL,
            triggered_by=user_id,
            input_data={
                "message": "Hello, this is a test execution!",
                "timestamp": str(int(time.time()))
            },
            metadata={
                "test": "true",
                "environment": "development"
            }
        )
        
        try:
            execution_response = stub.ExecuteWorkflow(execution_request)
            if execution_response.execution_id:
                print(f"✅ Workflow executed successfully!")
                print(f"   Execution ID: {execution_response.execution_id}")
                print(f"   Status: {execution_response.status}")
                print(f"   Message: {execution_response.message}")
            else:
                print(f"❌ Workflow execution failed: {execution_response.message}")
        except grpc.RpcError as e:
            print(f"❌ Error executing workflow: {e.details()}")
        
        # Step 3: Get execution status
        print("\n📋 Step 3: Get execution status")
        
        if 'execution_response' in locals() and execution_response.execution_id:
            status_request = execution_pb2.GetExecutionStatusRequest(
                execution_id=execution_response.execution_id
            )
            
            try:
                status_response = stub.GetExecutionStatus(status_request)
                if status_response.found:
                    print(f"✅ Execution status retrieved:")
                    execution = status_response.execution
                    print(f"   Status: {execution.status}")
                    print(f"   Progress: {execution.start_time}")  # Use start_time as progress indicator
                    print(f"   Result: {dict(execution.metadata)}")  # Use metadata as result
                else:
                    print(f"❌ Execution not found: {status_response.message}")
            except grpc.RpcError as e:
                print(f"❌ Error getting execution status: {e.details()}")
        
        # Step 4: List workflows to see the created one
        print("\n📋 Step 4: List workflows")
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
                    print(f"     Tags: {list(workflow.tags)}")
                    print(f"     Node count: {len(workflow.nodes)}")
        except grpc.RpcError as e:
            print(f"❌ Error listing workflows: {e.details()}")
        
        print("\n✅ Workflow execution test completed!")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        channel.close()

if __name__ == "__main__":
    test_workflow_execution() 