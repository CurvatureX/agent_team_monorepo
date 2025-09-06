"""
Integration tests for memory nodes with LLM invocations.

Tests memory preservation and context enhancement through real LLM calls.
"""

import asyncio
import logging
import os
import uuid

# Mock node execution context for testing
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest

# Memory implementations
from workflow_engine.memory_implementations.conversation_buffer import ConversationBufferMemory
from workflow_engine.memory_implementations.entity_memory import EntityMemory
from workflow_engine.memory_implementations.episodic_memory import EpisodicMemory
from workflow_engine.memory_implementations.graph_memory import GraphMemory
from workflow_engine.memory_implementations.knowledge_base import KnowledgeBaseMemory
from workflow_engine.memory_implementations.memory_context_merger import (
    MemoryContext,
    MemoryContextMerger,
    MemoryPriority,
)

try:
    import openai
    from supabase import create_client

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Skip tests if required dependencies are not available
pytestmark = pytest.mark.skipif(
    not OPENAI_AVAILABLE, reason="OpenAI and Supabase dependencies not available"
)

logger = logging.getLogger(__name__)


@dataclass
class MockConnection:
    """Mock connection for testing."""

    connection_type: str
    source_output: Dict[str, Any]


@dataclass
class MockNodeExecutionContext:
    """Mock node execution context for testing."""

    user_id: str
    session_id: str
    input_connections: Optional[List[MockConnection]] = None
    node_parameters: Optional[Dict[str, Any]] = None


class TestMemoryLLMIntegration:
    """Test suite for memory-LLM integration."""

    @pytest.fixture
    async def setup_test_environment(self):
        """Set up test environment with memory instances."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session_id = f"session_{uuid.uuid4().hex[:8]}"

        # Check for required environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SECRET_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if not all([supabase_url, supabase_key, openai_key]):
            pytest.skip("Required environment variables not set")

        # Initialize memory instances
        conversation_memory = ConversationBufferMemory(
            user_id=user_id,
            session_id=session_id,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
        )

        entity_memory = EntityMemory(
            user_id=user_id,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            openai_api_key=openai_key,
        )

        knowledge_memory = KnowledgeBaseMemory(
            user_id=user_id,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            openai_api_key=openai_key,
        )

        graph_memory = GraphMemory(
            user_id=user_id,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            openai_api_key=openai_key,
        )

        episodic_memory = EpisodicMemory(
            user_id=user_id, supabase_url=supabase_url, supabase_key=supabase_key
        )

        context_merger = MemoryContextMerger()

        # Initialize all memories
        await conversation_memory._setup()
        await entity_memory._setup()
        await knowledge_memory._setup()
        await graph_memory._setup()
        await episodic_memory._setup()

        return {
            "user_id": user_id,
            "session_id": session_id,
            "conversation_memory": conversation_memory,
            "entity_memory": entity_memory,
            "knowledge_memory": knowledge_memory,
            "graph_memory": graph_memory,
            "episodic_memory": episodic_memory,
            "context_merger": context_merger,
            "openai_key": openai_key,
        }

    async def make_llm_call(self, messages: List[Dict[str, str]], openai_key: str) -> str:
        """Make a real LLM call for testing."""
        client = openai.AsyncOpenAI(api_key=openai_key)

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini", messages=messages, temperature=0.1, max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"Error: {str(e)}"

    @pytest.mark.asyncio
    async def test_conversation_memory_preservation(self, setup_test_environment):
        """Test that conversation memory preserves context across LLM calls."""
        env = await setup_test_environment
        conversation_memory = env["conversation_memory"]
        openai_key = env["openai_key"]

        # First conversation turn - store user message and LLM response
        user_msg_1 = "My name is Alice and I work at OpenAI as a researcher."
        await conversation_memory.store({"role": "user", "content": user_msg_1})

        # Make LLM call without memory context
        llm_response_1 = await self.make_llm_call(
            [{"role": "user", "content": user_msg_1}], openai_key
        )

        await conversation_memory.store({"role": "assistant", "content": llm_response_1})

        # Second turn - ask about previous information
        user_msg_2 = "What do you remember about my job?"
        await conversation_memory.store({"role": "user", "content": user_msg_2})

        # Get conversation context
        context = await conversation_memory.get_context({"max_messages": 10})
        messages = context.get("messages", [])

        # Make LLM call with memory context
        llm_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
        llm_response_2 = await self.make_llm_call(llm_messages, openai_key)

        await conversation_memory.store({"role": "assistant", "content": llm_response_2})

        # Verify memory preservation
        assert (
            "Alice" in llm_response_2.lower()
            or "openai" in llm_response_2.lower()
            or "researcher" in llm_response_2.lower()
        ), f"LLM should remember previous context. Response: {llm_response_2}"

        # Verify conversation buffer contains all messages
        final_context = await conversation_memory.get_context({"max_messages": 10})
        assert len(final_context["messages"]) == 4, "Should have 4 messages stored"

        logger.info("✅ Conversation memory preservation test passed")

    @pytest.mark.asyncio
    async def test_entity_memory_extraction_and_context(self, setup_test_environment):
        """Test entity extraction and LLM context enhancement."""
        env = await setup_test_environment
        entity_memory = env["entity_memory"]
        openai_key = env["openai_key"]

        # Store text with entities
        test_text = "John Smith works at Microsoft as a software engineer. He lives in Seattle with his wife Sarah. They both graduated from Stanford University."

        result = await entity_memory.store({"text": test_text, "extract_entities": True})

        assert result["stored"], f"Entity storage failed: {result}"
        logger.info(f"Stored entities: {result.get('entities_stored', 0)}")

        # Wait for extraction to complete
        await asyncio.sleep(2)

        # Get entity context
        context = await entity_memory.get_context(
            {"entities": ["John Smith", "Microsoft"], "max_entities": 5}
        )

        # Create LLM prompt with entity context
        entity_context_str = context.get("entity_summary", "")

        user_question = "Tell me about John Smith's professional background."
        enhanced_prompt = f"""Context from memory:
{entity_context_str}

