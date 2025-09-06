#!/usr/bin/env python3
"""
Workflow Engine Protobuf Usage Example

This example demonstrates how to use the generated protobuf classes
to create and manipulate workflow definitions.
"""

import sys
import time
from pathlib import Path

# Add the parent directory to the path so we can import the proto modules
sys.path.append(str(Path(__file__).parent.parent))

try:
    from proto import ai_system_pb2, execution_pb2, integration_pb2, workflow_pb2
except ImportError as e:
    print(f"Error importing protobuf modules: {e}")
    print("Please run 'make proto' to generate the protobuf Python code first.")
    sys.exit(1)


def create_sample_workflow():
    """Create a sample workflow using protobuf messages."""
    print("Creating sample workflow...")

    # Create workflow
    workflow = workflow_pb2.Workflow()
    workflow.id = "workflow-secretary-001"
    workflow.name = "Personal Secretary Workflow"
    workflow.description = "AI-powered personal secretary for task management"
    workflow.active = True
    workflow.version = "1.0.0"
    workflow.tags.extend(["ai", "secretary", "automation"])

    # Set timestamps
    current_time = int(time.time())
    workflow.created_at = current_time
    workflow.updated_at = current_time

    # Create workflow settings
    settings = workflow_pb2.WorkflowSettings()
    settings.timezone = "Asia/Shanghai"
    settings.save_execution_progress = True
    settings.save_manual_executions = True
    settings.timeout = 300  # 5 minutes
    settings.error_policy = workflow_pb2.ErrorPolicy.CONTINUE_REGULAR_OUTPUT
    settings.caller_policy = workflow_pb2.CallerPolicy.WORKFLOW_MAIN
    workflow.settings.CopyFrom(settings)

    # Create nodes
    nodes = []

    # 1. Slack Trigger Node
    slack_trigger = workflow_pb2.Node()
    slack_trigger.id = "node-slack-trigger"
    slack_trigger.name = "Slack Trigger"
    slack_trigger.type = workflow_pb2.NodeType.TRIGGER_NODE
    slack_trigger.subtype = workflow_pb2.NodeSubtype.TRIGGER_CHAT
    slack_trigger.type_version = 1
    slack_trigger.disabled = False

    # Set position
    slack_trigger.position.x = 100.0
    slack_trigger.position.y = 100.0

    # Set parameters
    slack_trigger.parameters["channel"] = "#personal-assistant"
    slack_trigger.parameters["trigger_phrase"] = ""
    slack_trigger.parameters["auto_reply"] = "true"

    # Set credentials
    slack_trigger.credentials["slack_token"] = "SLACK_BOT_TOKEN"

    # Set error handling
    slack_trigger.on_error = workflow_pb2.ErrorHandling.STOP_WORKFLOW_ON_ERROR

    # Set retry policy
    retry_policy = workflow_pb2.RetryPolicy()
    retry_policy.max_tries = 1
    retry_policy.wait_between_tries = 0
    slack_trigger.retry_policy.CopyFrom(retry_policy)

    nodes.append(slack_trigger)

    # 2. AI Router Agent Node
    ai_router = workflow_pb2.Node()
    ai_router.id = "node-ai-router"
    ai_router.name = "AI Router Agent"
    ai_router.type = workflow_pb2.NodeType.AI_AGENT_NODE
    ai_router.subtype = workflow_pb2.NodeSubtype.AI_ROUTER_AGENT
    ai_router.type_version = 1
    ai_router.disabled = False

    ai_router.position.x = 300.0
    ai_router.position.y = 100.0

    ai_router.parameters["agent_type"] = "router"
    ai_router.parameters["prompt"] = "分析用户意图并路由到相应模块：日程管理、查询请求、总结生成"
    ai_router.parameters["model_provider"] = "openai"
    ai_router.parameters["model_name"] = "gpt-5-nano"

    ai_router.on_error = workflow_pb2.ErrorHandling.CONTINUE_REGULAR_OUTPUT_ON_ERROR

    retry_policy2 = workflow_pb2.RetryPolicy()
    retry_policy2.max_tries = 2
    retry_policy2.wait_between_tries = 5
    ai_router.retry_policy.CopyFrom(retry_policy2)

    nodes.append(ai_router)

    # 3. Google Calendar Tool Node
    calendar_tool = workflow_pb2.Node()
    calendar_tool.id = "node-calendar-tool"
    calendar_tool.name = "Google Calendar Tool"
    calendar_tool.type = workflow_pb2.NodeType.TOOL_NODE
    calendar_tool.subtype = workflow_pb2.NodeSubtype.TOOL_GOOGLE_CALENDAR_MCP
    calendar_tool.type_version = 1
    calendar_tool.disabled = False

    calendar_tool.position.x = 500.0
    calendar_tool.position.y = 100.0

    calendar_tool.parameters["mcp_server_url"] = "http://localhost:8080"
    calendar_tool.parameters["default_calendar_id"] = "primary"
    calendar_tool.parameters["timezone"] = "Asia/Shanghai"

    calendar_tool.credentials["google_oauth_token"] = "GOOGLE_OAUTH_TOKEN"

    nodes.append(calendar_tool)

    # Add nodes to workflow
    workflow.nodes.extend(nodes)

    # Create connections
    connections = workflow_pb2.ConnectionsMap()

    # Slack Trigger -> AI Router
    slack_connections = workflow_pb2.NodeConnections()
    main_connection_array = workflow_pb2.ConnectionArray()
    main_connection = workflow_pb2.Connection()
    main_connection.node = "AI Router Agent"
    main_connection.type = workflow_pb2.ConnectionType.MAIN
    main_connection.index = 0
    main_connection_array.connections.append(main_connection)
    slack_connections.connection_types["main"] = main_connection_array
    connections.connections["Slack Trigger"] = slack_connections

    # AI Router -> Calendar Tool
    router_connections = workflow_pb2.NodeConnections()
    router_main_array = workflow_pb2.ConnectionArray()
    router_main = workflow_pb2.Connection()
    router_main.node = "Google Calendar Tool"
    router_main.type = workflow_pb2.ConnectionType.MAIN
    router_main.index = 0
    router_main_array.connections.append(router_main)
    router_connections.connection_types["main"] = router_main_array
    connections.connections["AI Router Agent"] = router_connections

    workflow.connections.CopyFrom(connections)

    # Add static data
    workflow.static_data["user_preferences"] = '{"timezone": "Asia/Shanghai", "language": "zh-CN"}'
    workflow.static_data["default_calendar"] = "primary"

    return workflow


