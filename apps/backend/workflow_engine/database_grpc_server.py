#!/usr/bin/env python3
"""
Database-backed gRPC server for workflow engine
"""

import asyncio
import logging
import signal
import sys
import time
from concurrent import futures
from typing import Optional

import grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import protobuf files
from workflow_engine.proto import workflow_service_pb2_grpc, workflow_service_pb2
from database_service import DatabaseService

class DatabaseWorkflowService(workflow_service_pb2_grpc.WorkflowServiceServicer):
    """Database-backed workflow service."""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    def CreateWorkflow(self, request, context):
        """Create a workflow in database."""
        logger.info(f"CreateWorkflow called with name: {request.name}")
        logger.info(f"Number of nodes: {len(request.nodes)}")
        
        try:
            # Convert protobuf request to dict
            workflow_data = {
                'user_id': request.user_id,
                'name': request.name,
                'description': request.description,
                'active': True,
                'version': '1.0.0',
                'tags': list(request.tags),
                'static_data': dict(request.static_data),
                'nodes': []
            }
            
            # Convert nodes
            for node in request.nodes:
                node_data = {
                    'id': node.id,
                    'name': node.name,
                    'type': node.type,
                    'subtype': node.subtype,
                    'description': node.description,
                    'disabled': node.disabled,
                    'position': {
                        'x': node.position.x,
                        'y': node.position.y
                    },
                    'parameters': dict(node.parameters),
                    'credentials': dict(node.credentials)
                }
                workflow_data['nodes'].append(node_data)
            
            # Create workflow in database
            workflow_id = self.db_service.create_workflow(workflow_data)
            
            # Create response
            response = workflow_service_pb2.CreateWorkflowResponse()
            response.success = True
            response.message = "Workflow created successfully"
            
            # Create workflow object for response
            from workflow_engine.proto import workflow_pb2
            workflow = workflow_pb2.Workflow()
            workflow.id = workflow_id
            workflow.name = request.name
            workflow.description = request.description
            workflow.active = True
            workflow.version = "1.0.0"
            workflow.created_at = int(time.time())
            workflow.updated_at = int(time.time())
            
            # Add nodes to response
            for node in request.nodes:
                workflow.nodes.append(node)
            
            # Add static data and tags
            for key, value in request.static_data.items():
                workflow.static_data[key] = value
            
            workflow.tags.extend(request.tags)
            
            response.workflow.CopyFrom(workflow)
            
            logger.info(f"Workflow created in database: {workflow_id}, Nodes: {len(workflow.nodes)}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to create workflow: {e}")
            response = workflow_service_pb2.CreateWorkflowResponse()
            response.success = False
            response.message = f"Failed to create workflow: {str(e)}"
            return response
    
    def GetWorkflow(self, request, context):
        """Get a workflow from database."""
        logger.info(f"GetWorkflow called with ID: {request.workflow_id}")
        
        try:
            workflow_data = self.db_service.get_workflow(request.workflow_id)
            
            response = workflow_service_pb2.GetWorkflowResponse()
            
            if workflow_data:
                response.found = True
                response.message = "Workflow found"
                
                # Create workflow object
                from workflow_engine.proto import workflow_pb2
                workflow = workflow_pb2.Workflow()
                workflow.id = workflow_data['id']
                workflow.name = workflow_data['name']
                workflow.description = workflow_data['description']
                workflow.active = workflow_data['active']
                workflow.version = workflow_data['version']
                workflow.created_at = workflow_data['created_at']
                workflow.updated_at = workflow_data['updated_at']
                
                # Add nodes
                for node_data in workflow_data['nodes']:
                    node = workflow_pb2.Node()
                    node.id = node_data['node_id']
                    node.name = node_data['name']
                    node.type = node_data['node_type']
                    node.subtype = node_data['node_subtype']
                    node.description = node_data['description']
                    node.disabled = node_data['disabled']
                    node.position.x = node_data['position']['x']
                    node.position.y = node_data['position']['y']
                    
                    # Add parameters and credentials
                    for key, value in node_data['parameters'].items():
                        node.parameters[key] = str(value)
                    
                    for key, value in node_data['credentials'].items():
                        node.credentials[key] = str(value)
                    
                    workflow.nodes.append(node)
                
                # Add static data and tags
                for key, value in workflow_data['static_data'].items():
                    workflow.static_data[key] = str(value)
                
                workflow.tags.extend(workflow_data['tags'])
                
                response.workflow.CopyFrom(workflow)
                logger.info(f"Workflow found: {workflow_data['name']}, Nodes: {len(workflow_data['nodes'])}")
            else:
                response.found = False
                response.message = "Workflow not found"
                logger.warning(f"Workflow not found: {request.workflow_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get workflow: {e}")
            response = workflow_service_pb2.GetWorkflowResponse()
            response.found = False
            response.message = f"Failed to get workflow: {str(e)}"
            return response
    
    def ListWorkflows(self, request, context):
        """List workflows from database."""
        logger.info(f"ListWorkflows called for user: {request.user_id}")
        
        try:
            result = self.db_service.list_workflows(
                user_id=request.user_id,
                limit=request.limit,
                offset=request.offset
            )
            
            response = workflow_service_pb2.ListWorkflowsResponse()
            response.total_count = result['total_count']
            response.has_more = result['has_more']
            
            # Add workflows to response
            for workflow_data in result['workflows']:
                workflow = workflow_service_pb2.WorkflowSummary()
                workflow.id = workflow_data['id']
                workflow.name = workflow_data['name']
                workflow.description = workflow_data['description']
                workflow.active = workflow_data['active']
                workflow.version = workflow_data['version']
                workflow.created_at = workflow_data['created_at']
                workflow.updated_at = workflow_data['updated_at']
                workflow.tags.extend(workflow_data['tags'] or [])
                
                response.workflows.append(workflow)
            
            logger.info(f"Listed {len(result['workflows'])} workflows")
            return response
            
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            response = workflow_service_pb2.ListWorkflowsResponse()
            response.total_count = 0
            response.has_more = False
            return response
    
    def ExecuteWorkflow(self, request, context):
        """Execute a workflow."""
        logger.info(f"ExecuteWorkflow called with ID: {request.workflow_id}")
        
        try:
            # Check if workflow exists
            workflow_data = self.db_service.get_workflow(request.workflow_id)
            if not workflow_data:
                from workflow_engine.proto import execution_pb2
                response = execution_pb2.ExecuteWorkflowResponse()
                response.execution_id = ""
                response.status = execution_pb2.ExecutionStatus.ERROR
                response.message = "Workflow not found"
                return response
            
            # Create execution record
            execution_data = {
                'workflow_id': request.workflow_id,
                'status': 'RUNNING',
                'mode': request.mode,
                'triggered_by': request.triggered_by,
                'input_data': dict(request.input_data),
                'metadata': dict(request.metadata)
            }
            
            execution_id = self.db_service.create_execution(execution_data)
            
            from workflow_engine.proto import execution_pb2
            response = execution_pb2.ExecuteWorkflowResponse()
            response.execution_id = execution_id
            response.status = execution_pb2.ExecutionStatus.RUNNING
            response.message = "Workflow execution started"
            
            logger.info(f"Execution started: {execution_id} for workflow: {workflow_data['name']}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to execute workflow: {e}")
            from workflow_engine.proto import execution_pb2
            response = execution_pb2.ExecuteWorkflowResponse()
            response.execution_id = ""
            response.status = execution_pb2.ExecutionStatus.ERROR
            response.message = f"Failed to execute workflow: {str(e)}"
            return response
    
    def GetExecutionStatus(self, request, context):
        """Get execution status from database."""
        logger.info(f"GetExecutionStatus called with ID: {request.execution_id}")
        
        try:
            execution_data = self.db_service.get_execution(request.execution_id)
            
            from workflow_engine.proto import execution_pb2
            response = execution_pb2.GetExecutionStatusResponse()
            
            if execution_data:
                response.found = True
                response.message = "Execution found"
                
                # Create execution object
                execution = execution_pb2.ExecutionData()
                execution.execution_id = execution_data['execution_id']
                execution.workflow_id = execution_data['workflow_id']
                execution.status = execution_data['status']
                execution.start_time = execution_data['start_time']
                execution.end_time = execution_data['end_time'] or 0
                execution.mode = execution_data['mode']
                execution.triggered_by = execution_data['triggered_by']
                
                # Add metadata
                for key, value in execution_data['metadata'].items():
                    execution.metadata[key] = str(value)
                
                response.execution.CopyFrom(execution)
                logger.info(f"Execution found: {execution_data['execution_id']}, Status: {execution_data['status']}")
            else:
                response.found = False
                response.message = "Execution not found"
                logger.warning(f"Execution not found: {request.execution_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get execution status: {e}")
            from workflow_engine.proto import execution_pb2
            response = execution_pb2.GetExecutionStatusResponse()
            response.found = False
            response.message = f"Failed to get execution status: {str(e)}"
            return response

