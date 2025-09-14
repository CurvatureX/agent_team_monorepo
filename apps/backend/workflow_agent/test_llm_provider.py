#!/usr/bin/env python3
"""
Test script for LLM provider configuration
Tests both OpenAI and OpenRouter configurations
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_agent.core.llm_provider import LLMConfig, LLMFactory


async def test_openai_provider():
    """Test OpenAI provider configuration"""
    print("\n=== Testing OpenAI Provider ===")

    # Set environment for OpenAI
    os.environ["LLM_PROVIDER"] = "openai"

    config = LLMConfig()
    print(f"Provider: {config.provider}")
    print(f"Model: {config.get_model_name()}")
    print(f"Base URL: {config.get_base_url()}")

    try:
        llm = LLMFactory.create_llm(config)
        print("✅ OpenAI LLM created successfully")

        # Test a simple query
        response = await llm.ainvoke("Say 'Hello from OpenAI' in exactly 3 words")
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_openrouter_provider():
    """Test OpenRouter provider configuration"""
    print("\n=== Testing OpenRouter Provider ===")

    # Check if OpenRouter API key is configured
    if not os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY") == "your-openrouter-api-key-here":
        print("⚠️  OpenRouter API key not configured. Skipping test.")
        print("   To test OpenRouter, set OPENROUTER_API_KEY in .env file")
        return

    # Set environment for OpenRouter
    os.environ["LLM_PROVIDER"] = "openrouter"

    config = LLMConfig()
    print(f"Provider: {config.provider}")
    print(f"Model: {config.get_model_name()}")
    print(f"Base URL: {config.get_base_url()}")

    try:
        llm = LLMFactory.create_llm(config)
        print("✅ OpenRouter LLM created successfully")

        # Test a simple query
        response = await llm.ainvoke("Say 'Hello from OpenRouter' in exactly 3 words")
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_embedding_provider():
    """Test embedding provider configuration"""
    print("\n=== Testing Embedding Provider ===")

    config = LLMConfig()
    print(f"Embedding Provider: {config.embedding_provider}")
    print(f"Embedding Model: {config.embedding_model}")

    try:
        embeddings = LLMFactory.create_embedding_model(config)
        print("✅ Embedding model created successfully")

        # Test embedding generation
        test_text = "This is a test sentence for embedding."
        result = await embeddings.aembed_query(test_text)
        print(f"Embedding dimensions: {len(result)}")
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run all tests"""
    print("=" * 50)
    print("LLM Provider Configuration Test")
    print("=" * 50)

    # Load environment variables
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from: {env_path}")
    else:
        print(f"⚠️  No .env file found at: {env_path}")

    # Test OpenAI
    await test_openai_provider()

    # Test OpenRouter
    await test_openrouter_provider()

    # Test Embeddings
    await test_embedding_provider()

    print("\n" + "=" * 50)
    print("Test completed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())