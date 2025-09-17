"""
Basic Usage Examples for Memory Implementations.

This file demonstrates how to use each memory type for LLM context enhancement.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict

# Import memory implementations
from ..conversation_buffer import ConversationBufferMemory
from ..conversation_summary import ConversationSummaryMemory
from ..entity_memory import EntityMemory
from ..key_value_store import KeyValueStoreMemory
from ..vector_database import VectorDatabaseMemory
from ..working_memory import WorkingMemory


async def conversation_buffer_example():
    """Example: Using Conversation Buffer Memory for recent chat history."""
    print("=== Conversation Buffer Memory Example ===")

    config = {
        "redis_url": "redis://localhost:6379",
        "supabase_url": "YOUR_SUPABASE_URL",
        "supabase_key": "YOUR_SUPABASE_KEY",
        "window_size": 10,
        "window_type": "turns",
        "ttl_seconds": 3600,
    }

    buffer_memory = ConversationBufferMemory(config)
    await buffer_memory.initialize()

    session_id = "chat_session_123"

    # Store conversation messages
    messages = [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you! How can I help you today?"},
        {
            "role": "user",
            "content": "I'm working on a Python project and need help with async programming.",
        },
        {
            "role": "assistant",
            "content": "I'd be happy to help with async programming! What specific aspect are you working on?",
        },
    ]

    for i, msg in enumerate(messages):
        result = await buffer_memory.store(
            {
                "session_id": session_id,
                "user_id": "user_456",
                **msg,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        print(f"Stored message {i+1}: {result['stored']}")

    # Get context for LLM
    context = await buffer_memory.get_context({"session_id": session_id})
    print(f"Context contains {len(context['messages'])} messages")
    print(f"Total tokens: {context['total_tokens']}")

    # Format for LLM
    formatted_messages = context["messages"]
    print("LLM Context Messages:")
    for msg in formatted_messages:
        print(f"  {msg['role']}: {msg['content']}")

    print()


async def conversation_summary_example():
    """Example: Using Conversation Summary Memory for optimal LLM context."""
    print("=== Conversation Summary Memory Example ===")

    config = {
        "redis_url": "redis://localhost:6379",
        "supabase_url": "YOUR_SUPABASE_URL",
        "supabase_key": "YOUR_SUPABASE_KEY",
        "google_api_key": "YOUR_GOOGLE_API_KEY",
        "buffer_window_size": 5,
        "summary_context_weight": 0.3,  # 30% summary, 70% buffer
        "max_total_tokens": 2000,
        "auto_summarize": True,
    }

    hybrid_memory = ConversationSummaryMemory(config)
    await hybrid_memory.initialize()

    session_id = "chat_session_123"

    # Store a new message (will auto-summarize if needed)
    result = await hybrid_memory.store(
        {
            "session_id": session_id,
            "user_id": "user_456",
            "role": "user",
            "content": "Let's discuss the implementation details of the async code.",
        }
    )

    print(f"Message stored: {result['stored']}")
    print(f"Summary generated: {result['summary_generated']}")

    # Get optimized context for LLM
    context = await hybrid_memory.get_context(
        {"session_id": session_id, "context_strategy": "balanced", "prioritize_recency": True}
    )

    print(f"Hybrid context generated using: {context['hybrid_info']['composition_method']}")
    print(f"Buffer messages: {context['hybrid_info']['buffer_messages_count']}")
    print(f"Has summary: {context['hybrid_info']['has_summary']}")
    print(f"Total estimated tokens: {context['hybrid_info']['total_estimated_tokens']}")

    # This context is optimized for LLM consumption
    llm_context = {
        "recent_messages": context.get("messages", []),
        "background_summary": context.get("summary", ""),
        "key_points": context.get("key_points", []),
        "entities": context.get("entities", []),
    }

    print()


async def vector_database_example():
    """Example: Using Vector Database for semantic search and RAG."""
    print("=== Vector Database Memory Example ===")

    config = {
        "supabase_url": "YOUR_SUPABASE_URL",
        "supabase_key": "YOUR_SUPABASE_KEY",
        "openai_api_key": "YOUR_OPENAI_API_KEY",
        "embedding_model": "text-embedding-3-small",
        "similarity_threshold": 0.7,
        "max_results": 3,
    }

    vector_memory = VectorDatabaseMemory(config)
    await vector_memory.initialize()

    collection_name = "knowledge_base"

    # Store knowledge documents
    documents = [
        {
            "text": "Python async/await syntax allows for asynchronous programming. Use async def to define coroutines.",
            "metadata": {"topic": "python", "type": "tutorial", "difficulty": "beginner"},
        },
        {
            "text": "AsyncIO is Python's built-in library for writing concurrent code using async/await syntax.",
            "metadata": {"topic": "python", "type": "documentation", "difficulty": "intermediate"},
        },
        {
            "text": "Coroutines are functions defined with async def that can be paused and resumed.",
            "metadata": {"topic": "python", "type": "concept", "difficulty": "beginner"},
        },
    ]

    print("Storing knowledge documents...")
    for i, doc in enumerate(documents):
        result = await vector_memory.store(
            {"text": doc["text"], "collection_name": collection_name, "metadata": doc["metadata"]}
        )
        print(f"Stored document {i+1}: {result['stored']}")

    # Search for relevant context
    query = "How do I use async functions in Python?"
    context = await vector_memory.get_context(
        {
            "query": query,
            "collection_name": collection_name,
            "similarity_threshold": 0.6,
            "max_results": 2,
        }
    )

    print(f"\nSearch results for: '{query}'")
    print(f"Found {len(context['results'])} relevant documents:")

    for result in context["results"]:
        print(f"  - Similarity: {result['similarity']:.3f}")
        print(f"    Text: {result['text']}")
        print(f"    Topic: {result['metadata'].get('topic', 'unknown')}")

    # Use context_text for LLM prompt
    llm_prompt = f"""
    Based on the following relevant information:

    {context['context_text']}

    Answer the user's question: {query}
    """

    print()


async def working_memory_example():
    """Example: Using Working Memory for multi-step reasoning."""
    print("=== Working Memory Example ===")

    config = {
        "redis_url": "redis://localhost:6379",
        "ttl_seconds": 1800,  # 30 minutes
        "capacity_limit": 50,
        "eviction_policy": "importance",
        "enable_reasoning_chain": True,
    }

    working_memory = WorkingMemory(config)
    await working_memory.initialize()

    namespace = "problem_solving_session"

    # Store reasoning steps
    steps = [
        {
            "key": "problem_definition",
            "value": "User wants to implement async file processing in Python",
            "importance": 0.9,
            "reasoning_step": "Identified the core problem",
        },
        {
            "key": "requirements",
            "value": ["Process multiple files", "Handle errors gracefully", "Show progress"],
            "importance": 0.8,
            "reasoning_step": "Gathered requirements",
        },
        {
            "key": "approach",
            "value": "Use asyncio.gather() with semaphore for concurrency control",
            "importance": 0.9,
            "reasoning_step": "Decided on technical approach",
        },
        {
            "key": "current_progress",
            "value": "Implemented basic async file reader, working on error handling",
            "importance": 0.7,
            "reasoning_step": "Tracked implementation progress",
        },
    ]

    print("Storing reasoning steps...")
    for step in steps:
        result = await working_memory.store({"namespace": namespace, **step})
        print(f"Stored {step['key']}: {result['stored']}")

    # Get context for LLM
    context = await working_memory.get_context(
        {
            "namespace": namespace,
            "max_items": 10,
            "min_importance": 0.6,
            "include_reasoning_chain": True,
        }
    )

    print(f"\nWorking memory context:")
    print(f"Active items: {context['active_items']}")
    print(f"Average importance: {context['avg_importance']:.2f}")

    print("Current state:")
    for key, value in context["current_state"].items():
        print(f"  {key}: {value['value']} (importance: {value['importance']:.2f})")

    print("Reasoning chain:")
    for step in context["reasoning_chain"][-3:]:  # Show last 3 steps
        print(f"  [{step['timestamp']}] {step['step']}")

    # Format for LLM
    llm_context = {
        "current_problem": context["current_state"].get("problem_definition", {}).get("value", ""),
        "requirements": context["current_state"].get("requirements", {}).get("value", []),
        "chosen_approach": context["current_state"].get("approach", {}).get("value", ""),
        "progress": context["current_state"].get("current_progress", {}).get("value", ""),
        "reasoning_history": [step["step"] for step in context["reasoning_chain"]],
    }

    print()


async def key_value_store_example():
    """Example: Using Key-Value Store for user preferences and settings."""
    print("=== Key-Value Store Memory Example ===")

    config = {
        "redis_url": "redis://localhost:6379",
        "supabase_url": "YOUR_SUPABASE_URL",
        "supabase_key": "YOUR_SUPABASE_KEY",
        "namespace": "user_context",
        "serialize_json": True,
        "compression": False,
        "sync_to_postgres": True,
    }

    kv_memory = KeyValueStoreMemory(config)
    await kv_memory.initialize()

    user_id = "user_456"

    # Store user preferences
    preferences = {
        "theme": "dark",
        "language": "en",
        "code_style": "python",
        "difficulty_level": "intermediate",
        "preferred_explanation_style": "detailed_with_examples",
    }

    result = await kv_memory.store(
        {
            "key": f"preferences",
            "value": preferences,
            "namespace": user_id,
            "metadata": {
                "category": "user_settings",
                "last_updated": datetime.utcnow().isoformat(),
            },
        }
    )
    print(f"Stored preferences: {result['stored']}")

    # Store conversation context
    conversation_context = {
        "current_topic": "async programming",
        "expertise_level": "learning",
        "last_question_type": "implementation",
        "preferred_examples": "real_world_scenarios",
    }

    result = await kv_memory.store(
        {
            "key": "conversation_context",
            "value": conversation_context,
            "namespace": user_id,
            "ttl_seconds": 7200,  # 2 hours
            "metadata": {"category": "session_data"},
        }
    )
    print(f"Stored conversation context: {result['stored']}")

    # Get context for LLM
    context = await kv_memory.get_context({"namespace": user_id, "max_items": 10})

    print(f"\nUser context data:")
    for key, value in context["context_data"].items():
        print(f"  {key}: {type(value).__name__} data")
        if isinstance(value, dict) and len(value) <= 5:
            for k, v in value.items():
                print(f"    {k}: {v}")

    # Format for LLM
    llm_context = {
        "user_preferences": context["context_data"].get("preferences", {}),
        "current_session": context["context_data"].get("conversation_context", {}),
    }

    print()


async def entity_memory_example():
    """Example: Using Entity Memory for tracking people, organizations, etc."""
    print("=== Entity Memory Example ===")

    config = {
        "supabase_url": "YOUR_SUPABASE_URL",
        "supabase_key": "YOUR_SUPABASE_KEY",
        "openai_api_key": "YOUR_OPENAI_API_KEY",
        "entity_types": ["person", "organization", "location", "technology", "concept"],
        "extraction_model": "gpt-4o-mini",
        "relationship_tracking": True,
        "importance_scoring": True,
    }

    entity_memory = EntityMemory(config)
    await entity_memory.initialize()

    # Analyze conversation content for entities
    content = """
    I work at Google as a software engineer in Mountain View, California.
    My team is developing new AI features using TensorFlow and Python.
    We recently started using AsyncIO for better performance in our applications.
    My colleague Sarah Smith from the ML team has been helping us optimize the models.
    """

    result = await entity_memory.store(
        {
            "content": content,
            "context": {"session_id": "chat_123", "topic": "work_discussion"},
            "user_id": "user_456",
        }
    )

    print(f"Processed {result['entities_processed']} entities")
    print(f"Stored {result['entities_stored']} new entities")
    print(f"Updated {result['entities_updated']} existing entities")
    print(f"Created {result['relationships_created']} relationships")

    # Get entity context for LLM
    context = await entity_memory.get_context(
        {
            "content": "Tell me about my work setup and the technologies I use",
            "user_id": "user_456",
            "max_entities": 10,
            "include_relationships": True,
        }
    )

    print(f"\nEntity context:")
    print(f"Total entities: {context['total_entities']}")
    print(f"Entity summary: {context['entity_summary']}")

    print("Key entities:")
    for entity in context["entities"][:5]:
        print(f"  - {entity['name']} ({entity['type']}) - Importance: {entity['importance']:.2f}")
        if entity.get("attributes"):
            print(f"    Attributes: {entity['attributes']}")

    if context["relationships"]:
        print("Relationships:")
        for rel in context["relationships"][:3]:
            print(f"  - {rel['source']} {rel['relationship']} {rel['target']}")

    print()


async def run_all_examples():
    """Run all memory implementation examples."""
    print("🧠 Memory Implementations Examples\n")
    print("=" * 50)

    try:
        await conversation_buffer_example()
        await conversation_summary_example()
        await vector_database_example()
        await working_memory_example()
        await key_value_store_example()
        await entity_memory_example()

        print("✅ All examples completed successfully!")

    except Exception as e:
        print(f"❌ Example failed: {str(e)}")
        print("Note: Make sure to configure your API keys and database connections")


if __name__ == "__main__":
    asyncio.run(run_all_examples())
