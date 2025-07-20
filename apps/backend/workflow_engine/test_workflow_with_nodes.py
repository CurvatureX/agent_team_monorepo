#!/usr/bin/env python3
"""
Test workflow with actual nodes
"""

import os
import sys
import time
import logging
import grpc
from workflow_engine.proto import workflow_service_pb2_grpc, workflow_service_pb2, workflow_pb2
from workflow_engine.proto import execution_pb2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_workflow_with_nodes():
    """Create a workflow with various node types."""
    logger.info("=== CREATING WORKFLOW WITH NODES ===")
    
    # Create workflow request
    workflow_request = workflow_service_pb2.CreateWorkflowRequest()
    workflow_request.name = "Test Workflow with Nodes"
    workflow_request.description = "A comprehensive test workflow with various node types"
    workflow_request.user_id = "00000000-0000-0000-0000-000000000123"
    
    # Add nodes
    nodes = []
    
    # 1. TRIGGER_NODE - Manual trigger
    trigger_node = workflow_pb2.Node()
    trigger_node.id = "trigger_manual"
    trigger_node.name = "Manual Trigger"
    trigger_node.type = workflow_pb2.NodeType.TRIGGER_NODE
    trigger_node.subtype = workflow_pb2.NodeSubtype.TRIGGER_MANUAL
    trigger_node.parameters["require_confirmation"] = "false"
    trigger_node.parameters["trigger_data"] = "test_trigger_data"
    trigger_node.position.x = 100
    trigger_node.position.y = 100
    nodes.append(trigger_node)
    
    # 2. AI_AGENT_NODE - Task analyzer
    ai_agent_node = workflow_pb2.Node()
    ai_agent_node.id = "ai_agent_analyzer"
    ai_agent_node.name = "AI Task Analyzer"
    ai_agent_node.type = workflow_pb2.NodeType.AI_AGENT_NODE
    ai_agent_node.subtype = workflow_pb2.NodeSubtype.AI_TASK_ANALYZER
    ai_agent_node.parameters["model"] = "gpt-4"
    ai_agent_node.parameters["temperature"] = "0.7"
    ai_agent_node.parameters["max_tokens"] = "1000"
    ai_agent_node.parameters["task"] = "Analyze the input data and provide insights"
    ai_agent_node.position.x = 300
    ai_agent_node.position.y = 100
    nodes.append(ai_agent_node)
    
    # 3. ACTION_NODE - HTTP request
    action_node = workflow_pb2.Node()
    action_node.id = "action_http_request"
    action_node.name = "HTTP Request"
    action_node.type = workflow_pb2.NodeType.ACTION_NODE
    action_node.subtype = workflow_pb2.NodeSubtype.ACTION_SEND_HTTP_REQUEST
    action_node.parameters["method"] = "GET"
    action_node.parameters["url"] = "https://httpbin.org/get"
    action_node.parameters["timeout"] = "30"
    action_node.parameters["headers"] = '{"User-Agent": "WorkflowEngine/1.0"}'
    action_node.position.x = 500
    action_node.position.y = 100
    nodes.append(action_node)
    
    # 4. FLOW_NODE - If condition
    flow_node = workflow_pb2.Node()
    flow_node.id = "flow_if_condition"
    flow_node.name = "If Condition"
    flow_node.type = workflow_pb2.NodeType.FLOW_NODE
    flow_node.subtype = workflow_pb2.NodeSubtype.FLOW_IF
    flow_node.parameters["condition_type"] = "javascript"
    flow_node.parameters["condition_expression"] = "return input.status === 'success';"
    flow_node.position.x = 700
    flow_node.position.y = 100
    nodes.append(flow_node)
    
    # 5. TOOL_NODE - HTTP tool
    tool_node = workflow_pb2.Node()
    tool_node.id = "tool_http"
    tool_node.name = "HTTP Tool"
    tool_node.type = workflow_pb2.NodeType.TOOL_NODE
    tool_node.subtype = workflow_pb2.NodeSubtype.TOOL_HTTP
    tool_node.parameters["url"] = "https://httpbin.org/json"
    tool_node.parameters["method"] = "GET"
    tool_node.parameters["timeout"] = "30"
    tool_node.position.x = 300
    tool_node.position.y = 250
    nodes.append(tool_node)
    
    # 6. MEMORY_NODE - Buffer memory
    memory_node = workflow_pb2.Node()
    memory_node.id = "memory_buffer"
    memory_node.name = "Buffer Memory"
    memory_node.type = workflow_pb2.NodeType.MEMORY_NODE
    memory_node.subtype = workflow_pb2.NodeSubtype.MEMORY_BUFFER
    memory_node.parameters["max_token_limit"] = "2000"
    memory_node.parameters["return_messages"] = "true"
    memory_node.position.x = 500
    memory_node.position.y = 250
    nodes.append(memory_node)
    
    # 7. HUMAN_IN_THE_LOOP_NODE - Slack approval
    human_node = workflow_pb2.Node()
    human_node.id = "human_slack_approval"
    human_node.name = "Slack Approval"
    human_node.type = workflow_pb2.NodeType.HUMAN_IN_THE_LOOP_NODE
    human_node.subtype = workflow_pb2.NodeSubtype.HUMAN_SLACK
    human_node.parameters["approval_channel"] = "#test-approvals"
    human_node.parameters["timeout_minutes"] = "5"
    human_node.parameters["auto_approve_after_timeout"] = "false"
    human_node.position.x = 700
    human_node.position.y = 250
    nodes.append(human_node)
    
    # 8. EXTERNAL_ACTION_NODE - Slack message
    external_node = workflow_pb2.Node()
    external_node.id = "external_slack_message"
    external_node.name = "Slack Message"
    external_node.type = workflow_pb2.NodeType.EXTERNAL_ACTION_NODE
    external_node.subtype = workflow_pb2.NodeSubtype.EXTERNAL_SLACK
    external_node.parameters["action_type"] = "send_message"
    external_node.parameters["channel"] = "#test-channel"
    external_node.parameters["message"] = "Workflow completed successfully!"
    external_node.position.x = 900
    external_node.position.y = 100
    nodes.append(external_node)
    
    # Add nodes to workflow
    workflow_request.nodes.extend(nodes)
    
    # Add static data
    workflow_request.static_data["test_data"] = "This is static test data"
    workflow_request.static_data["config"] = '{"api_timeout": 30, "max_retries": 3}'
    
    # Add tags
    workflow_request.tags.extend(["test", "comprehensive", "nodes"])
    
    return workflow_request

