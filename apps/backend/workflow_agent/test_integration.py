#!/usr/bin/env python3
"""
Integration test for MCP-based workflow generation
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from agents.nodes import WorkflowAgentNodes
from agents.state import WorkflowStage, WorkflowState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_mcp_workflow_generation():
    """Test the MCP-based workflow generation"""
    
    print("\n" + "="*60)
    print("Testing MCP-based Workflow Generation")
    print("="*60)
    
    # Check if OpenAI key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OpenAI API key not set. Skipping MCP test.")
        print("   Set OPENAI_API_KEY environment variable to enable this test.")
        return
    
    # Initialize nodes
    nodes = WorkflowAgentNodes()
    
    # Test case: Simple Slack notification workflow
    test_state = WorkflowState(
        session_id="test-mcp-001",
        stage=WorkflowStage.WORKFLOW_GENERATION,
        user_message="Create a workflow that sends a Slack message every morning at 9 AM",
        intent_summary="Daily Slack notification at 9 AM",
        conversations=[],
        identified_gaps=[],
        gap_status="no_gap"
    )
    
    print("\n📋 Test Case: Daily Slack Notification")
    print(f"   Requirements: {test_state['intent_summary']}")
    
    try:
        print("\n🔧 Generating workflow with MCP tools...")
        result = await nodes.workflow_generation_node(test_state)
        
        if "current_workflow" in result:
            workflow = result["current_workflow"]
            print("\n✅ Workflow generated successfully!")
            
            # Basic validation
            print("\n📊 Workflow Summary:")
            print(f"   - ID: {workflow.get('id', 'N/A')}")
            print(f"   - Name: {workflow.get('name', 'N/A')}")
            print(f"   - Nodes: {len(workflow.get('nodes', []))}")
            print(f"   - Connections: {len(workflow.get('connections', []))}")
            
            # Check for expected node types
            nodes_list = workflow.get('nodes', [])
            has_trigger = any(n.get('type') == 'TRIGGER_NODE' for n in nodes_list)
            has_slack = any('slack' in str(n).lower() for n in nodes_list)
            
            print("\n🔍 Validation:")
            print(f"   - Has trigger node: {'✅' if has_trigger else '❌'}")
            print(f"   - Has Slack node: {'✅' if has_slack else '❌'}")
            
            # Save workflow to file for inspection
            output_file = "generated_workflow.json"
            with open(output_file, 'w') as f:
                json.dump(workflow, f, indent=2)
            print(f"\n💾 Workflow saved to: {output_file}")
            
        else:
            print("\n❌ No workflow generated")
            print(f"   Error: {result.get('debug_result', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error("Test failed", exc_info=True)

async def test_fallback_workflow():
    """Test fallback when OpenAI is not available"""
    
    print("\n" + "="*60)
    print("Testing Fallback Workflow Generation")
    print("="*60)
    
    # Initialize nodes and disable OpenAI
    nodes = WorkflowAgentNodes()
    nodes.openai_client = None
    
    test_state = WorkflowState(
        session_id="test-fallback-001",
        stage=WorkflowStage.WORKFLOW_GENERATION,
        user_message="Create a simple backup workflow",
        intent_summary="Data backup workflow",
        conversations=[],
        identified_gaps=[],
        gap_status="no_gap"
    )
    
    print("\n📋 Test Case: Fallback Generation")
    print("   (OpenAI client disabled)")
    
    try:
        result = await nodes.workflow_generation_node(test_state)
        
        if "current_workflow" in result:
            print("\n✅ Fallback workflow generated")
            workflow = result["current_workflow"]
            print(f"   - Nodes: {len(workflow.get('nodes', []))}")
            print(f"   - Type: Basic fallback structure")
        else:
            print("\n❌ Fallback generation failed")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

async def main():
    """Run all tests"""
    
    print("\n🚀 MCP Workflow Generation Integration Test")
    print("=" * 60)
    
    # Environment check
    print("\n🔍 Environment:")
    print(f"   - OpenAI API: {'✅ Configured' if os.getenv('OPENAI_API_KEY') else '❌ Not configured'}")
    print(f"   - API Gateway: http://localhost:8000")
    
    # Run tests
    await test_mcp_workflow_generation()
    await test_fallback_workflow()
    
    print("\n" + "="*60)
    print("✅ Integration tests completed!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())