Question: {user_question}"""

        # Make LLM call with entity context
        llm_response = await self.make_llm_call(
            [{"role": "user", "content": enhanced_prompt}], openai_key
        )

        # Verify entity information is used
        assert any(
            term in llm_response.lower() for term in ["microsoft", "software engineer", "seattle"]
        ), f"LLM should use entity context. Response: {llm_response}"

        logger.info("✅ Entity memory extraction and context test passed")

    @pytest.mark.asyncio
    async def test_knowledge_base_reasoning(self, setup_test_environment):
        """Test knowledge base facts and LLM reasoning."""
        env = await setup_test_environment
        knowledge_memory = env["knowledge_memory"]
        openai_key = env["openai_key"]

        # Store knowledge facts
        facts_text = "Python is a programming language. Django is a web framework written in Python. Flask is also a web framework for Python. Web frameworks help build web applications."

        result = await knowledge_memory.store(
            {"content": facts_text, "domain": "programming", "extract_facts": True}
        )

        assert result["stored"], f"Knowledge storage failed: {result}"
        logger.info(f"Stored facts: {result.get('facts_stored', 0)}")

        # Wait for fact extraction
        await asyncio.sleep(3)

        # Query knowledge base
        query_result = await knowledge_memory.retrieve(
            {"query": "web frameworks Python", "max_facts": 10}
        )

        # Get knowledge context
        context = await knowledge_memory.get_context(
            {"domain": "programming", "query": "Python web development"}
        )

        facts_summary = context.get("facts_summary", "")

        # Create reasoning prompt
        user_question = "Which Python web framework should I choose for a simple project?"
        enhanced_prompt = f"""Knowledge base facts:
{facts_summary}

Based on the above facts, answer: {user_question}"""

        # Make LLM call with knowledge context
        llm_response = await self.make_llm_call(
            [{"role": "user", "content": enhanced_prompt}], openai_key
        )

        # Verify knowledge-based reasoning
        assert any(
            framework in llm_response.lower() for framework in ["django", "flask"]
        ), f"LLM should use knowledge facts for reasoning. Response: {llm_response}"

        logger.info("✅ Knowledge base reasoning test passed")

    @pytest.mark.asyncio
    async def test_graph_memory_relationship_reasoning(self, setup_test_environment):
        """Test graph memory relationships and LLM reasoning."""
        env = await setup_test_environment
        graph_memory = env["graph_memory"]
        openai_key = env["openai_key"]

        # Store graph data with relationships
        relationship_text = "Alice works at Google. Bob works at Microsoft. Alice and Bob are friends. Google and Microsoft are competitors. Alice studied Computer Science at MIT."

        result = await graph_memory.store({"text": relationship_text, "extract_entities": True})

        assert result["stored"], f"Graph storage failed: {result}"
        logger.info(
            f"Stored nodes: {result.get('nodes_stored', 0)}, relationships: {result.get('relationships_stored', 0)}"
        )

        # Wait for entity extraction
        await asyncio.sleep(3)

        # Get relationship context
        context = await graph_memory.get_context(
            {"entities": ["Alice", "Bob"], "max_relationships": 10}
        )

        relationship_summary = context.get("relationship_summary", "")

        # Create reasoning prompt about relationships
        user_question = "What can you tell me about the relationship between Alice and Bob in terms of their work?"
        enhanced_prompt = f"""Relationship context:
{relationship_summary}