def test_workflow_with_nodes():
    """Test workflow with actual nodes."""
    logger.info("=== TESTING WORKFLOW WITH NODES ===")
    
    try:
        # Create gRPC channel
        channel = grpc.insecure_channel("localhost:50051")
        stub = workflow_service_pb2_grpc.WorkflowServiceStub(channel)
        
        # Test health check
        from grpc_health.v1 import health_pb2_grpc, health_pb2
        health_stub = health_pb2_grpc.HealthStub(channel)
        
        health_response = health_stub.Check(health_pb2.HealthCheckRequest())
        logger.info(f"✅ Health check: {health_response.status}")
        
        # Create workflow with nodes
        workflow_request = create_workflow_with_nodes()
        
        logger.info(f"Creating workflow with {len(workflow_request.nodes)} nodes...")
        response = stub.CreateWorkflow(workflow_request)
        
        if response.success:
            workflow_id = response.workflow.id
            logger.info(f"✅ Workflow created successfully: {workflow_id}")
            logger.info(f"   Name: {response.workflow.name}")
            logger.info(f"   Nodes: {len(response.workflow.nodes)}")
            logger.info(f"   Message: {response.message}")
            
            # Log node details
            logger.info("   Node details:")
            for i, node in enumerate(response.workflow.nodes):
                logger.info(f"     {i+1}. {node.name} ({node.type}) - {node.subtype}")
                logger.info(f"        ID: {node.id}, Position: ({node.position.x}, {node.position.y})")
                logger.info(f"        Parameters: {len(node.parameters)} items")
            
            # Test GetWorkflow
            get_request = workflow_service_pb2.GetWorkflowRequest()
            get_request.workflow_id = workflow_id
            get_request.user_id = "00000000-0000-0000-0000-000000000123"
            
            get_response = stub.GetWorkflow(get_request)
            if get_response.found:
                logger.info(f"✅ Workflow retrieved: {get_response.workflow.name}")
                logger.info(f"   Active: {get_response.workflow.active}")
                logger.info(f"   Version: {get_response.workflow.version}")
                logger.info(f"   Tags: {list(get_response.workflow.tags)}")
            else:
                logger.error(f"❌ Workflow not found: {get_response.message}")
            
            # Test ListWorkflows
            list_request = workflow_service_pb2.ListWorkflowsRequest()
            list_request.user_id = "00000000-0000-0000-0000-000000000123"
            list_request.active_only = True
            list_request.limit = 10
            list_request.offset = 0
            
            list_response = stub.ListWorkflows(list_request)
            logger.info(f"✅ Listed {list_response.total_count} workflows")
            logger.info(f"   Has more: {list_response.has_more}")
            
            # Test workflow execution
            logger.info("=== TESTING WORKFLOW EXECUTION ===")
            
            exec_request = execution_pb2.ExecuteWorkflowRequest()
            exec_request.workflow_id = workflow_id
            exec_request.mode = execution_pb2.ExecutionMode.MANUAL
            exec_request.triggered_by = "00000000-0000-0000-0000-000000000123"
            exec_request.input_data["test_input"] = "test_value"
            exec_request.input_data["user_id"] = "00000000-0000-0000-0000-000000000123"
            exec_request.metadata["debug_mode"] = "true"
            exec_request.metadata["test_run"] = "true"
            
            exec_response = stub.ExecuteWorkflow(exec_request)
            
            if exec_response.execution_id:
                execution_id = exec_response.execution_id
                logger.info(f"✅ Workflow execution started: {execution_id}")
                logger.info(f"   Status: {exec_response.status}")
                logger.info(f"   Message: {exec_response.message}")
                
                # Wait a bit for execution to progress
                time.sleep(2)
                
                # Test execution status
                status_request = execution_pb2.GetExecutionStatusRequest()
                status_request.execution_id = execution_id
                
                status_response = stub.GetExecutionStatus(status_request)
                
                if status_response.found:
                    execution = status_response.execution
                    logger.info(f"✅ Execution status retrieved: {execution.status}")
                    logger.info(f"   Message: {status_response.message}")
                    logger.info(f"   Workflow ID: {execution.workflow_id}")
                    logger.info(f"   Start Time: {execution.start_time}")
                    logger.info(f"   End Time: {execution.end_time}")
                    logger.info(f"   Mode: {execution.mode}")
                    logger.info(f"   Triggered By: {execution.triggered_by}")
                    
                    # Log execution details if available
                    if execution.HasField('run_data'):
                        run_data = execution.run_data
                        logger.info(f"   Execution Path Steps: {len(run_data.execution_path.steps)}")
                        logger.info(f"   Node Data Entries: {len(run_data.node_data)}")
                        logger.info(f"   Node Inputs: {len(run_data.node_inputs)}")
                        
                        # Log execution path details
                        for i, step in enumerate(run_data.execution_path.steps):
                            logger.info(f"     Step {i+1}: {step.node_name} ({step.node_type}) - {step.status}")
                            if step.HasField('error'):
                                logger.error(f"       Error: {step.error.message}")
                else:
                    logger.error(f"❌ Execution not found: {status_response.message}")
            else:
                logger.error(f"❌ Workflow execution failed: {exec_response.message}")
        else:
            logger.error(f"❌ Failed to create workflow: {response.message}")
        
        logger.info("=== WORKFLOW WITH NODES TEST COMPLETED ===")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_workflow_with_nodes() 