"""
MCP API routes - Model Context Protocol endpoints
支持API Key认证的MCP工具调用端点
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.dependencies import MCPDeps, get_tool_name, require_scope
from app.exceptions import ServiceUnavailableError, ValidationError
from app.models import (
    MCPErrorResponse,
    MCPHealthCheck,
    MCPInvokeRequest,
    MCPInvokeResponse,
    MCPTool,
    MCPToolsResponse,
)
from app.services.node_knowledge_service import NodeKnowledgeService
from app.utils.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

logger = get_logger(__name__)
router = APIRouter()


# Node Knowledge MCP Service
class NodeKnowledgeMCPService:
    def __init__(self):
        self.node_knowledge = NodeKnowledgeService()

    def get_available_tools(self) -> MCPToolsResponse:
        """Get available node knowledge tools."""
        tools = [
            MCPTool(
                name="get_node_types",
                description="Get all available workflow node types and their subtypes",
                parameters={
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
                                "HUMAN_LOOP_NODE",
                                "EXTERNAL_ACTION_NODE",
                            ],
                            "description": "Filter by node type (optional)",
                        }
                    },
                },
                category="workflow",
                tags=["nodes", "workflow", "specifications"],
            ),
            MCPTool(
                name="get_node_details",
                description="Get detailed specifications for workflow nodes including parameters, ports, and examples",
                parameters={
                    "type": "object",
                    "properties": {
                        "nodes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "node_type": {"type": "string"},
                                    "subtype": {"type": "string"},
                                },
                                "required": ["node_type", "subtype"],
                            },
                            "description": "List of nodes to get details for",
                        },
                        "include_examples": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include usage examples",
                        },
                        "include_schemas": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include input/output schemas",
                        },
                    },
                    "required": ["nodes"],
                },
                category="workflow",
                tags=["nodes", "specifications", "details"],
            ),
            MCPTool(
                name="search_nodes",
                description="Search workflow nodes by functionality, description, or capabilities",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query describing desired functionality",
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 10,
                            "description": "Maximum number of results",
                        },
                        "include_details": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include full specifications",
                        },
                    },
                    "required": ["query"],
                },
                category="workflow",
                tags=["search", "nodes", "discovery"],
            ),
        ]

        return MCPToolsResponse(
            tools=tools,
            total_count=len(tools),
            available_count=len(tools),  # All tools are available
            categories=list(set(t.category for t in tools if t.category)),
        )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        """Invoke specified node knowledge tool."""
        start_time = time.time()

        try:
            if tool_name == "get_node_types":
                type_filter = params.get("type_filter")
                result = self.node_knowledge.get_node_types(type_filter)

            elif tool_name == "get_node_details":
                nodes = params.get("nodes", [])
                include_examples = params.get("include_examples", True)
                include_schemas = params.get("include_schemas", True)
                result = self.node_knowledge.get_node_details(
                    nodes, include_examples, include_schemas
                )

            elif tool_name == "search_nodes":
                query = params.get("query", "")
                max_results = params.get("max_results", 10)
                include_details = params.get("include_details", False)
                result = self.node_knowledge.search_nodes(query, max_results, include_details)

            else:
                return MCPInvokeResponse(
                    success=False,
                    tool_name=tool_name,
                    error=f"Tool '{tool_name}' not found",
                    error_type="TOOL_NOT_FOUND",
                    execution_time_ms=round((time.time() - start_time) * 1000, 2),
                )

            return MCPInvokeResponse(
                success=True,
                tool_name=tool_name,
                result=result,
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
                timestamp=datetime.now(timezone.utc),
            )

        except Exception as e:
            return MCPInvokeResponse(
                success=False,
                tool_name=tool_name,
                error=f"Tool execution failed: {str(e)}",
                error_type="EXECUTION_ERROR",
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
                timestamp=datetime.now(timezone.utc),
            )

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific tool."""
        tools_map = {
            "get_node_types": {
                "name": "get_node_types",
                "description": "Get all available workflow node types and their subtypes",
                "version": "1.0.0",
                "available": True,
                "category": "workflow",
                "usage_examples": [
                    {"type_filter": "ACTION_NODE"},  # Filter by specific type
                ],
            },
            "get_node_details": {
                "name": "get_node_details",
                "description": "Get detailed specifications for workflow nodes",
                "version": "1.0.0",
                "available": True,
                "category": "workflow",
                "usage_examples": [
                    {
                        "nodes": [{"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"}],
                        "include_examples": True,
                    }
                ],
            },
            "search_nodes": {
                "name": "search_nodes",
                "description": "Search workflow nodes by functionality or description",
                "version": "1.0.0",
                "available": True,
                "category": "workflow",
                "usage_examples": [
                    {"query": "send email", "max_results": 5},
                    {"query": "HTTP request", "include_details": True},
                ],
            },
        }

        return tools_map.get(
            tool_name,
            {
                "name": tool_name,
                "description": f"Tool '{tool_name}' not found",
                "available": False,
                "error": "Tool not found",
            },
        )

    def health_check(self) -> MCPHealthCheck:
        """MCP service health check."""
        available_tools = ["get_node_types", "get_node_details", "search_nodes"]

        # Check if node knowledge service is available
        healthy = self.node_knowledge.registry is not None

        return MCPHealthCheck(
            healthy=healthy,
            version="3.0.0",
            available_tools=available_tools if healthy else [],
            timestamp=int(time.time()),
        )


# Initialize MCP service
mcp_service = NodeKnowledgeMCPService()


