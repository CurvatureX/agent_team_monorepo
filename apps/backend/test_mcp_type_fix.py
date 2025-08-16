#!/usr/bin/env python3
"""
Test workflow generation with MCP ParameterType-based mock value generation.
This tests that the LLM generates correct mock values based on MCP-provided types.
"""

import asyncio
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_workflow_generation():
    """Test workflow generation with GitHub issue creation"""
    from workflow_agent.agents.nodes import WorkflowAgentNodes
    from workflow_agent.agents.state import WorkflowState, WorkflowStage
    
    logger.info("=" * 80)
    logger.info("Testing MCP ParameterType-based Mock Value Generation")
    logger.info("=" * 80)
    
    # Initialize the workflow agent nodes
    nodes = WorkflowAgentNodes()
    
    # Create test state
    state = {
        "session_id": "test-session-mcp-types",
        "user_id": "test-user",
        "stage": WorkflowStage.WORKFLOW_GENERATION,
        "user_message": "Create a workflow that comments on GitHub issues when they are created",
        "intent_summary": "Create a workflow that automatically comments on new GitHub issues",
        "conversations": [],
        "tracking_id": f"test-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    }
    
    logger.info("\n🎯 Test Objective:")
    logger.info("Verify that LLM generates mock values based on MCP ParameterType")
    logger.info("Expected: issue_number should be an integer (123), not a string or template variable")
    
    try:
        # Run workflow generation
        logger.info("\n📦 Running workflow generation node...")
        result = await nodes.workflow_generation_node(state)
        
        # Check if workflow was generated
        if "current_workflow" in result:
            workflow = result["current_workflow"]
            logger.info("\n✅ Workflow generated successfully!")
            
            # Analyze parameters in the workflow
            logger.info("\n🔍 Analyzing parameter types in generated workflow:")
            for node in workflow.get("nodes", []):
                node_type = node.get("type")
                node_subtype = node.get("subtype")
                parameters = node.get("parameters", {})
                
                if parameters:
                    logger.info(f"\n  Node: {node_type}:{node_subtype}")
                    for param_name, param_value in parameters.items():
                        value_type = type(param_value).__name__
                        
                        # Check for problematic patterns
                        is_template = False
                        is_reference = False
                        
                        if isinstance(param_value, str):
                            is_template = "{{" in param_value or "${" in param_value
                        elif isinstance(param_value, dict):
                            is_reference = "$ref" in param_value or "$expr" in param_value
                        
                        # Log parameter analysis
                        status = "✅"
                        if is_template:
                            status = "❌ TEMPLATE"
                        elif is_reference:
                            status = "❌ REFERENCE"
                        elif param_name == "issue_number" and not isinstance(param_value, int):
                            status = "⚠️ WRONG TYPE"
                        
                        logger.info(f"    {status} {param_name}: {param_value} (type: {value_type})")
            
            # Check if workflow creation succeeded
            if "workflow_creation_error" in result:
                logger.error(f"\n❌ Workflow creation failed: {result['workflow_creation_error']}")
            elif "workflow_id" in result:
                logger.info(f"\n✅ Workflow created with ID: {result['workflow_id']}")
            
            # Save workflow for inspection
            output_file = "test_workflow_mcp_types.json"
            with open(output_file, "w") as f:
                json.dump(workflow, f, indent=2)
            logger.info(f"\n💾 Workflow saved to: {output_file}")
            
            # Check node specs cache
            if hasattr(nodes, 'node_specs_cache'):
                logger.info(f"\n📚 MCP Node Specs Cached: {len(nodes.node_specs_cache)} specs")
                for spec_key in list(nodes.node_specs_cache.keys())[:3]:
                    logger.info(f"  - {spec_key}")
            
        else:
            logger.error("❌ No workflow generated")
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_workflow_generation())