Question: {user_question}"""

        # Make LLM call with relationship context
        llm_response = await self.make_llm_call(
            [{"role": "user", "content": enhanced_prompt}], openai_key
        )

        # Verify relationship reasoning
        relationship_terms = ["friends", "google", "microsoft", "competitors", "work"]
        assert any(
            term in llm_response.lower() for term in relationship_terms
        ), f"LLM should use relationship context. Response: {llm_response}"

        logger.info("✅ Graph memory relationship reasoning test passed")

    @pytest.mark.asyncio
    async def test_episodic_memory_temporal_context(self, setup_test_environment):
        """Test episodic memory temporal context and LLM reasoning."""
        env = await setup_test_environment
        episodic_memory = env["episodic_memory"]
        openai_key = env["openai_key"]

        # Store episodic events
        events = [
            {
                "actor": "Alice",
                "action": "started_project",
                "object": "mobile app development",
                "context": {"team_size": 3, "deadline": "3 months"},
                "importance": 0.8,
                "timestamp": datetime.now(),
            },
            {
                "actor": "Alice",
                "action": "completed_milestone",
                "object": "user interface design",
                "context": {"duration_weeks": 2, "feedback": "positive"},
                "importance": 0.7,
                "timestamp": datetime.now(),
            },
            {
                "actor": "Alice",
                "action": "encountered_issue",
                "object": "database performance",
                "context": {"severity": "medium", "impact": "response_time"},
                "importance": 0.6,
                "timestamp": datetime.now(),
            },
        ]

        for event in events:
            result = await episodic_memory.store(event)
            assert result["stored"], f"Event storage failed: {result}"

        # Get episodic context
        context = await episodic_memory.get_context(
            {"actor": "Alice", "max_events": 5, "time_window_hours": 24}
        )

        event_summary = context.get("event_summary", "")

        # Create temporal reasoning prompt
        user_question = "What has Alice been working on recently and what challenges has she faced?"
        enhanced_prompt = f"""Recent events context:
{event_summary}

Question: {user_question}"""

        # Make LLM call with episodic context
        llm_response = await self.make_llm_call(
            [{"role": "user", "content": enhanced_prompt}], openai_key
        )

        # Verify temporal reasoning
        temporal_terms = ["mobile app", "interface", "database", "performance", "project"]
        assert any(
            term in llm_response.lower() for term in temporal_terms
        ), f"LLM should use episodic context. Response: {llm_response}"

        logger.info("✅ Episodic memory temporal context test passed")

    @pytest.mark.asyncio
    async def test_multi_memory_context_merger(self, setup_test_environment):
        """Test memory context merger with multiple memory types."""
        env = await setup_test_environment
        context_merger = env["context_merger"]
        conversation_memory = env["conversation_memory"]
        entity_memory = env["entity_memory"]
        openai_key = env["openai_key"]

        # Store conversation context
        await conversation_memory.store(
            {"role": "user", "content": "I'm working on a Python project using Django."}
        )
        await conversation_memory.store(
            {
                "role": "assistant",
                "content": "That's great! Django is a powerful web framework. What kind of application are you building?",
            }
        )

        # Store entity context
        await entity_memory.store(
            {
                "text": "Django is a high-level Python web framework. It follows the model-view-template pattern.",
                "extract_entities": True,
            }
        )

        # Wait for processing
        await asyncio.sleep(2)

        # Get contexts from different memory types
        conv_context = await conversation_memory.get_context({"max_messages": 5})
        entity_context = await entity_memory.get_context({"entities": ["Django", "Python"]})

        # Create memory contexts for merger
        memory_contexts = [
            MemoryContext(
                content=str(conv_context.get("messages", [])),
                source="conversation",
                priority=MemoryPriority.HIGH,
                relevance_score=0.9,
                token_count=len(str(conv_context)) // 4,
            ),
            MemoryContext(
                content=entity_context.get("entity_summary", ""),
                source="entities",
                priority=MemoryPriority.MEDIUM,
                relevance_score=0.7,
                token_count=len(entity_context.get("entity_summary", "")) // 4,
            ),
        ]

        # Merge contexts with different strategies
        user_message = "What are the benefits of using Django for web development?"

        # Test priority merge strategy
        merged_priority = context_merger.merge_contexts(
            memory_contexts, user_message, merge_strategy="priority"
        )

        # Test balanced merge strategy
        merged_balanced = context_merger.merge_contexts(
            memory_contexts, user_message, merge_strategy="balanced"
        )

        # Create LLM prompt with merged context
        enhanced_prompt = f"""Memory context:
{merged_balanced.get('merged_content', '')}

