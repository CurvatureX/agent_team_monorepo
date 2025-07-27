#!/usr/bin/env python3
"""
Test script for enhanced workflow execution engine with detailed data collection.
"""

import json
import time
from workflow_engine.execution_engine import EnhancedWorkflowExecutionEngine


def create_test_workflow():
    """Create a test workflow for execution testing."""
    
    return {
        "id": "test-workflow-001",
        "name": "Test Enhanced Workflow",
        "description": "A test workflow for enhanced execution engine",
        "nodes": [
            {
                "id": "trigger-1",
                "name": "Manual Trigger",
                "type": "TRIGGER_NODE",
                "subtype": "TRIGGER_MANUAL",
                "parameters": {
                    "message": "Hello from enhanced execution engine"
                }
            },
            {
                "id": "action-1",
                "name": "Data Processing",
                "type": "ACTION_NODE",
                "subtype": "ACTION_DATA_TRANSFORMATION",
                "parameters": {
                    "operation": "uppercase",
                    "field": "message"
                }
            },
            {
                "id": "memory-1",
                "name": "Store Result",
                "type": "MEMORY_NODE",
                "subtype": "MEMORY_SIMPLE",
                "parameters": {
                    "key": "processed_message"
                }
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
                },
                "Data Processing": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "Store Result",
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
            "environment": "test",
            "version": "1.0.0"
        }
    }


def test_enhanced_execution_engine():
    """Test the enhanced execution engine with detailed data collection."""
    
    print("🚀 Testing Enhanced Workflow Execution Engine")
    print("=" * 60)
    
    # Create execution engine
    engine = EnhancedWorkflowExecutionEngine()
    
    # Create test workflow
    workflow = create_test_workflow()
    
    # Test data
    initial_data = {
        "user_input": "Test message for enhanced execution",
        "timestamp": int(time.time())
    }
    
    credentials = {
        "api_key": "test_key_123",
        "user_id": "test_user"
    }
    
    print(f"📋 Workflow: {workflow['name']}")
    print(f"🔢 Nodes: {len(workflow['nodes'])}")
    print(f"🔗 Connections: {len(workflow['connections']['connections'])}")
    print()
    
    # Execute workflow
    print("▶️  Executing workflow...")
    execution_result = engine.execute_workflow(
        workflow_id=workflow["id"],
        execution_id="test-execution-001",
        workflow_definition=workflow,
        initial_data=initial_data,
        credentials=credentials
    )
    
    print(f"✅ Execution completed with status: {execution_result['status']}")
    print()
    
    # Get execution report
    print("📊 Generating execution report...")
    execution_report = engine.get_execution_report("test-execution-001")
    
    if execution_report:
        print_execution_report(execution_report)
    else:
        print("❌ Failed to generate execution report")
    
    # Test individual components
    print("\n🔍 Testing individual components...")
    test_execution_path(execution_result)
    test_node_inputs(execution_result)
    test_performance_metrics(execution_result)
    test_data_flow(execution_result)
    
    print("\n✅ Enhanced execution engine test completed!")


def print_execution_report(report):
    """Print the execution report in a readable format."""
    
    print("📈 EXECUTION REPORT")
    print("-" * 40)
    
    # Execution summary
    summary = report["execution_summary"]
    print(f"Execution ID: {summary['execution_id']}")
    print(f"Workflow ID: {summary['workflow_id']}")
    print(f"Status: {summary['status']}")
    print(f"Total Time: {summary['total_execution_time']:.2f}s")
    print(f"Nodes Executed: {summary['nodes_executed']}")
    print(f"Nodes Failed: {summary['nodes_failed']}")
    print(f"Start Time: {summary['start_time']}")
    print(f"End Time: {summary['end_time']}")
    print()
    
    # Execution path
    path = report["execution_path"]
    print("🛤️  EXECUTION PATH")
    print("-" * 20)
    for i, step in enumerate(path["steps"], 1):
        print(f"{i}. {step['node_name']} ({step['node_type']})")
        print(f"   Status: {step['status']}")
        print(f"   Time: {step['execution_time']:.3f}s")
        if step.get("error"):
            print(f"   Error: {step['error']}")
        print()
    
    # Node execution counts
    print("📊 NODE EXECUTION COUNTS")
    print("-" * 25)
    for node_name, count in path["node_execution_counts"].items():
        print(f"{node_name}: {count} time(s)")
    print()
    
    # Performance metrics
    metrics = report["performance_metrics"]
    print("⚡ PERFORMANCE METRICS")
    print("-" * 20)
    print(f"Total Execution Time: {metrics['total_execution_time']:.3f}s")
    print("Node Execution Times:")
    for node_id, node_metrics in metrics["node_execution_times"].items():
        duration = node_metrics.get("duration", 0)
        print(f"  {node_id}: {duration:.3f}s")
    print()
    
    # Data flow
    data_flow = report["data_flow"]
    print("🌊 DATA FLOW")
    print("-" * 10)
    print(f"Data Transfers: {len(data_flow['data_transfers'])}")
    for transfer in data_flow["data_transfers"]:
        print(f"  {transfer['node_name']}: {transfer['input_data_size']} → {transfer['output_data_size']} bytes")
    print()
    
    # Errors
    errors = report.get("errors", [])
    if errors:
        print("❌ ERRORS")
        print("-" * 8)
        for error in errors:
            print(f"Type: {error['error_type']}")
            print(f"Errors: {error['errors']}")
            print(f"Time: {error['timestamp']}")
            print()


