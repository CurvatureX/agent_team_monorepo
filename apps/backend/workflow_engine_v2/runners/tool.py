"""Tool node runner (e.g., MCP tools)."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

import httpx

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import TriggerInfo
from shared.models.workflow import Node
from workflow_engine_v2.core.template import render_structure
from workflow_engine_v2.runners.base import NodeRunner

logger = logging.getLogger(__name__)


def _get_api_gateway_url() -> str:
    """Get API Gateway URL from environment."""
    return os.getenv("API_GATEWAY_URL", "http://localhost:8000")


async def _call_mcp_tool_async(
    tool_name: str, arguments: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """Call MCP tool via API Gateway's /api/v1/mcp/invoke endpoint.

    Args:
        tool_name: Name of the MCP tool to invoke (e.g., "notion_search")
        arguments: Tool arguments/parameters
        user_id: User ID for OAuth token retrieval

    Returns:
        Dict containing tool execution result
    """
    api_gateway_url = _get_api_gateway_url()
    # Use internal endpoint that doesn't require authentication
    invoke_endpoint = f"{api_gateway_url}/api/v1/mcp/invoke/internal"

    # Prepare request payload
    payload = {
        "name": tool_name,
        "arguments": arguments,
        "_metadata": {"user_id": user_id},  # Pass user_id for OAuth token retrieval
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"🔧 Calling MCP tool '{tool_name}' via API Gateway (internal)")

            headers = {
                "Content-Type": "application/json",
            }

            response = await client.post(invoke_endpoint, json=payload, headers=headers)
            response.raise_for_status()

            # Internal endpoint returns direct result (not JSON-RPC wrapped)
            result = response.json()

            if result.get("isError"):
                error_msg = result.get("content", [{}])[0].get("text", "Unknown error")
                logger.error(f"❌ MCP tool '{tool_name}' failed: {error_msg}")
                return result
            else:
                logger.info(f"✅ MCP tool '{tool_name}' executed successfully")
                return result

    except Exception as e:
        logger.error(f"❌ Failed to call MCP tool '{tool_name}': {str(e)}")
        return {
            "content": [{"type": "text", "text": f"Tool execution failed: {str(e)}"}],
            "isError": True,
        }


class ToolRunner(NodeRunner):
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        """Execute MCP tool by calling API Gateway's /api/v1/mcp/invoke endpoint."""
        payload = inputs.get("result", inputs)
        engine_ctx = inputs.get("_ctx") if isinstance(inputs, dict) else None

        # Build template context
        ctx = {
            "input": payload,
            "config": node.configurations,
            "trigger": {"type": trigger.trigger_type, "data": trigger.trigger_data},
            "nodes_id": getattr(engine_ctx, "node_outputs", {}) if engine_ctx else {},
            "nodes_name": getattr(engine_ctx, "node_outputs_by_name", {}) if engine_ctx else {},
        }

        # Render template with context
        templated = render_structure(payload, ctx)

        # Extract tool call details from AI agent's output
        main_input = templated.get("main", templated) if isinstance(templated, dict) else templated
        tool_name = main_input.get("tool_name") if isinstance(main_input, dict) else None
        tool_args = main_input.get("args", {}) if isinstance(main_input, dict) else {}

        if not tool_name:
            logger.error("❌ No tool_name provided in MCP tool call")
            return {
                "result": {
                    "success": False,
                    "error_message": "No tool_name provided",
                    "result": None,
                }
            }

        # Get user_id from trigger for OAuth token retrieval
        user_id = trigger.user_id if hasattr(trigger, "user_id") else None
        if not user_id:
            logger.error("❌ No user_id found in trigger for OAuth token retrieval")
            return {
                "result": {
                    "success": False,
                    "error_message": "No user_id found for OAuth authentication",
                    "result": None,
                }
            }

        # Call MCP tool via API Gateway
        try:
            result = asyncio.run(_call_mcp_tool_async(tool_name, tool_args, user_id))

            # Extract content from MCP response
            if result.get("isError"):
                content_text = result.get("content", [{}])[0].get("text", "Tool execution failed")
                logger.error(f"❌ MCP tool returned error: {content_text}")
                return {
                    "result": {
                        "success": False,
                        "error_message": content_text,
                        "result": None,
                    }
                }
            else:
                # Extract actual result from MCP response
                content_items = result.get("content", [])
                if content_items:
                    content_text = content_items[0].get("text", "")
                else:
                    content_text = ""

                # Also include structured content if available
                structured = result.get("structuredContent")

                logger.info(f"✅ MCP tool '{tool_name}' executed successfully")
                return {
                    "result": {
                        "success": True,
                        "error_message": "",
                        "result": structured if structured else content_text,
                    }
                }

        except Exception as e:
            logger.error(f"❌ MCP tool execution failed: {str(e)}")
            return {
                "result": {
                    "success": False,
                    "error_message": f"Tool execution failed: {str(e)}",
                    "result": None,
                }
            }


__all__ = ["ToolRunner"]
