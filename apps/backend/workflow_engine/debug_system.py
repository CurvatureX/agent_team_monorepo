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

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from proto import (
    workflow_service_pb2,
    workflow_service_pb2_grpc,
    workflow_pb2,
    execution_pb2
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowDebugger:
    """Complete workflow system debugger."""
    
    def __init__(self, grpc_host: str = "localhost", grpc_port: int = 50051):
        self.grpc_host = grpc_host
        self.grpc_port = grpc_port
        self.channel = None
        self.stub = None
        self.test_user_id = None
        self.test_workflow_id = None
        
    def connect(self):
        """Connect to gRPC server."""
        try:
            self.channel = grpc.insecure_channel(f"{self.grpc_host}:{self.grpc_port}")
            self.stub = workflow_service_pb2_grpc.WorkflowServiceStub(self.channel)
            logger.info(f"Connected to gRPC server at {self.grpc_host}:{self.grpc_port}")
        except Exception as e:
            logger.error(f"Failed to connect to gRPC server: {e}")
            raise
    
    def create_test_user(self) -> str:
        """Create a test user for workflow operations."""
        try:
            # Create a test user (simplified - in real system this would be via auth service)
            self.test_user_id = str(uuid.uuid4())
            logger.info(f"Created test user: {self.test_user_id}")
            return self.test_user_id
        except Exception as e:
            logger.error(f"Failed to create test user: {e}")
            raise
    
    def create_comprehensive_workflow(self) -> workflow_pb2.Workflow:
        """Create a comprehensive test workflow with various node types and error scenarios."""
        
        # Create workflow with multiple node types and error scenarios
        workflow = workflow_pb2.Workflow(
            name="Comprehensive Test Workflow",
            description="A test workflow with various node types and error scenarios",
            active=True,
            version="1.0.0",
            created_at=int(time.time()),
            updated_at=int(time.time()),
            settings=workflow_pb2.WorkflowSettings(
                timeout=300
            )
        )
        
        # Add static data
        workflow.static_data["test_data"] = "This is static test data"
        workflow.static_data["config"] = '{"api_timeout": 30, "max_retries": 3}'
        
        # Add pin data
        workflow.pin_data["debug_mode"] = "true"
        workflow.pin_data["test_scenarios"] = '["success", "error", "timeout"]'
        
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
        
        # Add connections between nodes
        connections = []
        
        # Trigger -> AI Agent Success
        conn1 = workflow_pb2.Connection()
        conn1.node = "ai_agent_success"
        conn1.type = workflow_pb2.ConnectionType.MAIN
        conn1.index = 0
        connections.append(conn1)
        
        # Trigger -> AI Agent Error (parallel)
        conn2 = workflow_pb2.Connection()
        conn2.node = "ai_agent_error"
        conn2.type = workflow_pb2.ConnectionType.MAIN
        conn2.index = 1
        connections.append(conn2)
        
        # AI Agent Success -> HTTP Action Success
        conn3 = workflow_pb2.Connection()
        conn3.node = "action_http_success"
        conn3.type = workflow_pb2.ConnectionType.MAIN
        conn3.index = 0
        connections.append(conn3)
        
        # AI Agent Error -> HTTP Action Error
        conn4 = workflow_pb2.Connection()
        conn4.node = "action_http_error"
        conn4.type = workflow_pb2.ConnectionType.MAIN
        conn4.index = 0
        connections.append(conn4)
        
        # HTTP Action Success -> If Condition
        conn5 = workflow_pb2.Connection()
        conn5.node = "flow_if_condition"
        conn5.type = workflow_pb2.ConnectionType.MAIN
        conn5.index = 0
        connections.append(conn5)
        
        # If Condition -> HTTP Tool Success
        conn6 = workflow_pb2.Connection()
        conn6.node = "tool_http_success"
        conn6.type = workflow_pb2.ConnectionType.MAIN
        conn6.index = 0
        connections.append(conn6)
        
        # HTTP Tool Success -> Memory Buffer
        conn7 = workflow_pb2.Connection()
        conn7.node = "memory_buffer"
        conn7.type = workflow_pb2.ConnectionType.MAIN
        conn7.index = 0
        connections.append(conn7)
        
        # Memory Buffer -> Human Approval
        conn8 = workflow_pb2.Connection()
        conn8.node = "human_approval_timeout"
        conn8.type = workflow_pb2.ConnectionType.MAIN
        conn8.index = 0
        connections.append(conn8)
        
        # HTTP Action Error -> External Slack Error
        conn9 = workflow_pb2.Connection()
        conn9.node = "external_slack_error"
        conn9.type = workflow_pb2.ConnectionType.MAIN
        conn9.index = 0
        connections.append(conn9)
        
        # Create connections map
        connections_map = workflow_pb2.ConnectionsMap()
        
        # Add connections to the map
        trigger_connections = workflow_pb2.NodeConnections()
        main_connections = workflow_pb2.ConnectionArray()
        main_connections.connections.extend([conn1, conn2])
        trigger_connections.connection_types["MAIN"] = main_connections
        connections_map.connections["trigger_manual"] = trigger_connections
        
        ai_agent_success_connections = workflow_pb2.NodeConnections()
        main_connections2 = workflow_pb2.ConnectionArray()
        main_connections2.connections.append(conn3)
        ai_agent_success_connections.connection_types["MAIN"] = main_connections2
        connections_map.connections["ai_agent_success"] = ai_agent_success_connections
        
        ai_agent_error_connections = workflow_pb2.NodeConnections()
        main_connections3 = workflow_pb2.ConnectionArray()
        main_connections3.connections.append(conn4)
        ai_agent_error_connections.connection_types["MAIN"] = main_connections3
        connections_map.connections["ai_agent_error"] = ai_agent_error_connections
        
        action_http_success_connections = workflow_pb2.NodeConnections()
        main_connections4 = workflow_pb2.ConnectionArray()
        main_connections4.connections.append(conn5)
        action_http_success_connections.connection_types["MAIN"] = main_connections4
        connections_map.connections["action_http_success"] = action_http_success_connections
        
        action_http_error_connections = workflow_pb2.NodeConnections()
        main_connections5 = workflow_pb2.ConnectionArray()
        main_connections5.connections.append(conn9)
        action_http_error_connections.connection_types["MAIN"] = main_connections5
        connections_map.connections["action_http_error"] = action_http_error_connections
        
        flow_if_condition_connections = workflow_pb2.NodeConnections()
        main_connections6 = workflow_pb2.ConnectionArray()
        main_connections6.connections.append(conn6)
        flow_if_condition_connections.connection_types["MAIN"] = main_connections6
        connections_map.connections["flow_if_condition"] = flow_if_condition_connections
        
        tool_http_success_connections = workflow_pb2.NodeConnections()
        main_connections7 = workflow_pb2.ConnectionArray()
        main_connections7.connections.append(conn7)
        tool_http_success_connections.connection_types["MAIN"] = main_connections7
        connections_map.connections["tool_http_success"] = tool_http_success_connections
        
        memory_buffer_connections = workflow_pb2.NodeConnections()
        main_connections8 = workflow_pb2.ConnectionArray()
        main_connections8.connections.append(conn8)
        memory_buffer_connections.connection_types["MAIN"] = main_connections8
        connections_map.connections["memory_buffer"] = memory_buffer_connections
        
        workflow.connections.CopyFrom(connections_map)
        
        return workflow
    
    def create_workflow_via_grpc(self, workflow: workflow_pb2.Workflow) -> str:
        """Create workflow via gRPC service."""
        try:
            request = workflow_service_pb2.CreateWorkflowRequest(
                workflow=workflow,
                user_id=self.test_user_id
            )
            
            response = self.stub.CreateWorkflow(request)
            
            if response.success:
                self.test_workflow_id = response.workflow_id
                logger.info(f"Created workflow with ID: {self.test_workflow_id}")
                return self.test_workflow_id
            else:
                raise Exception(f"Failed to create workflow: {response.error_message}")
                
        except Exception as e:
            logger.error(f"Failed to create workflow via gRPC: {e}")
            raise
    
    def execute_workflow(self, workflow_id: str) -> str:
        """Execute workflow and return execution ID."""
        try:
            request = workflow_service_pb2.ExecuteWorkflowRequest(
                workflow_id=workflow_id,
                user_id=self.test_user_id,
                mode=execution_pb2.ExecutionMode.MANUAL,
                input_data={
                    "trigger_data": "test_execution_data",
                    "test_scenario": "comprehensive_test"
                }
            )
            
            response = self.stub.ExecuteWorkflow(request)
            
            if response.success:
                execution_id = response.execution_id
                logger.info(f"Started workflow execution: {execution_id}")
                return execution_id
            else:
                raise Exception(f"Failed to execute workflow: {response.error_message}")
                
        except Exception as e:
            logger.error(f"Failed to execute workflow: {e}")
            raise
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status and details."""
        try:
            request = workflow_service_pb2.GetExecutionRequest(
                execution_id=execution_id
            )
            
            response = self.stub.GetExecution(request)
            
            if response.success:
                execution_data = MessageToDict(response.execution_data)
                logger.info(f"Execution status: {execution_data.get('status', 'UNKNOWN')}")
                return execution_data
            else:
                raise Exception(f"Failed to get execution status: {response.error_message}")
                
        except Exception as e:
            logger.error(f"Failed to get execution status: {e}")
            raise
    
    def wait_for_execution_completion(self, execution_id: str, timeout_seconds: int = 300) -> Dict[str, Any]:
        """Wait for execution to complete and return final status."""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                execution_data = self.get_execution_status(execution_id)
                status = execution_data.get('status', 'UNKNOWN')
                
                logger.info(f"Execution {execution_id} status: {status}")
                
                if status in ['SUCCESS', 'ERROR', 'CANCELED']:
                    return execution_data
                
                time.sleep(5)  # Wait 5 seconds before next check
                
            except Exception as e:
                logger.error(f"Error checking execution status: {e}")
                time.sleep(5)
        
        raise TimeoutError(f"Execution {execution_id} did not complete within {timeout_seconds} seconds")
    
    def analyze_execution_results(self, execution_data: Dict[str, Any]):
        """Analyze execution results and validate data collection."""
        logger.info("=== EXECUTION ANALYSIS ===")
        
        # Check basic execution data
        status = execution_data.get('status', 'UNKNOWN')
        logger.info(f"Final Status: {status}")
        
        # Check run data
        run_data = execution_data.get('run_data', {})
        if run_data:
            logger.info("=== RUN DATA ANALYSIS ===")
            
            # Check execution path
            execution_path = run_data.get('execution_path', [])
            logger.info(f"Execution Path Length: {len(execution_path)}")
            for i, step in enumerate(execution_path):
                logger.info(f"  Step {i+1}: {step.get('node_id', 'unknown')} - {step.get('status', 'unknown')}")
            
            # Check node inputs
            node_inputs = run_data.get('node_inputs', {})
            logger.info(f"Node Inputs Collected: {len(node_inputs)}")
            for node_id, inputs in node_inputs.items():
                logger.info(f"  Node {node_id}: {len(inputs)} input records")
            
            # Check performance metrics
            performance_metrics = run_data.get('performance_metrics', {})
            if performance_metrics:
                logger.info("=== PERFORMANCE METRICS ===")
                for node_id, metrics in performance_metrics.items():
                    logger.info(f"  Node {node_id}:")
                    logger.info(f"    Start Time: {metrics.get('start_time', 'N/A')}")
                    logger.info(f"    End Time: {metrics.get('end_time', 'N/A')}")
                    logger.info(f"    Duration: {metrics.get('duration_ms', 'N/A')}ms")
            
            # Check data flow
            data_flow = run_data.get('data_flow', {})
            logger.info(f"Data Flow Records: {len(data_flow)}")
            
            # Check error records
            error_records = run_data.get('error_records', [])
            logger.info(f"Error Records: {len(error_records)}")
            for i, error in enumerate(error_records):
                logger.info(f"  Error {i+1}: {error.get('node_id', 'unknown')} - {error.get('error_type', 'unknown')}")
                logger.info(f"    Message: {error.get('error_message', 'N/A')}")
        
        # Validate expected error scenarios
        self.validate_error_scenarios(execution_data)
    
    def validate_error_scenarios(self, execution_data: Dict[str, Any]):
        """Validate that expected error scenarios occurred."""
        logger.info("=== ERROR SCENARIO VALIDATION ===")
        
        run_data = execution_data.get('run_data', {})
        error_records = run_data.get('error_records', [])
        
        expected_errors = [
            "ai_agent_error",      # Invalid API key
            "action_http_error",   # 404 error
            "external_slack_error", # Invalid credentials
            "human_approval_timeout" # Timeout
        ]
        
        found_errors = [error.get('node_id') for error in error_records]
        
        for expected_error in expected_errors:
            if expected_error in found_errors:
                logger.info(f"✅ Expected error found: {expected_error}")
            else:
                logger.warning(f"⚠️ Expected error not found: {expected_error}")
        
        # Check success scenarios
        execution_path = run_data.get('execution_path', [])
        successful_nodes = [step.get('node_id') for step in execution_path if step.get('status') == 'SUCCESS']
        
        expected_successes = [
            "trigger_manual",
            "ai_agent_success", 
            "action_http_success",
            "tool_http_success",
            "memory_buffer"
        ]
        
        for expected_success in expected_successes:
            if expected_success in successful_nodes:
                logger.info(f"✅ Expected success found: {expected_success}")
            else:
                logger.warning(f"⚠️ Expected success not found: {expected_success}")
    
    def run_complete_test(self):
        """Run complete system test."""
        logger.info("=== STARTING COMPLETE SYSTEM TEST ===")
        
        try:
            # 1. Connect to gRPC server
            self.connect()
            
            # 2. Create test user
            self.create_test_user()
            
            # 3. Create comprehensive workflow
            workflow = self.create_comprehensive_workflow()
            logger.info(f"Created workflow with {len(workflow.nodes)} nodes and {len(workflow.connections)} connections")
            
            # 4. Create workflow via gRPC
            workflow_id = self.create_workflow_via_grpc(workflow)
            
            # 5. Execute workflow
            execution_id = self.execute_workflow(workflow_id)
            
            # 6. Wait for completion
            logger.info("Waiting for execution to complete...")
            execution_data = self.wait_for_execution_completion(execution_id, timeout_seconds=600)
            
            # 7. Analyze results
            self.analyze_execution_results(execution_data)
            
            logger.info("=== SYSTEM TEST COMPLETED SUCCESSFULLY ===")
            
        except Exception as e:
            logger.error(f"System test failed: {e}")
            raise


def start_grpc_server():
    """Start the gRPC server in a separate process."""
    import subprocess
    import time
    
    logger.info("Starting gRPC server...")
    
    # Start server in background
    server_process = subprocess.Popen([
        sys.executable, "-m", "workflow_engine.main"
    ], cwd=os.path.dirname(os.path.abspath(__file__)))
    
    # Wait for server to start
    time.sleep(5)
    
    logger.info(f"gRPC server started with PID: {server_process.pid}")
    return server_process


def main():
    """Main entry point."""
    logger.info("=== WORKFLOW ENGINE SYSTEM DEBUG ===")
    
    # Start gRPC server
    server_process = start_grpc_server()
    
    try:
        # Create debugger and run test
        debugger = WorkflowDebugger()
        debugger.run_complete_test()
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        raise
    
    finally:
        # Clean up
        logger.info("Stopping gRPC server...")
        server_process.terminate()
        server_process.wait()
        logger.info("gRPC server stopped")


if __name__ == "__main__":
    main() 