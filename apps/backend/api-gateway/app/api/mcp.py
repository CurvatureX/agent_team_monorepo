"""
MCP API routes with comprehensive error handling and logging
"""

import time
from typing import Any, Dict

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from core.mcp_exceptions import (
    MCPError,
    MCPParameterError,
    MCPToolNotFoundError,
    MCPValidationError,
    classify_error,
    get_http_status_code,
    get_recovery_suggestions,
    get_support_info,
    get_user_friendly_message,
)
from models.mcp_models import (
    MCPErrorResponse,
    MCPInvokeRequest,
    MCPInvokeResponse,
    MCPToolsResponse,
)
from services.mcp_service import MCPService

logger = structlog.get_logger()

router = APIRouter()

# Initialize MCP service
mcp_service = MCPService()


def get_mcp_service(request: Request = None) -> MCPService:
    """Dependency to get the MCP service instance"""
    return mcp_service


@router.get("/tools", response_model=MCPToolsResponse)
async def list_tools(request: Request):
    """
    Get list of all available MCP tools

    Returns:
        MCPToolsResponse: List of available tools with their schemas
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
            tools=[tool.name for tool in tools_response.tools],
        )
        return tools_response

    except MCPError as e:
        processing_time = time.time() - start_time
        logger.error(
            "MCP error retrieving tools",
            request_id=request_id,
            error_id=e.error_id,
            error_type=e.error_type.value,
            error=e.message,
            processing_time_ms=round(processing_time * 1000, 2),
        )

        error_response = MCPErrorResponse(
            error=e.user_message,
            error_type=e.error_type.value,
            details={**e.details, "error_id": e.error_id, "request_id": request_id},
            error_id=e.error_id,
            request_id=request_id,
            retryable=e.retryable,
            retry_after=e.retry_after,
            timestamp=e.timestamp,
            recovery_suggestions=get_recovery_suggestions(e.error_type, e.details),
            support_info=get_support_info(e.error_type),
        )

        return JSONResponse(
            status_code=get_http_status_code(e.error_type), content=error_response.model_dump()
        )

    except Exception as e:
        processing_time = time.time() - start_time
        classified_error = classify_error(e)

        logger.error(
            "Unexpected error retrieving MCP tools",
            request_id=request_id,
            error_id=classified_error.error_id,
            error=str(e),
            error_type=type(e).__name__,
            processing_time_ms=round(processing_time * 1000, 2),
        )

        error_response = MCPErrorResponse(
            error=get_user_friendly_message(classified_error.error_type),
            error_type=classified_error.error_type.value,
            details={
                "error_id": classified_error.error_id,
                "request_id": request_id,
                "retryable": classified_error.retryable,
            },
            error_id=classified_error.error_id,
            request_id=request_id,
            retryable=classified_error.retryable,
            retry_after=classified_error.retry_after,
            timestamp=classified_error.timestamp,
            recovery_suggestions=get_recovery_suggestions(classified_error.error_type),
            support_info=get_support_info(classified_error.error_type),
        )

        return JSONResponse(
            status_code=get_http_status_code(classified_error.error_type),
            content=error_response.model_dump(),
        )


@router.post("/invoke", response_model=MCPInvokeResponse)
async def invoke_tool(invoke_request: MCPInvokeRequest, request: Request):
    """
    Invoke a specific MCP tool with parameters

    Args:
        invoke_request: Tool invocation request with tool_name and params
        request: FastAPI request object for context

    Returns:
        MCPInvokeResponse: Tool execution result
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
            tool_name=invoke_request.tool_name, params=invoke_request.params
        )

        processing_time = time.time() - start_time

        logger.info(
            "MCP tool invocation successful",
            request_id=request_id,
            tool_name=invoke_request.tool_name,
            success=result.success,
            processing_time_ms=round(processing_time * 1000, 2),
            result_size=len(str(result.result)) if result.result else 0,
        )

        return result

    except MCPError as e:
        processing_time = time.time() - start_time
        logger.error(
            "MCP tool invocation failed",
            request_id=request_id,
            tool_name=invoke_request.tool_name,
            error_id=e.error_id,
            error_type=e.error_type.value,
            error=e.message,
            processing_time_ms=round(processing_time * 1000, 2),
            retryable=e.retryable,
            retry_after=e.retry_after,
        )

        # Create enhanced error response
        error_response = MCPErrorResponse(
            error=e.user_message,
            error_type=e.error_type.value,
            details={
                **e.details,
                "error_id": e.error_id,
                "request_id": request_id,
                "retryable": e.retryable,
                "retry_after": e.retry_after,
                "tool_name": invoke_request.tool_name,
            },
            error_id=e.error_id,
            request_id=request_id,
            retryable=e.retryable,
            retry_after=e.retry_after,
            timestamp=e.timestamp,
            recovery_suggestions=get_recovery_suggestions(e.error_type, e.details),
            support_info=get_support_info(e.error_type),
        )

        status_code = get_http_status_code(e.error_type)

        # Add retry-after header for rate limit errors
        headers = {}
        if e.error_type.value == "RATE_LIMIT_ERROR" and e.retry_after:
            headers["Retry-After"] = str(e.retry_after)

        return JSONResponse(
            status_code=status_code, content=error_response.model_dump(), headers=headers
        )

    except Exception as e:
        processing_time = time.time() - start_time
        classified_error = classify_error(e)

        logger.error(
            "Unexpected error during tool invocation",
            request_id=request_id,
            tool_name=invoke_request.tool_name,
            error_id=classified_error.error_id,
            error=str(e),
            error_type=type(e).__name__,
            processing_time_ms=round(processing_time * 1000, 2),
        )

        # Enhanced generic error response
        error_response = MCPErrorResponse(
            error=get_user_friendly_message(classified_error.error_type),
            error_type=classified_error.error_type.value,
            details={
                "error_id": classified_error.error_id,
                "request_id": request_id,
                "tool_name": invoke_request.tool_name,
                "retryable": classified_error.retryable,
                "retry_after": classified_error.retry_after,
            },
            error_id=classified_error.error_id,
            request_id=request_id,
            retryable=classified_error.retryable,
            retry_after=classified_error.retry_after,
            timestamp=classified_error.timestamp,
            recovery_suggestions=get_recovery_suggestions(classified_error.error_type),
            support_info=get_support_info(classified_error.error_type),
        )

        return JSONResponse(
            status_code=get_http_status_code(classified_error.error_type),
            content=error_response.model_dump(),
        )


