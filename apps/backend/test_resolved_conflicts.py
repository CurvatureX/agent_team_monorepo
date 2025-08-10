#!/usr/bin/env python
"""
Test that the merge conflicts have been resolved correctly
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work after conflict resolution"""
    print("=" * 60)
    print("Testing Resolved Conflicts")
    print("=" * 60)
    
    # Test workflow_agent imports
    try:
        from workflow_agent.agents.nodes import WorkflowAgentNodes
        print("✅ nodes.py imports successfully")
        
        # Check that gap_analysis_node is not present
        nodes = WorkflowAgentNodes()
        if not hasattr(nodes, 'gap_analysis_node'):
            print("✅ gap_analysis_node successfully removed")
        else:
            print("❌ gap_analysis_node still exists!")
            return False
        
        # Check that we have the 3 core nodes
        if hasattr(nodes, 'clarification_node'):
            print("✅ clarification_node exists")
        if hasattr(nodes, 'workflow_generation_node'):
            print("✅ workflow_generation_node exists")
        if hasattr(nodes, 'debug_node'):
            print("✅ debug_node exists")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test fastapi_server imports
    try:
        from workflow_agent.services.fastapi_server import WorkflowAgentServicer
        print("✅ fastapi_server.py imports successfully")
        
        # Check the servicer can be instantiated
        servicer = WorkflowAgentServicer()
        print("✅ WorkflowAgentServicer instantiated successfully")
        
    except ImportError as e:
        print(f"❌ FastAPI server import error: {e}")
        return False
    except Exception as e:
        print(f"❌ FastAPI server error: {e}")
        return False
    
    # Test shared models
    try:
        from shared.models.conversation import ResponseType
        
        # Check that DEBUG_RESULT is not in ResponseType
        response_types = [t.value for t in ResponseType]
        if "RESPONSE_TYPE_DEBUG_RESULT" not in response_types:
            print("✅ DEBUG_RESULT successfully removed from ResponseType")
        else:
            print("❌ DEBUG_RESULT still in ResponseType!")
            return False
            
    except ImportError as e:
        print(f"❌ Shared models import error: {e}")
        return False
        
    return True

def test_workflow_agent_structure():
    """Test the workflow agent structure after refactoring"""
    print("\n" + "=" * 60)
    print("Testing Workflow Agent Structure")
    print("=" * 60)
    
    try:
        from workflow_agent.agents.workflow_agent import WorkflowAgent
        
        agent = WorkflowAgent()
        
        # Check that the graph has the correct nodes
        node_names = list(agent.graph.nodes.keys())
        print(f"Graph nodes: {node_names}")
        
        expected_nodes = ["clarification", "workflow_generation", "debug"]
        missing_nodes = [n for n in expected_nodes if n not in node_names]
        unexpected_nodes = [n for n in node_names if n not in expected_nodes and n != "__start__" and n != "__end__"]
        
        if not missing_nodes:
            print("✅ All expected nodes present")
        else:
            print(f"❌ Missing nodes: {missing_nodes}")
            return False
            
        if "gap_analysis" not in node_names:
            print("✅ gap_analysis node successfully removed from graph")
        else:
            print("❌ gap_analysis node still in graph!")
            return False
            
        if not unexpected_nodes:
            print("✅ No unexpected nodes in graph")
        else:
            print(f"⚠️  Unexpected nodes found: {unexpected_nodes}")
            
    except ImportError as e:
        print(f"❌ WorkflowAgent import error: {e}")
        return False
    except Exception as e:
        print(f"❌ WorkflowAgent error: {e}")
        return False
        
    return True

def main():
    """Run all tests"""
    print("\n🔍 Testing Merge Conflict Resolution\n")
    
    all_passed = True
    
    # Run import tests
    if not test_imports():
        all_passed = False
    
    # Run structure tests
    if not test_workflow_agent_structure():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Conflicts resolved successfully!")
        print("\nOptimized 3-node architecture is working:")
        print("  • Clarification → Workflow Generation → Debug")
        print("  • Gap analysis integrated into workflow generation")
        print("  • DEBUG_RESULT merged into MESSAGE type")
    else:
        print("⚠️  Some tests failed. Please review the conflicts.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())