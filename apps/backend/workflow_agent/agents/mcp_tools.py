"""
Optimized MCP (Model Context Protocol) tools with performance logging.
"""

import json
import time
from typing import Any, Dict, List, Optional
import logging
import aiohttp
from langchain_core.tools import Tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class NodeQuery(BaseModel):
    """Query parameters for node details."""
    node_type: str = Field(..., description="Node type (e.g., TRIGGER, AI_AGENT)")
    subtype: str = Field(..., description="Node subtype (e.g., schedule, webhook)")


class GetNodeTypesInput(BaseModel):
    """Input for get_node_types tool."""
    type_filter: Optional[str] = Field(
        None,
        description="Filter by node type (optional). Options: ACTION, TRIGGER, AI_AGENT, FLOW, TOOL, MEMORY, HUMAN_IN_THE_LOOP, EXTERNAL_ACTION"
    )


class GetNodeDetailsInput(BaseModel):
    """Input for get_node_details tool."""
    nodes: List[NodeQuery] = Field(
        ...,
        description="List of nodes to get details for"
    )
    include_examples: bool = Field(
        True,
        description="Include usage examples"
    )
    include_schemas: bool = Field(
        True,
        description="Include input/output schemas"
    )


class MCPToolCaller:
    """
    Optimized MCP client with performance tracking and connection reuse.
    """

    def __init__(self, server_url: str = None, api_key: str = "dev_default"):
        import os
        
        if server_url:
            self.server_url = server_url
        elif os.getenv("API_GATEWAY_URL"):
            api_gateway_url = os.getenv("API_GATEWAY_URL").rstrip("/")
            self.server_url = f"{api_gateway_url}/api/v1/mcp"
        elif os.getenv("WORKFLOW_ENGINE_URL", "").startswith("http://workflow-engine"):
            # We're in Docker, use service name
            self.server_url = "http://api-gateway:8000/api/v1/mcp"
        else:
            # Local development
            self.server_url = "http://localhost:8000/api/v1/mcp"
        
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Singleton session for connection reuse
        self._session = None
        self._session_created_at = None
        
        logger.info(f"🔧 MCP Tool initialized with server URL: {self.server_url}")
    
    async def _get_or_create_session(self):
        """Get existing session or create a new one with optimized settings"""
        start_time = time.time()
        
        if self._session is None:
            logger.info("📊 Creating new aiohttp session with connection pooling")
            
            # Optimized connector settings for faster connections
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool limit
                limit_per_host=50,  # Increased per-host limit
                ttl_dns_cache=600,  # Longer DNS cache (10 minutes)
                keepalive_timeout=60,  # Longer keepalive
                force_close=False,  # Reuse connections
                enable_cleanup_closed=True  # Clean up closed connections
            )
            
            # Shorter timeouts for faster failure detection
            timeout = aiohttp.ClientTimeout(
                total=30,  # Total timeout
                connect=3,  # Connection timeout
                sock_connect=3,  # Socket connection timeout
                sock_read=10  # Socket read timeout
            )
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                trust_env=True  # Trust environment proxy settings
            )
            self._session_created_at = time.time()
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Session created in {elapsed:.3f}s")
        else:
            # Check if session is still valid
            session_age = time.time() - (self._session_created_at or 0)
            logger.debug(f"📊 Reusing existing session (age: {session_age:.1f}s)")
            
        return self._session
    
    async def close(self):
        """Close the session when done"""
        if self._session:
            await self._session.close()
            self._session = None
            self._session_created_at = None
            logger.info("🔚 MCP session closed")

    async def get_node_types(self, type_filter: Optional[str] = None) -> Dict[str, Any]:
        """Get all available workflow node types with performance tracking"""
        total_start = time.time()
        metrics = {}
        
        try:
            # Prepare payload
            payload = {
                "name": "get_node_types",
                "tool_name": "get_node_types",
                "arguments": {}
            }
            
            if type_filter:
                payload["arguments"]["type_filter"] = type_filter
            
            logger.info(f"🔧 MCP Call: get_node_types ({payload['arguments']})")
            
            # Get or create session
            session_start = time.time()
            session = await self._get_or_create_session()
            metrics['session_setup'] = time.time() - session_start
            
            # Make HTTP request
            request_start = time.time()
            logger.info(f"📤 Sending POST request to {self.server_url}/invoke")
            
            async with session.post(
                f"{self.server_url}/invoke",
                json=payload,
                headers=self.headers
            ) as response:
                metrics['request_time'] = time.time() - request_start
                
                # Read response
                read_start = time.time()
                response.raise_for_status()
                result = await response.json()
                metrics['response_read'] = time.time() - read_start
                
                # Process result
                process_start = time.time()
                if "result" in result:
                    actual_result = result["result"]
                    if "structuredContent" in actual_result:
                        final_result = actual_result["structuredContent"]
                    elif "content" in actual_result:
                        content = actual_result["content"]
                        if isinstance(content, list) and content:
                            final_result = {"data": content}
                        else:
                            final_result = result
                    else:
                        final_result = result
                else:
                    final_result = result
                
                metrics['result_processing'] = time.time() - process_start
                metrics['total_time'] = time.time() - total_start
                
                # Log performance metrics
                logger.info(
                    f"✅ MCP Response: {type(final_result).__name__} "
                    f"(session: {metrics['session_setup']:.3f}s, "
                    f"request: {metrics['request_time']:.3f}s, "
                    f"read: {metrics['response_read']:.3f}s, "
                    f"process: {metrics['result_processing']:.3f}s, "
                    f"total: {metrics['total_time']:.3f}s)"
                )
                
                return final_result
                    
        except aiohttp.ClientError as e:
            elapsed = time.time() - total_start
            logger.error(f"❌ MCP request failed after {elapsed:.3f}s: {e}")
            raise
        except Exception as e:
            elapsed = time.time() - total_start
            logger.error(f"❌ MCP error after {elapsed:.3f}s: {e}")
            raise

    async def get_node_details(self, nodes: List[Dict[str, str]], 
                              include_examples: bool = True,
                              include_schemas: bool = True) -> Any:
        """Get detailed specifications for nodes with performance tracking"""
        total_start = time.time()
        metrics = {}
        
        try:
            # Log the nodes being requested (with smart formatting)
            node_summary = ", ".join([f"{n['node_type']}:{n['subtype']}" for n in nodes[:3]])
            if len(nodes) > 3:
                node_summary += f" (+{len(nodes)-3} more)"
            
            logger.info(f"🔧 MCP Call: get_node_details (nodes={len(nodes)} items)")
            logger.info(f"📦 Getting details for {len(nodes)} nodes: {node_summary}")
            
            payload = {
                "name": "get_node_details",
                "tool_name": "get_node_details",
                "arguments": {
                    "nodes": nodes,
                    "include_examples": include_examples,
                    "include_schemas": include_schemas
                }
            }
            
            # Get or create session
            session_start = time.time()
            session = await self._get_or_create_session()
            metrics['session_setup'] = time.time() - session_start
            
            # Make HTTP request
            request_start = time.time()
            logger.info(f"📤 Sending POST request to {self.server_url}/invoke")
            
            async with session.post(
                f"{self.server_url}/invoke",
                json=payload,
                headers=self.headers
            ) as response:
                metrics['request_time'] = time.time() - request_start
                
                # Read response
                read_start = time.time()
                response.raise_for_status()
                result = await response.json()
                metrics['response_read'] = time.time() - read_start
                
                # Process result
                process_start = time.time()
                if "result" in result:
                    actual_result = result["result"]
                    if "structuredContent" in actual_result:
                        nodes_data = actual_result["structuredContent"]
                        if isinstance(nodes_data, dict) and "nodes" in nodes_data:
                            final_result = nodes_data["nodes"]
                        else:
                            final_result = nodes_data
                    else:
                        final_result = result
                else:
                    final_result = result
                
                metrics['result_processing'] = time.time() - process_start
                metrics['total_time'] = time.time() - total_start
                
                # Log performance metrics
                result_count = len(final_result) if isinstance(final_result, list) else 1
                logger.info(
                    f"✅ MCP Response: {result_count} nodes returned "
                    f"(session: {metrics['session_setup']:.3f}s, "
                    f"request: {metrics['request_time']:.3f}s, "
                    f"read: {metrics['response_read']:.3f}s, "
                    f"process: {metrics['result_processing']:.3f}s, "
                    f"total: {metrics['total_time']:.3f}s)"
                )
                
                return final_result
                    
        except Exception as e:
            elapsed = time.time() - total_start
            logger.error(f"❌ MCP get_node_details failed after {elapsed:.3f}s: {e}")
            raise

    async def call_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generic method to call MCP tools by name.
        This is used by the LangChain tool execution logic.
        
        Args:
            tool_name: Name of the tool to call
            tool_args: Arguments for the tool
            
        Returns:
            Dictionary with tool result
        """
        logger.info(f"🔧 MCP Call Tool: {tool_name}")
        
        try:
            if tool_name == "get_node_types":
                type_filter = tool_args.get("type_filter")
                result = await self.get_node_types(type_filter)
            elif tool_name == "get_node_details":
                nodes = tool_args.get("nodes", [])
                include_examples = tool_args.get("include_examples", True)
                include_schemas = tool_args.get("include_schemas", True)
                result = await self.get_node_details(nodes, include_examples, include_schemas)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calling tool {tool_name}: {e}")
            return {"error": str(e)}

    def get_tools(self) -> List[Tool]:
        """Get Langchain tools for MCP operations"""
        
        async def get_node_types_wrapper(type_filter: Optional[str] = None) -> str:
            """Get available node types"""
            result = await self.get_node_types(type_filter)
            return json.dumps(result, indent=2)
        
        async def get_node_details_wrapper(
            nodes: List[Dict[str, str]], 
            include_examples: bool = True,
            include_schemas: bool = True
        ) -> str:
            """Get node details"""
            result = await self.get_node_details(nodes, include_examples, include_schemas)
            return json.dumps(result, indent=2)
        
        return [
            Tool(
                name="get_node_types",
                func=None,
                coroutine=get_node_types_wrapper,
                description="Get all available workflow node types and their subtypes",
                args_schema=GetNodeTypesInput
            ),
            Tool(
                name="get_node_details",
                func=None,
                coroutine=get_node_details_wrapper,
                description="Get detailed specifications for workflow nodes",
                args_schema=GetNodeDetailsInput
            )
        ]


# Singleton instance for connection reuse across requests
_mcp_client_instance = None

def get_mcp_client(server_url: str = None, api_key: str = "dev_default") -> MCPToolCaller:
    """Get or create singleton MCP client for connection reuse"""
    global _mcp_client_instance
    
    if _mcp_client_instance is None:
        _mcp_client_instance = MCPToolCaller(server_url, api_key)
        logger.info("📊 Created singleton MCP client instance")
    
    return _mcp_client_instance