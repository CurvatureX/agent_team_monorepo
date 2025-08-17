"""
MCP (Model Context Protocol) tools for workflow generation.
Provides tools for discovering and retrieving workflow node specifications.
"""

import json
from typing import Any, Dict, List, Optional
import logging
import aiohttp
from langchain_core.tools import Tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class NodeQuery(BaseModel):
    """Query parameters for node details."""
    node_type: str = Field(..., description="Node type (e.g., TRIGGER_NODE, AI_AGENT_NODE)")
    subtype: str = Field(..., description="Node subtype (e.g., schedule, webhook)")


class GetNodeTypesInput(BaseModel):
    """Input for get_node_types tool."""
    type_filter: Optional[str] = Field(
        None,
        description="Filter by node type (optional). Options: ACTION_NODE, TRIGGER_NODE, AI_AGENT_NODE, FLOW_NODE, TOOL_NODE, MEMORY_NODE, HUMAN_IN_THE_LOOP_NODE, EXTERNAL_ACTION_NODE"
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
    MCP client for connecting to the API Gateway's MCP endpoints.
    Provides tools for workflow node discovery and specification retrieval.
    """

    def __init__(self, server_url: str = None, api_key: str = "dev_default"):
        # Use API_GATEWAY_URL if set (for AWS/production), otherwise check Docker/local
        import os
        
        if server_url:
            # Use explicitly provided URL
            self.server_url = server_url
        elif os.getenv("API_GATEWAY_URL"):
            # Use configured API Gateway URL (AWS/production)
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
        
        # Create a shared session with connection pooling for better performance
        self._session = None
        
        logger.info(f"MCP Tool initialized with server URL: {self.server_url}")
    
    async def _get_session(self):
        """Get or create the aiohttp session with connection pooling"""
        if self._session is None:
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool limit
                limit_per_host=30,  # Per-host connection limit
                ttl_dns_cache=300,  # DNS cache timeout
                keepalive_timeout=30  # Keep connections alive for reuse
            )
            timeout = aiohttp.ClientTimeout(total=10, connect=2)  # 10s total, 2s connect
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
        return self._session
    
    async def close(self):
        """Close the session when done"""
        if self._session:
            await self._session.close()
            self._session = None

    async def get_node_types(self, type_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all available workflow node types and their subtypes.
        
        Args:
            type_filter: Optional filter by node type
            
        Returns:
            Dictionary with node types and their subtypes
        """
        try:
            payload = {
                "name": "get_node_types",
                "tool_name": "get_node_types",
                "arguments": {}
            }
            
            if type_filter:
                payload["arguments"]["type_filter"] = type_filter
            
            # Simplified API logging
            logger.debug(f"MCP API: POST {self.server_url}/invoke")
                
            session = await self._get_session()
            async with session.post(
                    f"{self.server_url}/invoke",
                    json=payload,
                    headers=self.headers
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    logger.debug(f"MCP API Response: {response.status}")
                    
                    # Extract the actual result from MCP response format
                    if "result" in result:
                        actual_result = result["result"]
                        if "structuredContent" in actual_result:
                            return actual_result["structuredContent"]
                        elif "content" in actual_result:
                            # Parse from content if needed
                            content = actual_result["content"]
                            if isinstance(content, list) and content:
                                return {"data": content}
                    
                    return result
                    
        except Exception as e:
            logger.error(f"❌ Error getting node types: {e}")
            return {"error": str(e)}

    async def get_node_details(
        self,
        nodes: List[Dict[str, str]],
        include_examples: bool = True,
        include_schemas: bool = True
    ) -> Dict[str, Any]:
        """
        Get detailed specifications for workflow nodes.
        
        Args:
            nodes: List of nodes to get details for (each with node_type and subtype)
            include_examples: Include usage examples
            include_schemas: Include input/output schemas
            
        Returns:
            Dictionary with detailed node specifications
        """
        try:
            payload = {
                "name": "get_node_details",
                "tool_name": "get_node_details",
                "arguments": {
                    "nodes": nodes,
                    "include_examples": include_examples,
                    "include_schemas": include_schemas
                }
            }
            
            # Simplified logging for node details request
            node_list = [f"{n.get('node_type', 'unknown')}:{n.get('subtype', 'unknown')}" for n in nodes]
            logger.info(f"📦 Getting details for {len(nodes)} nodes: {', '.join(node_list[:3])}{'...' if len(node_list) > 3 else ''}")
            
            session = await self._get_session()
            async with session.post(
                    f"{self.server_url}/invoke",
                    json=payload,
                    headers=self.headers
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    logger.debug(f"MCP API Response: {response.status}")
                    
                    # Extract the actual result from MCP response format
                    if "result" in result:
                        actual_result = result["result"]
                        if "structuredContent" in actual_result:
                            content = actual_result["structuredContent"]
                            if "nodes" in content:
                                logger.debug(f"Received details for {len(content['nodes'])} nodes")
                            return content
                        elif "content" in actual_result:
                            content = actual_result["content"]
                            if isinstance(content, list) and content:
                                logger.debug(f"Received details for {len(content)} nodes")
                                return {"nodes": content}
                    
                    return result
                    
        except Exception as e:
            logger.error(f"❌ Error getting node details: {e}")
            return {"error": str(e)}

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
        # Simplified logging - show tool name and brief args
        args_summary = f"nodes={len(tool_args.get('nodes', []))} items" if 'nodes' in tool_args else str(tool_args)
        logger.info(f"🔧 MCP Call: {tool_name} ({args_summary})")
        
        try:
            result = None
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
            
            # Simplified response logging
            if result:
                if isinstance(result, dict):
                    if "nodes" in result:
                        logger.info(f"✅ MCP Response: {len(result['nodes'])} nodes returned")
                    elif "node_types" in result:
                        logger.info(f"✅ MCP Response: {len(result.get('node_types', []))} node types")
                    else:
                        # For other responses, show keys
                        logger.info(f"✅ MCP Response: {list(result.keys())}")
                else:
                    logger.info(f"✅ MCP Response received")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calling tool {tool_name}: {e}")
            return {"error": str(e)}

    def get_langchain_tools(self) -> List[Tool]:
        """
        Get LangChain tools for use with function calling.
        
        Returns:
            List of LangChain Tool objects
        """
        tools = []
        
        # Tool for getting node types
        async def _get_node_types(type_filter: Optional[str] = None) -> str:
            result = await self.get_node_types(type_filter)
            return json.dumps(result, indent=2)
        
        get_node_types_tool = Tool(
            name="get_node_types",
            description="Get all available workflow node types and their subtypes. Use this to discover what nodes are available.",
            func=None,  # Async function will be set via coroutine
            coroutine=_get_node_types,
            args_schema=GetNodeTypesInput
        )
        tools.append(get_node_types_tool)
        
        # Tool for getting node details
        async def _get_node_details(
            nodes: List[Dict[str, str]],
            include_examples: bool = True,
            include_schemas: bool = True
        ) -> str:
            result = await self.get_node_details(nodes, include_examples, include_schemas)
            return json.dumps(result, indent=2)
        
        get_node_details_tool = Tool(
            name="get_node_details",
            description="Get detailed specifications for workflow nodes including parameters, ports, and examples. Use this to get the exact configuration requirements for nodes.",
            func=None,  # Async function will be set via coroutine
            coroutine=_get_node_details,
            args_schema=GetNodeDetailsInput
        )
        tools.append(get_node_details_tool)
        
        return tools


def create_openai_function_definitions() -> List[Dict[str, Any]]:
    """
    Create OpenAI function calling definitions for MCP tools.
    
    Returns:
        List of OpenAI function definitions
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_node_types",
                "description": "Get all available workflow node types and their subtypes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type_filter": {
                            "type": "string",
                            "enum": [
                                "ACTION_NODE",
                                "TRIGGER_NODE", 
                                "AI_AGENT_NODE",
                                "FLOW_NODE",
                                "TOOL_NODE",
                                "MEMORY_NODE",
                                "HUMAN_IN_THE_LOOP_NODE",
                                "EXTERNAL_ACTION_NODE"
                            ],
                            "description": "Filter by node type (optional)"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_node_details",
                "description": "Get detailed specifications for workflow nodes including parameters, ports, and examples",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nodes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "node_type": {"type": "string"},
                                    "subtype": {"type": "string"}
                                },
                                "required": ["node_type", "subtype"]
                            },
                            "description": "List of nodes to get details for"
                        },
                        "include_examples": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include usage examples"
                        },
                        "include_schemas": {
                            "type": "boolean", 
                            "default": True,
                            "description": "Include input/output schemas"
                        }
                    },
                    "required": ["nodes"]
                }
            }
        }
    ]