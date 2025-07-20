"""
gRPC Client for Workflow Service (MVP Placeholder)
"""

import asyncio
from typing import AsyncGenerator, Dict, Any
from app.config import settings
from app.utils import log_info, log_warning, log_error, log_debug

# MVP: gRPC is not yet implemented, using mock client
# TODO: Uncomment when gRPC dependencies are added
# import grpc


class WorkflowGRPCClient:
    """
    MVP placeholder for gRPC client
    TODO: Implement actual gRPC client once IDL is confirmed
    """
    
    def __init__(self):
        self.host = settings.WORKFLOW_SERVICE_HOST
        self.port = settings.WORKFLOW_SERVICE_PORT
        self.connected = False
    
    async def connect(self):
        """
        Connect to workflow service
        TODO: Implement actual gRPC connection
        """
        try:
            # Mock connection for MVP
            await asyncio.sleep(0.1)
            self.connected = True
            if settings.DEBUG:
                log_info(f"Mock connected to workflow service at {self.host}:{self.port}")
        except Exception as e:
            if settings.DEBUG:
                log_error(f"Failed to connect to workflow service: {e}")
            self.connected = False
    
    async def close(self):
        """Close gRPC connection"""
        self.connected = False
        if settings.DEBUG:
            log_info("Closed workflow service connection")
    
    async def generate_workflow_stream(self, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate workflow with streaming progress
        TODO: Replace with actual gRPC streaming call
        """
        if not self.connected:
            await self.connect()
        
        # Mock implementation for MVP
        stages = [
            {"type": "waiting", "message": "Analyzing requirements"},
            {"type": "start", "workflow_id": f"wf_{session_id[:8]}", "message": "Starting generation"},
            {"type": "draft", "workflow_id": f"wf_{session_id[:8]}", "message": "Creating draft"},
            {"type": "debugging", "workflow_id": f"wf_{session_id[:8]}", "message": "Optimizing workflow"},
            {"type": "complete", "workflow_id": f"wf_{session_id[:8]}", "message": "Generation complete"}
        ]
        
        for stage in stages:
            yield {
                "type": stage["type"],
                "workflow_id": stage.get("workflow_id"),
                "data": {
                    "message": stage["message"],
                    "session_id": session_id
                }
            }
            await asyncio.sleep(1.0)
    
    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get workflow by ID
        TODO: Replace with actual gRPC call
        """
        if not self.connected:
            await self.connect()
        
        # Mock implementation for MVP
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "data": {"mock": "workflow data"},
            "created_at": "2025-07-15T10:00:00Z"
        }


# Global gRPC client instance (MVP simplified)
workflow_client = WorkflowGRPCClient()


async def get_workflow_client() -> WorkflowGRPCClient:
    """Get workflow gRPC client instance"""
    return workflow_client