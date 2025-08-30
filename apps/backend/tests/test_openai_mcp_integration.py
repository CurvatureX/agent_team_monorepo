#!/usr/bin/env python3
"""
OpenAI MCP Integration Test - Workflow Generation Agent
Test file to connect OpenAI LLM to your deployed MCP server for workflow generation

This script implements the MCP (Model Context Protocol) client that allows
OpenAI's ChatGPT to act as a workflow generation agent using your custom
workflow tools deployed at:
http://agent-prod-alb-352817645.us-east-1.elb.amazonaws.com/api/v1/mcp/

The agent uses the workflow_gen_f1.j2 prompt template to:
1. Understand user workflow requirements
2. Use MCP tools to discover available workflow nodes
3. Generate valid workflow configurations in JSON format

Requirements:
- pip install openai requests jinja2
- Set your OpenAI API key as OPENAI_API_KEY environment variable
"""

import json
import os
from typing import Any, Dict, List, Optional

import requests
from jinja2 import Template
from openai import OpenAI

from shared.models.node_enums import OpenAIModel

# MCP Server Configuration
MCP_SERVER_URL = "http://localhost:8000/api/v1/mcp"
MCP_API_KEY = "dev_default"  # Your API key for the MCP server

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_workflow_generation_prompt() -> str:
    """Load the workflow generation prompt template"""
    try:
        prompt_path = os.path.join(
            os.path.dirname(__file__), "shared", "prompts", "workflow_gen_f1.j2"
        )
        with open(prompt_path, "r") as f:
            template_content = f.read()

        # For now, just return the template content as-is since no variables are needed
        template = Template(template_content)
        return template.render()
    except Exception as e:
        print(f"Warning: Could not load workflow generation prompt: {e}")
        return (
            "You are a Workflow Configuration Generator Agent specialized in converting "
            "natural language descriptions into executable workflow configurations. "
            "You must use MCP tools to discover available components before creating workflows. "
            "Always call get_node_types first, then intelligently use get_node_details for specific nodes."
        )


