#!/usr/bin/env python3
"""
Test runner for workflow_engine_v2.

This script provides various options for running tests:
- Run all tests
- Run specific test categories
- Run with coverage reporting
- Run performance tests
"""
import argparse
import subprocess
import sys
from pathlib import Path

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def run_command(cmd, description):
    """Run a command and handle the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed with exit code {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def run_basic_tests():
    """Run basic unit tests."""
    cmd = ["python", "-m", "pytest", "test_basic.py", "test_flow_wait_and_foreach.py", "-v"]
    return run_command(cmd, "Basic workflow engine tests")


def run_oauth_tests():
    """Run OAuth and credential management tests."""
    cmd = ["python", "-m", "pytest", "test_oauth2_service.py", "-v", "--tb=short"]
    return run_command(cmd, "OAuth2 and credential management tests")


def run_external_action_tests():
    """Run external action tests."""
    cmd = ["python", "-m", "pytest", "test_external_actions.py", "-v", "--tb=short"]
    return run_command(cmd, "External action implementation tests")


def run_memory_tests():
    """Run memory implementation tests."""
    cmd = ["python", "-m", "pytest", "test_memory_implementations.py", "-v", "--tb=short"]
    return run_command(cmd, "Memory implementation tests")


def run_hil_tests():
    """Run Human-in-the-Loop tests."""
    cmd = ["python", "-m", "pytest", "test_hil_services.py", "-v", "--tb=short"]
    return run_command(cmd, "HIL service tests")


def run_service_tests():
    """Run service layer tests."""
    cmd = ["python", "-m", "pytest", "test_services.py", "-v", "--tb=short"]
    return run_command(cmd, "Service layer tests")


def run_api_tests():
    """Run API endpoint tests."""
    cmd = ["python", "-m", "pytest", "test_api_endpoints.py", "-v", "--tb=short"]
    return run_command(cmd, "API endpoint tests")


def run_all_tests():
    """Run all tests."""
    cmd = ["python", "-m", "pytest", ".", "-v", "--tb=short"]
    return run_command(cmd, "All workflow_engine_v2 tests")


def run_tests_with_coverage():
    """Run tests with coverage reporting."""
    cmd = [
        "python",
        "-m",
        "pytest",
        ".",
        "--cov=workflow_engine_v2",
        "--cov-report=html",
        "--cov-report=term-missing",
        "-v",
    ]
    return run_command(cmd, "All tests with coverage reporting")


def run_integration_tests():
    """Run integration tests only."""
    cmd = ["python", "-m", "pytest", ".", "-m", "integration", "-v"]
    return run_command(cmd, "Integration tests only")


def run_performance_tests():
    """Run performance tests."""
    cmd = ["python", "-m", "pytest", ".", "-m", "slow", "-v", "--tb=short"]
    return run_command(cmd, "Performance tests")


def run_parallel_tests():
    """Run tests in parallel using pytest-xdist."""
    cmd = ["python", "-m", "pytest", ".", "-n", "auto", "-v"]
    return run_command(cmd, "All tests in parallel")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Test runner for workflow_engine_v2")
    parser.add_argument(
        "test_type",
        choices=[
            "all",
            "basic",
            "oauth",
            "external",
            "memory",
            "hil",
            "services",
            "api",
            "coverage",
            "integration",
            "performance",
            "parallel",
        ],
        help="Type of tests to run",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Run with verbose output")
    parser.add_argument("--failfast", "-x", action="store_true", help="Stop on first failure")

    args = parser.parse_args()

    # Change to the tests directory
    tests_dir = Path(__file__).parent
    original_cwd = Path.cwd()

    try:
        import os

        os.chdir(tests_dir)

        print(f"Running {args.test_type} tests from {tests_dir}")

        # Run the appropriate test suite
        success = False
        if args.test_type == "all":
            success = run_all_tests()
        elif args.test_type == "basic":
            success = run_basic_tests()
        elif args.test_type == "oauth":
            success = run_oauth_tests()
        elif args.test_type == "external":
            success = run_external_action_tests()
        elif args.test_type == "memory":
            success = run_memory_tests()
        elif args.test_type == "hil":
            success = run_hil_tests()
        elif args.test_type == "services":
            success = run_service_tests()
        elif args.test_type == "api":
            success = run_api_tests()
        elif args.test_type == "coverage":
            success = run_tests_with_coverage()
        elif args.test_type == "integration":
            success = run_integration_tests()
        elif args.test_type == "performance":
            success = run_performance_tests()
        elif args.test_type == "parallel":
            success = run_parallel_tests()

        if success:
            print(f"\n✅ {args.test_type.title()} tests completed successfully!")
            return 0
        else:
            print(f"\n❌ {args.test_type.title()} tests failed!")
            return 1

    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    sys.exit(main())
