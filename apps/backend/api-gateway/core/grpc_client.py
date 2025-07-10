"""
gRPC client for communicating with Workflow Agent
"""
import asyncio
import grpc
import structlog
from typing import Dict, Any, Optional

from .config import settings
from ..proto import workflow_agent_pb2
from ..proto import workflow_agent_pb2_grpc

logger = structlog.get_logger()


class WorkflowAgentClient:
    """gRPC client for Workflow Agent service"""
    
    def __init__(self):
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub = None
        
    async def connect(self):
        """Connect to the Workflow Agent gRPC service"""
        try:
            server_address = f"{settings.WORKFLOW_AGENT_HOST}:{settings.WORKFLOW_AGENT_PORT}"
            self.channel = grpc.aio.insecure_channel(server_address)
            
            # Create the gRPC stub
            self.stub = workflow_agent_pb2_grpc.WorkflowAgentStub(self.channel)
            
            logger.info("Connected to Workflow Agent", server_address=server_address)
            
        except Exception as e:
            logger.error("Failed to connect to Workflow Agent", error=str(e))
            raise
    
    async def close(self):
        """Close the gRPC connection"""
        if self.channel:
            await self.channel.close()
            logger.info("Closed connection to Workflow Agent")
    
    def _workflow_data_to_dict(self, workflow_data) -> Dict[str, Any]:
        """Convert WorkflowData protobuf to dictionary"""
        if not workflow_data:
            return None
        
        # Convert nodes
        nodes = []
        for node in workflow_data.nodes:
            node_dict = {
                "id": node.id,
                "name": node.name,
                "type": node.type,
                "subtype": node.subtype,
                "type_version": node.type_version,
                "position": {
                    "x": node.position.x,
                    "y": node.position.y
                },
                "disabled": node.disabled,
                "parameters": dict(node.parameters),
                "credentials": dict(node.credentials),
                "on_error": node.on_error,
                "retry_policy": {
                    "max_tries": node.retry_policy.max_tries,
                    "wait_between_tries": node.retry_policy.wait_between_tries
                },
                "notes": dict(node.notes),
                "webhooks": list(node.webhooks)
            }
            nodes.append(node_dict)
        
        # Convert connections
        connections = {"connections": {}}
        for node_name, node_connections in workflow_data.connections.connections.items():
            connections["connections"][node_name] = {}
            for conn_type, conn_array in node_connections.connection_types.items():
                conn_list = []
                for conn in conn_array.connections:
                    conn_list.append({
                        "node": conn.node,
                        "type": conn.type,
                        "index": conn.index
                    })
                connections["connections"][node_name][conn_type] = {"connections": conn_list}
        
        # Convert workflow
        result = {
            "id": workflow_data.id,
            "name": workflow_data.name,
            "active": workflow_data.active,
            "nodes": nodes,
            "connections": connections,
            "settings": {
                "timezone": dict(workflow_data.settings.timezone),
                "save_execution_progress": workflow_data.settings.save_execution_progress,
                "save_manual_executions": workflow_data.settings.save_manual_executions,
                "timeout": workflow_data.settings.timeout,
                "error_policy": workflow_data.settings.error_policy,
                "caller_policy": workflow_data.settings.caller_policy
            },
            "static_data": dict(workflow_data.static_data),
            "pin_data": dict(workflow_data.pin_data),
            "created_at": workflow_data.created_at,
            "updated_at": workflow_data.updated_at,
            "version": workflow_data.version,
            "tags": list(workflow_data.tags)
        }
        
        return result

    async def generate_workflow(self, description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate workflow from natural language description"""
        try:
            if not self.stub:
                raise RuntimeError("gRPC client not connected")
            
            # Create the request
            request = workflow_agent_pb2.WorkflowGenerationRequest(
                description=description,
                context=context or {},
                user_preferences={}
            )
            
            # Call the service
            response = await self.stub.GenerateWorkflow(request)
            
            # Convert response to dictionary
            workflow_dict = None
            if response.workflow:
                workflow_dict = self._workflow_data_to_dict(response.workflow)
            
            return {
                "success": response.success,
                "workflow": workflow_dict,
                "suggestions": list(response.suggestions),
                "missing_info": list(response.missing_info),
                "errors": list(response.errors)
            }
            
        except Exception as e:
            logger.error("Failed to generate workflow", error=str(e))
            raise
    
    async def refine_workflow(self, workflow_id: str, feedback: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Refine existing workflow based on feedback"""
        try:
            if not self.stub:
                raise RuntimeError("gRPC client not connected")
            
            # Create the original workflow protobuf (simplified for now)
            original_workflow = workflow_agent_pb2.WorkflowData(
                id=workflow_data.get("id", ""),
                name=workflow_data.get("name", ""),
                active=workflow_data.get("active", True)
                # Add more fields as needed
            )
            
            # Create the request
            request = workflow_agent_pb2.WorkflowRefinementRequest(
                workflow_id=workflow_id,
                feedback=feedback,
                original_workflow=original_workflow
            )
            
            # Call the service
            response = await self.stub.RefineWorkflow(request)
            
            # Convert response to dictionary
            updated_workflow_dict = None
            if response.updated_workflow:
                updated_workflow_dict = self._workflow_data_to_dict(response.updated_workflow)
            
            return {
                "success": response.success,
                "updated_workflow": updated_workflow_dict,
                "changes": list(response.changes),
                "errors": list(response.errors)
            }
            
        except Exception as e:
            logger.error("Failed to refine workflow", error=str(e))
            raise
    
    async def validate_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow structure and configuration"""
        try:
            if not self.stub:
                raise RuntimeError("gRPC client not connected")
            
            # Create the request (simplified workflow data conversion)
            request = workflow_agent_pb2.WorkflowValidationRequest(
                workflow_data=workflow_data or {}
            )
            
            # Call the service
            response = await self.stub.ValidateWorkflow(request)
            
            return {
                "valid": response.valid,
                "errors": list(response.errors),
                "warnings": list(response.warnings)
            }
            
        except Exception as e:
            logger.error("Failed to validate workflow", error=str(e))
            raise