def create_ai_agent_config():
    """Create an AI agent configuration."""
    print("Creating AI agent configuration...")

    config = ai_system_pb2.AIAgentConfig()
    config.agent_type = "secretary"
    config.prompt = "You are a helpful personal secretary AI assistant."

    # Language model configuration
    llm = ai_system_pb2.AILanguageModel()
    llm.model_type = "openai"
    llm.model_name = "gpt-4"
    llm.temperature = 0.1
    llm.max_tokens = 2000
    llm.top_p = 0.9
    config.language_model.CopyFrom(llm)

    # AI tools
    calendar_tool = ai_system_pb2.AITool()
    calendar_tool.tool_type = "mcp"
    calendar_tool.tool_name = "google_calendar"
    calendar_tool.description = "Google Calendar integration for scheduling"
    calendar_tool.endpoint_url = "http://localhost:8080/calendar"
    config.tools.append(calendar_tool)

    # AI memory
    memory = ai_system_pb2.AIMemory()
    memory.memory_type = "buffer"
    memory.max_tokens = 4000
    memory.max_messages = 10
    config.memory.CopyFrom(memory)

    return config


def create_execution_data():
    """Create execution data example."""
    print("Creating execution data...")

    execution = execution_pb2.ExecutionData()
    execution.execution_id = "exec-001"
    execution.workflow_id = "workflow-secretary-001"
    execution.status = execution_pb2.ExecutionStatus.RUNNING
    execution.mode = execution_pb2.ExecutionMode.TRIGGER
    execution.triggered_by = "slack_user_123"
    execution.start_time = int(time.time())

    # Run data
    run_data = execution_pb2.RunData()

    # Node run data
    node_run_data = execution_pb2.NodeRunData()

    # Task data
    task_data = execution_pb2.TaskData()
    task_data.start_time = int(time.time())
    task_data.execution_time = 1500  # 1.5 seconds
    task_data.source = "slack_trigger"

    # Node execution data
    node_exec_data = execution_pb2.NodeExecutionData()

    # Data item
    data_item = execution_pb2.DataItem()
    data_item.json_data["message"] = "Schedule a meeting with John tomorrow at 2 PM"
    data_item.json_data["user_id"] = "user_123"
    data_item.json_data["channel"] = "#personal-assistant"
    data_item.paused = False

    node_exec_data.data.append(data_item)
    task_data.data.append(node_exec_data)
    node_run_data.tasks.append(task_data)

    run_data.node_data["node-slack-trigger"] = node_run_data
    execution.run_data.CopyFrom(run_data)

    return execution


