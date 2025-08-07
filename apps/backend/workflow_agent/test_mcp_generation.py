#!/usr/bin/env python3
"""
Test script for MCP-based workflow generation
Tests the new workflow_generation_node that uses MCP tools for accurate node discovery
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from workflow_agent.agents.nodes import WorkflowAgentNodes
from workflow_agent.agents.state import WorkflowStage, WorkflowState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_workflow_generation():
    """Test the MCP-based workflow generation"""
    
    # Initialize the nodes
    nodes = WorkflowAgentNodes()
    
    # Create a test state with requirements
    test_state = WorkflowState(
        session_id="test-session-123",
        stage=WorkflowStage.WORKFLOW_GENERATION,
        user_message="Create a workflow that monitors a Slack channel for bug reports, creates GitHub issues for each report, assigns them to the right team member based on the bug category, and sends a daily summary email to the engineering manager.",
        intent_summary="""User wants to create an automated bug tracking workflow that:
1. Monitors Slack channel for bug reports
2. Creates GitHub issues automatically
3. Assigns issues based on bug category
4. Sends daily summary emails to manager""",
        conversations=[],
        identified_gaps=[],
        gap_status="no_gap"
    )
    
    print("\n" + "="*60)
    print("Testing MCP-based Workflow Generation")
    print("="*60)
    
    print("\n📋 Test Requirements:")
    print(test_state.get("intent_summary"))
    
    print("\n🔧 Starting workflow generation with MCP tools...")
    
    try:
        # Run the workflow generation node
        result_state = await nodes.workflow_generation_node(test_state)
        
        # Check if workflow was generated
        if "current_workflow" in result_state:
            workflow = result_state["current_workflow"]
            
            print("\n✅ Workflow generated successfully!")
            print("\n📄 Generated Workflow:")
            print(json.dumps(workflow, indent=2))
            
            # Analyze the workflow
            print("\n📊 Workflow Analysis:")
            print(f"- Workflow ID: {workflow.get('id', 'N/A')}")
            print(f"- Name: {workflow.get('name', 'N/A')}")
            print(f"- Number of nodes: {len(workflow.get('nodes', []))}")
            print(f"- Number of connections: {len(workflow.get('connections', []))}")
            
            # Check node types
            nodes_list = workflow.get('nodes', [])
            node_types = {}
            for node in nodes_list:
                node_type = node.get('type', 'unknown')
                node_types[node_type] = node_types.get(node_type, 0) + 1
            
            print("\n📈 Node Type Distribution:")
            for node_type, count in node_types.items():
                print(f"  - {node_type}: {count}")
            
            # Verify MCP tool usage
            print("\n🔍 Verification:")
            has_slack_trigger = any(
                'slack' in str(node).lower() 
                for node in nodes_list
            )
            has_github_action = any(
                'github' in str(node).lower()
                for node in nodes_list
            )
            has_email_action = any(
                'email' in str(node).lower() or 'mail' in str(node).lower()
                for node in nodes_list  
            )
            
            print(f"  - Has Slack integration: {'✅' if has_slack_trigger else '❌'}")
            print(f"  - Has GitHub integration: {'✅' if has_github_action else '❌'}")
            print(f"  - Has Email capability: {'✅' if has_email_action else '❌'}")
            
            # Check if it moved to debug stage
            if result_state.get("stage") == WorkflowStage.DEBUG:
                print("\n✅ Successfully moved to DEBUG stage")
            else:
                print(f"\n⚠️ Unexpected stage: {result_state.get('stage')}")
                
        else:
            print("\n❌ No workflow generated")
            print(f"Debug result: {result_state.get('debug_result', 'N/A')}")
            
    except Exception as e:
        print(f"\n❌ Error during workflow generation: {e}")
        logger.error("Workflow generation failed", exc_info=True)

async def test_fallback_generation():
    """Test the fallback generation when OpenAI is not available"""
    
    print("\n" + "="*60)
    print("Testing Fallback Workflow Generation")
    print("="*60)
    
    # Temporarily disable OpenAI client
    nodes = WorkflowAgentNodes()
    original_client = nodes.openai_client
    nodes.openai_client = None
    
    test_state = WorkflowState(
        session_id="test-fallback-456",
        stage=WorkflowStage.WORKFLOW_GENERATION,
        user_message="Create a simple data backup workflow",
        intent_summary="User wants to create a data backup workflow",
        conversations=[],
        identified_gaps=[],
        gap_status="no_gap"
    )
    
    try:
        result_state = await nodes.workflow_generation_node(test_state)
        
        if "current_workflow" in result_state:
            print("\n✅ Fallback workflow generated successfully")
            workflow = result_state["current_workflow"]
            print(f"- Workflow ID: {workflow.get('id', 'N/A')}")
            print(f"- Nodes: {len(workflow.get('nodes', []))}")
        else:
            print("\n❌ Fallback generation failed")
            
    finally:
        # Restore OpenAI client
        nodes.openai_client = original_client

async def main():
    """Run all tests"""
    
    print("\n🚀 Starting MCP Workflow Generation Tests")
    print("=" * 60)
    
    # Check environment
    print("\n🔍 Environment Check:")
    print(f"  - OpenAI API Key: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}")
    print(f"  - Anthropic API Key: {'✅ Set' if os.getenv('ANTHROPIC_API_KEY') else '❌ Not set'}")
    print(f"  - API Gateway URL: http://localhost:8000")
    
    # Remind to start API Gateway
    print("\n⚠️  Make sure the API Gateway is running:")
    print("   cd ../api-gateway && python main.py")
    
    # Check if running interactively
    import sys
    if sys.stdin.isatty():
        input("\nPress Enter to continue with tests...")
    else:
        print("\nRunning in non-interactive mode, continuing...")
    
    # Run tests
    await test_workflow_generation()
    await test_fallback_generation()
    
    print("\n✅ All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())