@router.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str, request: Request):
    """
    Get detailed information about a specific tool

    Args:
        tool_name: Name of the tool to get information for
        request: FastAPI request object for context

    Returns:
        Tool information including schema and description
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

    except MCPError as e:
        processing_time = time.time() - start_time
        logger.error(
            "MCP error retrieving tool information",
            request_id=request_id,
            tool_name=tool_name,
            error_id=e.error_id,
            error_type=e.error_type.value,
            error=e.message,
            processing_time_ms=round(processing_time * 1000, 2),
        )

        error_response = MCPErrorResponse(
            error=e.user_message,
            error_type=e.error_type.value,
            details={
                **e.details,
                "error_id": e.error_id,
                "request_id": request_id,
                "tool_name": tool_name,
            },
            error_id=e.error_id,
            request_id=request_id,
            retryable=e.retryable,
            retry_after=e.retry_after,
            timestamp=e.timestamp,
            recovery_suggestions=get_recovery_suggestions(e.error_type, e.details),
            support_info=get_support_info(e.error_type),
        )

        return JSONResponse(
            status_code=get_http_status_code(e.error_type), content=error_response.model_dump()
        )

    except Exception as e:
        processing_time = time.time() - start_time
        classified_error = classify_error(e)

        logger.error(
            "Unexpected error retrieving tool information",
            request_id=request_id,
            tool_name=tool_name,
            error_id=classified_error.error_id,
            error=str(e),
            error_type=type(e).__name__,
            processing_time_ms=round(processing_time * 1000, 2),
        )

        error_response = MCPErrorResponse(
            error=get_user_friendly_message(classified_error.error_type),
            error_type=classified_error.error_type.value,
            details={
                "error_id": classified_error.error_id,
                "request_id": request_id,
                "tool_name": tool_name,
                "retryable": classified_error.retryable,
            },
            error_id=classified_error.error_id,
            request_id=request_id,
            retryable=classified_error.retryable,
            retry_after=classified_error.retry_after,
            timestamp=classified_error.timestamp,
            recovery_suggestions=get_recovery_suggestions(classified_error.error_type),
            support_info=get_support_info(classified_error.error_type),
        )

        return JSONResponse(
            status_code=get_http_status_code(classified_error.error_type),
            content=error_response.model_dump(),
        )


@router.get("/health")
async def mcp_health(request: Request):
    """
    Health check for MCP service

    Args:
        request: FastAPI request object for context

    Returns:
        Health status information
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        logger.info(
            "Performing MCP service health check", request_id=request_id, endpoint="health_check"
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
            available_tools=health_info.get("available_tools", []),
        )

        return JSONResponse(status_code=status_code, content=health_info)

    except Exception as e:
        processing_time = time.time() - start_time
        classified_error = classify_error(e)

        logger.error(
            "MCP health check failed",
            request_id=request_id,
            error_id=classified_error.error_id,
            error=str(e),
            error_type=type(e).__name__,
            processing_time_ms=round(processing_time * 1000, 2),
        )

        return JSONResponse(
            status_code=500,
            content={
                "healthy": False,
                "error": get_user_friendly_message(classified_error.error_type),
                "error_type": classified_error.error_type.value,
                "error_id": classified_error.error_id,
                "request_id": request_id,
                "processing_time_ms": round(processing_time * 1000, 2),
                "retryable": classified_error.retryable,
            },
        )
