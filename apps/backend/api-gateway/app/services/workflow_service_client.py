"""
gRPC Client for Workflow Service
"""

import asyncio
from typing import Dict, Any, Optional, List

from app.config import settings
from app.utils import log_info, log_error

import grpc
try:
    from proto import workflow_service_pb2
    from proto import workflow_service_pb2_grpc
    from proto import workflow_pb2
    GRPC_AVAILABLE = True
    log_info("✅ Workflow Service gRPC modules loaded successfully")
except ImportError as e:
    log_error(f"❌ Workflow Service gRPC proto modules not available: {e}.")
    workflow_service_pb2 = None
    workflow_service_pb2_grpc = None
    workflow_pb2 = None
    GRPC_AVAILABLE = False


class WorkflowServiceClient:
    """gRPC client for the WorkflowService."""

    def __init__(self):
        self.host = settings.WORKFLOW_ENGINE_HOST
        self.port = settings.WORKFLOW_ENGINE_PORT
        self.channel = None
        self.stub = None
        self.connected = False

    async def connect(self):
        """Connect to workflow service."""
        try:
            if GRPC_AVAILABLE:
                self.channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")
                self.stub = workflow_service_pb2_grpc.WorkflowServiceStub(self.channel)
                await asyncio.wait_for(self.channel.channel_ready(), timeout=5.0)
                self.connected = True
                log_info(f"Connected to WorkflowService at {self.host}:{self.port}")
            else:
                await asyncio.sleep(0.1)
                self.connected = True
                log_info(f"Mock connected to WorkflowService at {self.host}:{self.port}")
        except Exception as e:
            log_error(f"Failed to connect to WorkflowService: {e}")
            self.connected = False
            raise

    async def close(self):
        """Close gRPC connection."""
        if self.channel:
            await self.channel.close()
        self.connected = False
        log_info("Closed WorkflowService connection")

    async def list_all_node_templates(
        self,
        category_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        include_system_templates: bool = True
    ) -> List[Dict[str, Any]]:
        """List all available node templates."""
        if not self.connected:
            await self.connect()

        if not GRPC_AVAILABLE:
            return [] # Return empty list if gRPC is not available

        try:
            node_type_enum = workflow_pb2.NodeType.Value(type_filter) if type_filter else workflow_pb2.NodeType.TRIGGER_NODE
            
            request = workflow_service_pb2.ListAllNodeTemplatesRequest(
                category_filter=category_filter,
                type_filter=node_type_enum,
                include_system_templates=include_system_templates
            )
            log_info(f"gRPC request to ListAllNodeTemplates: {request}")
            response = await self.stub.ListAllNodeTemplates(request)
            log_info(f"gRPC response from ListAllNodeTemplates: {response}")
            
            from google.protobuf.json_format import MessageToDict
            templates_dict = [MessageToDict(t) for t in response.node_templates]
            log_info(f"Converted node templates to dict: {templates_dict}")
            return templates_dict

        except grpc.aio.AioRpcError as e:
            log_error(f"gRPC error listing node templates: {e.details()}")
            return []
        except Exception as e:
            log_error(f"Error listing node templates: {e}")
            return []

# Global instance
workflow_service_client = WorkflowServiceClient()

async def get_workflow_service_client() -> WorkflowServiceClient:
    """Get workflow service gRPC client instance."""
    return workflow_service_client 