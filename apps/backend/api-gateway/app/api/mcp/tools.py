"""
MCP API routes - 简化版本用于三层架构测试
"""

import time
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter()

# 简化的模型
class MCPInvokeRequest(BaseModel):
    tool_name: str
    params: Dict[str, Any]

class MCPInvokeResponse(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class MCPToolsResponse(BaseModel):
    tools: List[Dict[str, Any]]

class MCPErrorResponse(BaseModel):
    success: bool = False
    error: str
    error_type: str

# 简化的MCP服务
class MockMCPService:
    def get_available_tools(self):
        return MCPToolsResponse(tools=[
            {
                "name": "example_tool", 
                "description": "Example tool for testing three-layer API",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Test message"}
                    }
                }
            }
        ])
    
    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]):
        return MCPInvokeResponse(
            success=True,
            result={
                "message": f"Tool {tool_name} executed successfully with params: {params}",
                "timestamp": int(time.time())
            }
        )
    
    def get_tool_info(self, tool_name: str):
        return {
            "name": tool_name, 
            "description": f"Detailed information for {tool_name}",
            "version": "1.0.0",
            "available": True
        }
    
    def health_check(self):
        return {
            "healthy": True, 
            "available_tools": ["example_tool"],
            "timestamp": int(time.time()),
            "version": "2.0.0"
        }

# Initialize MCP service
mcp_service = MockMCPService()


@router.get("/tools", response_model=MCPToolsResponse)
async def list_tools(request: Request):
    """
    Get list of all available MCP tools
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        logger.info("Retrieving available MCP tools", request_id=request_id, endpoint="list_tools")
        
        tools_response = mcp_service.get_available_tools()
        processing_time = time.time() - start_time
        
        logger.info(
            "MCP tools retrieved successfully",
            request_id=request_id,
            tool_count=len(tools_response.tools),
            processing_time_ms=round(processing_time * 1000, 2),
        )
        return tools_response
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            "Error retrieving MCP tools",
            request_id=request_id,
            error=str(e),
            processing_time_ms=round(processing_time * 1000, 2),
        )
        
        return JSONResponse(
            status_code=500,
            content=MCPErrorResponse(
                error=f"Failed to retrieve tools: {str(e)}",
                error_type="INTERNAL_ERROR"
            ).dict()
        )


@router.post("/invoke", response_model=MCPInvokeResponse)
async def invoke_tool(invoke_request: MCPInvokeRequest, request: Request):
    """
    Invoke a specific MCP tool with parameters
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        logger.info(
            "Invoking MCP tool",
            request_id=request_id,
            tool_name=invoke_request.tool_name,
            params=invoke_request.params,
            endpoint="invoke_tool",
        )
        
        result = await mcp_service.invoke_tool(
            tool_name=invoke_request.tool_name, 
            params=invoke_request.params
        )
        
        processing_time = time.time() - start_time
        
        logger.info(
            "MCP tool invocation successful",
            request_id=request_id,
            tool_name=invoke_request.tool_name,
            success=result.success,
            processing_time_ms=round(processing_time * 1000, 2),
        )
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            "MCP tool invocation failed",
            request_id=request_id,
            tool_name=invoke_request.tool_name,
            error=str(e),
            processing_time_ms=round(processing_time * 1000, 2),
        )
        
        return JSONResponse(
            status_code=500,
            content=MCPErrorResponse(
                error=f"Tool invocation failed: {str(e)}",
                error_type="EXECUTION_ERROR"
            ).dict()
        )


@router.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str, request: Request):
    """
    Get detailed information about a specific tool
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        logger.info(
            "Retrieving tool information",
            request_id=request_id,
            tool_name=tool_name,
            endpoint="get_tool_info",
        )
        
        tool_info = mcp_service.get_tool_info(tool_name)
        processing_time = time.time() - start_time
        
        logger.info(
            "Tool information retrieved successfully",
            request_id=request_id,
            tool_name=tool_name,
            processing_time_ms=round(processing_time * 1000, 2),
        )
        return tool_info
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            "Error retrieving tool information",
            request_id=request_id,
            tool_name=tool_name,
            error=str(e),
            processing_time_ms=round(processing_time * 1000, 2),
        )
        
        return JSONResponse(
            status_code=500,
            content=MCPErrorResponse(
                error=f"Failed to get tool info: {str(e)}",
                error_type="TOOL_NOT_FOUND"
            ).dict()
        )


@router.get("/health")
async def mcp_health(request: Request):
    """
    Health check for MCP service
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        logger.info(
            "Performing MCP service health check", 
            request_id=request_id, 
            endpoint="health_check"
        )
        
        health_info = mcp_service.health_check()
        processing_time = time.time() - start_time
        
        status_code = 200 if health_info.get("healthy", False) else 503
        
        # Add processing time to health info
        health_info["processing_time_ms"] = round(processing_time * 1000, 2)
        health_info["request_id"] = request_id
        
        logger.info(
            "MCP health check completed",
            request_id=request_id,
            healthy=health_info.get("healthy", False),
            processing_time_ms=health_info["processing_time_ms"],
        )
        
        return JSONResponse(status_code=status_code, content=health_info)
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            "MCP health check failed",
            request_id=request_id,
            error=str(e),
            processing_time_ms=round(processing_time * 1000, 2),
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "healthy": False,
                "error": f"Health check failed: {str(e)}",
                "error_type": "HEALTH_CHECK_ERROR",
                "request_id": request_id,
                "processing_time_ms": round(processing_time * 1000, 2),
            },
        )