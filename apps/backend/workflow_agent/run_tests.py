#!/usr/bin/env python3
"""
Test runner script for Workflow Agent MVP
Runs all unit tests and generates coverage reports
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_tests(
    test_pattern: str | None = None,
    verbose: bool = False,
    coverage: bool = False,
    parallel: bool = False,
    failfast: bool = False,
):
    """Run tests with specified options"""

    # Base pytest command
    cmd = ["python", "-m", "pytest"]

    # Add test directory
    cmd.append("tests/")

    # Add test pattern if specified
    if test_pattern:
        cmd.extend(["-k", test_pattern])

    # Add verbosity
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    # Add parallel execution
    if parallel:
        cmd.extend(["-n", "auto"])

    # Add fail fast
    if failfast:
        cmd.append("-x")

    # Add coverage if requested
    if coverage:
        cmd.extend(
            [
                "--cov=core",
                "--cov=agents",
                "--cov-report=html:htmlcov",
                "--cov-report=term-missing",
                "--cov-report=xml",
            ]
        )

    # Add additional pytest options
    cmd.extend(["--tb=short", "--strict-markers", "--disable-warnings"])

    print(f"Running command: {' '.join(cmd)}")
    print("-" * 60)

    # Run the tests
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def run_specific_component_tests():
    """Run tests for each component separately"""
    components = [
        ("Design Engine", "test_design_engine.py"),
        ("Workflow Agent", "test_workflow_agent.py"),
        ("Intelligence Engines", "test_intelligence.py"),
        ("Data Models", "test_models.py"),
    ]

    results = {}

    for component_name, test_file in components:
        print(f"\n{'='*60}")
        print(f"Testing {component_name}")
        print(f"{'='*60}")

        cmd = ["python", "-m", "pytest", f"tests/{test_file}", "-v", "--tb=short"]

        try:
            result = subprocess.run(cmd, check=False)
            results[component_name] = result.returncode == 0
        except Exception as e:
            print(f"Error testing {component_name}: {e}")
            results[component_name] = False

    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    for component_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{component_name:30} {status}")

    all_passed = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

    return 0 if all_passed else 1


def lint_code():
    """Run code linting"""
    print("Running code linting...")

    # Run black for formatting check
    print("\n1. Checking code formatting with black...")
    black_cmd = ["python", "-m", "black", "--check", "--diff", "core/", "agents/", "tests/"]
    subprocess.run(black_cmd, check=False)

    # Run isort for import sorting check
    print("\n2. Checking import sorting with isort...")
    isort_cmd = ["python", "-m", "isort", "--check-only", "--diff", "core/", "agents/", "tests/"]
    subprocess.run(isort_cmd, check=False)

    # Run flake8 for style checking
    print("\n3. Checking code style with flake8...")
    flake8_cmd = ["python", "-m", "flake8", "core/", "agents/", "tests/"]
    subprocess.run(flake8_cmd, check=False)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run Workflow Agent tests")

    # Test mode options
    parser.add_argument(
        "--mode",
        choices=["all", "components", "quick", "coverage"],
        default="all",
        help="Test mode to run",
    )

    # Test filtering
    parser.add_argument("-k", "--pattern", help="Run tests matching this pattern")

    # Test execution options
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")

    parser.add_argument("-x", "--failfast", action="store_true", help="Stop on first failure")

    # Code quality options
    parser.add_argument("--lint", action="store_true", help="Run code linting")

    parser.add_argument("--fix", action="store_true", help="Fix code formatting issues")

    args = parser.parse_args()

    # Fix code formatting if requested
    if args.fix:
        print("Fixing code formatting...")
        subprocess.run(["python", "-m", "black", "core/", "agents/", "tests/"])
        subprocess.run(["python", "-m", "isort", "core/", "agents/", "tests/"])
        print("Code formatting fixed!")
        return 0

    # Run linting if requested
    if args.lint:
        lint_code()
        return 0

    # Run tests based on mode
    if args.mode == "components":
        return run_specific_component_tests()

    elif args.mode == "quick":
        print("Running quick tests (no coverage)...")
        return run_tests(
            test_pattern=args.pattern,
            verbose=args.verbose,
            coverage=False,
            parallel=args.parallel,
            failfast=args.failfast,
        )

    elif args.mode == "coverage":
        print("Running tests with coverage...")
        return run_tests(
            test_pattern=args.pattern,
            verbose=args.verbose,
            coverage=True,
            parallel=False,  # Coverage doesn't work well with parallel
            failfast=args.failfast,
        )

    else:  # mode == "all"
        print("Running all tests...")
        return run_tests(
            test_pattern=args.pattern,
            verbose=args.verbose,
            coverage=True,
            parallel=args.parallel,
            failfast=args.failfast,
        )


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
