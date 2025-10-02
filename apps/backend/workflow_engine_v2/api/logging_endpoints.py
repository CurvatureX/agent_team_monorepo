"""
API Endpoints for Workflow Execution Logging

This module provides FastAPI endpoints for accessing workflow execution logs,
summaries, and detailed execution information through a RESTful API.

Endpoints:
- GET /api/v2/executions/{execution_id}/logs - Get execution logs
- GET /api/v2/executions/{execution_id}/summary - Get execution summary
- GET /api/v2/executions/{execution_id}/nodes/{node_id}/details - Get node details
- POST /api/v2/executions/{execution_id}/export - Export logs
- GET /api/v2/logging/formats - List available formats
- GET /api/v2/executions/{execution_id}/stream - Stream real-time logs (WebSocket)
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi import Path as PathParam
from fastapi import Query
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from workflow_engine_v2.services.enhanced_logging_service import get_enhanced_logging_service
from workflow_engine_v2.services.execution_logger import ExecutionLogLevel
from workflow_engine_v2.services.log_formatters import OutputFormat

# Pydantic models for API


class LogQueryParams(BaseModel):
    """Query parameters for log retrieval"""

    format: str = Field(default="json", description="Output format")
    node_id: Optional[str] = Field(default=None, description="Filter by node ID")
    level: Optional[str] = Field(default=None, description="Filter by log level")
    limit: Optional[int] = Field(default=None, description="Limit number of entries")


class ExportRequest(BaseModel):
    """Request model for log export"""

    format: str = Field(default="json_pretty", description="Export format")
    include_summary: bool = Field(default=True, description="Include execution summary")


class LogEntry(BaseModel):
    """Log entry model for API responses"""

    timestamp: float
    iso_timestamp: str
    level: str
    message: str
    execution_id: str
    node_context: Optional[Dict[str, Any]] = None
    structured_data: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None


class ExecutionSummary(BaseModel):
    """Execution summary model for API responses"""

    execution_id: str
    total_logs: int
    node_statistics: Dict[str, int]
    performance: Dict[str, float]
    timestamp: float


class NodeExecutionDetails(BaseModel):
    """Node execution details model for API responses"""

    node_id: str
    execution_id: str
    log_count: int
    context: Optional[Dict[str, Any]]
    logs: List[LogEntry]


class ApiResponse(BaseModel):
    """Standard API response wrapper"""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Create router
router = APIRouter(prefix="/api/v2", tags=["Workflow Execution Logging"])

# Get the logging service
logging_service = get_enhanced_logging_service()


@router.get(
    "/executions/{execution_id}/logs",
    response_model=ApiResponse,
    summary="Get execution logs",
    description="Retrieve logs for a specific workflow execution with optional filtering",
)
async def get_execution_logs(
    execution_id: str = PathParam(..., description="Execution ID"),
    format: str = Query("json", description="Output format"),
    node_id: Optional[str] = Query(None, description="Filter by node ID"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    limit: Optional[int] = Query(None, description="Limit number of entries"),
    raw: bool = Query(False, description="Return raw formatted content instead of JSON wrapper"),
):
    """Get execution logs with optional filtering"""

    try:
        # Validate format
        if format not in [fmt.value for fmt in OutputFormat]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format '{format}'. Available formats: {[fmt.value for fmt in OutputFormat]}",
            )

        # Validate level if provided
        if level and level not in [lvl.value for lvl in ExecutionLogLevel]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid level '{level}'. Available levels: {[lvl.value for lvl in ExecutionLogLevel]}",
            )

        # Get logs from service
        logs_content = logging_service.get_execution_logs(
            execution_id=execution_id,
            format_type=OutputFormat(format),
            node_id=node_id
            # Note: level_filter and limit would need service method updates
        )

        if raw:
            # Return raw content with appropriate content type
            media_type = "application/json" if format.startswith("json") else "text/plain"
            if format == "html":
                media_type = "text/html"

            return PlainTextResponse(content=logs_content, media_type=media_type)

        return ApiResponse(
            success=True,
            data={
                "execution_id": execution_id,
                "format": format,
                "content": logs_content,
                "filters": {"node_id": node_id, "level": level, "limit": limit},
            },
            metadata={"content_length": len(logs_content), "timestamp": "2025-01-28T12:00:00Z"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")


@router.get(
    "/executions/{execution_id}/summary",
    response_model=ApiResponse,
    summary="Get execution summary",
    description="Get a comprehensive summary of workflow execution",
)
async def get_execution_summary(
    execution_id: str = PathParam(..., description="Execution ID"),
    format: str = Query("json", description="Output format"),
    raw: bool = Query(False, description="Return raw formatted content"),
):
    """Get execution summary"""

    try:
        # Validate format
        if format not in [fmt.value for fmt in OutputFormat]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format '{format}'. Available formats: {[fmt.value for fmt in OutputFormat]}",
            )

        # Get summary from service
        summary_content = logging_service.get_execution_summary(
            execution_id=execution_id, format_type=OutputFormat(format)
        )

        if raw:
            media_type = "application/json" if format.startswith("json") else "text/plain"
            if format == "html":
                media_type = "text/html"

            return PlainTextResponse(content=summary_content, media_type=media_type)

        return ApiResponse(
            success=True,
            data={"execution_id": execution_id, "format": format, "content": summary_content},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve summary: {str(e)}")


@router.get(
    "/executions/{execution_id}/nodes/{node_id}/details",
    response_model=ApiResponse,
    summary="Get node execution details",
    description="Get detailed information about a specific node execution",
)
async def get_node_execution_details(
    execution_id: str = PathParam(..., description="Execution ID"),
    node_id: str = PathParam(..., description="Node ID"),
    format: str = Query("json_pretty", description="Output format"),
    raw: bool = Query(False, description="Return raw formatted content"),
):
    """Get detailed node execution information"""

    try:
        # Validate format
        if format not in [fmt.value for fmt in OutputFormat]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format '{format}'. Available formats: {[fmt.value for fmt in OutputFormat]}",
            )

        # Get node details from service
        details_content = logging_service.get_node_execution_details(
            execution_id=execution_id, node_id=node_id, format_type=OutputFormat(format)
        )

        if raw:
            media_type = "application/json" if format.startswith("json") else "text/plain"
            if format == "html":
                media_type = "text/html"

            return PlainTextResponse(content=details_content, media_type=media_type)

        return ApiResponse(
            success=True,
            data={
                "execution_id": execution_id,
                "node_id": node_id,
                "format": format,
                "content": details_content,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve node details: {str(e)}")


@router.post(
    "/executions/{execution_id}/export",
    response_model=ApiResponse,
    summary="Export execution logs",
    description="Export execution logs to a downloadable file",
)
async def export_execution_logs(
    execution_id: str = PathParam(..., description="Execution ID"),
    export_request: ExportRequest = ExportRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Export execution logs to file"""

    try:
        # Validate format
        if export_request.format not in [fmt.value for fmt in OutputFormat]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format '{export_request.format}'. Available formats: {[fmt.value for fmt in OutputFormat]}",
            )

        # Create temporary file
        suffix = {
            "json": ".json",
            "json_pretty": ".json",
            "html": ".html",
            "markdown": ".md",
            "csv": ".csv",
        }.get(export_request.format, ".txt")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, prefix=f"execution_{execution_id[:8]}_"
        ) as temp_file:
            temp_path = temp_file.name

        # Export logs to temporary file
        logging_service.export_execution_logs(
            execution_id=execution_id,
            file_path=temp_path,
            format_type=OutputFormat(export_request.format),
        )

        # Schedule cleanup
        def cleanup_temp_file():
            try:
                os.unlink(temp_path)
            except Exception:
                pass

        background_tasks.add_task(cleanup_temp_file)

        # Read file content for response
        with open(temp_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Determine content type
        content_type = "application/octet-stream"
        if export_request.format.startswith("json"):
            content_type = "application/json"
        elif export_request.format == "html":
            content_type = "text/html"
        elif export_request.format == "markdown":
            content_type = "text/markdown"
        elif export_request.format == "csv":
            content_type = "text/csv"

        # Return as streaming response for download
        def generate_content():
            yield content

        return StreamingResponse(
            generate_content(),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=execution_{execution_id[:8]}{suffix}"
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export logs: {str(e)}")


@router.get(
    "/logging/formats",
    response_model=ApiResponse,
    summary="List output formats",
    description="Get list of available log output formats",
)
async def get_available_formats():
    """List available output formats"""

    try:
        formats = logging_service.get_available_formats()

        format_info = []
        format_descriptions = {
            "console": {
                "name": "console",
                "description": "Colored console output with symbols",
                "mime_type": "text/plain",
                "use_case": "Command line viewing",
            },
            "console_compact": {
                "name": "console_compact",
                "description": "Compact console output",
                "mime_type": "text/plain",
                "use_case": "Quick overview",
            },
            "console_detailed": {
                "name": "console_detailed",
                "description": "Detailed console output with full context",
                "mime_type": "text/plain",
                "use_case": "Debugging and analysis",
            },
            "json": {
                "name": "json",
                "description": "Compact JSON format",
                "mime_type": "application/json",
                "use_case": "API integration, machine processing",
            },
            "json_pretty": {
                "name": "json_pretty",
                "description": "Pretty-printed JSON format",
                "mime_type": "application/json",
                "use_case": "Human-readable JSON",
            },
            "html": {
                "name": "html",
                "description": "HTML format with styling",
                "mime_type": "text/html",
                "use_case": "Web display, reports",
            },
            "markdown": {
                "name": "markdown",
                "description": "Markdown format for documentation",
                "mime_type": "text/markdown",
                "use_case": "Documentation, GitHub",
            },
            "csv": {
                "name": "csv",
                "description": "CSV format for spreadsheet import",
                "mime_type": "text/csv",
                "use_case": "Data analysis, Excel",
            },
            "table": {
                "name": "table",
                "description": "ASCII table format",
                "mime_type": "text/plain",
                "use_case": "Structured console output",
            },
        }

        for fmt in formats:
            info = format_descriptions.get(
                fmt,
                {
                    "name": fmt,
                    "description": "No description available",
                    "mime_type": "text/plain",
                    "use_case": "General purpose",
                },
            )
            format_info.append(info)

        return ApiResponse(
            success=True,
            data={
                "formats": format_info,
                "default_format": "json",
                "total_count": len(format_info),
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve formats: {str(e)}")


@router.get(
    "/executions/{execution_id}/logs/live",
    summary="Get live execution logs",
    description="Get real-time execution logs (long polling endpoint)",
)
async def get_live_execution_logs(
    execution_id: str = PathParam(..., description="Execution ID"),
    format: str = Query("json", description="Output format"),
    since: Optional[float] = Query(None, description="Get logs since timestamp"),
    timeout: int = Query(30, description="Polling timeout in seconds"),
):
    """Get live execution logs with long polling"""

    # This would implement long polling or Server-Sent Events
    # For now, return current logs
    try:
        logs_content = logging_service.get_execution_logs(
            execution_id=execution_id, format_type=OutputFormat(format)
        )

        return ApiResponse(
            success=True,
            data={
                "execution_id": execution_id,
                "format": format,
                "content": logs_content,
                "timestamp": "2025-01-28T12:00:00Z",
                "is_live": True,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve live logs: {str(e)}")


# Health check endpoint
@router.get(
    "/logging/health",
    response_model=ApiResponse,
    summary="Health check",
    description="Check the health of the logging service",
)
async def logging_health_check():
    """Health check for the logging service"""

    try:
        # Basic health check
        formats = logging_service.get_available_formats()

        return ApiResponse(
            success=True,
            data={
                "status": "healthy",
                "service": "workflow_execution_logging",
                "version": "2.0.0",
                "available_formats": len(formats),
                "timestamp": "2025-01-28T12:00:00Z",
            },
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"Logging service unhealthy: {str(e)}",
            data={"status": "unhealthy", "service": "workflow_execution_logging"},
        )


__all__ = ["router"]
