"""MCP Tool Discovery and Integration for AI Agents.

This module provides utilities for discovering MCP tools from attached TOOL nodes
and integrating them with AI models.

MCP tools are hosted in the API Gateway at /api/v1/mcp/tools and provide real
integrations to external services like Slack, Notion, Google Calendar, etc.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from shared.models.node_enums import ToolSubtype
from shared.models.workflow import Node

logger = logging.getLogger(__name__)


# Cache for MCP tool schemas fetched from API Gateway
_mcp_tools_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None
_cache_timestamp: Optional[float] = None
_cache_ttl: int = 300  # 5 minutes


def _get_api_gateway_url() -> str:
    """Get API Gateway URL from environment.

    Uses API_GATEWAY_URL which is already configured in ECS for service discovery.
    Defaults to localhost for local development and docker-compose.
    """
    return os.getenv("API_GATEWAY_URL", "http://localhost:8000")


async def fetch_mcp_tools_from_api_gateway() -> Dict[str, List[Dict[str, Any]]]:
    """Fetch MCP tool schemas from API Gateway /api/v1/mcp/tools endpoint.

    Returns:
        Dict mapping tool subtypes to their available tools
    """
    global _mcp_tools_cache, _cache_timestamp

    import time

    current_time = time.time()

    # Return cached results if still valid
    if _mcp_tools_cache and _cache_timestamp and (current_time - _cache_timestamp) < _cache_ttl:
        logger.debug("🔧 Using cached MCP tools")
        return _mcp_tools_cache

    api_gateway_url = _get_api_gateway_url()
    # Use internal endpoint that doesn't require API key authentication
    tools_endpoint = f"{api_gateway_url}/api/v1/mcp/tools/internal"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(tools_endpoint)
            response.raise_for_status()
            data = response.json()

            # Organize tools by category/subtype
            tools_by_subtype: Dict[str, List[Dict[str, Any]]] = {}

            if "tools" in data:
                for tool in data["tools"]:
                    # Map category to ToolSubtype
                    category = tool.get("category", "unknown")

                    # Determine tool subtype from category
                    subtype_map = {
                        "slack": ToolSubtype.SLACK_MCP_TOOL.value,
                        "discord": ToolSubtype.DISCORD_MCP_TOOL.value,
                        "notion": ToolSubtype.NOTION_MCP_TOOL.value,
                        "google_calendar": ToolSubtype.GOOGLE_CALENDAR_MCP_TOOL.value,
                        "firecrawl": ToolSubtype.FIRECRAWL_MCP_TOOL.value,
                        "github": "GITHUB_MCP_TOOL",
                        "gmail": "GMAIL_MCP_TOOL",
                    }

                    subtype = subtype_map.get(category, "UNKNOWN_MCP_TOOL")

                    if subtype not in tools_by_subtype:
                        tools_by_subtype[subtype] = []

                    # Convert MCP tool format to our internal format
                    tool_def = {
                        "name": tool["name"],
                        "description": tool.get("description", f"Execute {tool['name']}"),
                        "parameters": tool.get("inputSchema", tool.get("parameters", {})),
                        "category": category,
                    }

                    tools_by_subtype[subtype].append(tool_def)

            # Update cache
            _mcp_tools_cache = tools_by_subtype
            _cache_timestamp = current_time

            logger.info(f"🔧 Fetched {len(data.get('tools', []))} MCP tools from API Gateway")
            return tools_by_subtype

    except Exception as e:
        logger.error(f"❌ Failed to fetch MCP tools from API Gateway: {str(e)}")

        # Return fallback minimal schemas if API Gateway is unavailable
        logger.warning("⚠️ Using fallback MCP tool schemas")
        return _get_fallback_tool_schemas()


def _get_fallback_tool_schemas() -> Dict[str, List[Dict[str, Any]]]:
    """Fallback tool schemas if API Gateway is unavailable.

    These are minimal schemas - full schemas should be fetched from API Gateway.
    """
    return {
        ToolSubtype.SLACK_MCP_TOOL.value: [
            {
                "name": "slack_send_message",
                "description": "Send a message to a Slack channel or direct message",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name (e.g., 'C1234567890' or '#general')",
                        },
                        "text": {
                            "type": "string",
                            "description": "Message text to send",
                        },
                        "thread_ts": {
                            "type": "string",
                            "description": "Optional: Thread timestamp for replying in a thread",
                        },
                    },
                    "required": ["channel", "text"],
                },
            },
            {
                "name": "slack_list_channels",
                "description": "List all channels in the Slack workspace",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "types": {
                            "type": "string",
                            "description": "Channel types: 'public_channel', 'private_channel', 'mpim', 'im'",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of channels to return (default 100)",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "slack_get_user_info",
                "description": "Get information about a Slack user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID to retrieve information for",
                        },
                    },
                    "required": ["user_id"],
                },
            },
            {
                "name": "slack_get_channel_history",
                "description": "Get message history from a Slack channel",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of messages to retrieve (default 100)",
                        },
                    },
                    "required": ["channel"],
                },
            },
        ],
        ToolSubtype.DISCORD_MCP_TOOL.value: [
            {
                "name": "discord_send_message",
                "description": "Send a message to a Discord channel",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Discord channel ID",
                        },
                        "content": {
                            "type": "string",
                            "description": "Message content to send",
                        },
                    },
                    "required": ["channel_id", "content"],
                },
            },
        ],
        ToolSubtype.NOTION_MCP_TOOL.value: [
            {
                "name": "notion_search",
                "description": "Search for pages and databases in Notion",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query string",
                        },
                        "filter": {
                            "type": "object",
                            "description": "Filter by object type (page, database)",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "notion_get_page",
                "description": "Get a Notion page by ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Notion page ID",
                        },
                    },
                    "required": ["page_id"],
                },
            },
            {
                "name": "notion_update_page",
                "description": "Update properties of a Notion page",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Notion page ID",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Page properties to update",
                        },
                    },
                    "required": ["page_id", "properties"],
                },
            },
            {
                "name": "notion_create_page",
                "description": "Create a new page in Notion",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "parent_id": {
                            "type": "string",
                            "description": "Parent page or database ID",
                        },
                        "title": {
                            "type": "string",
                            "description": "Page title",
                        },
                        "content": {
                            "type": "string",
                            "description": "Page content in markdown or blocks",
                        },
                    },
                    "required": ["parent_id", "title"],
                },
            },
            {
                "name": "notion_query_database",
                "description": "Query a Notion database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "Notion database ID",
                        },
                        "filter": {
                            "type": "object",
                            "description": "Filter conditions for the query",
                        },
                    },
                    "required": ["database_id"],
                },
            },
        ],
        ToolSubtype.GOOGLE_CALENDAR_MCP_TOOL.value: [
            {
                "name": "calendar_create_event",
                "description": "Create a new event in Google Calendar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Event title",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Event start time (ISO 8601 format)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "Event end time (ISO 8601 format)",
                        },
                        "description": {
                            "type": "string",
                            "description": "Event description",
                        },
                        "attendees": {
                            "type": "array",
                            "description": "List of attendee email addresses",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["summary", "start_time", "end_time"],
                },
            },
            {
                "name": "calendar_list_events",
                "description": "List events from Google Calendar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "time_min": {
                            "type": "string",
                            "description": "Lower bound (ISO 8601) for event start time",
                        },
                        "time_max": {
                            "type": "string",
                            "description": "Upper bound (ISO 8601) for event end time",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of events to return",
                        },
                    },
                    "required": [],
                },
            },
        ],
        ToolSubtype.FIRECRAWL_MCP_TOOL.value: [
            {
                "name": "firecrawl_scrape",
                "description": "Scrape content from a website URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Website URL to scrape",
                        },
                        "formats": {
                            "type": "array",
                            "description": "Output formats (markdown, html, etc.)",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["url"],
                },
            },
        ],
    }


def discover_mcp_tools_from_nodes(tool_nodes: List[Node]) -> List[Dict[str, Any]]:
    """Discover available MCP tool functions from attached TOOL nodes.

    Fetches tool schemas from API Gateway at /api/v1/mcp/tools and matches them
    with the attached TOOL nodes' configurations.

    Args:
        tool_nodes: List of TOOL type nodes attached to the AI agent

    Returns:
        List of tool function definitions with name, description, and parameters
    """
    # Fetch MCP tool schemas from API Gateway (async)
    import asyncio

    try:
        tools_by_subtype = asyncio.run(fetch_mcp_tools_from_api_gateway())
    except Exception as e:
        logger.error(f"❌ Failed to fetch MCP tools: {str(e)}")
        # Use fallback schemas
        tools_by_subtype = _get_fallback_tool_schemas()

    available_tools = []

    for tool_node in tool_nodes:
        try:
            tool_subtype = str(tool_node.subtype)

            # Get tool schemas for this tool type from fetched schemas
            if tool_subtype not in tools_by_subtype:
                logger.warning(f"⚠️ No MCP tools available for type: {tool_subtype}")
                continue

            tool_schemas = tools_by_subtype[tool_subtype]

            # Get available tools from node configuration
            configured_tool_names = tool_node.configurations.get("available_tools", [])

            # Try to match configured tools with actual MCP tools
            matched_tools = []
            if configured_tool_names:
                for tool_name in configured_tool_names:
                    tool_schema = next((t for t in tool_schemas if t["name"] == tool_name), None)
                    if tool_schema:
                        matched_tools.append(tool_schema)
                    else:
                        logger.warning(f"⚠️ Configured tool '{tool_name}' not found in MCP server")

            # If no tools matched or no tools configured, use all available tools for this type
            if not matched_tools:
                if configured_tool_names:
                    logger.warning(
                        f"⚠️ None of the configured tools matched MCP server, using all {len(tool_schemas)} available tools"
                    )
                matched_tools = tool_schemas

            # Add each matched tool
            for tool_schema in matched_tools:
                tool_def = tool_schema.copy()

                # Add metadata about the source tool node
                tool_def["_source_node_id"] = tool_node.id
                tool_def["_source_node_name"] = tool_node.name
                tool_def["_tool_subtype"] = tool_subtype

                available_tools.append(tool_def)
                logger.info(f"🔧 Added MCP tool: {tool_schema['name']} from {tool_node.id}")

        except Exception as e:
            logger.error(f"❌ Failed to discover tools from {tool_node.id}: {str(e)}")

    logger.info(f"🔧 Discovered {len(available_tools)} MCP tool functions")
    return available_tools


def generate_mcp_system_guidance(available_tools: List[Dict[str, Any]]) -> str:
    """Generate system prompt guidance for using MCP tools.

    Args:
        available_tools: List of available MCP tool definitions

    Returns:
        System prompt text explaining how to use MCP tools
    """
    if not available_tools:
        return ""

    tool_names = [tool["name"] for tool in available_tools]

    guidance = f"""
