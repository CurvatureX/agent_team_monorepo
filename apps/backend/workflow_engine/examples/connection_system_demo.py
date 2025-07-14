#!/usr/bin/env python3
"""
ConnectionsMap System Demo

This example demonstrates the new ConnectionsMap system for workflow execution.
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow_engine.execution_engine import WorkflowExecutionEngine


def create_connections_map_workflow():
    """Create a workflow using the new ConnectionsMap system."""
    
    # This workflow demonstrates:
    # 1. A manual trigger
    # 2. An AI Agent that uses multiple connection types
    # 3. Different tools connected via different connection types
    
    workflow_definition = {
        "id": "connections-demo",
        "name": "ConnectionsMap Demo Workflow",
        "nodes": [
            {
                "id": "trigger-1",
                "name": "Manual Trigger",
                "type": "TRIGGER_NODE",
                "subtype": "MANUAL",
                "parameters": {},
                "credentials": {}
            },
            {
                "id": "ai-agent-1",
                "name": "Secretary AI Agent",
                "type": "AI_AGENT_NODE",
                "subtype": "ROUTER_AGENT",
                "parameters": {
                    "model_provider": "openai",
                    "model_name": "gpt-4",
                    "system_prompt": "You are a personal secretary AI agent."
                },
                "credentials": {}
            },
            {
                "id": "tool-1",
                "name": "Google Calendar Tool",
                "type": "TOOL_NODE",
                "subtype": "CALENDAR",
                "parameters": {
                    "calendar_id": "primary"
                },
                "credentials": {}
            },
            {
                "id": "memory-1",
                "name": "User Preferences Memory",
                "type": "MEMORY_NODE",
                "subtype": "SIMPLE_STORAGE",
                "parameters": {
                    "storage_type": "user_preferences"
                },
                "credentials": {}
            },
            {
                "id": "action-1",
                "name": "Send Notification",
                "type": "ACTION_NODE",
                "subtype": "DATA_TRANSFORMATION",
                "parameters": {
                    "transformation_type": "format_notification"
                },
                "credentials": {}
            }
        ],
        "connections": {
            "connections": {
                "Manual Trigger": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "Secretary AI Agent",
                                    "type": "MAIN",
                                    "index": 0
                                }
                            ]
                        }
                    }
                },
                "Secretary AI Agent": {
                    "connection_types": {
                        "ai_tool": {
                            "connections": [
                                {
                                    "node": "Google Calendar Tool",
                                    "type": "AI_TOOL",
                                    "index": 0
                                }
                            ]
                        },
                        "ai_memory": {
                            "connections": [
                                {
                                    "node": "User Preferences Memory",
                                    "type": "AI_MEMORY",
                                    "index": 0
                                }
                            ]
                        },
                        "main": {
                            "connections": [
                                {
                                    "node": "Send Notification",
                                    "type": "MAIN",
                                    "index": 0
                                }
                            ]
                        }
                    }
                }
            }
        },
        "static_data": {
            "user_timezone": "Asia/Shanghai",
            "default_calendar": "primary"
        }
    }
    
    return workflow_definition


def create_simple_workflow():
    """Create a simple workflow for comparison."""
    
    workflow_definition = {
        "id": "simple-demo",
        "name": "Simple Demo Workflow",
        "nodes": [
            {
                "id": "trigger-1",
                "name": "Manual Trigger",
                "type": "TRIGGER_NODE",
                "subtype": "MANUAL",
                "parameters": {},
                "credentials": {}
            },
            {
                "id": "action-1",
                "name": "Data Processing",
                "type": "ACTION_NODE",
                "subtype": "DATA_TRANSFORMATION",
                "parameters": {
                    "transformation_type": "filter"
                },
                "credentials": {}
            }
        ],
        "connections": {
            "connections": {
                "Manual Trigger": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "Data Processing",
                                    "type": "MAIN",
                                    "index": 0
                                }
                            ]
                        }
                    }
                }
            }
        },
        "static_data": {}
    }
    
    return workflow_definition


def demo_connections_map_validation():
    """Demo validation of ConnectionsMap workflows."""
    print("\n" + "="*60)
    print("CONNECTIONSMAP VALIDATION DEMO")
    print("="*60)
    
    engine = WorkflowExecutionEngine()
    
    # Test 1: Valid ConnectionsMap workflow
    print("\n1. Testing valid ConnectionsMap workflow...")
    workflow = create_connections_map_workflow()
    errors = engine._validate_workflow(workflow)
    
    if errors:
        print("❌ Validation failed with errors:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ Validation passed!")
    
    # Test 2: Invalid ConnectionsMap workflow (missing target node)
    print("\n2. Testing invalid ConnectionsMap workflow (missing target node)...")
    invalid_workflow = create_connections_map_workflow()
    invalid_workflow["connections"]["connections"]["Manual Trigger"]["connection_types"]["main"]["connections"][0]["node"] = "Non-existent Node"
    
    errors = engine._validate_workflow(invalid_workflow)
    
    if errors:
        print("✅ Validation correctly failed with errors:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("❌ Validation should have failed!")
    
    # Test 3: Invalid connection type
    print("\n3. Testing invalid connection type...")
    invalid_workflow = create_connections_map_workflow()
    invalid_workflow["connections"]["connections"]["Manual Trigger"]["connection_types"]["invalid_type"] = {
        "connections": [
            {
                "node": "Secretary AI Agent",
                "type": "MAIN",
                "index": 0
            }
        ]
    }
    
    errors = engine._validate_workflow(invalid_workflow)
    
    if errors:
        print("✅ Validation correctly failed with errors:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("❌ Validation should have failed!")


def demo_execution_order():
    """Demo execution order calculation with ConnectionsMap."""
    print("\n" + "="*60)
    print("EXECUTION ORDER CALCULATION DEMO")
    print("="*60)
    
    engine = WorkflowExecutionEngine()
    
    # Test complex workflow execution order
    workflow = create_connections_map_workflow()
    execution_order = engine._calculate_execution_order(workflow)
    
    print(f"Execution order: {execution_order}")
    
    # Verify the order makes sense
    node_names = {node["id"]: node["name"] for node in workflow["nodes"]}
    print("\nExecution sequence:")
    for i, node_id in enumerate(execution_order):
        print(f"  {i+1}. {node_names[node_id]} ({node_id})")


def demo_data_flow():
    """Demo data flow with different connection types."""
    print("\n" + "="*60)
    print("DATA FLOW DEMO")
    print("="*60)
    
    engine = WorkflowExecutionEngine()
    
    # Create a simple workflow
    workflow = create_simple_workflow()
    
    # Mock execution state
    execution_state = {
        "workflow_id": "test",
        "execution_id": "test",
        "node_results": {
            "trigger-1": {
                "status": "success",
                "output_data": {
                    "user_request": "Schedule a meeting tomorrow at 2 PM",
                    "timestamp": "2024-01-15T10:00:00Z"
                }
            }
        }
    }
    
    # Test data preparation for the second node
    input_data = engine._prepare_node_input_data(
        "action-1", 
        workflow, 
        execution_state, 
        {}
    )
    
    print("Input data prepared for 'Data Processing' node:")
    print(f"  {input_data}")
    
    # Test with multiple connection types
    print("\n" + "-"*40)
    print("Testing with multiple connection types...")
    
    complex_workflow = create_connections_map_workflow()
    
    # Mock execution state with multiple results
    complex_execution_state = {
        "workflow_id": "test",
        "execution_id": "test",
        "node_results": {
            "trigger-1": {
                "status": "success",
                "output_data": {
                    "user_request": "Schedule a meeting tomorrow at 2 PM",
                    "timestamp": "2024-01-15T10:00:00Z"
                }
            },
            "tool-1": {
                "status": "success",
                "output_data": {
                    "available_slots": ["2024-01-16T14:00:00Z", "2024-01-16T15:00:00Z"],
                    "calendar_id": "primary"
                }
            },
            "memory-1": {
                "status": "success",
                "output_data": {
                    "user_preferences": {
                        "meeting_duration": 60,
                        "preferred_time": "afternoon"
                    }
                }
            }
        }
    }
    
    # Test data preparation for AI Agent (should receive data from multiple connection types)
    ai_agent_input = engine._prepare_node_input_data(
        "action-1",  # The notification node
        complex_workflow,
        complex_execution_state,
        {}
    )
    
    print("Input data prepared for 'Send Notification' node:")
    print(f"  {ai_agent_input}")


def demo_circular_dependency_detection():
    """Demo circular dependency detection."""
    print("\n" + "="*60)
    print("CIRCULAR DEPENDENCY DETECTION DEMO")
    print("="*60)
    
    engine = WorkflowExecutionEngine()
    
    # Create a workflow with circular dependency
    circular_workflow = {
        "id": "circular-demo",
        "name": "Circular Dependency Demo",
        "nodes": [
            {
                "id": "node-a",
                "name": "Node A",
                "type": "ACTION_NODE",
                "subtype": "DATA_TRANSFORMATION",
                "parameters": {},
                "credentials": {}
            },
            {
                "id": "node-b",
                "name": "Node B",
                "type": "ACTION_NODE",
                "subtype": "DATA_TRANSFORMATION",
                "parameters": {},
                "credentials": {}
            },
            {
                "id": "node-c",
                "name": "Node C",
                "type": "ACTION_NODE",
                "subtype": "DATA_TRANSFORMATION",
                "parameters": {},
                "credentials": {}
            }
        ],
        "connections": {
            "connections": {
                "Node A": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "Node B",
                                    "type": "MAIN",
                                    "index": 0
                                }
                            ]
                        }
                    }
                },
                "Node B": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "Node C",
                                    "type": "MAIN",
                                    "index": 0
                                }
                            ]
                        }
                    }
                },
                "Node C": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "Node A",  # Creates circular dependency
                                    "type": "MAIN",
                                    "index": 0
                                }
                            ]
                        }
                    }
                }
            }
        },
        "static_data": {}
    }
    
    has_circular = engine._has_circular_dependencies(
        circular_workflow["nodes"],
        circular_workflow["connections"]
    )
    
    print(f"Circular dependency detected: {has_circular}")
    
    # Test validation
    errors = engine._validate_workflow(circular_workflow)
    
    if errors:
        print("✅ Validation correctly detected circular dependency:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("❌ Validation should have detected circular dependency!")


def main():
    """Run all demos."""
    print("🔗 ConnectionsMap System Demo")
    print("=" * 60)
    
    try:
        demo_connections_map_validation()
        demo_execution_order()
        demo_data_flow()
        demo_circular_dependency_detection()
        
        print("\n" + "="*60)
        print("✅ All demos completed successfully!")
        print("ConnectionsMap system is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 