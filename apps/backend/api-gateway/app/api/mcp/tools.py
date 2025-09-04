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
    MCPContentItem,
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

from shared.models.node_enums import ActionSubtype, NodeType

from .notion_tools import notion_mcp_service

logger = get_logger(__name__)
router = APIRouter()


def get_service_for_tool(tool_name: str):
    """Route tool to appropriate service based on name patterns."""
    notion_prefixes = ["notion_"]
    notion_exact_matches = {
        "notion_search",
        "notion_page",
        "notion_database",
    }

    if (
        any(tool_name.startswith(prefix) for prefix in notion_prefixes)
        or tool_name in notion_exact_matches
    ):
        return notion_mcp_service

    # Default to main MCP service for all other tools
    return mcp_service


# Node Knowledge MCP Service
class NodeKnowledgeMCPService:
    def __init__(self):
        self.node_knowledge = NodeKnowledgeService()

    def get_available_tools(self) -> MCPToolsResponse:
        """Get available node knowledge tools."""
        tools = [
            MCPTool(
                name="get_node_types",
                description="Get all available workflow node types and their subtypes. 🎯 IMPORTANT: HUMAN_IN_THE_LOOP nodes have built-in AI response analysis - DO NOT create separate IF or AI_AGENT nodes for HIL response classification.",
                parameters={
                    "type": "object",
                    "properties": {
                        "type_filter": {
                            "type": "string",
                            "enum": [node_type.value for node_type in NodeType],
                            "description": "Filter by node type (optional)",
                        }
                    },
                },
                category="workflow",
                tags=["nodes", "workflow", "specifications"],
            ),
            MCPTool(
                name="get_node_details",
                description="Get detailed specifications for workflow nodes including parameters, ports, and examples. 🤖 KEY FEATURE: HUMAN_IN_THE_LOOP nodes include integrated AI response analysis with confirmed/rejected/unrelated/timeout output ports - eliminating need for separate IF/AI_AGENT nodes.",
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
        ]

        return MCPToolsResponse(
            tools=tools,
            total_count=len(tools),
            available_count=len(tools),  # All tools are available
            categories=list(set(t.category for t in tools if t.category)),
        )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        """Invoke specified node knowledge tool - returns MCP-compliant response."""
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

            else:
                # Return MCP-compliant error response
                response = MCPInvokeResponse(
                    content=[
                        MCPContentItem(type="text", text=f"Error: Tool '{tool_name}' not found")
                    ],
                    isError=True,
                )
                response._tool_name = tool_name
                response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
                return response

            # Convert result to MCP-compliant content format
            if isinstance(result, (dict, list)):
                # For structured data, provide both text and structured content
                content = [
                    MCPContentItem(type="text", text=f"Tool '{tool_name}' executed successfully")
                ]
                # Ensure structured_content is always a dictionary
                if isinstance(result, dict):
                    structured_content = result
                else:  # result is a list
                    # Wrap list in appropriate structure based on tool type
                    if tool_name == "get_node_details":
                        structured_content = {"nodes": result}
                    else:
                        structured_content = {"data": result}
            else:
                # For simple results, convert to text
                content = [MCPContentItem(type="text", text=str(result))]
                structured_content = None

            response = MCPInvokeResponse(
                content=content, isError=False, structuredContent=structured_content
            )
            response._tool_name = tool_name
            response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return response

        except Exception as e:
            response = MCPInvokeResponse(
                content=[MCPContentItem(type="text", text=f"Tool execution failed: {str(e)}")],
                isError=True,
            )
            response._tool_name = tool_name
            response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return response

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific tool."""
        tools_map = {
            "get_node_types": {
                "name": "get_node_types",
                "description": "Get all available workflow node types and their subtypes. 🎯 CRITICAL: HUMAN_IN_THE_LOOP nodes have built-in AI response analysis capabilities. DO NOT create separate IF or AI_AGENT nodes for HIL response processing.",
                "version": "1.0.0",
                "available": True,
                "category": "workflow",
                "workflow_guidance": "❌ ANTI-PATTERN: HIL → AI_AGENT → IF. ✅ CORRECT: Single HIL node with built-in AI analysis and multiple output ports.",
                "usage_examples": [
                    {"type_filter": NodeType.ACTION.value},  # Filter by specific type
                ],
            },
            "get_node_details": {
                "name": "get_node_details",
                "description": "Get detailed specifications for workflow nodes including parameters, ports, and examples. 🤖 HIL nodes include integrated AI response analysis with multiple output ports (confirmed/rejected/unrelated/timeout).",
                "version": "1.0.0",
                "available": True,
                "category": "workflow",
                "workflow_guidance": "🎯 HIL NODE OPTIMIZATION: Use confirmed/rejected/unrelated output ports instead of creating separate AI_AGENT + IF nodes for response analysis. This reduces workflows from 6+ nodes to 2 nodes.",
                "usage_examples": [
                    {
                        "nodes": [
                            {
                                "node_type": NodeType.HUMAN_IN_THE_LOOP.value,
                                "subtype": "SLACK_INTERACTION",
                            }
                        ],
                        "include_examples": True,
                    }
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
        available_tools = ["get_node_types", "get_node_details"]

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


@router.get("/tools")
async def list_tools(
    deps: MCPDeps = Depends(), tools_scope: None = Depends(require_scope("tools:read"))
):
    """
    Get list of all available MCP tools - follows MCP JSON-RPC 2.0 standard
    获取所有可用的MCP工具列表 - 遵循MCP JSON-RPC 2.0标准
    """
    start_time = time.time()
    request_id = deps.request_context.get("request_id", "unknown")

    try:
        logger.info(f"🔧 Retrieving MCP tools for client {deps.mcp_client.client_name}")

        # Get tools from all services
        node_tools_response = mcp_service.get_available_tools()
        notion_tools_response = notion_mcp_service.get_available_tools()

        # Combine tools from all services
        all_tools = node_tools_response.tools + notion_tools_response.tools
        total_count = len(all_tools)
        available_count = (
            node_tools_response.available_count + notion_tools_response.available_count
        )

        # Combine categories
        all_categories = list(
            set(node_tools_response.categories + notion_tools_response.categories)
        )

        processing_time = time.time() - start_time

        logger.info(
            f"✅ MCP tools retrieved: {total_count} tools ({node_tools_response.total_count} node + {notion_tools_response.total_count} notion)"
        )

        # Return JSON-RPC 2.0 format per MCP standard
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": all_tools}}

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Error retrieving MCP tools: {e}")

        # Return JSON-RPC 2.0 error format
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,  # Internal error per JSON-RPC 2.0
                    "message": f"Failed to retrieve tools: {str(e)}",
                    "data": {
                        "error_type": "INTERNAL_ERROR",
                        "request_id": request_id,
                    },
                },
            },
        )


@router.post("/invoke")
async def invoke_tool(
    invoke_request: MCPInvokeRequest,
    deps: MCPDeps = Depends(),
    execute_scope: None = Depends(require_scope("tools:execute")),
):
    """
    Invoke a specific MCP tool - follows MCP JSON-RPC 2.0 tools/call standard
    调用指定的MCP工具 - 遵循MCP JSON-RPC 2.0 tools/call标准
    """
    start_time = time.time()
    request_id = deps.request_context.get("request_id", "unknown")

    try:
        tool_name = invoke_request.name
        arguments = invoke_request.arguments

        logger.info(f"⚡ Invoking MCP tool '{tool_name}' for client {deps.mcp_client.client_name}")

        # Route tool call to appropriate service
        service = get_service_for_tool(tool_name)
        result = await service.invoke_tool(tool_name=tool_name, params=arguments)

        # Store internal metadata
        result._request_id = request_id
        if not result._execution_time_ms:
            result._execution_time_ms = round((time.time() - start_time) * 1000, 2)

        logger.info(f"✅ Tool '{tool_name}' executed successfully in {result._execution_time_ms}ms")

        # Return JSON-RPC 2.0 format per MCP tools/call standard
        return {"jsonrpc": "2.0", "id": request_id, "result": result.model_dump()}

    except ValidationError:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        tool_name = getattr(invoke_request, "name", "unknown")
        logger.error(f"❌ Tool '{tool_name}' execution failed: {e}")

        # Return JSON-RPC 2.0 error format
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,  # Internal error per JSON-RPC 2.0
                    "message": f"Tool invocation failed: {str(e)}",
                    "data": {
                        "tool_name": tool_name,
                        "error_type": "EXECUTION_ERROR",
                        "request_id": request_id,
                    },
                },
            },
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

        # Route tool info request to appropriate service
        service = get_service_for_tool(tool_name)
        tool_info = service.get_tool_info(tool_name)
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
                ).model_dump(),
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
            ).model_dump(),
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

        # Check health of all services
        node_health = mcp_service.health_check()
        notion_health = notion_mcp_service.health_check()

        # Combine health status
        overall_healthy = node_health.healthy and notion_health.healthy
        all_tools = node_health.available_tools + notion_health.available_tools

        processing_time = time.time() - start_time

        # Create combined health response
        combined_health = MCPHealthCheck(
            healthy=overall_healthy,
            version="3.0.0",
            available_tools=all_tools,
            timestamp=int(time.time()),
            error=None
            if overall_healthy
            else f"Node service: {node_health.error}, Notion service: {notion_health.error}",
            request_id=request_id,
            processing_time_ms=round(processing_time * 1000, 2),
        )

        status_code = 200 if overall_healthy else 503

        logger.info(
            f"✅ MCP health check completed: {'healthy' if overall_healthy else 'unhealthy'} (Node: {node_health.healthy}, Notion: {notion_health.healthy})"
        )

        return JSONResponse(status_code=status_code, content=combined_health.model_dump())

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
            ).model_dump(),
        )
