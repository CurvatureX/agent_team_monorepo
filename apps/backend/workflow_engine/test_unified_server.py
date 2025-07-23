#!/usr/bin/env python3
"""
Test Unified Server - 测试统一gRPC服务器
测试workflow创建、执行和查询的完整流程
"""

import time
import uuid
import logging
from datetime import datetime

import grpc
from google.protobuf.json_format import MessageToDict

# Import protobuf modules
from proto import workflow_service_pb2
from proto import workflow_service_pb2_grpc
from proto import workflow_pb2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UnifiedServerTester:
    """Test the unified gRPC server."""
    
    def __init__(self, host="localhost", port=50051):
        self.host = host
        self.port = port
        self.channel = None
        self.workflow_stub = None
        # 使用固定的UUID进行测试
        self.test_user_id = "00000000-0000-0000-0000-000000000123"  # 固定UUID
        
    def connect(self):
        """Connect to the gRPC server."""
        try:
            address = f"{self.host}:{self.port}"
            logger.info(f"Connecting to gRPC server at {address}")
            
            self.channel = grpc.insecure_channel(address)
            self.workflow_stub = workflow_service_pb2_grpc.WorkflowServiceStub(self.channel)
            
            logger.info("✅ Connected to gRPC server successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to gRPC server: {e}")
            return False
    
    def create_test_workflow(self):
        """Create a test workflow with multiple nodes."""
        try:
            logger.info("Creating test workflow with nodes...")
            
            # Create workflow request
            request = workflow_service_pb2.CreateWorkflowRequest()
            request.name = f"Test Workflow {datetime.now().strftime('%Y%m%d_%H%M%S')}"
            request.description = "A comprehensive test workflow with multiple node types"
            request.user_id = self.test_user_id  # 使用固定UUID
            
            # Add tags
            request.tags.extend(["test", "comprehensive", "unified-server"])
            
            # Add static data
            request.static_data["test_data"] = "This is test static data"
            request.static_data["created_by"] = "unified_server_test"
            
            # Add settings
            request.settings.timeout = 300  # 5 minutes
            # request.settings.retry_count = 3  # 这个字段不存在
            # request.settings.parallel_execution = True  # 这个字段不存在
            
            # Create nodes
            nodes = self._create_test_nodes()
            request.nodes.extend(nodes)
            
            # Create connections
            connections = self._create_test_connections(nodes)
            request.connections.CopyFrom(connections)
            
            # Send request
            response = self.workflow_stub.CreateWorkflow(request)
            
            if response.success:
                logger.info(f"✅ Workflow created successfully: {response.workflow.id}")
                logger.info(f"   Name: {response.workflow.name}")
                logger.info(f"   Nodes: {len(response.workflow.nodes)}")
                logger.info(f"   Connections: {len(response.workflow.connections.connections)}")
                return response.workflow.id
            else:
                logger.error(f"❌ Failed to create workflow: {response.message}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating workflow: {e}")
            return None
    
    def _create_test_nodes(self):
        """Create test nodes of different types."""
        nodes = []
        
        # 1. Trigger Node
        trigger_node = workflow_pb2.Node()
        trigger_node.id = "trigger_001"
        trigger_node.name = "Email Trigger"
        trigger_node.type = workflow_pb2.NodeType.TRIGGER_NODE
        trigger_node.subtype = workflow_pb2.NodeSubtype.TRIGGER_EMAIL
        trigger_node.parameters["email_filter"] = "subject:test"
        trigger_node.parameters["check_interval"] = "60"
        nodes.append(trigger_node)
        
        # 2. AI Agent Node
        ai_node = workflow_pb2.Node()
        ai_node.id = "ai_agent_001"
        ai_node.name = "Content Analyzer"
        ai_node.type = workflow_pb2.NodeType.AI_AGENT_NODE
        ai_node.subtype = workflow_pb2.NodeSubtype.AI_TASK_ANALYZER
        ai_node.parameters["model"] = "gpt-4"
        ai_node.parameters["max_tokens"] = "1000"
        ai_node.parameters["temperature"] = "0.7"
        nodes.append(ai_node)
        
        # 3. Action Node
        action_node = workflow_pb2.Node()
        action_node.id = "action_001"
        action_node.name = "Data Processor"
        action_node.type = workflow_pb2.NodeType.ACTION_NODE
        action_node.subtype = workflow_pb2.NodeSubtype.ACTION_DATA_TRANSFORMATION
        action_node.parameters["operation"] = "filter"
        action_node.parameters["field"] = "priority"
        action_node.parameters["value"] = "high"
        nodes.append(action_node)
        
        # 4. Tool Node
        tool_node = workflow_pb2.Node()
        tool_node.id = "tool_001"
        tool_node.name = "Email Sender"
        tool_node.type = workflow_pb2.NodeType.TOOL_NODE
        tool_node.subtype = workflow_pb2.NodeSubtype.TOOL_EMAIL
        tool_node.parameters["smtp_server"] = "smtp.gmail.com"
        tool_node.parameters["to_recipients"] = "admin@example.com"
        tool_node.parameters["subject_template"] = "Workflow Alert: {status}"
        nodes.append(tool_node)
        
        # 5. Memory Node
        memory_node = workflow_pb2.Node()
        memory_node.id = "memory_001"
        memory_node.name = "Result Storage"
        memory_node.type = workflow_pb2.NodeType.MEMORY_NODE
        memory_node.subtype = workflow_pb2.NodeSubtype.MEMORY_VECTOR_STORE
        memory_node.parameters["collection_name"] = "workflow_results"
        memory_node.parameters["embedding_model"] = "text-embedding-ada-002"
        nodes.append(memory_node)
        
        # 6. Human Loop Node
        human_node = workflow_pb2.Node()
        human_node.id = "human_001"
        human_node.name = "Manual Review"
        human_node.type = workflow_pb2.NodeType.HUMAN_IN_THE_LOOP_NODE
        human_node.subtype = workflow_pb2.NodeSubtype.HUMAN_GMAIL
        human_node.parameters["approvers"] = "manager@example.com,lead@example.com"
        human_node.parameters["timeout_hours"] = "24"
        nodes.append(human_node)
        
        # 7. Flow Node
        flow_node = workflow_pb2.Node()
        flow_node.id = "flow_001"
        flow_node.name = "Conditional Router"
        flow_node.type = workflow_pb2.NodeType.FLOW_NODE
        flow_node.subtype = workflow_pb2.NodeSubtype.FLOW_IF
        flow_node.parameters["condition"] = "priority == 'high'"
        flow_node.parameters["true_branch"] = "high_priority_flow"
        flow_node.parameters["false_branch"] = "normal_flow"
        nodes.append(flow_node)
        
        # 8. Another Action Node
        action_node2 = workflow_pb2.Node()
        action_node2.id = "action_002"
        action_node2.name = "Final Processor"
        action_node2.type = workflow_pb2.NodeType.ACTION_NODE
        action_node2.subtype = workflow_pb2.NodeSubtype.ACTION_DATA_TRANSFORMATION
        action_node2.parameters["aggregation_type"] = "summary"
        action_node2.parameters["output_format"] = "json"
        nodes.append(action_node2)
        
        return nodes
    
    def _create_test_connections(self, nodes):
        """Create connections between nodes."""
        connections_map = workflow_pb2.ConnectionsMap()
        
        # Create a simple linear flow
        node_ids = [node.id for node in nodes]
        
        for i in range(len(node_ids) - 1):
            source_node_id = node_ids[i]
            target_node_id = node_ids[i + 1]
            
            # 创建NodeConnections
            node_connections = workflow_pb2.NodeConnections()
            
            # 创建ConnectionArray
            connection_array = workflow_pb2.ConnectionArray()
            
            # 创建Connection
            connection = workflow_pb2.Connection()
            connection.node = target_node_id  # 目标节点
            connection.type = workflow_pb2.ConnectionType.MAIN  # 连接类型
            connection.index = i  # 端口索引
            
            # 将Connection添加到ConnectionArray
            connection_array.connections.append(connection)
            
            # 将ConnectionArray添加到NodeConnections的connection_types映射
            connection_type_str = workflow_pb2.ConnectionType.Name(workflow_pb2.ConnectionType.MAIN)
            node_connections.connection_types[connection_type_str].CopyFrom(connection_array)
            
            # 将NodeConnections添加到ConnectionsMap
            connections_map.connections[source_node_id].CopyFrom(node_connections)
        
        return connections_map
    
    def execute_workflow(self, workflow_id):
        """Execute a workflow."""
        try:
            logger.info(f"Executing workflow: {workflow_id}")
            
            request = workflow_service_pb2.ExecuteWorkflowRequest()
            request.workflow_id = workflow_id
            request.mode = workflow_service_pb2.ExecutionMode.MANUAL
            request.triggered_by = "unified_server_test"
            request.metadata["test_run"] = "true"
            request.metadata["timestamp"] = str(int(time.time()))
            
            response = self.workflow_stub.ExecuteWorkflow(request)
            
            if response.execution_id:
                logger.info(f"✅ Workflow execution started: {response.execution_id}")
                logger.info(f"   Status: {workflow_service_pb2.ExecutionStatus.Name(response.status)}")
                logger.info(f"   Message: {response.message}")
                return response.execution_id
            else:
                logger.error(f"❌ Failed to execute workflow: {response.message}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error executing workflow: {e}")
            return None
    
    def get_execution_status(self, execution_id):
        """Get execution status."""
        try:
            logger.info(f"Getting execution status: {execution_id}")
            
            request = workflow_service_pb2.GetExecutionStatusRequest()
            request.execution_id = execution_id
            
            response = self.workflow_stub.GetExecutionStatus(request)
            
            if response.found:
                execution = response.execution
                logger.info(f"✅ Execution status retrieved:")
                logger.info(f"   Execution ID: {execution.execution_id}")
                logger.info(f"   Workflow ID: {execution.workflow_id}")
                logger.info(f"   Status: {workflow_service_pb2.ExecutionStatus.Name(execution.status)}")
                logger.info(f"   Mode: {workflow_service_pb2.ExecutionMode.Name(execution.mode)}")
                logger.info(f"   Start Time: {execution.start_time}")
                logger.info(f"   End Time: {execution.end_time}")
                logger.info(f"   Triggered By: {execution.triggered_by}")
                logger.info(f"   Metadata: {dict(execution.metadata)}")
                return True
            else:
                logger.error(f"❌ Execution not found: {response.message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error getting execution status: {e}")
            return False
    
    def get_workflow(self, workflow_id):
        """Get workflow details."""
        try:
            logger.info(f"Getting workflow: {workflow_id}")
            
            request = workflow_service_pb2.GetWorkflowRequest()
            request.workflow_id = workflow_id
            request.user_id = self.test_user_id  # 使用固定UUID
            
            response = self.workflow_stub.GetWorkflow(request)
            
            if response.found:
                workflow = response.workflow
                logger.info(f"✅ Workflow retrieved:")
                logger.info(f"   ID: {workflow.id}")
                logger.info(f"   Name: {workflow.name}")
                logger.info(f"   Description: {workflow.description}")
                logger.info(f"   Active: {workflow.active}")
                logger.info(f"   Version: {workflow.version}")
                logger.info(f"   Nodes: {len(workflow.nodes)}")
                logger.info(f"   Connections: {len(workflow.connections.connections)}")
                logger.info(f"   Tags: {list(workflow.tags)}")
                logger.info(f"   Static Data: {dict(workflow.static_data)}")
                return True
            else:
                logger.error(f"❌ Workflow not found: {response.message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error getting workflow: {e}")
            return False
    
    def list_workflows(self):
        """List all workflows for the user."""
        try:
            logger.info("Listing workflows...")
            
            request = workflow_service_pb2.ListWorkflowsRequest()
            request.user_id = self.test_user_id  # 使用固定UUID
            request.limit = 10
            request.offset = 0
            
            response = self.workflow_stub.ListWorkflows(request)
            
            logger.info(f"✅ Found {len(response.workflows)} workflows:")
            for workflow in response.workflows:
                logger.info(f"   - {workflow.id}: {workflow.name} ({workflow.active})")
            
            return response.workflows
            
        except Exception as e:
            logger.error(f"❌ Error listing workflows: {e}")
            return []
    
    def run_comprehensive_test(self):
        """Run comprehensive test of the unified server."""
        logger.info("🚀 Starting Comprehensive Unified Server Test")
        logger.info("=" * 60)
        
        # 1. Connect to server
        if not self.connect():
            return False
        
        # 2. List existing workflows
        logger.info("\n📋 Step 1: List existing workflows")
        existing_workflows = self.list_workflows()
        
        # 3. Create new workflow
        logger.info("\n🔧 Step 2: Create new workflow with nodes")
        workflow_id = self.create_test_workflow()
        if not workflow_id:
            return False
        
        # 4. Get workflow details
        logger.info("\n📖 Step 3: Get workflow details")
        if not self.get_workflow(workflow_id):
            return False
        
        # 5. Execute workflow
        logger.info("\n▶️ Step 4: Execute workflow")
        execution_id = self.execute_workflow(workflow_id)
        if not execution_id:
            return False
        
        # 6. Get execution status
        logger.info("\n📊 Step 5: Get execution status")
        if not self.get_execution_status(execution_id):
            return False
        
        # 7. List workflows again to see the new one
        logger.info("\n📋 Step 6: List workflows (after creation)")
        updated_workflows = self.list_workflows()
        
        # 8. Summary
        logger.info("\n" + "=" * 60)
        logger.info("🎉 Comprehensive Test Summary:")
        logger.info(f"   ✅ Workflow created: {workflow_id}")
        logger.info(f"   ✅ Workflow executed: {execution_id}")
        logger.info(f"   ✅ Total workflows: {len(updated_workflows)}")
        logger.info("   ✅ All operations completed successfully!")
        logger.info("=" * 60)
        
        return True
    
    def close(self):
        """Close the connection."""
        if self.channel:
            self.channel.close()
            logger.info("Connection closed")

def main():
    """Main test function."""
    tester = UnifiedServerTester()
    
    try:
        success = tester.run_comprehensive_test()
        if success:
            logger.info("🎯 All tests passed! Unified server is working correctly.")
        else:
            logger.error("❌ Some tests failed. Please check the logs.")
            return 1
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return 1
    finally:
        tester.close()
    
    return 0

if __name__ == "__main__":
    exit(main()) 