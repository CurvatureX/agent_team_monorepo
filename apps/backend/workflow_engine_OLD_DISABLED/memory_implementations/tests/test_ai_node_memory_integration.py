"""
Integration tests for AI Agent nodes with memory port connections.

Tests the complete memory integration pipeline through AI node execution.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

import pytest

# Import node specifications and execution components
from shared.node_specs.base import ConnectionType, InputPortSpec, OutputPortSpec
from shared.node_specs.definitions.ai_agent_nodes import OPENAI_NODE_SPEC

# Import memory implementations
from workflow_engine.memory_implementations.conversation_buffer import ConversationBufferMemory
from workflow_engine.memory_implementations.entity_memory import EntityMemory
from workflow_engine.memory_implementations.knowledge_base import KnowledgeBaseMemory
from workflow_engine.memory_implementations.memory_context_merger import (
    MemoryContext,
    MemoryContextMerger,
    MemoryPriority,
)

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


# Mock classes for testing AI node execution
class MockNodeExecutionContext:
    """Mock execution context with memory connections."""

    def __init__(
        self, user_id: str, session_id: str, memory_connections: List[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.input_connections = memory_connections or []
        self.node_parameters = {}
        self.execution_id = str(uuid.uuid4())


class MockMemoryConnection:
    """Mock memory connection for testing."""

    def __init__(self, connection_type: str, memory_output: Dict[str, Any]):
        self.connection_type = connection_type
        self.output_data = memory_output


class AIAgentNodeMemoryExecutor:
    """Enhanced AI Agent Node executor with memory integration."""

    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.context_merger = MemoryContextMerger()

    async def execute(
        self, context: MockNodeExecutionContext, user_message: str, model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """Execute AI node with memory context enhancement."""
        try:
            # Extract memory contexts from input connections
            memory_contexts = self._extract_memory_contexts(context)

            # Enhance user message with memory context
            enhanced_messages = await self._enhance_with_memory_context(
                user_message, memory_contexts, context
            )

            # Make LLM call
            client = openai.AsyncOpenAI(api_key=self.openai_api_key)

            response = await client.chat.completions.create(
                model=model, messages=enhanced_messages, temperature=0.1, max_tokens=1000
            )

            llm_response = response.choices[0].message.content

            # Store interaction in memory if conversation memory is connected
            await self._store_interaction_in_memory(
                context, user_message, llm_response, memory_contexts
            )

            return {
                "success": True,
                "response": llm_response,
                "memory_contexts_used": len(memory_contexts),
                "enhanced_messages": enhanced_messages,
            }

        except Exception as e:
            logger.error(f"AI node execution failed: {e}")
            return {"success": False, "error": str(e), "response": f"Error: {str(e)}"}

    def _extract_memory_contexts(self, context: MockNodeExecutionContext) -> List[MemoryContext]:
        """Extract memory contexts from input connections."""
        memory_contexts = []

        for connection in context.input_connections:
            if connection.connection_type == ConnectionType.MEMORY:
                output_data = connection.output_data

                # Create memory context based on output data structure
                memory_context = MemoryContext(
                    content=self._format_memory_content(output_data),
                    source=output_data.get("context_type", "unknown"),
                    priority=self._determine_priority(output_data),
                    relevance_score=output_data.get("relevance_score", 0.5),
                    token_count=self._estimate_token_count(output_data),
                )

                memory_contexts.append(memory_context)

        return memory_contexts

    def _format_memory_content(self, memory_output: Dict[str, Any]) -> str:
        """Format memory output into readable content."""
        context_type = memory_output.get("context_type", "")

        if context_type == "conversation_buffer":
            messages = memory_output.get("messages", [])
            formatted_messages = []
            for msg in messages[-5:]:  # Last 5 messages
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                formatted_messages.append(f"{role}: {content}")
            return "\\n".join(formatted_messages)

        elif context_type == "entity_context":
            return memory_output.get("entity_summary", "")

        elif context_type == "knowledge_facts":
            return memory_output.get("facts_summary", "")

        elif context_type == "graph_relationships":
            return memory_output.get("relationship_summary", "")

        else:
            # Generic formatting
            return str(memory_output.get("summary", memory_output))

    def _determine_priority(self, memory_output: Dict[str, Any]) -> MemoryPriority:
        """Determine memory priority based on context type."""
        context_type = memory_output.get("context_type", "")

        if context_type == "conversation_buffer":
            return MemoryPriority.HIGH
        elif context_type in ["entity_context", "knowledge_facts"]:
            return MemoryPriority.MEDIUM
        else:
            return MemoryPriority.LOW

    def _estimate_token_count(self, memory_output: Dict[str, Any]) -> int:
        """Estimate token count for memory content."""
        content = self._format_memory_content(memory_output)
        return len(content) // 4  # Rough estimation

    async def _enhance_with_memory_context(
        self,
        user_message: str,
        memory_contexts: List[MemoryContext],
        context: MockNodeExecutionContext,
    ) -> List[Dict[str, str]]:
        """Enhance user message with memory context."""

        if not memory_contexts:
            return [{"role": "user", "content": user_message}]

        # Merge memory contexts
        merged_context = self.context_merger.merge_contexts(
            memory_contexts, user_message, merge_strategy="balanced"
        )

        # Create system message with memory context
        system_message = f"""You are an AI assistant with access to memory context. Use the following context to provide more personalized and informed responses:

{merged_context.get('merged_content', '')}

Remember to reference relevant information from this context when appropriate."""

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

    async def _store_interaction_in_memory(
        self,
        context: MockNodeExecutionContext,
        user_message: str,
        llm_response: str,
        memory_contexts: List[MemoryContext],
    ):
        """Store the interaction back in memory if conversation memory is available."""
        # This would typically update the conversation buffer
        # For testing, we'll just log the interaction
        logger.info(
            f"Interaction stored - User: {user_message[:50]}... LLM: {llm_response[:50]}..."
        )


class TestAINodeMemoryIntegration:
    """Test suite for AI node memory integration."""

    @pytest.fixture
    async def setup_test_environment(self):
        """Set up test environment."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session_id = f"session_{uuid.uuid4().hex[:8]}"

        # Check environment variables
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

        # Initialize AI node executor
        ai_executor = AIAgentNodeMemoryExecutor(openai_key)

        # Setup memories
        await conversation_memory._setup()
        await entity_memory._setup()
        await knowledge_memory._setup()

        return {
            "user_id": user_id,
            "session_id": session_id,
            "conversation_memory": conversation_memory,
            "entity_memory": entity_memory,
            "knowledge_memory": knowledge_memory,
            "ai_executor": ai_executor,
            "openai_key": openai_key,
        }

    @pytest.mark.asyncio
    async def test_ai_node_with_conversation_memory(self, setup_test_environment):
        """Test AI node execution with conversation memory connection."""
        env = await setup_test_environment
        conversation_memory = env["conversation_memory"]
        ai_executor = env["ai_executor"]
        user_id = env["user_id"]
        session_id = env["session_id"]

        # Store conversation history
        await conversation_memory.store(
            {"role": "user", "content": "My name is John and I'm a software developer."}
        )
        await conversation_memory.store(
            {
                "role": "assistant",
                "content": "Nice to meet you, John! What kind of software development do you focus on?",
            }
        )
        await conversation_memory.store(
            {"role": "user", "content": "I mainly work with Python and web frameworks like Django."}
        )
        await conversation_memory.store(
            {
                "role": "assistant",
                "content": "That's great! Django is an excellent framework for web development. Are you working on any specific projects?",
            }
        )

        # Get conversation context
        conv_context = await conversation_memory.get_context({"max_messages": 8})

        # Create memory connection
        memory_connection = MockMemoryConnection(
            connection_type=ConnectionType.MEMORY, memory_output=conv_context
        )

        # Create execution context with memory connection
        execution_context = MockNodeExecutionContext(
            user_id=user_id, session_id=session_id, memory_connections=[memory_connection]
        )

        # Execute AI node with memory
        user_message = "What programming language do I use and what's my profession?"
        result = await ai_executor.execute(execution_context, user_message)

        # Verify execution success
        assert result["success"], f"AI node execution failed: {result.get('error')}"

        # Verify memory context was used
        assert result["memory_contexts_used"] > 0, "Should have used memory context"

        # Verify response contains information from memory
        response = result["response"].lower()
        assert (
            "john" in response or "software developer" in response or "python" in response
        ), f"Response should contain information from conversation memory: {result['response']}"

        logger.info("✅ AI node with conversation memory test passed")

    @pytest.mark.asyncio
    async def test_ai_node_with_multiple_memory_types(self, setup_test_environment):
        """Test AI node execution with multiple memory connections."""
        env = await setup_test_environment
        conversation_memory = env["conversation_memory"]
        entity_memory = env["entity_memory"]
        knowledge_memory = env["knowledge_memory"]
        ai_executor = env["ai_executor"]
        user_id = env["user_id"]
        session_id = env["session_id"]

        # Store data in different memory types

        # Conversation memory
        await conversation_memory.store(
            {"role": "user", "content": "I'm working on a machine learning project."}
        )

        # Entity memory
        await entity_memory.store(
            {
                "text": "Machine learning is a subset of artificial intelligence. TensorFlow and PyTorch are popular ML frameworks.",
                "extract_entities": True,
            }
        )

        # Knowledge memory
        await knowledge_memory.store(
            {
                "content": "Neural networks are computing systems inspired by biological neural networks. Deep learning uses neural networks with many layers.",
                "domain": "machine_learning",
                "extract_facts": True,
            }
        )

        # Wait for processing
        await asyncio.sleep(3)

        # Get contexts from all memory types
        conv_context = await conversation_memory.get_context({"max_messages": 5})
        entity_context = await entity_memory.get_context(
            {"entities": ["machine learning", "TensorFlow", "PyTorch"]}
        )
        knowledge_context = await knowledge_memory.get_context(
            {"domain": "machine_learning", "query": "neural networks"}
        )

        # Create multiple memory connections
        memory_connections = [
            MockMemoryConnection(ConnectionType.MEMORY, conv_context),
            MockMemoryConnection(ConnectionType.MEMORY, entity_context),
            MockMemoryConnection(ConnectionType.MEMORY, knowledge_context),
        ]

        # Create execution context
        execution_context = MockNodeExecutionContext(
            user_id=user_id, session_id=session_id, memory_connections=memory_connections
        )

        # Execute AI node with multiple memory types
        user_message = (
            "Can you explain neural networks and recommend a good framework for my ML project?"
        )
        result = await ai_executor.execute(execution_context, user_message)

        # Verify execution success
        assert result["success"], f"AI node execution failed: {result.get('error')}"

        # Verify multiple memory contexts were used
        assert result["memory_contexts_used"] >= 2, "Should have used multiple memory contexts"

        # Verify response incorporates information from different memory types
        response = result["response"].lower()
        ml_terms = ["neural network", "tensorflow", "pytorch", "machine learning", "deep learning"]
        used_terms = [term for term in ml_terms if term in response]

        assert (
            len(used_terms) >= 2
        ), f"Response should incorporate information from multiple memory types. Used terms: {used_terms}. Response: {result['response']}"

        logger.info("✅ AI node with multiple memory types test passed")

    @pytest.mark.asyncio
    async def test_ai_node_memory_context_prioritization(self, setup_test_environment):
        """Test memory context prioritization in AI node execution."""
        env = await setup_test_environment
        conversation_memory = env["conversation_memory"]
        entity_memory = env["entity_memory"]
        ai_executor = env["ai_executor"]
        user_id = env["user_id"]
        session_id = env["session_id"]

        # Store high-priority conversation context
        await conversation_memory.store(
            {
                "role": "user",
                "content": "I need help with my urgent Python project deadline tomorrow.",
            }
        )
        await conversation_memory.store(
            {
                "role": "assistant",
                "content": "I understand this is urgent. What specific help do you need with your Python project?",
            }
        )

        # Store lower-priority entity context
        await entity_memory.store(
            {
                "text": "Python is a programming language created by Guido van Rossum. It was first released in 1991.",
                "extract_entities": True,
            }
        )

        # Wait for processing
        await asyncio.sleep(2)

        # Get contexts
        conv_context = await conversation_memory.get_context({"max_messages": 5})
        entity_context = await entity_memory.get_context({"entities": ["Python"]})

        # Create memory connections with different priorities
        memory_connections = [
            MockMemoryConnection(ConnectionType.MEMORY, conv_context),  # High priority
            MockMemoryConnection(ConnectionType.MEMORY, entity_context),  # Lower priority
        ]

        # Create execution context
        execution_context = MockNodeExecutionContext(
            user_id=user_id, session_id=session_id, memory_connections=memory_connections
        )

        # Execute AI node
        user_message = "What's the status of my project?"
        result = await ai_executor.execute(execution_context, user_message)

        # Verify execution success
        assert result["success"], f"AI node execution failed: {result.get('error')}"

        # Verify response prioritizes urgent context over historical facts
        response = result["response"].lower()

        # Should reference urgency/deadline more than historical Python facts
        urgency_terms = ["urgent", "deadline", "tomorrow", "help", "project"]
        historical_terms = ["guido", "1991", "created", "released"]

        urgency_matches = sum(1 for term in urgency_terms if term in response)
        historical_matches = sum(1 for term in historical_terms if term in response)

        # High-priority conversation context should be more prominent
        assert (
            urgency_matches >= historical_matches
        ), f"Should prioritize urgent conversation context. Response: {result['response']}"

        logger.info("✅ AI node memory context prioritization test passed")

    @pytest.mark.asyncio
    async def test_ai_node_memory_enhanced_workflow(self, setup_test_environment):
        """Test complete workflow with AI node and memory enhancement."""
        env = await setup_test_environment
        conversation_memory = env["conversation_memory"]
        entity_memory = env["entity_memory"]
        ai_executor = env["ai_executor"]
        user_id = env["user_id"]
        session_id = env["session_id"]

        # Simulate a multi-step workflow with memory accumulation
        workflow_steps = [
            {
                "user_input": "I'm Dr. Sarah Chen, a cardiologist at Stanford Hospital. I'm researching heart disease prevention.",
                "expected_memory": ["sarah chen", "cardiologist", "stanford", "heart disease"],
            },
            {
                "user_input": "I'm particularly interested in dietary factors that affect cardiovascular health.",
                "expected_memory": ["dietary", "cardiovascular", "health"],
            },
            {
                "user_input": "Can you summarize my research focus based on our conversation?",
                "expected_memory": ["research", "cardiologist", "heart disease", "dietary"],
            },
        ]

        for i, step in enumerate(workflow_steps):
            user_input = step["user_input"]

            # Store user input in conversation memory
            await conversation_memory.store({"role": "user", "content": user_input})

            # Extract entities from first input
            if i == 0:
                await entity_memory.store({"text": user_input, "extract_entities": True})
                await asyncio.sleep(2)  # Wait for entity extraction

            # Get memory contexts
            conv_context = await conversation_memory.get_context({"max_messages": 10})
            entity_context = await entity_memory.get_context(
                {"entities": ["Dr. Sarah Chen", "cardiologist", "Stanford Hospital"]}
            )

            # Create memory connections
            memory_connections = [MockMemoryConnection(ConnectionType.MEMORY, conv_context)]

            if entity_context.get("entity_summary"):
                memory_connections.append(
                    MockMemoryConnection(ConnectionType.MEMORY, entity_context)
                )

            # Create execution context
            execution_context = MockNodeExecutionContext(
                user_id=user_id, session_id=session_id, memory_connections=memory_connections
            )

            # Execute AI node
            result = await ai_executor.execute(execution_context, user_input)

            # Verify execution success
            assert result["success"], f"Step {i+1} failed: {result.get('error')}"

            # Store AI response in conversation memory
            await conversation_memory.store({"role": "assistant", "content": result["response"]})

            # For the final step, verify comprehensive memory usage
            if i == 2:
                response = result["response"].lower()
                expected_terms = step["expected_memory"]

                matched_terms = [term for term in expected_terms if term in response]

                assert (
                    len(matched_terms) >= 2
                ), f"Final response should reference multiple memory elements. Matched: {matched_terms}. Response: {result['response']}"

            logger.info(f"Workflow step {i+1} completed successfully")

        # Verify final conversation length
        final_context = await conversation_memory.get_context({"max_messages": 20})
        assert len(final_context["messages"]) == 6, "Should have 6 messages (3 user + 3 assistant)"

        logger.info("✅ AI node memory-enhanced workflow test passed")

    @pytest.mark.asyncio
    async def test_memory_node_specifications(self, setup_test_environment):
        """Test that AI agent node specifications include memory ports."""
        # Verify AI agent node spec has memory input port
        memory_input_port = None

        for input_port in OPENAI_NODE_SPEC.input_ports:
            if input_port.name == "memory":
                memory_input_port = input_port
                break

        assert memory_input_port is not None, "AI agent node should have memory input port"
        assert (
            memory_input_port.type == ConnectionType.MEMORY
        ), "Memory port should use MEMORY connection type"
        assert memory_input_port.max_connections == -1, "Should allow multiple memory connections"
        assert not memory_input_port.required, "Memory port should be optional"

        logger.info("✅ Memory node specifications test passed")


# Utility function for standalone testing
async def run_standalone_test():
    """Run a single test for debugging."""
    test_instance = TestAINodeMemoryIntegration()
    env = await test_instance.setup_test_environment()
    await test_instance.test_ai_node_with_conversation_memory(env)


if __name__ == "__main__":
    asyncio.run(run_standalone_test())