class MCPClient:
    """MCP Client for connecting to your deployed MCP server"""

    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from the MCP server"""
        try:
            response = self.session.get(f"{self.server_url}/tools")
            response.raise_for_status()

            data = response.json()
            if "result" in data and "tools" in data["result"]:
                return data["result"]["tools"]
            return []
        except Exception as e:
            print(f"Error getting tools: {e}")
            return []

    def invoke_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a specific tool on the MCP server"""
        try:
            payload = {"name": tool_name, "tool_name": tool_name, "arguments": arguments}

            response = self.session.post(f"{self.server_url}/invoke", json=payload)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            print(f"Error invoking tool {tool_name}: {e}")
            return {"error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Check MCP server health"""
        try:
            response = self.session.get(f"{self.server_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Health check failed: {e}")
            return {"healthy": False, "error": str(e)}


def create_openai_function_definitions(mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert MCP tool definitions to OpenAI function calling format"""
    openai_functions = []

    for tool in mcp_tools:
        function_def = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("parameters", {}),
            },
        }
        openai_functions.append(function_def)

    return openai_functions


def handle_function_call(mcp_client: MCPClient, function_name: str, arguments: str) -> str:
    """Handle OpenAI function call by invoking MCP tool"""
    try:
        # Parse arguments from JSON string
        args = json.loads(arguments) if isinstance(arguments, str) else arguments

        # Invoke the tool via MCP
        result = mcp_client.invoke_tool(function_name, args)

        # Extract the result content - handle both direct result and JSON-RPC format
        actual_result = result.get("result", result)

        if "content" in actual_result:
            content = actual_result["content"]
            if content and len(content) > 0:
                # Return the text content or structured content
                if content[0].get("type") == "text":
                    text_result = content[0].get("text", "")
                    # Also include structured content if available
                    structured_content = actual_result.get("structuredContent")
                    if structured_content:
                        return f"{text_result}\n\nDetailed results:\n{json.dumps(structured_content, indent=2)}"
                    return text_result

        # Fallback to full result
        return json.dumps(result, indent=2)

    except Exception as e:
        return f"Error executing function {function_name}: {str(e)}"


def test_openai_mcp_integration():
    """Test the OpenAI + MCP integration for workflow generation"""
    print("🚀 Testing OpenAI MCP Integration - Workflow Generation Agent")
    print("=" * 60)

    # Initialize MCP client
    mcp_client = MCPClient(MCP_SERVER_URL, MCP_API_KEY)

    # Test MCP server health
    print("1. Testing MCP Server Health...")
    health = mcp_client.health_check()
    print(f"   Health Status: {health}")

    if not health.get("healthy", False):
        print("❌ MCP Server is not healthy. Aborting test.")
        return

    # Get available tools
    print("\n2. Getting Available Tools...")
    tools = mcp_client.get_available_tools()
    print(f"   Found {len(tools)} tools:")
    for tool in tools:
        print(f"   - {tool['name']}: {tool['description']}")

    if not tools:
        print("❌ No tools available. Aborting test.")
        return

    # Filter out search_nodes to force agent to use intelligent mapping
    filtered_tools = [tool for tool in tools if tool["name"] != "search_nodes"]
    print(
        f"   Filtered out search_nodes - using {len(filtered_tools)} tools: {[t['name'] for t in filtered_tools]}"
    )

    # Convert to OpenAI function format
    print("\n3. Converting to OpenAI Function Format...")
    openai_functions = create_openai_function_definitions(filtered_tools)
    print(f"   Converted {len(openai_functions)} functions for OpenAI")

    # Test with OpenAI ChatGPT as Workflow Generation Agent
    print("\n4. Testing Workflow Generation Agent with OpenAI...")

    try:
        messages = [
            {
                "role": "system",
                "content": load_workflow_generation_prompt(),
            },
            {
                "role": "user",
                "content": "Create a comprehensive workflow based on these EXACT requirements. Do not simplify - implement every detail:\n\n"
                "该工作流为个人智能日程助理，旨在通过Slack与Google Calendar集成，根据用户输入的任务内容（包含优先级、截止日期和所需时间），智能识别空闲时间并安排任务，动态调整优先级和任务拆解，实现高效且个性化的时间管理。通过自动提醒和交互式确认，帮助用户有序推进每日工作，避免漏掉重要事项。\n\n"
                "## 触发器\n"
                "### 1. 新任务创建\n"
                "**触发条件：** 用户通过Slack发送新任务及其相关信息（优先级、截止日期、预计时长）\n"
                "**工作流程：**\n"
                "1. **任务接收** - 通过Slack消息获取任务详情，包括优先级、截止日期、预计所需时间\n"
                "2. **任务分析与拆解** - 对于复杂或耗时较长任务，智能拆分为可管理的小任务，并通过Slack与用户确认分解方案\n"
                "3. **空闲时间段查找** - 检查Google Calendar，在10:00-18:00工作时段（跳过12:00-13:30饭点和已存在的会议/活动），筛选可用时间段\n"
                "4. **排程建议生成** - 优先将高优先级及临近截止任务插入空档，根据任务属性灵活调整已有日程，对于可选时间段，通过Slack发送多个推荐方案，用户确认后安排到日历\n"
                "5. **日历同步** - 将任务最终安排行程写入Google Calendar，并为每个任务设置开始前提醒\n\n"
                "### 2. 任务执行与进展反馈\n"
                "**触发条件：** 每个已计划任务开始前、结束后\n"
                "**工作流程：**\n"
                "1. **任务开始提醒** - 通过Slack消息在任务开始前提醒用户\n"
                "2. **任务完成询问** - 任务结束后，通过Slack询问用户任务是否完成\n"
                "3. **未完成任务处理** - 如未完成，询问用户是否需要加急将其前置/挤占其他任务，或顺延至后续空档，根据用户选择，自动重新规划剩余工作并更新日历\n\n"
                "### 3. 任务优先级变更或新增反馈\n"
                "**触发条件：** 用户通过Slack对已存在任务做优先级、时间、内容等变更\n"
                "**工作流程：**\n"
                "1. **变更接收** - 检测到Slack内任务调整需求\n"
                "2. **日程再规划** - 自动重新调整任务顺序，按新优先级和截止时间重新分配日程安排，并及时通知用户确认\n\n"
                "IMPLEMENT ALL THREE TRIGGERS AND EVERY WORKFLOW STEP MENTIONED ABOVE.",
            },
        ]

        # Make the OpenAI API call with function calling - using GPT-4.1 for complex reasoning
        response = openai_client.chat.completions.create(
            model=OpenAIModel.GPT_4_1.value,
            messages=messages,
            tools=openai_functions,
            tool_choice="auto",
        )

        # Process the response
        message = response.choices[0].message
        print(f"   OpenAI Response: {message.content}")

        # Handle function calls if any
        if message.tool_calls:
            print("\n5. Processing Function Calls...")

            # Add assistant message with tool calls first
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": message.tool_calls,
                }
            )

            # Process all tool calls and add their responses
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = tool_call.function.arguments

                print(f"   Calling function: {function_name}")
                print(f"   Arguments: {function_args}")

                # Execute the function via MCP
                function_result = handle_function_call(mcp_client, function_name, function_args)
                print(f"   Result:\n{function_result}")

                # Add tool response
                messages.append(
                    {"role": "tool", "tool_call_id": tool_call.id, "content": function_result}
                )

            # Get the final response after all tool calls are processed
            final_response = openai_client.chat.completions.create(
                model=OpenAIModel.GPT_5_NANO.value, messages=messages
            )

            print(f"\n   Final OpenAI Response:")
            print(f"   {final_response.choices[0].message.content}")

            # Add the response to messages and prompt for continuation
            messages.append(
                {"role": "assistant", "content": final_response.choices[0].message.content}
            )

            # Prompt agent to get node details and output JSON
            messages.append(
                {
                    "role": "user",
                    "content": "FIRST: Call get_node_details for ALL the nodes you identified. THEN: Output ONLY the complete JSON workflow configuration using the actual node specifications. No text, no explanations, no markdown - just pure JSON starting with { and ending with }.",
                }
            )

            print(f"\n6. Prompting agent to generate complete workflow...")

            # Continue the conversation to get the full workflow - using GPT-4.1 for complex workflow generation
            continuation_response = openai_client.chat.completions.create(
                model=OpenAIModel.GPT_4_1.value,
                messages=messages,
                tools=openai_functions,
                tool_choice="auto",
            )

            continuation_message = continuation_response.choices[0].message

            # Handle any additional function calls
            if continuation_message.tool_calls:
                print(f"\n   Additional function calls...")

                # Add assistant message with tool calls
                messages.append(
                    {
                        "role": "assistant",
                        "content": continuation_message.content,
                        "tool_calls": continuation_message.tool_calls,
                    }
                )

                # Process all tool calls
                for tool_call in continuation_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = tool_call.function.arguments

                    print(f"   Calling function: {function_name}")
                    print(f"   Arguments: {function_args}")

                    # Execute function via MCP
                    function_result = handle_function_call(mcp_client, function_name, function_args)
                    print(f"   Result:\n{function_result}")

                    # Add tool response
                    messages.append(
                        {"role": "tool", "tool_call_id": tool_call.id, "content": function_result}
                    )

                # Get final workflow generation response - using GPT-4.1 for comprehensive output
                final_workflow_response = openai_client.chat.completions.create(
                    model=OpenAIModel.GPT_4_1.value, messages=messages
                )

                print(f"\n   Final Workflow Configuration:")
                print(f"   {final_workflow_response.choices[0].message.content}")
            else:
                print(f"\n   Direct response:")
                print(f"   {continuation_message.content}")

        print("\n✅ Workflow Generation Agent Test Completed Successfully!")

    except Exception as e:
        print(f"❌ OpenAI Integration Error: {e}")


def interactive_chat():
    """Interactive chat session with OpenAI Workflow Generation Agent using MCP tools"""
    print("\n🤖 Starting Interactive Workflow Generation Chat")
    print("=" * 50)
    print("Type 'quit' to exit")
    print("Ask me to create workflows for you! For example:")
    print("- 'Create a workflow that backs up my database daily'")
    print("- 'I need a workflow to process uploaded images'")
    print("- 'Generate a workflow for customer email notifications'")

    # Initialize
    mcp_client = MCPClient(MCP_SERVER_URL, MCP_API_KEY)
    tools = mcp_client.get_available_tools()
    openai_functions = create_openai_function_definitions(tools)

    messages = [
        {
            "role": "system",
            "content": load_workflow_generation_prompt(),
        }
    ]

    while True:
        user_input = input("\n👤 You: ").strip()

        if user_input.lower() in ["quit", "exit", "bye"]:
            print("👋 Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            # Get OpenAI response
            response = openai_client.chat.completions.create(
                model=OpenAIModel.GPT_4_1.value,
                messages=messages,
                tools=openai_functions,
                tool_choice="auto",
            )

            message = response.choices[0].message

            # Handle function calls
            if message.tool_calls:
                # Add assistant message with tool calls first
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": message.tool_calls,
                    }
                )

                # Process all tool calls and add their responses
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = tool_call.function.arguments

                    print(f"🔧 Using tool: {function_name}")

                    # Execute function via MCP
                    function_result = handle_function_call(mcp_client, function_name, function_args)

                    # Add function result to messages
                    messages.append(
                        {"role": "tool", "tool_call_id": tool_call.id, "content": function_result}
                    )

                # Get final response with all function results
                final_response = openai_client.chat.completions.create(
                    model=OpenAIModel.GPT_5_NANO.value, messages=messages
                )

                assistant_message = final_response.choices[0].message.content
                messages.append({"role": "assistant", "content": assistant_message})
                print(f"🤖 Assistant: {assistant_message}")

            else:
                # No function calls, just add the response
                messages.append({"role": "assistant", "content": message.content})
                print(f"🤖 Assistant: {message.content}")

        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("OpenAI MCP Integration Test - Workflow Generation Agent")
    print("=" * 60)

    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set your OPENAI_API_KEY environment variable")
        print("   Example: export OPENAI_API_KEY=sk-your-api-key-here")
        exit(1)

    # Run the test
    test_openai_mcp_integration()

    # Ask if user wants to try interactive chat (only if running interactively)
    import sys

    if sys.stdin.isatty():
        try_interactive = (
            input("\n🤔 Would you like to try interactive chat? (y/n): ").strip().lower()
        )
        if try_interactive in ["y", "yes"]:
            interactive_chat()
    else:
        print("\n✅ Test completed. Run interactively to try the chat feature.")
