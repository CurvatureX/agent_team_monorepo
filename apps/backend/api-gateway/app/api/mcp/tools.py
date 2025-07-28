"""
MCP API routes - Model Context Protocol endpoints
支持API Key认证的MCP工具调用端点
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.dependencies import MCPDeps, get_tool_name, require_scope
from app.exceptions import ServiceUnavailableError, ValidationError
from app.models.mcp import (
    MCPErrorResponse,
    MCPHealthCheck,
    MCPInvokeRequest,
    MCPInvokeResponse,
    MCPTool,
    MCPToolsResponse,
)
from app.utils.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

logger = get_logger(__name__)
router = APIRouter()


# Enhanced MCP Service
class EnhancedMCPService:
    def get_available_tools(self) -> MCPToolsResponse:
        """获取可用工具列表"""
        tools = [
            MCPTool(
                name="text_analysis",
                description="Analyze text content for sentiment, keywords, and structure",
                parameters={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to analyze"},
                        "analysis_type": {
                            "type": "string",
                            "enum": ["sentiment", "keywords", "structure"],
                            "description": "Type of analysis to perform",
                        },
                    },
                    "required": ["text"],
                },
                category="analysis",
                tags=["text", "nlp", "analysis"],
            ),
            MCPTool(
                name="workflow_generator",
                description="Generate workflow definitions from natural language descriptions",
                parameters={
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Natural language workflow description",
                        },
                        "complexity": {
                            "type": "string",
                            "enum": ["simple", "medium", "complex"],
                            "default": "medium",
                        },
                    },
                    "required": ["description"],
                },
                category="workflow",
                tags=["workflow", "generation", "automation"],
            ),
            MCPTool(
                name="example_tool",
                description="Example tool for testing MCP API functionality",
                parameters={
                    "type": "object",
                    "properties": {"message": {"type": "string", "description": "Test message"}},
                },
                category="testing",
                tags=["test", "example"],
            ),
        ]

        return MCPToolsResponse(
            success=True,
            tools=tools,
            total_count=len(tools),
            available_count=len([t for t in tools if t.available]),
            categories=list(set(t.category for t in tools if t.category)),
            timestamp=datetime.now(timezone.utc),
        )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        """调用指定工具"""
        start_time = time.time()

        # 模拟不同工具的处理逻辑
        if tool_name == "text_analysis":
            text = params.get("text", "")
            analysis_type = params.get("analysis_type", "sentiment")

            # 模拟分析结果
            result = {
                "text": text,
                "analysis_type": analysis_type,
                "result": {
                    "sentiment": "positive" if "good" in text.lower() else "neutral",
                    "confidence": 0.85,
                    "keywords": text.split()[:5] if analysis_type == "keywords" else [],
                },
            }

        elif tool_name == "workflow_generator":
            description = params.get("description", "")
            complexity = params.get("complexity", "medium")

            result = {
                "description": description,
                "complexity": complexity,
                "workflow": {
                    "name": f"Generated Workflow - {complexity}",
                    "nodes": ["start", "process", "end"],
                    "connections": [["start", "process"], ["process", "end"]],
                },
            }

        elif tool_name == "example_tool":
            message = params.get("message", "No message provided")
            result = {
                "original_message": message,
                "response": f"Processed: {message}",
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }

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

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """获取工具详细信息"""
        tools_map = {
            "text_analysis": {
                "name": "text_analysis",
                "description": "Advanced text analysis tool with sentiment analysis and keyword extraction",
                "version": "1.2.0",
                "available": True,
                "category": "analysis",
                "usage_examples": [
                    {"text": "This is great!", "analysis_type": "sentiment"},
                    {"text": "Machine learning and AI", "analysis_type": "keywords"},
                ],
            },
            "workflow_generator": {
                "name": "workflow_generator",
                "description": "Generate automated workflows from natural language descriptions",
                "version": "1.1.0",
                "available": True,
                "category": "workflow",
                "usage_examples": [
                    {"description": "Create a user onboarding workflow", "complexity": "medium"}
                ],
            },
            "example_tool": {
                "name": "example_tool",
                "description": "Simple example tool for testing MCP functionality",
                "version": "1.0.0",
                "available": True,
                "category": "testing",
                "usage_examples": [{"message": "Hello, MCP!"}],
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
        """MCP服务健康检查"""
        available_tools = ["text_analysis", "workflow_generator", "example_tool"]

        return MCPHealthCheck(
            healthy=True,
            version="2.0.0",
            available_tools=available_tools,
            timestamp=int(time.time()),
        )


# Initialize MCP service
mcp_service = EnhancedMCPService()


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
        if invoke_request.timeout and (invoke_request.timeout < 1 or invoke_request.timeout > 300):
            raise ValidationError("Timeout must be between 1 and 300 seconds")

        result = await mcp_service.invoke_tool(
            tool_name=invoke_request.tool_name, params=invoke_request.params
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
