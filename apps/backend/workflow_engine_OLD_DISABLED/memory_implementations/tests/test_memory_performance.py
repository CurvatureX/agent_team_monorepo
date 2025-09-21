"""
Performance tests for memory implementations with LLM integration.

Tests memory system performance, token optimization, and scalability.
"""

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest

from workflow_engine.memory_implementations.conversation_buffer import ConversationBufferMemory
from workflow_engine.memory_implementations.entity_memory import EntityMemory
from workflow_engine.memory_implementations.graph_memory import GraphMemory
from workflow_engine.memory_implementations.knowledge_base import KnowledgeBaseMemory
from workflow_engine.memory_implementations.memory_context_merger import (
    MemoryContext,
    MemoryContextMerger,
    MemoryPriority,
)
from workflow_engine.memory_implementations.vector_database import VectorDatabaseMemory

try:
    import openai
    from supabase import create_client

    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not DEPENDENCIES_AVAILABLE, reason="Required dependencies not available"
)

logger = logging.getLogger(__name__)


class TestMemoryPerformance:
    """Performance test suite for memory implementations."""

    @pytest.fixture
    async def setup_performance_test(self):
        """Set up performance test environment."""
        user_id = f"perf_test_{uuid.uuid4().hex[:8]}"
        session_id = f"session_{uuid.uuid4().hex[:8]}"

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SECRET_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if not all([supabase_url, supabase_key, openai_key]):
            pytest.skip("Required environment variables not set")

        # Initialize memory instances
        memories = {
            "conversation": ConversationBufferMemory(
                user_id=user_id,
                session_id=session_id,
                supabase_url=supabase_url,
                supabase_key=supabase_key,
            ),
            "entity": EntityMemory(
                user_id=user_id,
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                openai_api_key=openai_key,
            ),
            "knowledge": KnowledgeBaseMemory(
                user_id=user_id,
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                openai_api_key=openai_key,
            ),
            "graph": GraphMemory(
                user_id=user_id,
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                openai_api_key=openai_key,
            ),
            "vector": VectorDatabaseMemory(
                user_id=user_id,
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                openai_api_key=openai_key,
            ),
        }

        # Initialize all memories
        for memory in memories.values():
            await memory._setup()

        context_merger = MemoryContextMerger()

        return {
            "user_id": user_id,
            "session_id": session_id,
            "memories": memories,
            "context_merger": context_merger,
            "openai_key": openai_key,
        }

    async def measure_execution_time(self, func, *args, **kwargs):
        """Measure execution time of async function."""
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time

    @pytest.mark.asyncio
    async def test_conversation_memory_bulk_storage_performance(self, setup_performance_test):
        """Test conversation memory performance with bulk storage."""
        env = await setup_performance_test
        conversation_memory = env["memories"]["conversation"]

        # Test storing many messages
        num_messages = 100
        messages = [
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"This is test message number {i} with some additional content to make it realistic.",
            }
            for i in range(num_messages)
        ]

        # Measure bulk storage time
        start_time = time.time()
        for message in messages:
            await conversation_memory.store(message)
        storage_time = time.time() - start_time

        # Measure context retrieval time
        retrieval_result, retrieval_time = await self.measure_execution_time(
            conversation_memory.get_context, {"max_messages": num_messages}
        )

        # Performance assertions
        assert (
            storage_time < 30.0
        ), f"Storage of {num_messages} messages should complete within 30s, took {storage_time:.2f}s"
        assert (
            retrieval_time < 5.0
        ), f"Context retrieval should complete within 5s, took {retrieval_time:.2f}s"

        # Verify all messages were stored
        retrieved_messages = retrieval_result.get("messages", [])
        assert (
            len(retrieved_messages) == num_messages
        ), f"Should retrieve all {num_messages} messages"

        logger.info(
            f"✅ Conversation memory performance: {num_messages} messages stored in {storage_time:.2f}s, retrieved in {retrieval_time:.2f}s"
        )

    @pytest.mark.asyncio
    async def test_entity_memory_extraction_performance(self, setup_performance_test):
        """Test entity memory performance with multiple extractions."""
        env = await setup_performance_test
        entity_memory = env["memories"]["entity"]

        # Test with multiple text chunks for entity extraction
        text_chunks = [
            "John Smith works at Microsoft as a software engineer in Seattle.",
            "Sarah Johnson is a data scientist at Google in Mountain View.",
            "Michael Brown teaches computer science at Stanford University.",
            "Lisa Davis runs a startup called TechCorp in San Francisco.",
            "David Wilson is a consultant at McKinsey & Company in New York.",
        ]

        # Measure entity extraction performance
        extraction_times = []
        total_entities = 0

        for i, text in enumerate(text_chunks):
            result, extraction_time = await self.measure_execution_time(
                entity_memory.store, {"text": text, "extract_entities": True}
            )

            extraction_times.append(extraction_time)
            if result.get("entities_stored"):
                total_entities += result["entities_stored"]

            logger.info(
                f"Chunk {i+1}: {extraction_time:.2f}s, entities: {result.get('entities_stored', 0)}"
            )

        # Wait for all extractions to complete
        await asyncio.sleep(3)

        # Measure context retrieval performance
        context_result, context_time = await self.measure_execution_time(
            entity_memory.get_context, {"max_entities": 20}
        )

        # Performance assertions
        avg_extraction_time = sum(extraction_times) / len(extraction_times)
        assert (
            avg_extraction_time < 10.0
        ), f"Average extraction time should be under 10s, got {avg_extraction_time:.2f}s"
        assert context_time < 3.0, f"Context retrieval should be under 3s, got {context_time:.2f}s"
        assert total_entities > 0, "Should have extracted some entities"

        logger.info(
            f"✅ Entity memory performance: {len(text_chunks)} extractions, avg {avg_extraction_time:.2f}s, context {context_time:.2f}s"
        )

    @pytest.mark.asyncio
    async def test_knowledge_base_fact_storage_performance(self, setup_performance_test):
        """Test knowledge base performance with fact extraction and storage."""
        env = await setup_performance_test
        knowledge_memory = env["memories"]["knowledge"]

        # Test with knowledge-rich content
        knowledge_content = [
            "Python is a high-level programming language. It was created by Guido van Rossum. Python supports multiple programming paradigms.",
            "Machine learning is a subset of artificial intelligence. It uses statistical techniques to enable computers to learn from data.",
            "Django is a web framework written in Python. It follows the model-view-template architectural pattern.",
            "PostgreSQL is an open-source relational database system. It supports both SQL and JSON querying.",
            "React is a JavaScript library for building user interfaces. It was developed by Facebook and is now maintained by Meta.",
        ]

        # Measure fact extraction and storage performance
        storage_times = []
        total_facts = 0

        for i, content in enumerate(knowledge_content):
            result, storage_time = await self.measure_execution_time(
                knowledge_memory.store,
                {"content": content, "domain": f"technology_{i}", "extract_facts": True},
            )

            storage_times.append(storage_time)
            if result.get("facts_stored"):
                total_facts += result["facts_stored"]

            logger.info(
                f"Knowledge {i+1}: {storage_time:.2f}s, facts: {result.get('facts_stored', 0)}"
            )

        # Wait for fact extraction to complete
        await asyncio.sleep(5)

        # Measure knowledge retrieval performance
        retrieval_result, retrieval_time = await self.measure_execution_time(
            knowledge_memory.retrieve, {"query": "Python programming", "max_facts": 10}
        )

        # Measure context generation performance
        context_result, context_time = await self.measure_execution_time(
            knowledge_memory.get_context, {"domain": "technology", "query": "programming languages"}
        )

        # Performance assertions
        avg_storage_time = sum(storage_times) / len(storage_times)
        assert (
            avg_storage_time < 15.0
        ), f"Average fact storage time should be under 15s, got {avg_storage_time:.2f}s"
        assert retrieval_time < 3.0, f"Fact retrieval should be under 3s, got {retrieval_time:.2f}s"
        assert context_time < 3.0, f"Context generation should be under 3s, got {context_time:.2f}s"

        logger.info(
            f"✅ Knowledge base performance: {len(knowledge_content)} documents, avg {avg_storage_time:.2f}s, retrieval {retrieval_time:.2f}s"
        )

    @pytest.mark.asyncio
    async def test_graph_memory_relationship_performance(self, setup_performance_test):
        """Test graph memory performance with relationship modeling."""
        env = await setup_performance_test
        graph_memory = env["memories"]["graph"]

        # Test with relationship-rich content
        relationship_texts = [
            "Alice works at Google. Bob works at Microsoft. Alice and Bob are friends.",
            "Google and Microsoft are competitors. Both companies develop software products.",
            "Alice studied at MIT. Bob studied at Stanford. MIT and Stanford are prestigious universities.",
            "Google is located in Mountain View. Microsoft is located in Redmond.",
            "Alice leads a team of engineers. Bob manages product development.",
        ]

        # Measure graph storage performance
        storage_times = []
        total_nodes = 0
        total_relationships = 0

        for i, text in enumerate(relationship_texts):
            result, storage_time = await self.measure_execution_time(
                graph_memory.store, {"text": text, "extract_entities": True}
            )

            storage_times.append(storage_time)
            if result.get("nodes_stored"):
                total_nodes += result["nodes_stored"]
            if result.get("relationships_stored"):
                total_relationships += result["relationships_stored"]

            logger.info(
                f"Graph {i+1}: {storage_time:.2f}s, nodes: {result.get('nodes_stored', 0)}, rels: {result.get('relationships_stored', 0)}"
            )

        # Wait for entity extraction
        await asyncio.sleep(5)

        # Measure path finding performance
        path_result, path_time = await self.measure_execution_time(
            graph_memory.retrieve,
            {"type": "find_paths", "source": "Alice", "target": "Bob", "max_depth": 3},
        )

        # Measure graph context performance
        context_result, context_time = await self.measure_execution_time(
            graph_memory.get_context, {"entities": ["Alice", "Bob"], "max_relationships": 10}
        )

        # Performance assertions
        avg_storage_time = sum(storage_times) / len(storage_times)
        assert (
            avg_storage_time < 12.0
        ), f"Average graph storage time should be under 12s, got {avg_storage_time:.2f}s"
        assert path_time < 5.0, f"Path finding should be under 5s, got {path_time:.2f}s"
        assert context_time < 3.0, f"Graph context should be under 3s, got {context_time:.2f}s"

        logger.info(
            f"✅ Graph memory performance: {total_nodes} nodes, {total_relationships} relationships, path finding {path_time:.2f}s"
        )

    @pytest.mark.asyncio
    async def test_memory_context_merger_performance(self, setup_performance_test):
        """Test memory context merger performance with multiple contexts."""
        env = await setup_performance_test
        context_merger = env["context_merger"]

        # Create multiple large memory contexts
        large_contexts = []

        for i in range(10):
            # Create progressively larger contexts
            content_size = (i + 1) * 500  # 500, 1000, 1500, ... characters
            content = f"This is context {i} with detailed information. " * (content_size // 50)

            memory_context = MemoryContext(
                content=content,
                source=f"memory_type_{i}",
                priority=MemoryPriority.MEDIUM if i % 2 == 0 else MemoryPriority.HIGH,
                relevance_score=0.8 - (i * 0.05),  # Decreasing relevance
                token_count=len(content) // 4,
            )
            large_contexts.append(memory_context)

        # Test different merge strategies performance
        user_message = (
            "This is a test query that needs comprehensive context from multiple memory sources."
        )

        merge_strategies = ["priority", "balanced", "conversation_first", "semantic"]

        for strategy in merge_strategies:
            # Measure merge performance
            merge_result, merge_time = await self.measure_execution_time(
                context_merger.merge_contexts, large_contexts, user_message, strategy
            )

            # Performance assertions
            assert (
                merge_time < 2.0
            ), f"{strategy} merge should complete under 2s, took {merge_time:.2f}s"
            assert merge_result["total_contexts"] == len(
                large_contexts
            ), "Should process all contexts"
            assert "merged_content" in merge_result, "Should produce merged content"

            # Check token optimization
            merged_tokens = merge_result.get("estimated_tokens", 0)
            original_tokens = sum(ctx.token_count for ctx in large_contexts)
            compression_ratio = merged_tokens / original_tokens if original_tokens > 0 else 0

            logger.info(
                f"{strategy}: {merge_time:.2f}s, tokens: {original_tokens}→{merged_tokens} (ratio: {compression_ratio:.2f})"
            )

    @pytest.mark.asyncio
    async def test_concurrent_memory_operations_performance(self, setup_performance_test):
        """Test concurrent memory operations performance."""
        env = await setup_performance_test
        memories = env["memories"]

        # Define concurrent operations
        async def concurrent_conversation_ops():
            results = []
            for i in range(20):
                result = await memories["conversation"].store(
                    {"role": "user", "content": f"Concurrent message {i}"}
                )
                results.append(result)
            return results

        async def concurrent_entity_ops():
            texts = [f"Person {i} works at Company {i} in City {i}." for i in range(10)]
            results = []
            for text in texts:
                result = await memories["entity"].store({"text": text, "extract_entities": True})
                results.append(result)
            return results

        async def concurrent_knowledge_ops():
            contents = [
                f"Technology {i} is used for purpose {i}. It was created in year {2000 + i}."
                for i in range(5)
            ]
            results = []
            for content in contents:
                result = await memories["knowledge"].store(
                    {"content": content, "domain": "tech", "extract_facts": True}
                )
                results.append(result)
            return results

        # Measure concurrent execution performance
        start_time = time.time()

        conversation_results, entity_results, knowledge_results = await asyncio.gather(
            concurrent_conversation_ops(),
            concurrent_entity_ops(),
            concurrent_knowledge_ops(),
            return_exceptions=True,
        )

        concurrent_time = time.time() - start_time

        # Verify results
        assert not isinstance(
            conversation_results, Exception
        ), f"Conversation ops failed: {conversation_results}"
        assert not isinstance(entity_results, Exception), f"Entity ops failed: {entity_results}"
        assert not isinstance(
            knowledge_results, Exception
        ), f"Knowledge ops failed: {knowledge_results}"

        # Performance assertion
        assert (
            concurrent_time < 60.0
        ), f"Concurrent operations should complete within 60s, took {concurrent_time:.2f}s"

        logger.info(f"✅ Concurrent operations completed in {concurrent_time:.2f}s")

    @pytest.mark.asyncio
    async def test_memory_context_size_optimization(self, setup_performance_test):
        """Test memory context size optimization and token management."""
        env = await setup_performance_test
        context_merger = env["context_merger"]

        # Create contexts of different sizes
        test_cases = [
            {"max_tokens": 1000, "contexts": 5},
            {"max_tokens": 2000, "contexts": 10},
            {"max_tokens": 4000, "contexts": 15},
            {"max_tokens": 8000, "contexts": 20},
        ]

        for case in test_cases:
            max_tokens = case["max_tokens"]
            num_contexts = case["contexts"]

            # Create contexts that exceed token limit
            large_contexts = []
            total_original_tokens = 0

            for i in range(num_contexts):
                content = f"Large context {i}: " + "detailed information " * 200
                token_count = len(content) // 4
                total_original_tokens += token_count

                context = MemoryContext(
                    content=content,
                    source=f"source_{i}",
                    priority=MemoryPriority.HIGH if i < 3 else MemoryPriority.MEDIUM,
                    relevance_score=1.0 - (i * 0.05),
                    token_count=token_count,
                )
                large_contexts.append(context)

            # Test context optimization
            user_message = "Please provide a summary based on the available context."

            merge_result, merge_time = await self.measure_execution_time(
                context_merger.merge_contexts, large_contexts, user_message, "balanced", max_tokens
            )

            # Verify optimization
            final_tokens = merge_result.get("estimated_tokens", 0)
            contexts_used = merge_result.get("contexts_used", 0)

            assert (
                final_tokens <= max_tokens * 1.1
            ), f"Should respect token limit of {max_tokens}, got {final_tokens}"
            assert contexts_used > 0, "Should use at least some contexts"
            assert merge_time < 3.0, f"Optimization should complete quickly, took {merge_time:.2f}s"

            compression_ratio = (
                final_tokens / total_original_tokens if total_original_tokens > 0 else 0
            )

            logger.info(
                f"Optimization {max_tokens} tokens: {total_original_tokens}→{final_tokens} "
                f"({compression_ratio:.2f} ratio), {contexts_used}/{num_contexts} contexts, {merge_time:.2f}s"
            )


# Standalone performance test runner
async def run_performance_tests():
    """Run performance tests standalone."""
    logger.info("🚀 Running memory performance tests...")

    test_instance = TestMemoryPerformance()
    env = await test_instance.setup_performance_test()

    tests = [
        (
            "Conversation Memory Bulk Storage",
            test_instance.test_conversation_memory_bulk_storage_performance,
        ),
        ("Entity Memory Extraction", test_instance.test_entity_memory_extraction_performance),
        ("Knowledge Base Fact Storage", test_instance.test_knowledge_base_fact_storage_performance),
        ("Graph Memory Relationships", test_instance.test_graph_memory_relationship_performance),
        ("Memory Context Merger", test_instance.test_memory_context_merger_performance),
        ("Concurrent Operations", test_instance.test_concurrent_memory_operations_performance),
        ("Context Size Optimization", test_instance.test_memory_context_size_optimization),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            logger.info(f"Running: {test_name}")
            await test_func(env)
            results.append((test_name, "PASSED"))
            logger.info(f"✅ {test_name} - PASSED")
        except Exception as e:
            results.append((test_name, f"FAILED: {e}"))
            logger.error(f"❌ {test_name} - FAILED: {e}")

    # Print results
    logger.info("\\n" + "=" * 50)
    logger.info("🏃 PERFORMANCE TEST RESULTS")
    logger.info("=" * 50)

    passed = sum(1 for _, status in results if status == "PASSED")
    total = len(results)

    for test_name, status in results:
        logger.info(f"  {test_name}: {status}")

    logger.info(f"\\nPassed: {passed}/{total}")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_performance_tests())
