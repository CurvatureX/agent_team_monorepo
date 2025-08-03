#!/usr/bin/env python3
"""
OpenAI MCP Integration Test
Test file to connect OpenAI LLM to your deployed MCP server

This script implements the MCP (Model Context Protocol) client that allows
OpenAI's ChatGPT to use your custom workflow tools deployed at:
http://agent-prod-alb-352817645.us-east-1.elb.amazonaws.com/api/v1/mcp/

Requirements:
- pip install openai requests
- Set your OpenAI API key as OPENAI_API_KEY environment variable
"""

import json
import os
from typing import Any, Dict, List, Optional

import requests
from openai import OpenAI

# MCP Server Configuration
MCP_SERVER_URL = "http://localhost:8000/api/v1/mcp"
MCP_API_KEY = "dev_default"  # Your API key for the MCP server

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
    """Test the OpenAI + MCP integration"""
    print("🚀 Testing OpenAI MCP Integration")
    print("=" * 50)

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

    # Convert to OpenAI function format
    print("\n3. Converting to OpenAI Function Format...")
    openai_functions = create_openai_function_definitions(tools)
    print(f"   Converted {len(openai_functions)} functions for OpenAI")

    # Test with OpenAI ChatGPT
    print("\n4. Testing with OpenAI ChatGPT...")

    try:
        messages = [
            {
                "role": "system",
                "content": "You are an AI assistant with access to workflow node tools. "
                "You can help users understand and work with workflow nodes. "
                "Use the available tools to provide helpful information.",
            },
            {
                "role": "user",
                "content": "Can you show me what types of workflow nodes are available? "
                "I'm particularly interested in action nodes.",
            },
        ]

        # Make the OpenAI API call with function calling
        response = openai_client.chat.completions.create(
            model="gpt-4.1", messages=messages, tools=openai_functions, tool_choice="auto"
        )

        # Process the response
        message = response.choices[0].message
        print(f"   OpenAI Response: {message.content}")

        # Handle function calls if any
        if message.tool_calls:
            print("\n5. Processing Function Calls...")

            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = tool_call.function.arguments

                print(f"   Calling function: {function_name}")
                print(f"   Arguments: {function_args}")

                # Execute the function via MCP
                function_result = handle_function_call(mcp_client, function_name, function_args)
                print(f"   Result:\n{function_result}")

                # Continue the conversation with the function result
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": message.tool_calls,
                    }
                )

                messages.append(
                    {"role": "tool", "tool_call_id": tool_call.id, "content": function_result}
                )

                # Get the final response
                final_response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo", messages=messages
                )

                print(f"\n   Final OpenAI Response:")
                print(f"   {final_response.choices[0].message.content}")

        print("\n✅ OpenAI MCP Integration Test Completed Successfully!")

    except Exception as e:
        print(f"❌ OpenAI Integration Error: {e}")


def interactive_chat():
    """Interactive chat session with OpenAI using MCP tools"""
    print("\n🤖 Starting Interactive Chat with MCP Tools")
    print("=" * 50)
    print("Type 'quit' to exit")

    # Initialize
    mcp_client = MCPClient(MCP_SERVER_URL, MCP_API_KEY)
    tools = mcp_client.get_available_tools()
    openai_functions = create_openai_function_definitions(tools)

    messages = [
        {
            "role": "system",
            "content": "You are an AI assistant with access to workflow node tools. "
            "You can help users understand and work with workflow nodes. "
            "Use the available tools when helpful to provide detailed information.",
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
                model="gpt-3.5-turbo", messages=messages, tools=openai_functions, tool_choice="auto"
            )

            message = response.choices[0].message

            # Handle function calls
            if message.tool_calls:
                # Add assistant message with tool calls
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": message.tool_calls,
                    }
                )

                # Process each tool call
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

                # Get final response with function results
                final_response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo", messages=messages
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
    print("OpenAI MCP Integration Test")
    print("=" * 50)

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
