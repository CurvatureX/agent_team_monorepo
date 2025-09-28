#!/usr/bin/env python3
"""
Comprehensive Logging Demo for Workflow Engine V2

This script demonstrates the comprehensive logging system by executing
a sample workflow and showing how logs are created, stored, and retrieved
through the user-friendly API endpoints.

Run with: python examples/demo_comprehensive_logging.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import TriggerInfo
from shared.models.node_enums import ActionSubtype, AIAgentSubtype, NodeType
from shared.models.workflow_new import Connection, Node, NodePort, Workflow, WorkflowMetadata
from workflow_engine_v2.core.modern_engine import ModernExecutionEngine
from workflow_engine_v2.services.user_friendly_logger import get_user_friendly_logger


def create_sample_workflow() -> Workflow:
    """Create a sample workflow for demonstration"""

    # Create nodes with different types
    nodes = [
        Node(
            id="trigger_001",
            name="Slack Trigger",
            type=NodeType.TRIGGER,
            subtype="SLACK",
            configurations={"action_type": "message", "channel": "#general"},
            input_ports=[],
            output_ports=[NodePort(id="main", name="main", data_type="dict")],
        ),
        Node(
            id="ai_001",
            name="Message Analyzer",
            type=NodeType.AI_AGENT,
            subtype=AIAgentSubtype.OPENAI_CHATGPT,
            configurations={
                "model": "gpt-4",
                "system_prompt": "Analyze the sentiment of incoming messages",
                "temperature": 0.3,
            },
            input_ports=[NodePort(id="main", name="main", data_type="dict")],
            output_ports=[NodePort(id="main", name="main", data_type="dict")],
        ),
        Node(
            id="action_001",
            name="Send Response",
            type=NodeType.ACTION,
            subtype=ActionSubtype.HTTP_REQUEST,
            configurations={
                "method": "POST",
                "url": "https://api.slack.com/api/chat.postMessage",
                "headers": {"Authorization": "Bearer {{slack_token}}"},
            },
            input_ports=[NodePort(id="main", name="main", data_type="dict")],
            output_ports=[NodePort(id="main", name="main", data_type="dict")],
        ),
        Node(
            id="hil_001",
            name="Human Review",
            type=NodeType.HUMAN_IN_THE_LOOP,
            subtype="SLACK_INTERACTION",
            configurations={
                "interaction_type": "approval",
                "timeout_minutes": 30,
                "message_template": "Please review the AI's sentiment analysis",
            },
            input_ports=[NodePort(id="main", name="main", data_type="dict")],
            output_ports=[
                NodePort(id="confirmed", name="confirmed", data_type="dict"),
                NodePort(id="rejected", name="rejected", data_type="dict"),
            ],
        ),
    ]

    # Create connections
    connections = [
        Connection(from_node="trigger_001", from_port="main", to_node="ai_001", to_port="main"),
        Connection(from_node="ai_001", from_port="main", to_node="action_001", to_port="main"),
        Connection(from_node="action_001", from_port="main", to_node="hil_001", to_port="main"),
    ]

    # Create workflow metadata
    metadata = WorkflowMetadata(
        id="demo_workflow_001",
        name="Slack Sentiment Analysis with Human Review",
        description="Demo workflow showing comprehensive logging",
        version=1,
    )

    return Workflow(metadata=metadata, nodes=nodes, connections=connections)


def create_sample_trigger() -> TriggerInfo:
    """Create a sample trigger"""
    return TriggerInfo(type="SLACK", source="slack_webhook", timestamp=int(time.time() * 1000))


async def demonstrate_execution_logging():
    """Demonstrate comprehensive execution logging"""

    print("🎯 Workflow Engine V2 - Comprehensive Logging Demo")
    print("=" * 60)

    # Create sample workflow and trigger
    workflow = create_sample_workflow()
    trigger = create_sample_trigger()

    print(f"📋 Sample Workflow: {workflow.metadata.name}")
    print(f"   - {len(workflow.nodes)} nodes")
    print(f"   - {len(workflow.connections)} connections")
    print()

    # Create execution engine
    engine = ModernExecutionEngine()

    print("🚀 Starting workflow execution with comprehensive logging...")
    print()

    try:
        # Execute workflow
        execution = await engine.execute_workflow(
            workflow=workflow, trigger=trigger, trace_id="demo_trace_001"
        )

        print(f"✅ Workflow execution completed!")
        print(f"   - Execution ID: {execution.execution_id}")
        print(f"   - Status: {execution.status}")
        print(f"   - Duration: {(execution.end_time - execution.start_time) / 1000:.2f} seconds")
        print()

        # Show execution progress
        progress = engine.get_execution_progress(execution.execution_id)
        if progress:
            print("📊 Execution Progress:")
            print(f"   - Total nodes: {progress.get('total_nodes', 0)}")
            print(f"   - Completed: {progress.get('completed_nodes', 0)}")
            print(f"   - Failed: {progress.get('failed_nodes', 0)}")
            print()

        return execution.execution_id

    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        return None


async def demonstrate_log_retrieval(execution_id: str):
    """Demonstrate log retrieval through the API"""

    print("📋 Log Retrieval Demo")
    print("-" * 30)

    # Import the logs service
    from workflow_engine_v2.api.logs_endpoints import LogsService

    logs_service = LogsService()

    # Get all logs
    all_logs = await logs_service.get_logs(execution_id, limit=100)

    print(f"📑 Retrieved {len(all_logs.get('logs', []))} log entries")
    print()

    # Display user-friendly logs
    logs = all_logs.get("logs", [])
    for i, log in enumerate(logs[:10], 1):  # Show first 10 logs
        timestamp = log.get("timestamp", "")[:19].replace("T", " ")  # Format timestamp
        level = log.get("level", "info").upper()
        user_message = log.get("user_friendly_message", log.get("message", ""))

        # Add step info if available
        step_info = ""
        if log.get("step_number") and log.get("total_steps"):
            step_info = f" [{log['step_number']}/{log['total_steps']}]"

        # Format with appropriate symbol
        symbols = {"INFO": "ℹ️", "DEBUG": "🔍", "WARN": "⚠️", "ERROR": "❌", "CRITICAL": "🚨"}
        symbol = symbols.get(level, "📝")

        print(f"{i:2d}. {symbol} {timestamp}{step_info}")
        print(f"     {user_message}")

        # Show additional details for milestones
        if log.get("is_milestone"):
            print("     🎯 MILESTONE")

        print()

    # Show summary
    if len(logs) > 10:
        print(f"... and {len(logs) - 10} more log entries")
        print()

    # Show log categories
    levels = {}
    event_types = {}
    for log in logs:
        level = log.get("level", "info")
        event_type = log.get("event_type", "log")
        levels[level] = levels.get(level, 0) + 1
        event_types[event_type] = event_types.get(event_type, 0) + 1

    print("📈 Log Statistics:")
    print("   Levels:", ", ".join(f"{k}: {v}" for k, v in levels.items()))
    print("   Events:", ", ".join(f"{k}: {v}" for k, v in event_types.items()))
    print()


def demonstrate_api_format():
    """Show the API format that would be returned to the API Gateway"""

    print("🔗 API Gateway Integration")
    print("-" * 30)

    # Example of what the API Gateway would receive
    sample_api_response = {
        "execution_id": "abc123-def456-789",
        "logs": [
            {
                "id": "log_001",
                "execution_id": "abc123-def456-789",
                "timestamp": "2025-01-28T12:34:56.789Z",
                "level": "info",
                "message": "Workflow execution started",
                "user_friendly_message": "🚀 Started workflow: Slack Sentiment Analysis with Human Review - 4 steps to execute",
                "event_type": "workflow_started",
                "node_id": None,
                "node_name": None,
                "display_priority": 9,
                "is_milestone": True,
                "data": {
                    "workflow_name": "Slack Sentiment Analysis with Human Review",
                    "total_nodes": 4,
                    "trigger_info": "slack webhook",
                },
                "step_number": 0,
                "total_steps": 4,
            },
            {
                "id": "log_002",
                "execution_id": "abc123-def456-789",
                "timestamp": "2025-01-28T12:34:57.123Z",
                "level": "info",
                "message": "Node execution started: Message Analyzer",
                "user_friendly_message": "⚡ Step 1/4: Message Analyzer (ChatGPT AI) - Processing: message: 'Hello world!'",
                "event_type": "step_started",
                "node_id": "ai_001",
                "node_name": "Message Analyzer",
                "display_priority": 6,
                "is_milestone": False,
                "data": {
                    "node_subtype": "OPENAI_CHATGPT",
                    "input_summary": "message: 'Hello world!'",
                },
                "step_number": 1,
                "total_steps": 4,
            },
            {
                "id": "log_003",
                "execution_id": "abc123-def456-789",
                "timestamp": "2025-01-28T12:34:58.456Z",
                "level": "info",
                "message": "Node execution completed: Message Analyzer",
                "user_friendly_message": "✅ Step 1/4: Message Analyzer completed (1333ms) - Result: sentiment: 'positive', confidence: 0.8",
                "event_type": "step_completed",
                "node_id": "ai_001",
                "node_name": "Message Analyzer",
                "display_priority": 7,
                "is_milestone": False,
                "data": {
                    "success": True,
                    "duration_ms": 1333.2,
                    "output_summary": "sentiment: 'positive', confidence: 0.8",
                    "node_subtype": "OPENAI_CHATGPT",
                },
                "step_number": 1,
                "total_steps": 4,
            },
        ],
        "total_count": 15,
        "pagination": {"limit": 100, "offset": 0, "has_more": False},
    }

    print("📡 Sample API Response (formatted for /api/v1/app/executions/{execution_id}/logs):")
    print()
    print(json.dumps(sample_api_response, indent=2))
    print()

    print("✨ Key Features:")
    print("   - User-friendly messages with emojis and clear progress")
    print("   - Step tracking (1/4, 2/4, etc.)")
    print("   - Input/output parameter summaries")
    print("   - Performance metrics (duration)")
    print("   - Milestone tracking for important events")
    print("   - Structured data for detailed analysis")
    print()


async def main():
    """Main demo function"""

    print()
    print("🎯 WORKFLOW ENGINE V2 - COMPREHENSIVE LOGGING DEMO")
    print("=" * 60)
    print()

    # 1. Demonstrate workflow execution with logging
    execution_id = await demonstrate_execution_logging()

    if execution_id:
        # 2. Demonstrate log retrieval
        await demonstrate_log_retrieval(execution_id)

    # 3. Show API format
    demonstrate_api_format()

    print("🎉 Demo completed!")
    print()
    print("💡 Next Steps:")
    print("   1. Start the workflow_engine_v2 FastAPI server: python main.py")
    print("   2. Call /api/v2/workflows/executions/{execution_id}/logs")
    print("   3. API Gateway will forward these to /api/v1/app/executions/{execution_id}/logs")
    print()


if __name__ == "__main__":
    asyncio.run(main())
