"""
gRPC client for workflow agent service
"""

import asyncio
import grpc
import structlog
from typing import Optional

from core.config import settings

logger = structlog.get_logger()


class WorkflowAgentClient:
    """gRPC client for workflow agent service"""
    
    def __init__(self):
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub = None
        self._connected = False
    
    async def connect(self):
        """Connect to the gRPC server"""
        try:
            server_address = f"{settings.WORKFLOW_SERVICE_HOST}:{settings.WORKFLOW_SERVICE_PORT}"
            self.channel = grpc.aio.insecure_channel(server_address)
            
            # Import here to avoid circular imports
            from proto.workflow_agent_pb2_grpc import WorkflowAgentStub
            self.stub = WorkflowAgentStub(self.channel)
            
            # Test connection
            await self._test_connection()
            self._connected = True
            
            logger.info("✅ gRPC client connected", server_address=server_address)
            
        except Exception as e:
            logger.error("❌ Failed to connect to gRPC server", error=str(e))
            raise
    
    async def _test_connection(self):
        """Test the gRPC connection"""
        try:
            # This will be implemented when we have the actual gRPC service methods
            pass
        except Exception as e:
            raise ConnectionError(f"Failed to connect to workflow agent: {e}")
    
    async def close(self):
        """Close the gRPC connection"""
        if self.channel:
            await self.channel.close()
            self._connected = False
            logger.info("gRPC client disconnected")
    
    @property
    def is_connected(self) -> bool:
        """Check if the client is connected"""
        return self._connected