def create_integration():
    """Create integration example."""
    print("Creating integration...")

    integration = integration_pb2.Integration()
    integration.integration_id = "google-calendar-001"
    integration.integration_type = "google_calendar"
    integration.name = "Google Calendar Integration"
    integration.version = "1.0.0"
    integration.active = True
    integration.created_at = int(time.time())
    integration.updated_at = int(time.time())

    # Configuration
    integration.configuration["api_version"] = "v3"
    integration.configuration["scopes"] = "https://www.googleapis.com/auth/calendar"

    # Credentials
    credentials = integration_pb2.CredentialConfig()
    credentials.credential_type = "oauth2"
    credentials.credential_id = "google-oauth-001"
    credentials.is_valid = True
    credentials.expires_at = int(time.time()) + 3600  # 1 hour from now
    credentials.credential_data["access_token"] = "ya29.xxx"
    credentials.credential_data["refresh_token"] = "1//xxx"

    integration.credentials.CopyFrom(credentials)

    # Supported operations
    integration.supported_operations.extend(
        ["create_event", "list_events", "update_event", "delete_event", "get_freebusy"]
    )

    return integration


def main():
    """Main function to demonstrate protobuf usage."""
    print("Workflow Engine Protobuf Example")
    print("=" * 40)

    # Create sample workflow
    workflow = create_sample_workflow()
    print(f"Created workflow: {workflow.name}")
    print(f"  ID: {workflow.id}")
    print(f"  Nodes: {len(workflow.nodes)}")
    print(f"  Active: {workflow.active}")

    # Create AI agent config
    ai_config = create_ai_agent_config()
    print(f"Created AI config: {ai_config.agent_type}")
    print(f"  Model: {ai_config.language_model.model_name}")
    print(f"  Tools: {len(ai_config.tools)}")

    # Create execution data
    execution = create_execution_data()
    print(f"Created execution: {execution.execution_id}")
    print(f"  Status: {execution_pb2.ExecutionStatus.Name(execution.status)}")
    print(f"  Mode: {execution_pb2.ExecutionMode.Name(execution.mode)}")

    # Create integration
    integration = create_integration()
    print(f"Created integration: {integration.name}")
    print(f"  Type: {integration.integration_type}")
    print(f"  Operations: {len(integration.supported_operations)}")

    print("\n" + "=" * 40)
    print("Example completed successfully!")
    print("You can now use these protobuf messages in your workflow engine.")


if __name__ == "__main__":
    main()