## Available MCP Tools

You have access to the following Model Context Protocol (MCP) tools that you can invoke to perform actions:

{', '.join(tool_names)}

**Important Instructions for Tool Usage:**

1. **When to Use Tools**: Use these tools whenever the user's request requires external actions like sending messages, querying data, or performing operations outside of text generation.

2. **How to Invoke Tools**: When you need to use a tool, invoke it using the function calling mechanism. Provide all required parameters as specified in the tool definition.

3. **Tool Results**: After invoking a tool, wait for the result before continuing. The tool execution result will be provided to you, and you should incorporate it into your response to the user.

4. **Multiple Tools**: You can invoke multiple tools if needed to complete the user's request. Invoke them sequentially or in parallel as appropriate.

5. **Error Handling**: If a tool invocation fails, acknowledge the error and suggest alternative approaches or ask the user for clarification.

**Example Usage:**
- User asks: "Send a message to #general saying hello"
- You should invoke: slack_send_message(channel="#general", text="hello")
- Then respond: "I've sent the message to #general."

Use these tools proactively when they can help accomplish the user's goals.
"""

    return guidance.strip()


def get_tool_invocation_guidance(provider: str) -> str:
    """Get provider-specific guidance for tool invocation.

    Args:
        provider: AI provider name ('openai', 'anthropic', 'gemini')

    Returns:
        Provider-specific tool usage guidance
    """
    if provider == "openai":
        return """
When you need to use a tool, use the function calling capability.
OpenAI will automatically format your function calls correctly.
"""
    elif provider == "anthropic":
        return """
When you need to use a tool, invoke it using Claude's tool use format.
Anthropic will handle the tool invocation and provide results.
"""
    elif provider == "gemini":
        return """
When you need to use a tool, invoke it using Gemini's function calling.
Google will execute the function and return the results to you.
"""
    else:
        return """
When you need to use a tool, invoke it using the function calling mechanism provided by your AI model.
"""


__all__ = [
    "fetch_mcp_tools_from_api_gateway",
    "discover_mcp_tools_from_nodes",
    "generate_mcp_system_guidance",
    "get_tool_invocation_guidance",
]
