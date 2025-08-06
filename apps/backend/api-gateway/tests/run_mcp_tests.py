#!/usr/bin/env python3
"""
Test runner for MCP Node Knowledge Server tests.
Runs all MCP-related tests and provides a summary.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run all MCP tests and provide summary"""

    print("=" * 80)
    print("Running MCP Node Knowledge Server Test Suite")
    print("=" * 80)

    # Test files to run
    test_files = [
        "tests/test_basic.py",
        "tests/test_node_knowledge_service.py",
        "tests/test_mcp_tools.py",
        "tests/test_mcp_endpoints.py",
        "tests/test_mcp_error_handling.py",
        "tests/test_mcp_performance.py",
    ]

    # Pytest arguments
    pytest_args = [
        "python",
        "-m",
        "pytest",
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--durations=10",  # Show 10 slowest tests
        "-x",  # Stop on first failure
    ]

    # Add test files
    pytest_args.extend(test_files)

    print(f"Running command: {' '.join(pytest_args)}")
    print()

    try:
        # Run pytest
        result = subprocess.run(
            pytest_args,
            capture_output=False,  # Show output in real-time
            text=True,
            cwd=Path(__file__).parent,
        )

        print("\n" + "=" * 80)
        if result.returncode == 0:
            print("✅ All MCP tests passed successfully!")
        else:
            print("❌ Some MCP tests failed.")
            print(f"Exit code: {result.returncode}")
        print("=" * 80)

        return result.returncode

    except FileNotFoundError:
        print("❌ Error: pytest not found. Please install pytest:")
        print("pip install pytest pytest-asyncio")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def run_quick_tests():
    """Run a subset of critical tests for quick validation"""

    print("=" * 60)
    print("Running Quick MCP Tests")
    print("=" * 60)

    # Critical test files
    test_files = [
        "tests/test_basic.py::test_mcp_node_knowledge_integration",
        "tests/test_node_knowledge_service.py::TestNodeKnowledgeService::test_get_node_types_all",
        "tests/test_mcp_tools.py::TestNodeKnowledgeMCPService::test_get_available_tools",
        "tests/test_mcp_endpoints.py::TestMCPEndpoints::test_mcp_tools_endpoint_without_auth",
    ]

    pytest_args = [
        "python",
        "-m",
        "pytest",
        "-v",
        "--tb=short",
    ] + test_files

    print(f"Running command: {' '.join(pytest_args)}")
    print()

    try:
        result = subprocess.run(
            pytest_args, capture_output=False, text=True, cwd=Path(__file__).parent
        )

        print("\n" + "=" * 60)
        if result.returncode == 0:
            print("✅ Quick MCP tests passed!")
        else:
            print("❌ Quick MCP tests failed.")
        print("=" * 60)

        return result.returncode

    except Exception as e:
        print(f"❌ Error running quick tests: {e}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        exit_code = run_quick_tests()
    else:
        exit_code = run_tests()

    sys.exit(exit_code)