def test_execution_path(execution_result):
    """Test execution path data collection."""
    
    print("🛤️  Testing Execution Path...")
    
    execution_path = execution_result.get("execution_path", {})
    
    # Check if execution path exists
    if not execution_path:
        print("❌ No execution path data found")
        return
    
    steps = execution_path.get("steps", [])
    print(f"✅ Found {len(steps)} execution steps")
    
    # Check step details
    for step in steps:
        required_fields = ["node_id", "node_name", "status", "execution_time"]
        missing_fields = [field for field in required_fields if field not in step]
        
        if missing_fields:
            print(f"❌ Step missing fields: {missing_fields}")
        else:
            print(f"✅ Step {step['node_name']}: {step['status']} ({step['execution_time']:.3f}s)")
    
    # Check execution counts
    counts = execution_path.get("node_execution_counts", {})
    print(f"✅ Node execution counts: {counts}")
    print()


def test_node_inputs(execution_result):
    """Test node input data collection."""
    
    print("📥 Testing Node Inputs...")
    
    node_inputs = execution_result.get("node_inputs", {})
    
    if not node_inputs:
        print("❌ No node input data found")
        return
    
    print(f"✅ Found input data for {len(node_inputs)} nodes")
    
    for node_id, input_data in node_inputs.items():
        print(f"  Node {node_id}:")
        print(f"    Name: {input_data.get('node_name', 'Unknown')}")
        print(f"    Input Data Keys: {list(input_data.get('input_data', {}).keys())}")
        print(f"    Parameters: {list(input_data.get('parameters', {}).keys())}")
        print(f"    Timestamp: {input_data.get('timestamp', 'Unknown')}")
    print()


def test_performance_metrics(execution_result):
    """Test performance metrics collection."""
    
    print("⚡ Testing Performance Metrics...")
    
    metrics = execution_result.get("performance_metrics", {})
    
    if not metrics:
        print("❌ No performance metrics found")
        return
    
    total_time = metrics.get("total_execution_time", 0)
    node_times = metrics.get("node_execution_times", {})
    
    print(f"✅ Total execution time: {total_time:.3f}s")
    print(f"✅ Node execution times: {len(node_times)} nodes")
    
    for node_id, node_metrics in node_times.items():
        duration = node_metrics.get("duration", 0)
        print(f"  {node_id}: {duration:.3f}s")
    print()


def test_data_flow(execution_result):
    """Test data flow collection."""
    
    print("🌊 Testing Data Flow...")
    
    data_flow = execution_result.get("data_flow", {})
    
    if not data_flow:
        print("❌ No data flow information found")
        return
    
    transfers = data_flow.get("data_transfers", [])
    sources = data_flow.get("data_sources", {})
    
    print(f"✅ Data transfers: {len(transfers)}")
    print(f"✅ Data sources: {len(sources)} nodes")
    
    for transfer in transfers:
        print(f"  {transfer['node_name']}: {transfer['input_data_size']} → {transfer['output_data_size']} bytes")
    print()


def test_error_handling():
    """Test error handling and recording."""
    
    print("❌ Testing Error Handling...")
    
    engine = EnhancedWorkflowExecutionEngine()
    
    # Create a workflow with an invalid node
    invalid_workflow = {
        "id": "invalid-workflow",
        "name": "Invalid Workflow",
        "nodes": [
            {
                "id": "invalid-node",
                "name": "Invalid Node",
                "type": "INVALID_TYPE",
                "subtype": "INVALID_SUBTYPE"
            }
        ],
        "connections": {"connections": {}}
    }
    
    # Execute invalid workflow
    result = engine.execute_workflow(
        workflow_id="invalid-workflow",
        execution_id="test-error-001",
        workflow_definition=invalid_workflow
    )
    
    print(f"✅ Error execution status: {result['status']}")
    
    # Check error records
    error_records = result.get("error_records", [])
    print(f"✅ Error records: {len(error_records)}")
    
    for error in error_records:
        print(f"  Type: {error['error_type']}")
        print(f"  Errors: {error['errors']}")
    print()


if __name__ == "__main__":
    try:
        test_enhanced_execution_engine()
        test_error_handling()
        print("🎉 All tests completed successfully!")
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc() 