@router.get("/tools", response_model=MCPToolsResponse)
async def list_tools(
    deps: MCPDeps = Depends(), tools_scope: None = Depends(require_scope("tools:read"))
):
    """
    Get list of all available MCP tools
    获取所有可用的MCP工具列表
    """
    start_time = time.time()
    request_id = deps.request_context.get("request_id", "unknown")

    try:
        logger.info(f"🔧 Retrieving MCP tools for client {deps.mcp_client.client_name}")

        tools_response = mcp_service.get_available_tools()
        processing_time = time.time() - start_time

        # Add request metadata
        tools_response.processing_time_ms = round(processing_time * 1000, 2)
        tools_response.request_id = request_id

        logger.info(f"✅ MCP tools retrieved: {tools_response.total_count} tools")
        return tools_response

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Error retrieving MCP tools: {e}")

        return JSONResponse(
            status_code=500,
            content=MCPErrorResponse(
                error=f"Failed to retrieve tools: {str(e)}",
                error_type="INTERNAL_ERROR",
                request_id=request_id,
            ).dict(),
        )


@router.post("/invoke", response_model=MCPInvokeResponse)
async def invoke_tool(
    invoke_request: MCPInvokeRequest,
    deps: MCPDeps = Depends(),
    execute_scope: None = Depends(require_scope("tools:execute")),
):
    """
    Invoke a specific MCP tool with parameters
    调用指定的MCP工具
    """
    start_time = time.time()
    request_id = deps.request_context.get("request_id", "unknown")

    try:
        logger.info(
            f"⚡ Invoking MCP tool '{invoke_request.tool_name}' for client {deps.mcp_client.client_name}"
        )

        # Validate timeout
        if invoke_request.timeout is not None and (
            invoke_request.timeout < 1 or invoke_request.timeout > 300
        ):
            raise ValidationError("Timeout must be between 1 and 300 seconds")

        result = await mcp_service.invoke_tool(
            tool_name=invoke_request.tool_name, params=invoke_request.parameters
        )

        # Add request metadata
        result.request_id = request_id
        if not result.execution_time_ms:
            result.execution_time_ms = round((time.time() - start_time) * 1000, 2)

        logger.info(
            f"✅ Tool '{invoke_request.tool_name}' executed successfully in {result.execution_time_ms}ms"
        )
        return result

    except ValidationError:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Tool '{invoke_request.tool_name}' execution failed: {e}")

        return JSONResponse(
            status_code=500,
            content=MCPErrorResponse(
                error=f"Tool invocation failed: {str(e)}",
                error_type="EXECUTION_ERROR",
                tool_name=invoke_request.tool_name,
                request_id=request_id,
            ).dict(),
        )


@router.get("/tools/{tool_name}")
async def get_tool_info(
    tool_name: str = Depends(get_tool_name),
    deps: MCPDeps = Depends(),
    tools_scope: None = Depends(require_scope("tools:read")),
):
    """
    Get detailed information about a specific tool
    获取指定工具的详细信息
    """
    start_time = time.time()
    request_id = deps.request_context.get("request_id", "unknown")

    try:
        logger.info(
            f"🔍 Getting tool info for '{tool_name}' for client {deps.mcp_client.client_name}"
        )

        tool_info = mcp_service.get_tool_info(tool_name)
        processing_time = time.time() - start_time

        # Add metadata
        tool_info["processing_time_ms"] = round(processing_time * 1000, 2)
        tool_info["request_id"] = request_id

        if not tool_info.get("available", True):
            logger.warning(f"🚫 Tool '{tool_name}' not found or unavailable")
            return JSONResponse(
                status_code=404,
                content=MCPErrorResponse(
                    error=f"Tool '{tool_name}' not found",
                    error_type="TOOL_NOT_FOUND",
                    tool_name=tool_name,
                    request_id=request_id,
                ).dict(),
            )

        logger.info(f"✅ Tool info retrieved for '{tool_name}'")
        return tool_info

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Error retrieving tool info for '{tool_name}': {e}")

        return JSONResponse(
            status_code=500,
            content=MCPErrorResponse(
                error=f"Failed to get tool info: {str(e)}",
                error_type="INTERNAL_ERROR",
                tool_name=tool_name,
                request_id=request_id,
            ).dict(),
        )


@router.get("/health", response_model=MCPHealthCheck)
async def mcp_health(
    deps: MCPDeps = Depends(), health_scope: None = Depends(require_scope("health:check"))
):
    """
    Health check for MCP service
    MCP服务健康检查
    """
    start_time = time.time()
    request_id = deps.request_context.get("request_id", "unknown")

    try:
        logger.info(f"🏥 Performing MCP health check for client {deps.mcp_client.client_name}")

        health_info = mcp_service.health_check()
        processing_time = time.time() - start_time

        # Add metadata
        health_info.processing_time_ms = round(processing_time * 1000, 2)
        health_info.request_id = request_id

        status_code = 200 if health_info.healthy else 503

        logger.info(
            f"✅ MCP health check completed: {'healthy' if health_info.healthy else 'unhealthy'}"
        )

        return JSONResponse(status_code=status_code, content=health_info.dict())

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ MCP health check failed: {e}")

        return JSONResponse(
            status_code=500,
            content=MCPHealthCheck(
                healthy=False,
                version="2.0.0",
                available_tools=[],
                timestamp=int(time.time()),
                error=f"Health check failed: {str(e)}",
                request_id=request_id,
                processing_time_ms=round(processing_time * 1000, 2),
            ).dict(),
        )
