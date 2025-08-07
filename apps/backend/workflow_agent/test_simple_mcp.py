#!/usr/bin/env python3
"""
Simple test for MCP tool calling
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from agents.mcp_tools import MCPToolCaller

logging.basicConfig(level=logging.INFO)

async def test_mcp_tools():
    """Test basic MCP tool functionality"""
    
    print("Testing MCP Tools")
    print("="*50)
    
    # Initialize MCP client
    mcp_client = MCPToolCaller()
    
    # Test 1: Get node types
    print("\n1. Testing get_node_types...")
    try:
        result = await mcp_client.get_node_types()
        print("✅ Success! Node types retrieved:")
        print(json.dumps(result, indent=2)[:500] + "...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Get specific node details
    print("\n2. Testing get_node_details...")
    try:
        nodes_to_query = [
            {"node_type": "TRIGGER_NODE", "subtype": "schedule"},
            {"node_type": "EXTERNAL_ACTION_NODE", "subtype": "SLACK"}
        ]
        result = await mcp_client.get_node_details(nodes_to_query)
        print("✅ Success! Node details retrieved:")
        print(json.dumps(result, indent=2)[:500] + "...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n✅ MCP Tools test completed!")

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())