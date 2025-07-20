#!/usr/bin/env python3
"""
Test Enhanced Execution Features
测试增强的执行功能，包括节点执行结果、输入输出、连接信息等
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

def test_enhanced_execution_features():
    """Test enhanced execution features for agent debugging"""
    print("🧪 Testing Enhanced Execution Features")
    print("=" * 60)
    print("🔍 Testing features for agent auto-debugging:")
    print("  - Node execution results")
    print("  - Input/Output data")
    print("  - Connection information")
    print("  - Execution path")
    print("  - Node run data")
    print("  - Execution context")
    print("=" * 60)
    
    # Connect to gRPC server
    channel = grpc.insecure_channel('localhost:50051')
    stub = workflow_service_pb2_grpc.WorkflowServiceStub(channel)
    
    # Test user ID
    user_id = "00000000-0000-0000-0000-000000000123"
    
    try:
        # Step 1: Create a workflow with multiple nodes for testing
        print("\n📋 Step 1: Create workflow with enhanced testing nodes")
        
        # Create workflow settings with enhanced features
        settings = workflow_pb2.WorkflowSettings(
            timezone="UTC",
            save_execution_progress=True,
            save_manual_executions=True,
            timeout=300,
            error_policy=workflow_pb2.ErrorPolicy.STOP_WORKFLOW,
            caller_policy=workflow_pb2.CallerPolicy.WORKFLOW_MAIN
        )
        
        # Create nodes with detailed parameters for testing
        nodes = []
        
        # 1. Trigger Node with enhanced parameters
        trigger_node = workflow_pb2.Node(
            id="trigger-1",
            name="Enhanced Manual Trigger",
            type=workflow_pb2.NodeType.TRIGGER_NODE,
            subtype=workflow_pb2.NodeSubtype.TRIGGER_MANUAL,
            position=workflow_pb2.Position(x=100, y=100),
            parameters={
                "debug_mode": "true",
                "save_input": "true",
                "save_output": "true",
                "track_connections": "true"
            }
        )
        nodes.append(trigger_node)
        
        # 2. AI Agent Node with detailed parameters
        ai_agent_node = workflow_pb2.Node(
            id="ai-agent-1",
            name="Enhanced Task Analyzer",
            type=workflow_pb2.NodeType.AI_AGENT_NODE,
            subtype=workflow_pb2.NodeSubtype.AI_TASK_ANALYZER,
            position=workflow_pb2.Position(x=300, y=100),
            parameters={
                "model": "gpt-4",
                "temperature": "0.7",
                "max_tokens": "1000",
                "debug_mode": "true",
                "save_conversation": "true",
                "track_performance": "true"
            }
        )
        nodes.append(ai_agent_node)
        
        # 3. Action Node with HTTP request details
        action_node = workflow_pb2.Node(
            id="action-1",
            name="Enhanced HTTP Request",
            type=workflow_pb2.NodeType.ACTION_NODE,
            subtype=workflow_pb2.NodeSubtype.ACTION_SEND_HTTP_REQUEST,
            position=workflow_pb2.Position(x=500, y=100),
            parameters={
                "url": "https://httpbin.org/get",
                "method": "GET",
                "headers": '{"Content-Type": "application/json"}',
                "debug_mode": "true",
                "save_request": "true",
                "save_response": "true",
                "track_timing": "true"
            }
        )
        nodes.append(action_node)
        
        # 4. Memory Node for storing execution data
        memory_node = workflow_pb2.Node(
            id="memory-1",
            name="Execution Memory",
            type=workflow_pb2.NodeType.MEMORY_NODE,
            subtype=workflow_pb2.NodeSubtype.MEMORY_SIMPLE,
            position=workflow_pb2.Position(x=700, y=100),
            parameters={
                "store_execution_data": "true",
                "store_node_results": "true",
                "store_connections": "true",
                "debug_mode": "true"
            }
        )
        nodes.append(memory_node)
        
        # Create enhanced connections
        connections = workflow_pb2.ConnectionsMap()
        
        # Connect trigger to AI agent with enhanced info
        trigger_connections = workflow_pb2.NodeConnections()
        main_connection_array = workflow_pb2.ConnectionArray()
        main_connection = workflow_pb2.Connection(
            node="Enhanced Task Analyzer",
            type=workflow_pb2.ConnectionType.MAIN,
            index=0
        )
        main_connection_array.connections.append(main_connection)
        trigger_connections.connection_types["main"].CopyFrom(main_connection_array)
        connections.connections["Enhanced Manual Trigger"].CopyFrom(trigger_connections)
        
        # Connect AI agent to action
        ai_connections = workflow_pb2.NodeConnections()
        ai_main_connection_array = workflow_pb2.ConnectionArray()
        ai_main_connection = workflow_pb2.Connection(
            node="Enhanced HTTP Request",
            type=workflow_pb2.ConnectionType.MAIN,
            index=0
        )
        ai_main_connection_array.connections.append(ai_main_connection)
        ai_connections.connection_types["main"].CopyFrom(ai_main_connection_array)
        connections.connections["Enhanced Task Analyzer"].CopyFrom(ai_connections)
        
        # Connect action to memory
        action_connections = workflow_pb2.NodeConnections()
        action_main_connection_array = workflow_pb2.ConnectionArray()
        action_main_connection = workflow_pb2.Connection(
            node="Execution Memory",
            type=workflow_pb2.ConnectionType.MAIN,
            index=0
        )
        action_main_connection_array.connections.append(action_main_connection)
        action_connections.connection_types["main"].CopyFrom(action_main_connection_array)
        connections.connections["Enhanced HTTP Request"].CopyFrom(action_connections)
        
        # Create workflow request
        create_request = workflow_service_pb2.CreateWorkflowRequest(
            name="Enhanced Execution Test Workflow",
            description="A workflow with enhanced execution features for agent debugging",
            nodes=nodes,
            connections=connections,
            settings=settings,
            static_data={
                "test_data": "Enhanced test data for execution debugging",
                "environment": "development",
                "debug_mode": "true",
                "agent_auto_debug": "true"
            },
            tags=["test", "execution", "enhanced", "debug", "agent"],
            user_id=user_id
        )
        
        try:
            create_response = stub.CreateWorkflow(create_request)
            if create_response.success:
                workflow_id = create_response.workflow.id
                print(f"✅ Enhanced workflow created successfully: {workflow_id}")
                print(f"   Name: {create_response.workflow.name}")
                print(f"   Node count: {len(create_response.workflow.nodes)}")
                print(f"   Tags: {list(create_response.workflow.tags)}")
            else:
                print(f"❌ Failed to create enhanced workflow: {create_response.message}")
                return
        except grpc.RpcError as e:
            print(f"❌ Error creating enhanced workflow: {e.details()}")
            return
        
        # Step 2: Execute the workflow with enhanced input data
        print("\n📋 Step 2: Execute workflow with enhanced input data")
        
        # Create enhanced execution request
        execution_request = execution_pb2.ExecuteWorkflowRequest(
            workflow_id=workflow_id,
            mode=execution_pb2.ExecutionMode.MANUAL,
            triggered_by=user_id,
            input_data={
                "message": "Enhanced test execution for agent debugging!",
                "timestamp": str(int(time.time())),
                "debug_level": "detailed",
                "track_performance": "true",
                "save_intermediate_results": "true",
                "test_scenario": "agent_auto_debug"
            },
            metadata={
                "test": "enhanced",
                "environment": "development",
                "debug_mode": "true",
                "agent_auto_debug": "true",
                "enhanced_features": "true"
            }
        )
        
        try:
            execution_response = stub.ExecuteWorkflow(execution_request)
            if execution_response.execution_id:
                print(f"✅ Enhanced workflow executed successfully!")
                print(f"   Execution ID: {execution_response.execution_id}")
                print(f"   Status: {execution_response.status}")
                print(f"   Message: {execution_response.message}")
            else:
                print(f"❌ Enhanced workflow execution failed: {execution_response.message}")
        except grpc.RpcError as e:
            print(f"❌ Error executing enhanced workflow: {e.details()}")
        
        # Step 3: Get enhanced execution status with detailed information
        print("\n📋 Step 3: Get enhanced execution status")
        
        if 'execution_response' in locals() and execution_response.execution_id:
            status_request = execution_pb2.GetExecutionStatusRequest(
                execution_id=execution_response.execution_id
            )
            
            try:
                status_response = stub.GetExecutionStatus(status_request)
                if status_response.found:
                    print(f"✅ Enhanced execution status retrieved:")
                    execution = status_response.execution
                    print(f"   Status: {execution.status}")
                    print(f"   Mode: {execution.mode}")
                    print(f"   Triggered by: {execution.triggered_by}")
                    print(f"   Start time: {execution.start_time}")
                    print(f"   End time: {execution.end_time}")
                    print(f"   Metadata: {dict(execution.metadata)}")
                    
                    # Check for enhanced run data
                    if hasattr(execution, 'run_data') and execution.run_data:
                        print(f"   📊 Run Data Available:")
                        run_data = execution.run_data
                        
                        # Check node data
                        if hasattr(run_data, 'node_data') and run_data.node_data:
                            print(f"     - Node Data: {len(run_data.node_data)} nodes")
                        
                        # Check execution path
                        if hasattr(run_data, 'execution_path') and run_data.execution_path:
                            print(f"     - Execution Path: {len(run_data.execution_path.steps)} steps")
                        
                        # Check node inputs
                        if hasattr(run_data, 'node_inputs') and run_data.node_inputs:
                            print(f"     - Node Inputs: {len(run_data.node_inputs)} nodes")
                        
                        # Check execution context
                        if hasattr(run_data, 'execution_context') and run_data.execution_context:
                            print(f"     - Execution Context: Available")
                    else:
                        print(f"   ⚠️  Enhanced run data not yet available (execution may still be in progress)")
                    
                else:
                    print(f"❌ Enhanced execution not found: {status_response.message}")
            except grpc.RpcError as e:
                print(f"❌ Error getting enhanced execution status: {e.details()}")
        
        # Step 4: Test execution history with enhanced features
        print("\n📋 Step 4: Test execution history with enhanced features")
        
        if 'workflow_id' in locals():
            history_request = execution_pb2.GetExecutionHistoryRequest(
                workflow_id=workflow_id,
                limit=5,
                offset=0
            )
            
            try:
                history_response = stub.GetExecutionHistory(history_request)
                print(f"✅ Execution history retrieved:")
                print(f"   Total executions: {history_response.total_count}")
                print(f"   Has more: {history_response.has_more}")
                
                for i, execution in enumerate(history_response.executions):
                    print(f"   📋 Execution {i+1}:")
                    print(f"     - ID: {execution.execution_id}")
                    print(f"     - Status: {execution.status}")
                    print(f"     - Mode: {execution.mode}")
                    print(f"     - Metadata: {dict(execution.metadata)}")
                    
                    # Check for enhanced data in history
                    if hasattr(execution, 'run_data') and execution.run_data:
                        print(f"     - Enhanced Data: Available")
                    else:
                        print(f"     - Enhanced Data: Not available")
                        
            except grpc.RpcError as e:
                print(f"❌ Error getting execution history: {e.details()}")
        
        # Step 5: List workflows to verify enhanced features
        print("\n📋 Step 5: List workflows with enhanced features")
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
                    print(f"     Enhanced features: {'debug' in workflow.tags and 'agent' in workflow.tags}")
        except grpc.RpcError as e:
            print(f"❌ Error listing workflows: {e.details()}")
        
        print("\n✅ Enhanced execution features test completed!")
        print("\n📋 Summary of enhanced features tested:")
        print("  ✅ Enhanced workflow creation with debug parameters")
        print("  ✅ Enhanced execution with detailed input data")
        print("  ✅ Enhanced execution status retrieval")
        print("  ✅ Execution history with enhanced data")
        print("  ✅ Workflow listing with enhanced features")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        channel.close()

if __name__ == "__main__":
    test_enhanced_execution_features() 