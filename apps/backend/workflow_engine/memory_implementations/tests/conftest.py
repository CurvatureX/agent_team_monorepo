"""
Pytest configuration and fixtures for memory integration tests.
"""

import asyncio
import logging
import os
from typing import Any, Dict

import pytest

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture."""
    return {
        "supabase_url": os.getenv("SUPABASE_URL"),
        "supabase_key": os.getenv("SUPABASE_SECRET_KEY"),
        "openai_key": os.getenv("OPENAI_API_KEY"),
        "test_timeout": 30,  # seconds
        "max_retries": 3,
    }


@pytest.fixture
def skip_if_no_credentials(test_config):
    """Skip test if required credentials are not available."""
    required_vars = ["supabase_url", "supabase_key", "openai_key"]
    missing_vars = [var for var in required_vars if not test_config.get(var)]

    if missing_vars:
        pytest.skip(f"Required environment variables not set: {missing_vars}")

    return test_config


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring external services"
    )
    config.addinivalue_line("markers", "llm: mark test as requiring LLM API calls")
    config.addinivalue_line("markers", "memory: mark test as testing memory functionality")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add integration marker to integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Add llm marker to LLM tests
        if "llm" in item.nodeid.lower():
            item.add_marker(pytest.mark.llm)

        # Add memory marker to memory tests
        if "memory" in item.nodeid.lower():
            item.add_marker(pytest.mark.memory)


# Custom assertion helpers
def assert_memory_context_valid(context: Dict[str, Any], expected_type: str = None):
    """Assert that memory context has valid structure."""
    assert isinstance(context, dict), "Memory context should be a dictionary"

    if expected_type:
        assert (
            context.get("context_type") == expected_type
        ), f"Expected context type {expected_type}, got {context.get('context_type')}"

    # Check for required fields based on context type
    context_type = context.get("context_type", "")

    if context_type == "conversation_buffer":
        assert "messages" in context, "Conversation context should have messages"
        assert isinstance(context["messages"], list), "Messages should be a list"

    elif context_type == "entity_context":
        assert "entity_summary" in context, "Entity context should have entity_summary"

    elif context_type == "knowledge_facts":
        assert "facts_summary" in context, "Knowledge context should have facts_summary"

    elif context_type == "graph_relationships":
        assert "relationship_summary" in context, "Graph context should have relationship_summary"


def assert_llm_response_uses_context(response: str, expected_terms: list, min_matches: int = 1):
    """Assert that LLM response uses context by checking for expected terms."""
    response_lower = response.lower()
    matched_terms = [term for term in expected_terms if term.lower() in response_lower]

    assert len(matched_terms) >= min_matches, (
        f"LLM response should contain at least {min_matches} of {expected_terms}. "
        f"Found: {matched_terms}. Response: {response[:200]}..."
    )


# Export assertion helpers
__all__ = ["assert_memory_context_valid", "assert_llm_response_uses_context"]
