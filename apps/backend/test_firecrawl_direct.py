"""
Direct test script for Firecrawl External Action using SDK.

Tests all supported Firecrawl operations with real Firecrawl API and validates
that output_data follows the node spec format from FIRECRAWL.py.

Usage:
    FIRECRAWL_API_KEY="fc-..." python test_firecrawl_direct.py
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus, NodeExecutionResult, TriggerInfo
from shared.models.workflow import Node
from workflow_engine_v2.core.context import NodeExecutionContext
from workflow_engine_v2.runners.external_actions.firecrawl_external_action import (
    FirecrawlExternalAction,
)

# ============================================================================
# Configuration
# ============================================================================

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "fc-a3b3b5add40242dd8470e886bc13b6b0")
TEST_URL = "https://firecrawl.dev"  # Firecrawl's own website for testing
TEST_SEARCH_QUERY = "artificial intelligence"


# ============================================================================
# Output Validation (per node spec)
# ============================================================================


def validate_node_spec_output(output_data: dict, action_type: str) -> bool:
    """
    Validate that output_data follows the FIRECRAWL.py node spec format.

    Required output_params per spec:
    - success: boolean
    - content: string (extracted content)
    - data: object (structured data)
    - urls_processed: array
    - error_message: string
    - stats: object (execution statistics)
    """
    required_fields = {
        "success": bool,
        "content": str,
        "data": dict,
        "urls_processed": list,
        "error_message": str,
        "stats": dict,
    }

    print(f"\n📋 Validating output for action_type: {action_type}")
    all_valid = True

    for field, expected_type in required_fields.items():
        if field not in output_data:
            print(f"  ❌ Missing field: {field}")
            all_valid = False
        elif not isinstance(output_data[field], expected_type):
            print(
                f"  ❌ Wrong type for {field}: expected {expected_type.__name__}, "
                f"got {type(output_data[field]).__name__}"
            )
            all_valid = False
        else:
            print(f"  ✅ {field}: {expected_type.__name__}")

    if all_valid:
        print("  ✅ All output fields valid!")
    else:
        print("  ❌ Output validation failed!")

    return all_valid


# ============================================================================
# Test Helper
# ============================================================================


async def run_firecrawl_test(
    test_name: str,
    action_type: str,
    input_data: Dict[str, Any],
    configurations: Dict[str, Any] = None,
) -> NodeExecutionResult:
    """Run a single Firecrawl operation test with validation."""
    print(f"\n{'='*80}")
    print(f"🧪 TEST: {test_name}")
    print(f"{'='*80}")
    print(f"Action Type: {action_type}")
    print(f"Input Data: {input_data}")

    # Create test action instance
    action = FirecrawlExternalAction()

    # Create test node with configurations
    default_configs = {
        "firecrawl_api_key": FIRECRAWL_API_KEY,
        "action_type": action_type,
    }
    if configurations:
        default_configs.update(configurations)

    node = Node(
        id=f"test-firecrawl-{action_type}",
        name=f"Test_Firecrawl_{action_type.replace('_', '-')}",
        type="EXTERNAL_ACTION",
        subtype="FIRECRAWL",
        description=f"Test node for Firecrawl {action_type} operation",
        configurations=default_configs,
    )

    # Create execution context (workflow_engine_v2 style)
    trigger = TriggerInfo(
        trigger_type="MANUAL",
        trigger_subtype="MANUAL",
        trigger_data={"test_action": action_type},
        timestamp=int(time.time() * 1000),
    )

    context = NodeExecutionContext(
        node=node,
        input_data=input_data,
        trigger=trigger,
        metadata={
            "user_id": "test-user-001",
            "test_action": action_type,
        },
    )

    # Execute the operation (workflow_engine_v2 uses execute method)
    result = await action.execute(context)

    # Display results
    print(f"\n📊 Result Status: {result.status.value}")
    print(f"Output Data Keys: {list(result.output_data.keys())}")

    # Check both status and output_data.success for actual success
    api_success = result.output_data.get("success", False)

    if result.status == ExecutionStatus.SUCCESS and api_success:
        print(f"✅ Operation succeeded!")
        print(f"Content Length: {len(result.output_data.get('content', ''))} characters")
        print(f"URLs Processed: {result.output_data.get('urls_processed')}")
        print(f"Stats: {result.output_data.get('stats')}")

        # Show preview of content (first 200 chars)
        content = result.output_data.get("content", "")
        if content:
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"Content Preview: {preview}")

        # Show data if available
        data = result.output_data.get("data", {})
        if data:
            print(f"Data Keys: {list(data.keys())}")
    else:
        print(f"❌ Operation failed!")
        print(f"Status: {result.status.value}, API Success: {api_success}")
        print(f"Error: {result.error_message or result.output_data.get('error_message')}")
        if result.error_details:
            print(f"Error Details: {result.error_details}")

    # Validate output format
    output_valid = validate_node_spec_output(result.output_data, action_type)
    if not output_valid:
        print("\n⚠️  WARNING: Output does not match node spec!")

    return result


# ============================================================================
# Test Cases
# ============================================================================


async def test_scrape_single_page():
    """Test 1: Scrape a single webpage with markdown format."""
    result = await run_firecrawl_test(
        test_name="Scrape Single Page (Markdown)",
        action_type="scrape",
        input_data={
            "url": TEST_URL,
            "format": "markdown",
            "exclude_selectors": ["nav", "footer", "script", "style"],
        },
    )
    return result


async def test_scrape_with_html_format():
    """Test 2: Scrape a webpage with HTML format."""
    result = await run_firecrawl_test(
        test_name="Scrape Single Page (HTML)",
        action_type="scrape",
        input_data={
            "url": TEST_URL,
            "format": "html",
            "include_selectors": ["article", "main", ".content"],
        },
    )
    return result


async def test_crawl_website():
    """Test 3: Crawl multiple pages from a website."""
    result = await run_firecrawl_test(
        test_name="Crawl Website (Limited Depth)",
        action_type="crawl",
        input_data={
            "url": TEST_URL,
            "max_depth": 2,
            "limit": 5,  # Limit to 5 pages to keep test fast
            "exclude_selectors": ["nav", "footer"],
        },
    )
    return result


async def test_extract_structured_data():
    """Test 4: Extract structured data using schema."""
    result = await run_firecrawl_test(
        test_name="Extract Structured Data",
        action_type="extract",
        input_data={
            "url": TEST_URL,
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "main_heading": {"type": "string"},
                    "key_features": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
    )
    return result


async def test_map_urls():
    """Test 6: Map/discover URLs from a website."""
    result = await run_firecrawl_test(
        test_name="Map URLs",
        action_type="map",
        input_data={
            "url": TEST_URL,
        },
    )
    return result


async def test_search():
    """Test 7: Search the web and scrape results."""
    result = await run_firecrawl_test(
        test_name="Search Web",
        action_type="search",
        input_data={
            "query": TEST_SEARCH_QUERY,
            "limit": 5,
        },
    )
    return result


async def test_scrape_with_custom_headers():
    """Test 8: Scrape with custom HTTP headers."""
    result = await run_firecrawl_test(
        test_name="Scrape with Custom Headers",
        action_type="scrape",
        input_data={
            "url": TEST_URL,
            "format": "markdown",
            "headers": {
                "User-Agent": "Mozilla/5.0 (compatible; WorkflowBot/1.0)",
                "Accept-Language": "en-US,en;q=0.9",
            },
        },
    )
    return result


async def test_dynamic_action_type():
    """Test 9: Use dynamic action_type from input_params (overrides config)."""
    result = await run_firecrawl_test(
        test_name="Dynamic Action Type Override",
        action_type="scrape",  # Config default
        input_data={
            "action_type": "map",  # Override with input_params
            "url": TEST_URL,
        },
    )
    return result


async def test_error_missing_url():
    """Test 10: Error handling for missing required URL parameter."""
    result = await run_firecrawl_test(
        test_name="Error: Missing URL",
        action_type="scrape",
        input_data={
            # Missing 'url' parameter
            "format": "markdown",
        },
    )
    return result


async def test_error_invalid_api_key():
    """Test 11: Error handling for invalid API key."""
    result = await run_firecrawl_test(
        test_name="Error: Invalid API Key",
        action_type="scrape",
        input_data={
            "url": TEST_URL,
        },
        configurations={
            "firecrawl_api_key": "fc-invalid-key-12345",  # Invalid key
        },
    )
    return result


# ============================================================================
# Main Test Runner
# ============================================================================


async def main():
    """Run all Firecrawl operation tests."""
    print("=" * 80)
    print("🚀 Firecrawl External Action SDK Test Suite")
    print("=" * 80)
    print(f"Test URL: {TEST_URL}")
    print(f"Search Query: {TEST_SEARCH_QUERY}")
    print(f"API Key: {FIRECRAWL_API_KEY[:10]}..." if FIRECRAWL_API_KEY else "Not Set")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)

    if not FIRECRAWL_API_KEY or FIRECRAWL_API_KEY == "":
        print("\n❌ ERROR: FIRECRAWL_API_KEY not set!")
        print("Please set FIRECRAWL_API_KEY environment variable.")
        return

    # Store results for summary
    results = {}

    # Run tests sequentially
    test_functions = [
        ("Scrape (Markdown)", test_scrape_single_page),
        ("Scrape (HTML)", test_scrape_with_html_format),
        ("Crawl Website", test_crawl_website),
        ("Extract Data", test_extract_structured_data),
        ("Map URLs", test_map_urls),
        ("Search Web", test_search),
        ("Custom Headers", test_scrape_with_custom_headers),
        ("Dynamic Action", test_dynamic_action_type),
        ("Error: No URL", test_error_missing_url),
        ("Error: Bad Key", test_error_invalid_api_key),
    ]

    for test_name, test_func in test_functions:
        try:
            result = await test_func()
            # Check both execution status AND API success
            api_success = result.output_data.get("success", False)
            results[test_name] = {
                "status": result.status.value,
                "success": result.status == ExecutionStatus.SUCCESS and api_success,
            }
        except Exception as e:
            print(f"\n❌ Test '{test_name}' raised exception: {e}")
            import traceback

            traceback.print_exc()
            results[test_name] = {"status": "EXCEPTION", "success": False, "error": str(e)}

        # Small delay between tests to avoid rate limiting
        await asyncio.sleep(2)

    # Print summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    success_count = sum(1 for r in results.values() if r.get("success"))
    total_count = len(results)

    for test_name, result in results.items():
        status_emoji = "✅" if result.get("success") else "❌"
        print(f"{status_emoji} {test_name}: {result['status']}")

    print("=" * 80)
    print(f"Total: {success_count}/{total_count} tests passed")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
