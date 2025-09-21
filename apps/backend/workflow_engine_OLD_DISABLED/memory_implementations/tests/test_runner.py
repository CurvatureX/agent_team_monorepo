#!/usr/bin/env python3
"""
Test runner for memory integration tests.

Runs comprehensive tests of memory-LLM integration with proper environment setup.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from workflow_engine.memory_implementations.tests.test_ai_node_memory_integration import (
    TestAINodeMemoryIntegration,
)

# Import test modules
from workflow_engine.memory_implementations.tests.test_memory_llm_integration import (
    TestMemoryLLMIntegration,
)

logger = logging.getLogger(__name__)


class MemoryTestRunner:
    """Test runner for memory integration tests."""

    def __init__(self):
        self.setup_logging()
        self.check_environment()

    def setup_logging(self):
        """Configure logging for test runs."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(), logging.FileHandler("memory_tests.log")],
        )

    def check_environment(self):
        """Check required environment variables."""
        required_vars = ["SUPABASE_URL", "SUPABASE_SECRET_KEY", "OPENAI_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            logger.error("Please set the following environment variables:")
            for var in missing_vars:
                logger.error(f"  export {var}='your_{var.lower()}'")
            sys.exit(1)

        logger.info("✅ Environment variables verified")

    async def run_basic_memory_tests(self):
        """Run basic memory functionality tests."""
        logger.info("🧪 Running basic memory tests...")

        test_instance = TestMemoryLLMIntegration()
        env = await test_instance.setup_test_environment()

        tests = [
            (
                "Conversation Memory Preservation",
                test_instance.test_conversation_memory_preservation,
            ),
            ("Entity Memory Extraction", test_instance.test_entity_memory_extraction_and_context),
            ("Knowledge Base Reasoning", test_instance.test_knowledge_base_reasoning),
            ("Graph Memory Relationships", test_instance.test_graph_memory_relationship_reasoning),
            (
                "Episodic Memory Temporal Context",
                test_instance.test_episodic_memory_temporal_context,
            ),
        ]

        results = []
        for test_name, test_func in tests:
            try:
                logger.info(f"Running: {test_name}")
                await test_func(env)
                results.append((test_name, "PASSED", None))
                logger.info(f"✅ {test_name} - PASSED")
            except Exception as e:
                results.append((test_name, "FAILED", str(e)))
                logger.error(f"❌ {test_name} - FAILED: {e}")

        return results

    async def run_integration_tests(self):
        """Run AI node integration tests."""
        logger.info("🔗 Running AI node integration tests...")

        test_instance = TestAINodeMemoryIntegration()
        env = await test_instance.setup_test_environment()

        tests = [
            (
                "AI Node with Conversation Memory",
                test_instance.test_ai_node_with_conversation_memory,
            ),
            (
                "AI Node with Multiple Memory Types",
                test_instance.test_ai_node_with_multiple_memory_types,
            ),
            (
                "Memory Context Prioritization",
                test_instance.test_ai_node_memory_context_prioritization,
            ),
            ("Memory Enhanced Workflow", test_instance.test_ai_node_memory_enhanced_workflow),
        ]

        results = []
        for test_name, test_func in tests:
            try:
                logger.info(f"Running: {test_name}")
                await test_func(env)
                results.append((test_name, "PASSED", None))
                logger.info(f"✅ {test_name} - PASSED")
            except Exception as e:
                results.append((test_name, "FAILED", str(e)))
                logger.error(f"❌ {test_name} - FAILED: {e}")

        return results

    async def run_comprehensive_test(self):
        """Run comprehensive memory-LLM integration test."""
        logger.info("🌟 Running comprehensive integration test...")

        test_instance = TestMemoryLLMIntegration()
        env = await test_instance.setup_test_environment()

        try:
            await test_instance.test_multi_memory_context_merger(env)
            await test_instance.test_memory_enhanced_conversation_flow(env)
            logger.info("✅ Comprehensive integration test - PASSED")
            return [("Comprehensive Integration", "PASSED", None)]
        except Exception as e:
            logger.error(f"❌ Comprehensive integration test - FAILED: {e}")
            return [("Comprehensive Integration", "FAILED", str(e))]

    def print_results_summary(self, all_results):
        """Print test results summary."""
        total_tests = sum(len(results) for results in all_results)
        passed_tests = sum(
            1 for results in all_results for _, status, _ in results if status == "PASSED"
        )
        failed_tests = total_tests - passed_tests

        logger.info("\\n" + "=" * 60)
        logger.info("🧪 MEMORY INTEGRATION TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        if failed_tests > 0:
            logger.info("\\n❌ FAILED TESTS:")
            for results in all_results:
                for test_name, status, error in results:
                    if status == "FAILED":
                        logger.info(f"  - {test_name}: {error}")

        logger.info("=" * 60)

        return failed_tests == 0

    async def run_all_tests(self, test_type="all"):
        """Run all tests based on specified type."""
        logger.info(f"🚀 Starting memory integration tests (type: {test_type})")

        all_results = []

        if test_type in ["all", "basic"]:
            basic_results = await self.run_basic_memory_tests()
            all_results.append(basic_results)

        if test_type in ["all", "integration"]:
            integration_results = await self.run_integration_tests()
            all_results.append(integration_results)

        if test_type in ["all", "comprehensive"]:
            comprehensive_results = await self.run_comprehensive_test()
            all_results.append(comprehensive_results)

        success = self.print_results_summary(all_results)
        return success


async def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Run memory integration tests")
    parser.add_argument(
        "--type",
        choices=["all", "basic", "integration", "comprehensive"],
        default="all",
        help="Type of tests to run",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    runner = MemoryTestRunner()
    success = await runner.run_all_tests(args.type)

    if success:
        logger.info("🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error("💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
