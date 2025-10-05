"""
AI helper methods for Notion External Action.

This file contains the AI decision logic, context building, and resource accumulation
methods separated from the main implementation for better organization.
"""

import json
import logging
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)


async def build_ai_context(context_obj: Any, instruction: str, execution_state: dict) -> dict:
    """Build comprehensive 5-layer context for AI decision-making."""
    return {
        # Layer 1: User-provided explicit context
        "user_context": execution_state.get("user_context", {}),
        # Layer 2: Workflow execution context
        "workflow_context": {
            "trigger_type": (context_obj.trigger.trigger_type if context_obj.trigger else None),
            "trigger_data": (context_obj.trigger.trigger_data if context_obj.trigger else {}),
            "workflow_name": (
                getattr(context_obj.workflow, "name", None)
                if hasattr(context_obj, "workflow")
                else None
            ),
        },
        # Layer 3: Previous node outputs
        "previous_outputs": extract_previous_outputs(context_obj),
        # Layer 4: Execution history (current AI loop)
        "execution_history": execution_state.get("rounds", []),
        # Layer 5: Discovered Notion resources
        "notion_context": execution_state.get("discovered_resources", {}),
    }


def extract_previous_outputs(context_obj: Any) -> dict:
    """Extract outputs from upstream workflow nodes."""
    previous = {}

    # Main input from previous node
    main_input = context_obj.input_data.get("result", {})
    if main_input:
        previous["main_input"] = main_input

    # Extract common data keys
    for key in ["data", "content", "message", "items", "results", "summary"]:
        if key in context_obj.input_data:
            previous[key] = context_obj.input_data[key]

    return previous


def accumulate_context(execution_state: dict, action_type: str, result: dict) -> None:
    """Extract and accumulate discovered Notion resources + schemas."""
    discovered = execution_state["discovered_resources"]
    schemas = execution_state["schemas_cache"]

    # Search results → store databases/pages
    if action_type == "search":
        results = result.get("notion_response", {}).get("results", [])
        if isinstance(results, list):
            for item in results:
                obj_type = item.get("object")
                obj_id = item.get("id")
                title = extract_title_from_object(item)

                if obj_type == "database":
                    discovered.setdefault("databases", {})[title] = obj_id
                elif obj_type == "page":
                    discovered.setdefault("pages", {})[title] = obj_id

    # Created resources
    elif action_type in ["create_page", "create_database"]:
        resource_id = result.get("resource_id")
        if resource_id:
            resource_type = "database" if "database" in action_type else "page"
            discovered.setdefault(f"created_{resource_type}", []).append(resource_id)

    # Database schema retrieval → CACHE IT!
    elif action_type == "retrieve_database":
        database_data = result.get("notion_response", {})
        if isinstance(database_data, dict):
            database_id = database_data.get("id")
            properties = database_data.get("properties", {})

            if database_id and properties:
                schemas[database_id] = {
                    "properties": list(properties.keys()),
                    "schema": properties,
                }
                logger.info(
                    f"📚 Cached schema for database {database_id}: {list(properties.keys())}"
                )

    # Query results → store count
    elif action_type == "query_database":
        db_id = result.get("execution_metadata", {}).get("database_id")
        count = len(result.get("results", []))
        if db_id:
            discovered[f"query_{db_id}_count"] = count

    # Retrieved block children → store block IDs for batch operations
    elif action_type == "retrieve_block_children":
        block_id = result.get("execution_metadata", {}).get("block_id")
        blocks_data = result.get("notion_response", {}).get("results", [])

        if block_id and blocks_data:
            # Extract all block IDs
            block_ids = [block.get("id") for block in blocks_data if block.get("id")]
            if block_ids:
                discovered[f"page_{block_id}_blocks"] = {
                    "block_ids": block_ids,
                    "count": len(block_ids),
                }
                logger.info(f"📦 Cached {len(block_ids)} block IDs for page {block_id}")


def extract_title_from_object(notion_object: dict) -> str:
    """Extract title from Notion page/database object."""
    # Database title
    if "title" in notion_object:
        title_array = notion_object["title"]
        if title_array and len(title_array) > 0:
            return title_array[0].get("plain_text", "Untitled")

    # Page title (from properties)
    properties = notion_object.get("properties", {})
    for prop_name, prop_data in properties.items():
        if prop_data.get("type") == "title":
            title_array = prop_data.get("title", [])
            if title_array:
                return title_array[0].get("plain_text", "Untitled")

    return "Untitled"


async def call_ai_model_anthropic(
    api_key: str,
    system_prompt: str,
    user_message: str,
    model: str = "claude-sonnet-4-20250514",
    timeout: int = 120,
) -> dict:
    """Call Anthropic Claude API for AI decision."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    body = {
        "model": model,
        "max_tokens": 4096,
        "temperature": 0.7,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages", headers=headers, json=body
            )
            resp.raise_for_status()
            data = resp.json()

            # Extract content
            content = ""
            if "content" in data and data["content"]:
                for block in data["content"]:
                    if block.get("type") == "text":
                        content += block.get("text", "")

            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response as JSON: {content[:500]}")
                raise ValueError(f"AI returned invalid JSON: {content[:200]}")

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Anthropic API error: {e.response.status_code} - {e.response.text}")
        raise ValueError(f"Anthropic API error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"❌ Anthropic API request failed: {str(e)}")
        raise


async def call_ai_model_openai(
    api_key: str,
    system_prompt: str,
    user_message: str,
    model: str = "gpt-4",
    timeout: int = 120,
) -> dict:
    """Call OpenAI API for AI decision."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions", headers=headers, json=body
            )
            resp.raise_for_status()
            data = resp.json()

            # Extract content
            content = ""
            if "choices" in data and data["choices"]:
                content = data["choices"][0].get("message", {}).get("content", "")

            # Parse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse OpenAI response as JSON: {content[:500]}")
                raise ValueError(f"AI returned invalid JSON: {content[:200]}")

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ OpenAI API error: {e.response.status_code} - {e.response.text}")
        raise ValueError(f"OpenAI API error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"❌ OpenAI API request failed: {str(e)}")
        raise