Question: {user_message}"""

        # Make LLM call with merged context
        llm_response = await self.make_llm_call(
            [{"role": "user", "content": enhanced_prompt}], openai_key
        )

        # Verify merged context usage
        django_terms = ["django", "python", "framework", "web", "model"]
        assert any(
            term in llm_response.lower() for term in django_terms
        ), f"LLM should use merged memory context. Response: {llm_response}"

        # Verify merge metadata
        assert merged_balanced["total_contexts"] == 2
        assert merged_balanced["merge_strategy"] == "balanced"
        assert "conversation" in merged_balanced["sources_used"]

        logger.info("✅ Multi-memory context merger test passed")

    @pytest.mark.asyncio
    async def test_memory_enhanced_conversation_flow(self, setup_test_environment):
        """Test complete conversation flow with memory enhancement."""
        env = await setup_test_environment
        conversation_memory = env["conversation_memory"]
        entity_memory = env["entity_memory"]
        context_merger = env["context_merger"]
        openai_key = env["openai_key"]

        # Simulate multi-turn conversation with memory
        turns = [
            {
                "user": "Hi, I'm Sarah Johnson, a data scientist at Netflix working on recommendation systems.",
                "expected_memory": ["sarah", "netflix", "data scientist", "recommendation"],
            },
            {
                "user": "I'm particularly interested in collaborative filtering techniques.",
                "expected_memory": ["collaborative filtering", "techniques"],
            },
            {
                "user": "Can you remind me what my job title is and where I work?",
                "expected_memory": ["data scientist", "netflix"],
            },
        ]

        conversation_history = []

        for i, turn in enumerate(turns):
            user_message = turn["user"]

            # Store user message
            await conversation_memory.store({"role": "user", "content": user_message})

            # Extract and store entities if it's the first turn
            if i == 0:
                await entity_memory.store({"text": user_message, "extract_entities": True})
                await asyncio.sleep(2)  # Wait for entity extraction

            # Get memory contexts
            conv_context = await conversation_memory.get_context({"max_messages": 10})
            entity_context = await entity_memory.get_context(
                {"entities": ["Sarah Johnson", "Netflix", "data scientist"]}
            )

            # Create memory contexts for merger
            memory_contexts = [
                MemoryContext(
                    content=str(conv_context.get("messages", [])),
                    source="conversation",
                    priority=MemoryPriority.HIGH,
                    relevance_score=0.9,
                    token_count=len(str(conv_context)) // 4,
                )
            ]

            if entity_context.get("entity_summary"):
                memory_contexts.append(
                    MemoryContext(
                        content=entity_context.get("entity_summary", ""),
                        source="entities",
                        priority=MemoryPriority.MEDIUM,
                        relevance_score=0.8,
                        token_count=len(entity_context.get("entity_summary", "")) // 4,
                    )
                )

            # Merge contexts
            merged_context = context_merger.merge_contexts(
                memory_contexts, user_message, merge_strategy="conversation_first"
            )

            # Create enhanced prompt
            if i == 0:
                # First turn - no memory context needed
                enhanced_prompt = user_message
            else:
                enhanced_prompt = f"""Memory context:
{merged_context.get('merged_content', '')}

Current message: {user_message}"""

            # Make LLM call
            messages = [{"role": "user", "content": enhanced_prompt}]
            if i > 0:
                # Add conversation history
                for msg in conversation_history:
                    messages.insert(-1, msg)

            llm_response = await self.make_llm_call(messages, openai_key)

            # Store LLM response
            await conversation_memory.store({"role": "assistant", "content": llm_response})

            # Update conversation history
            conversation_history.extend(
                [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": llm_response},
                ]
            )

            # Verify expected memory terms appear in response (for later turns)
            if i >= 2:  # Third turn should remember previous context
                expected_terms = turn["expected_memory"]
                response_lower = llm_response.lower()
                memory_preserved = any(term in response_lower for term in expected_terms)

                assert (
                    memory_preserved
                ), f"Turn {i+1}: LLM should remember context. Expected terms: {expected_terms}. Response: {llm_response}"

            logger.info(f"Turn {i+1} completed successfully")

        # Final verification - check total conversation length
        final_context = await conversation_memory.get_context({"max_messages": 20})
        assert (
            len(final_context["messages"]) == 6
        ), "Should have 6 total messages (3 user + 3 assistant)"

        logger.info("✅ Memory-enhanced conversation flow test passed")


# Utility functions for standalone testing
async def run_single_test():
    """Run a single test for debugging."""
    test_instance = TestMemoryLLMIntegration()
    env = await test_instance.setup_test_environment()
    await test_instance.test_conversation_memory_preservation(env)


if __name__ == "__main__":
    # Run basic test
    asyncio.run(run_single_test())