class DatabaseGRPCServer:
    """Database-backed gRPC server manager."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 50051):
        self.host = host
        self.port = port
        self.server: Optional[grpc.Server] = None
        self.db_service = DatabaseService()
        
    def create_server(self) -> grpc.Server:
        """Create and configure gRPC server."""
        # Create server with thread pool
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=10),
            options=[
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 5000),
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
                ('grpc.http2.min_ping_interval_without_data_ms', 300000),
            ]
        )
        
        # Add services
        workflow_service_pb2_grpc.add_WorkflowServiceServicer_to_server(
            DatabaseWorkflowService(), server
        )
        
        # Add health check service
        from grpc_health.v1 import health_pb2_grpc, health_pb2
        from grpc_health.v1.health import HealthServicer
        health_servicer = HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
        
        # Set all services as serving
        health_servicer.set("", health_pb2.HealthCheckResponse.ServingStatus.SERVING)
        health_servicer.set("WorkflowService", health_pb2.HealthCheckResponse.ServingStatus.SERVING)
        
        # Add listening port
        listen_addr = f"{self.host}:{self.port}"
        server.add_insecure_port(listen_addr)
        
        logger.info(f"Database gRPC server configured to listen on {listen_addr}")
        return server
    
    def start(self):
        """Start the gRPC server."""
        try:
            # Test database connection
            self.db_service.get_connection()
            logger.info("Database connection test successful")
            
            # Create and start server
            self.server = self.create_server()
            self.server.start()
            
            logger.info("Database gRPC server started successfully")
            
            # Set up signal handlers
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, shutting down...")
                self.stop()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Wait for termination
            self.server.wait_for_termination()
            
        except Exception as e:
            logger.error(f"Failed to start database gRPC server: {e}")
            sys.exit(1)
    
    def stop(self):
        """Stop the gRPC server."""
        if self.server:
            logger.info("Stopping database gRPC server...")
            self.server.stop(grace=30)
            logger.info("Database gRPC server stopped")
        
        # Close database connection
        self.db_service.close_connection()

def main():
    """Main entry point."""
    logger.info("Starting Database Workflow Engine gRPC Server")
    
    server = DatabaseGRPCServer()
    server.start()

if __name__ == "__main__":
    main() 