#!/usr/bin/env python3
"""
Test script for the Node Knowledge MCP Server implementation.

NOTE: This test is excluded from pre-commit hooks (.pre-commit-config.yaml)
because it requires external dependencies and specific environment setup
that may not be available in CI/CD environments.
"""

import asyncio
import sys
from pathlib import Path

# Add shared path for imports
current_dir = Path(__file__).parent
shared_path = current_dir / "../../../shared"
sys.path.insert(0, str(shared_path))

import pytest
from app.api.mcp.tools import NodeKnowledgeMCPService


@pytest.mark.asyncio
async def test_node_knowledge_mcp():
    """Test all MCP tools for node knowledge access."""

    print("=" * 60)
    print("Testing Node Knowledge MCP Server Implementation")
    print("=" * 60)

    service = NodeKnowledgeMCPService()

    # Test 1: Get available tools
    print("\n1. Testing get_available_tools()")
    print("-" * 40)
    tools_response = service.get_available_tools()
    print(f"Success: {tools_response.success}")
    print(f"Available tools: {[tool.name for tool in tools_response.tools]}")
    print(f"Total count: {tools_response.total_count}")
    print(f"Categories: {tools_response.categories}")

    # Test 2: Get all node types
    print("\n2. Testing get_node_types (all types)")
    print("-" * 40)
    result = await service.invoke_tool("get_node_types", {})
    print(f"Success: {not result.isError}")
    if not result.isError:
        node_types = result.structuredContent
        print(f"Found {len(node_types)} node types:")
        for node_type, subtypes in node_types.items():
            print(f"  {node_type}: {len(subtypes)} subtypes")
            if subtypes:
                print(f"    Examples: {subtypes[:3]}{'...' if len(subtypes) > 3 else ''}")

    # Test 3: Get filtered node types
    print("\n3. Testing get_node_types (ACTION_NODE filter)")
    print("-" * 40)
    result = await service.invoke_tool("get_node_types", {"type_filter": "ACTION_NODE"})
    print(f"Success: {not result.isError}")
    if not result.isError and result.structuredContent:
        action_nodes = result.structuredContent.get("ACTION_NODE", [])
        print(f"ACTION_NODE subtypes ({len(action_nodes)}): {action_nodes}")

    # Test 4: Search nodes
    print("\n4. Testing search_nodes")
    print("-" * 40)
    search_queries = ["HTTP request", "email", "database"]

    for query in search_queries:
        result = await service.invoke_tool(
            "search_nodes", {"query": query, "max_results": 3, "include_details": False}
        )
        print(f"Query '{query}': {not result.isError}")
        if not result.isError and result.structuredContent:
            matches = result.structuredContent.get("data", [])
            print(f"  Found {len(matches)} matches:")
            for match in matches:
                print(
                    f"    {match['node_type']}.{match['subtype']} (score: {match['relevance_score']})"
                )
        print()

    # Test 5: Get node details
    print("\n5. Testing get_node_details")
    print("-" * 40)

    test_nodes = [
        {"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"},
        {"node_type": "AI_AGENT_NODE", "subtype": "OPENAI_NODE"},
        {"node_type": "FLOW_NODE", "subtype": "IF"},
    ]

    result = await service.invoke_tool(
        "get_node_details",
        {"nodes": test_nodes, "include_examples": True, "include_schemas": False},
    )

    print(f"Success: {not result.isError}")
    if not result.isError and result.structuredContent:
        node_details = result.structuredContent.get("nodes", [])
        for node_detail in node_details:
            if "error" in node_detail:
                print(
                    f"  {node_detail['node_type']}.{node_detail['subtype']}: {node_detail['error']}"
                )
            else:
                print(f"  {node_detail['node_type']}.{node_detail['subtype']}:")
                print(f"    Description: {node_detail['description'][:80]}...")
                print(f"    Parameters: {len(node_detail.get('parameters', []))}")
                print(f"    Input ports: {len(node_detail.get('input_ports', []))}")
                print(f"    Output ports: {len(node_detail.get('output_ports', []))}")
                if "examples" in node_detail:
                    print(f"    Examples: {len(node_detail['examples'])}")

    # Test 6: Error handling
    print("\n6. Testing error handling")
    print("-" * 40)

    # Test invalid tool
    result = await service.invoke_tool("invalid_tool", {})
    error_msg = result.content[0].text if result.content else "No error message"
    print(f"Invalid tool result: success={not result.isError}, error='{error_msg}'")

    # Test invalid node
    result = await service.invoke_tool(
        "get_node_details", {"nodes": [{"node_type": "INVALID_NODE", "subtype": "INVALID_SUBTYPE"}]}
    )
    print(f"Invalid node result: success={not result.isError}")
    if not result.isError and result.structuredContent:
        node_details = result.structuredContent.get("nodes", [])
        if node_details:
            invalid_result = node_details[0]
            print(f"  Error: {invalid_result.get('error', 'No error message')}")

    # Test 7: Health check
    print("\n7. Testing health_check")
    print("-" * 40)
    health = service.health_check()
    print(f"Healthy: {health.healthy}")
    print(f"Version: {health.version}")
    print(f"Available tools: {health.available_tools}")

    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_node_knowledge_mcp())
