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
        
        logger.info(f"MCP Tool initialized with server URL: {self.server_url}")

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
                
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.server_url}/invoke",
                    json=payload,
                    headers=self.headers
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
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
            logger.error(f"Error getting node types: {e}")
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
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.server_url}/invoke",
                    json=payload,
                    headers=self.headers
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    # Extract the actual result from MCP response format
                    if "result" in result:
                        actual_result = result["result"]
                        if "structuredContent" in actual_result:
                            return actual_result["structuredContent"]
                        elif "content" in actual_result:
                            content = actual_result["content"]
                            if isinstance(content, list) and content:
                                return {"nodes": content}
                    
                    return result
                    
        except Exception as e:
            logger.error(f"Error getting node details: {e}")
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