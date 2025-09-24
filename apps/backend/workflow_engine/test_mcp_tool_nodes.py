"""
Integration tests for MCP Tool Nodes with Notion and Google Calendar
Tests the workflow engine's ability to execute MCP tools via tool nodes
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

# Add the backend directory to the path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from workflow_engine.nodes.base import ExecutionStatus, NodeExecutionContext
from workflow_engine.nodes.tool_node import ToolNodeExecutor


async def test_notion_mcp_integration():
    """Test Notion MCP tool integration via workflow engine."""
    print("🧪 Testing Notion MCP Integration...")

    # Create tool node executor
    executor = ToolNodeExecutor()

    # Test context for Notion search
    context = NodeExecutionContext(
        execution_id="test-exec-1",
        workflow_id="test-workflow",
        node_id="notion_search_node",
        input_data={
            "function_name": "notion_search",
            "function_args": {
                "access_token": os.getenv("NOTION_API_KEY", "test_token"),
                "query": "meeting notes",
                "ai_format": "structured",
                "limit": 5,
                "relevance_scoring": True,
            },
        },
        parameters={"tool_subtype": "notion_mcp", "operation": "execute"},
    )

    try:
        # Execute the tool node
        start_time = time.time()
        result = await executor.execute(context)
        execution_time = time.time() - start_time

        print(f"⏱️ Execution time: {execution_time:.2f}s")
        print(f"📋 Result status: {result.status}")

        if result.status == ExecutionStatus.SUCCESS:
            print("✅ Notion MCP tool executed successfully!")
            if result.output_data:
                print(f"📄 Output keys: {list(result.output_data.keys())}")

                # Check for expected MCP response structure
                if "structured_content" in result.output_data:
                    structured_content = result.output_data["structured_content"]
                    if isinstance(structured_content, dict):
                        print(f"🔍 Search query: {structured_content.get('query', 'N/A')}")
                        print(f"📊 Results count: {len(structured_content.get('results', []))}")

                        # Check for AI optimization features
                        if "results" in structured_content:
                            for i, result_item in enumerate(
                                structured_content["results"][:2]
                            ):  # Show first 2
                                print(f"  {i+1}. {result_item.get('title', 'No title')}")
                                if "relevance_score" in result_item:
                                    print(f"     Relevance: {result_item['relevance_score']}")
        else:
            print(f"❌ Notion MCP tool failed: {result.error_message}")
            if result.error_details:
                print(f"🔍 Error details: {json.dumps(result.error_details, indent=2)}")

        return result.status == ExecutionStatus.SUCCESS

    except Exception as e:
        print(f"❌ Exception during Notion MCP test: {e}")
        return False


async def test_google_calendar_mcp_integration():
    """Test Google Calendar MCP tool integration via workflow engine."""
    print("\n📅 Testing Google Calendar MCP Integration...")

    # Create tool node executor
    executor = ToolNodeExecutor()

    # Test context for Google Calendar events listing
    context = NodeExecutionContext(
        execution_id="test-exec-2",
        workflow_id="test-workflow",
        node_id="calendar_events_node",
        input_data={
            "function_name": "google_calendar_events",
            "function_args": {
                "access_token": os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN", "test_token"),
                "action": "list",
                "filters": {"time_min": "today", "max_results": 5},
            },
        },
        parameters={"tool_subtype": "google_calendar", "operation": "execute"},
    )

    try:
        # Execute the tool node
        start_time = time.time()
        result = await executor.execute(context)
        execution_time = time.time() - start_time

        print(f"⏱️ Execution time: {execution_time:.2f}s")
        print(f"📋 Result status: {result.status}")

        if result.status == ExecutionStatus.SUCCESS:
            print("✅ Google Calendar MCP tool executed successfully!")
            if result.output_data:
                print(f"📄 Output keys: {list(result.output_data.keys())}")

                # Check for expected MCP response structure
                if "structured_content" in result.output_data:
                    structured_content = result.output_data["structured_content"]
                    if isinstance(structured_content, dict):
                        print(f"🎯 Action: {structured_content.get('action', 'N/A')}")
                        print(f"📊 Events count: {len(structured_content.get('events', []))}")

                        # Show first few events
                        events = structured_content.get("events", [])
                        for i, event in enumerate(events[:2]):  # Show first 2
                            print(f"  {i+1}. {event.get('title', 'No title')}")
                            if event.get("start_time"):
                                print(f"     Time: {event['start_time']}")
        else:
            print(f"❌ Google Calendar MCP tool failed: {result.error_message}")
            if result.error_details:
                print(f"🔍 Error details: {json.dumps(result.error_details, indent=2)}")

        return result.status == ExecutionStatus.SUCCESS

    except Exception as e:
        print(f"❌ Exception during Google Calendar MCP test: {e}")
        return False


async def test_google_calendar_quick_add():
    """Test Google Calendar quick add with natural language."""
    print("\n🚀 Testing Google Calendar Quick Add...")

    executor = ToolNodeExecutor()

    context = NodeExecutionContext(
        execution_id="test-exec-3",
        workflow_id="test-workflow",
        node_id="calendar_quick_add_node",
        input_data={
            "function_name": "google_calendar_quick_add",
            "function_args": {
                "access_token": os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN", "test_token"),
                "text": "Team standup meeting tomorrow at 9am for 30 minutes",
            },
        },
        parameters={"tool_subtype": "google_calendar", "operation": "execute"},
    )

    try:
        start_time = time.time()
        result = await executor.execute(context)
        execution_time = time.time() - start_time

        print(f"⏱️ Execution time: {execution_time:.2f}s")
        print(f"📋 Result status: {result.status}")

        if result.status == ExecutionStatus.SUCCESS:
            print("✅ Google Calendar Quick Add executed successfully!")
            if result.output_data and "structured_content" in result.output_data:
                structured_content = result.output_data["structured_content"]
                print(f"📝 Parsed text: {structured_content.get('parsed_text', 'N/A')}")
                print(f"🆔 Event ID: {structured_content.get('event_id', 'N/A')}")
        else:
            print(f"❌ Quick Add failed: {result.error_message}")

        return result.status == ExecutionStatus.SUCCESS

    except Exception as e:
        print(f"❌ Exception during Quick Add test: {e}")
        return False


async def test_notion_ai_format_integration():
    """Test Notion search with different AI formats."""
    print("\n🤖 Testing Notion AI Format Integration...")

    executor = ToolNodeExecutor()

    # Test different AI formats
    formats = ["structured", "narrative", "summary"]
    results = {}

    for ai_format in formats:
        print(f"\n  Testing {ai_format} format...")

        context = NodeExecutionContext(
            execution_id=f"test-exec-notion-{ai_format}",
            workflow_id="test-workflow",
            node_id=f"notion_{ai_format}_node",
            input_data={
                "function_name": "notion_search",
                "function_args": {
                    "access_token": os.getenv("NOTION_API_KEY", "test_token"),
                    "query": "project documentation",
                    "ai_format": ai_format,
                    "relevance_scoring": True,
                    "limit": 3,
                },
            },
            parameters={"tool_subtype": "notion_mcp", "operation": "execute"},
        )

        try:
            result = await executor.execute(context)
            results[ai_format] = result.status == ExecutionStatus.SUCCESS

            if result.status == ExecutionStatus.SUCCESS:
                print(f"    ✅ {ai_format} format worked!")

                # Check for format-specific features
                if result.output_data and "structured_content" in result.output_data:
                    content = result.output_data["structured_content"]

                    if ai_format == "narrative" and "ai_narrative" in content:
                        print(f"    📖 Narrative preview: {content['ai_narrative'][:100]}...")
                    elif ai_format == "summary" and "ai_summary" in content:
                        summary = content["ai_summary"]
                        print(f"    📊 Summary found: {summary.get('total_found', 0)} items")
                    elif ai_format == "structured" and "results" in content:
                        print(f"    🏗️ Structured results: {len(content['results'])} items")
            else:
                print(f"    ❌ {ai_format} format failed: {result.error_message}")

        except Exception as e:
            print(f"    ❌ Exception in {ai_format} test: {e}")
            results[ai_format] = False

    return all(results.values())


async def test_mcp_error_handling():
    """Test MCP tool error handling in workflow engine."""
    print("\n🛡️ Testing MCP Error Handling...")

    executor = ToolNodeExecutor()

    # Test missing access token
    context = NodeExecutionContext(
        execution_id="test-exec-error",
        workflow_id="test-workflow",
        node_id="error_test_node",
        input_data={
            "function_name": "notion_search",
            "function_args": {
                # Missing access_token
                "query": "test"
            },
        },
        parameters={"tool_subtype": "notion_mcp", "operation": "execute"},
    )

    try:
        result = await executor.execute(context)

        print(f"📋 Result status: {result.status}")

        if result.status == ExecutionStatus.ERROR:
            print("✅ Error handling works correctly!")
            print(f"📝 Error message: {result.error_message}")

            # Check that error is properly structured
            if "access_token parameter is required" in result.error_message:
                print("✅ Specific error message is correct!")
                return True
            else:
                print("❌ Error message doesn't match expected content")
                return False
        else:
            print("❌ Expected error but got success")
            return False

    except Exception as e:
        print(f"❌ Unexpected exception: {e}")
        return False


async def test_workflow_engine_mcp_performance():
    """Test performance of MCP tools in workflow engine."""
    print("\n⚡ Testing MCP Performance in Workflow Engine...")

    executor = ToolNodeExecutor()

    # Test multiple quick executions
    execution_times = []
    success_count = 0

    for i in range(3):  # Test 3 quick executions
        context = NodeExecutionContext(
            execution_id=f"test-exec-perf-{i}",
            workflow_id="test-workflow",
            node_id=f"perf_test_node_{i}",
            input_data={
                "function_name": "notion_search",
                "function_args": {
                    "access_token": os.getenv("NOTION_API_KEY", "test_token"),
                    "query": f"test query {i}",
                    "limit": 2,
                },
            },
            parameters={"tool_subtype": "notion_mcp", "operation": "execute"},
        )

        try:
            start_time = time.time()
            result = await executor.execute(context)
            execution_time = time.time() - start_time
            execution_times.append(execution_time)

            if result.status == ExecutionStatus.SUCCESS:
                success_count += 1

            print(
                f"  Execution {i+1}: {execution_time:.2f}s - {'✅' if result.status == ExecutionStatus.SUCCESS else '❌'}"
            )

        except Exception as e:
            print(f"  Execution {i+1}: ❌ Exception: {e}")

    if execution_times:
        avg_time = sum(execution_times) / len(execution_times)
        print(f"\n📊 Performance Summary:")
        print(f"  Average execution time: {avg_time:.2f}s")
        print(
            f"  Success rate: {success_count}/{len(execution_times)} ({success_count/len(execution_times)*100:.1f}%)"
        )

        # Performance should be reasonable (under 2 seconds for most operations)
        performance_ok = avg_time < 2.0 and success_count >= len(execution_times) * 0.5
        print(f"  Performance assessment: {'✅ Good' if performance_ok else '⚠️ Needs improvement'}")

        return performance_ok
    else:
        print("❌ No execution times recorded")
        return False


async def main():
    """Run all MCP integration tests."""
    print("🔧 Starting MCP Tool Node Integration Tests...")
    print("=" * 60)

    # Keep track of test results
    test_results = {}

    # Run all tests
    test_functions = [
        ("Notion MCP Integration", test_notion_mcp_integration),
        ("Google Calendar MCP Integration", test_google_calendar_mcp_integration),
        ("Google Calendar Quick Add", test_google_calendar_quick_add),
        ("Notion AI Format Integration", test_notion_ai_format_integration),
        ("MCP Error Handling", test_mcp_error_handling),
        ("MCP Performance", test_workflow_engine_mcp_performance),
    ]

    for test_name, test_func in test_functions:
        try:
            print(f"\n{'='*60}")
            print(f"Running: {test_name}")
            print(f"{'='*60}")

            result = await test_func()
            test_results[test_name] = result

            print(f"\n{test_name}: {'✅ PASSED' if result else '❌ FAILED'}")

        except Exception as e:
            print(f"\n❌ {test_name} failed with exception: {e}")
            test_results[test_name] = False

    # Print summary
    print(f"\n{'='*60}")
    print("🎯 TEST SUMMARY")
    print(f"{'='*60}")

    passed = 0
    total = len(test_results)

    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n📊 Overall Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 All MCP integration tests passed!")
        return True
    else:
        print(f"⚠️ {total - passed} test(s) failed. Check the details above.")
        return False


if __name__ == "__main__":
    # Check environment variables
    print("🔍 Checking environment variables...")

    notion_key = os.getenv("NOTION_API_KEY")
    calendar_token = os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN")

    if notion_key and not notion_key.startswith("test_"):
        print("✅ Notion API key found")
    else:
        print("⚠️ Using test Notion API key (some tests may fail)")

    if calendar_token and not calendar_token.startswith("test_"):
        print("✅ Google Calendar access token found")
    else:
        print("⚠️ Using test Google Calendar token (some tests may fail)")

    print("\n🚀 Starting tests...")

    # Run the tests
    success = asyncio.run(main())

    # Exit with appropriate code
    sys.exit(0 if success else 1)
