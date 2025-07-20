#!/usr/bin/env python3
"""
Complete System Debug Script
- Starts gRPC server
- Creates test workflow with various node types
- Tests execution with error scenarios
- Validates execution data collection
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List

import grpc
from google.protobuf.json_format import MessageToDict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_workflow():
    """Create a comprehensive test workflow with various node types and error scenarios."""
    from workflow_engine.proto import workflow_pb2
    from workflow_engine.proto import workflow_service_pb2
    
    # Create workflow
    workflow = workflow_service_pb2.CreateWorkflowRequest()
    workflow.name = "Comprehensive Test Workflow"
    workflow.description = "A test workflow with various node types and error scenarios"
    workflow.user_id = "test-user-123"
    
    # Add nodes with various types and error scenarios
    nodes = []
    
    # 1. TRIGGER_NODE - Manual trigger (success)
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
    
    # 2. AI_AGENT_NODE - Success case
    ai_agent_success = workflow_pb2.Node()
    ai_agent_success.id = "ai_agent_success"
    ai_agent_success.name = "AI Agent Success"
    ai_agent_success.type = workflow_pb2.NodeType.AI_AGENT_NODE
    ai_agent_success.subtype = workflow_pb2.NodeSubtype.AI_TASK_ANALYZER
    ai_agent_success.parameters["model"] = "gpt-4"
    ai_agent_success.parameters["temperature"] = "0.7"
    ai_agent_success.parameters["max_tokens"] = "1000"
    ai_agent_success.parameters["task"] = "Analyze the input data and provide insights"
    ai_agent_success.position.x = 300
    ai_agent_success.position.y = 100
    nodes.append(ai_agent_success)
    
    # 3. AI_AGENT_NODE - Error case (invalid API key)
    ai_agent_error = workflow_pb2.Node()
    ai_agent_error.id = "ai_agent_error"
    ai_agent_error.name = "AI Agent Error"
    ai_agent_error.type = workflow_pb2.NodeType.AI_AGENT_NODE
    ai_agent_error.subtype = workflow_pb2.NodeSubtype.AI_ROUTER_AGENT
    ai_agent_error.parameters["model"] = "gpt-4"
    ai_agent_error.parameters["api_key"] = "invalid_key_that_will_fail"
    ai_agent_error.parameters["temperature"] = "0.5"
    ai_agent_error.parameters["max_tokens"] = "500"
    ai_agent_error.position.x = 500
    ai_agent_error.position.y = 100
    nodes.append(ai_agent_error)
    
    # 4. ACTION_NODE - HTTP request success
    action_http_success = workflow_pb2.Node()
    action_http_success.id = "action_http_success"
    action_http_success.name = "HTTP Request Success"
    action_http_success.type = workflow_pb2.NodeType.ACTION_NODE
    action_http_success.subtype = workflow_pb2.NodeSubtype.ACTION_SEND_HTTP_REQUEST
    action_http_success.parameters["method"] = "GET"
    action_http_success.parameters["url"] = "https://httpbin.org/get"
    action_http_success.parameters["timeout"] = "30"
    action_http_success.parameters["headers"] = '{"User-Agent": "WorkflowEngine/1.0"}'
    action_http_success.position.x = 300
    action_http_success.position.y = 250
    nodes.append(action_http_success)
    
    # 5. ACTION_NODE - HTTP request error (404)
    action_http_error = workflow_pb2.Node()
    action_http_error.id = "action_http_error"
    action_http_error.name = "HTTP Request Error"
    action_http_error.type = workflow_pb2.NodeType.ACTION_NODE
    action_http_error.subtype = workflow_pb2.NodeSubtype.ACTION_SEND_HTTP_REQUEST
    action_http_error.parameters["method"] = "GET"
    action_http_error.parameters["url"] = "https://httpbin.org/nonexistent"
    action_http_error.parameters["timeout"] = "30"
    action_http_error.position.x = 500
    action_http_error.position.y = 250
    nodes.append(action_http_error)
    
    # 6. FLOW_NODE - If condition
    flow_if_condition = workflow_pb2.Node()
    flow_if_condition.id = "flow_if_condition"
    flow_if_condition.name = "If Condition"
    flow_if_condition.type = workflow_pb2.NodeType.FLOW_NODE
    flow_if_condition.subtype = workflow_pb2.NodeSubtype.FLOW_IF
    flow_if_condition.parameters["condition_type"] = "javascript"
    flow_if_condition.parameters["condition_expression"] = "return input.status === 'success';"
    flow_if_condition.position.x = 700
    flow_if_condition.position.y = 100
    nodes.append(flow_if_condition)
    
    # 7. TOOL_NODE - Success case
    tool_http_success = workflow_pb2.Node()
    tool_http_success.id = "tool_http_success"
    tool_http_success.name = "HTTP Tool Success"
    tool_http_success.type = workflow_pb2.NodeType.TOOL_NODE
    tool_http_success.subtype = workflow_pb2.NodeSubtype.TOOL_HTTP
    tool_http_success.parameters["url"] = "https://httpbin.org/json"
    tool_http_success.parameters["method"] = "GET"
    tool_http_success.parameters["timeout"] = "30"
    tool_http_success.position.x = 300
    tool_http_success.position.y = 400
    nodes.append(tool_http_success)
    
    # 8. MEMORY_NODE - Buffer memory
    memory_buffer = workflow_pb2.Node()
    memory_buffer.id = "memory_buffer"
    memory_buffer.name = "Buffer Memory"
    memory_buffer.type = workflow_pb2.NodeType.MEMORY_NODE
    memory_buffer.subtype = workflow_pb2.NodeSubtype.MEMORY_BUFFER
    memory_buffer.parameters["max_token_limit"] = "2000"
    memory_buffer.parameters["return_messages"] = "true"
    memory_buffer.position.x = 500
    memory_buffer.position.y = 400
    nodes.append(memory_buffer)
    
    # 9. HUMAN_IN_THE_LOOP_NODE - Timeout scenario
    human_approval_timeout = workflow_pb2.Node()
    human_approval_timeout.id = "human_approval_timeout"
    human_approval_timeout.name = "Human Approval Timeout"
    human_approval_timeout.type = workflow_pb2.NodeType.HUMAN_IN_THE_LOOP_NODE
    human_approval_timeout.subtype = workflow_pb2.NodeSubtype.HUMAN_SLACK
    human_approval_timeout.parameters["approval_channel"] = "#test-approvals"
    human_approval_timeout.parameters["timeout_minutes"] = "1"
    human_approval_timeout.parameters["auto_approve_after_timeout"] = "false"
    human_approval_timeout.position.x = 700
    human_approval_timeout.position.y = 400
    nodes.append(human_approval_timeout)
    
    # 10. EXTERNAL_ACTION_NODE - Error case (invalid credentials)
    external_slack_error = workflow_pb2.Node()
    external_slack_error.id = "external_slack_error"
    external_slack_error.name = "Slack Action Error"
    external_slack_error.type = workflow_pb2.NodeType.EXTERNAL_ACTION_NODE
    external_slack_error.subtype = workflow_pb2.NodeSubtype.EXTERNAL_SLACK
    external_slack_error.parameters["action_type"] = "send_message"
    external_slack_error.parameters["channel"] = "#test-channel"
    external_slack_error.parameters["message"] = "Test message"
    external_slack_error.parameters["token"] = "invalid_slack_token"
    external_slack_error.position.x = 900
    external_slack_error.position.y = 100
    nodes.append(external_slack_error)
    
    workflow.nodes.extend(nodes)
    
    # Add static data
    workflow.static_data["test_data"] = "This is static test data"
    workflow.static_data["config"] = '{"api_timeout": 30, "max_retries": 3}'
    
    # Add tags
    workflow.tags.extend(["test", "debug", "comprehensive"])
    
    return workflow

def test_workflow_creation(stub):
    """Test workflow creation."""
    logger.info("=== TESTING WORKFLOW CREATION ===")
    
    try:
        # Create test workflow
        workflow_request = create_test_workflow()
        
        # Call CreateWorkflow
        response = stub.CreateWorkflow(workflow_request)
        
        if response.success:
            logger.info(f"✅ Workflow created successfully: {response.workflow.id}")
            logger.info(f"   Name: {response.workflow.name}")
            logger.info(f"   Nodes: {len(response.workflow.nodes)}")
            logger.info(f"   Message: {response.message}")
            return response.workflow.id
        else:
            logger.error(f"❌ Failed to create workflow: {response.message}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Workflow creation failed: {e}")
        return None

def test_workflow_execution(stub, workflow_id):
    """Test workflow execution."""
    logger.info("=== TESTING WORKFLOW EXECUTION ===")
    
    try:
        from workflow_engine.proto import execution_pb2
        
        # Create execution request
        request = execution_pb2.ExecuteWorkflowRequest()
        request.workflow_id = workflow_id
        request.mode = execution_pb2.ExecutionMode.MANUAL
        request.triggered_by = "test-user-123"
        request.input_data["test_input"] = "test_value"
        request.metadata["debug_mode"] = "true"
        
        # Execute workflow
        response = stub.ExecuteWorkflow(request)
        
        logger.info(f"✅ Workflow execution started: {response.execution_id}")
        logger.info(f"   Status: {response.status}")
        logger.info(f"   Message: {response.message}")
        
        return response.execution_id
        
    except Exception as e:
        logger.error(f"❌ Workflow execution failed: {e}")
        return None

def test_execution_status(stub, execution_id):
    """Test execution status retrieval."""
    logger.info("=== TESTING EXECUTION STATUS ===")
    
    try:
        from workflow_engine.proto import execution_pb2
        
        # Get execution status
        request = execution_pb2.GetExecutionStatusRequest()
        request.execution_id = execution_id
        
        response = stub.GetExecutionStatus(request)
        
        if response.found:
            logger.info(f"✅ Execution status retrieved: {response.execution.status}")
            logger.info(f"   Message: {response.message}")
            
            # Log execution details
            execution = response.execution
            logger.info(f"   Workflow ID: {execution.workflow_id}")
            logger.info(f"   Start Time: {execution.start_time}")
            logger.info(f"   End Time: {execution.end_time}")
            logger.info(f"   Mode: {execution.mode}")
            logger.info(f"   Triggered By: {execution.triggered_by}")
            
            # Log run data if available
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
            logger.error(f"❌ Execution not found: {response.message}")
            
    except Exception as e:
        logger.error(f"❌ Execution status retrieval failed: {e}")

def test_workflow_operations(stub, workflow_id):
    """Test other workflow operations."""
    logger.info("=== TESTING WORKFLOW OPERATIONS ===")
    
    try:
        from workflow_engine.proto import workflow_service_pb2
        
        # Test GetWorkflow
        get_request = workflow_service_pb2.GetWorkflowRequest()
        get_request.workflow_id = workflow_id
        get_request.user_id = "test-user-123"
        
        get_response = stub.GetWorkflow(get_request)
        
        if get_response.found:
            logger.info(f"✅ Workflow retrieved: {get_response.workflow.name}")
        else:
            logger.error(f"❌ Workflow not found: {get_response.message}")
        
        # Test ListWorkflows
        list_request = workflow_service_pb2.ListWorkflowsRequest()
        list_request.user_id = "test-user-123"
        list_request.active_only = True
        list_request.limit = 10
        list_request.offset = 0
        
        list_response = stub.ListWorkflows(list_request)
        
        logger.info(f"✅ Listed {list_response.total_count} workflows")
        logger.info(f"   Has more: {list_response.has_more}")
        
        for i, wf in enumerate(list_response.workflows):
            logger.info(f"   Workflow {i+1}: {wf.name} (ID: {wf.id})")
            
    except Exception as e:
        logger.error(f"❌ Workflow operations failed: {e}")

def main():
    """Main debug function."""
    logger.info("=== COMPLETE SYSTEM DEBUG ===")
    
    try:
        # Import protobuf modules
        from workflow_engine.proto import workflow_service_pb2_grpc, workflow_service_pb2
        
        # Create gRPC channel
        channel = grpc.insecure_channel("localhost:50051")
        stub = workflow_service_pb2_grpc.WorkflowServiceStub(channel)
        
        # Test health check
        from grpc_health.v1 import health_pb2_grpc, health_pb2
        health_stub = health_pb2_grpc.HealthStub(channel)
        
        health_response = health_stub.Check(health_pb2.HealthCheckRequest())
        logger.info(f"✅ Health check: {health_response.status}")
        
        # Test workflow creation
        workflow_id = test_workflow_creation(stub)
        
        if workflow_id:
            # Test workflow operations
            test_workflow_operations(stub, workflow_id)
            
            # Test workflow execution
            execution_id = test_workflow_execution(stub, workflow_id)
            
            if execution_id:
                # Wait a bit for execution to progress
                time.sleep(2)
                
                # Test execution status
                test_execution_status(stub, execution_id)
        
        logger.info("=== DEBUG COMPLETED ===")
        
    except Exception as e:
        logger.error(f"❌ Debug failed: {e}")

if __name__ == "__main__":
    main() 