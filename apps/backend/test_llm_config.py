#!/usr/bin/env python
"""Test script to verify LLM configuration"""

import os
import sys
sys.path.insert(0, '/Users/bytedance/personal/agent_team_monorepo/apps/backend')

# Print environment variables
print("=== Environment Variables ===")
print(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER')}")
print(f"OPENROUTER_API_KEY: {os.getenv('OPENROUTER_API_KEY', 'Not set')[:20]}...")
print(f"OPENROUTER_MODEL: {os.getenv('OPENROUTER_MODEL')}")
print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY', 'Not set')[:20]}...")
print(f"OPENAI_MODEL: {os.getenv('OPENAI_MODEL')}")
print(f"DEFAULT_MODEL_PROVIDER: {os.getenv('DEFAULT_MODEL_PROVIDER')}")
print(f"DEFAULT_MODEL_NAME: {os.getenv('DEFAULT_MODEL_NAME')}")

# Import and test LLMFactory
print("\n=== LLMFactory Configuration ===")
from workflow_agent.core.llm_provider import LLMConfig, LLMFactory

config = LLMConfig()
print(f"Provider: {config.provider}")
print(f"API Key: {config.get_api_key()[:20]}...")
print(f"Model: {config.get_model_name()}")
print(f"Base URL: {config.get_base_url()}")

# Try creating an LLM instance
print("\n=== Creating LLM Instance ===")
try:
    llm = LLMFactory.create_llm(temperature=0)
    print(f"LLM created successfully: {type(llm)}")
    print(f"Model name: {llm.model_name if hasattr(llm, 'model_name') else 'N/A'}")

    # Test with a simple prompt
    print("\n=== Testing LLM ===")
    response = llm.invoke("Say 'Hello, I'm working!' in 5 words or less.")
    print(f"Response: {response.content if hasattr(response, 'content') else response}")
except Exception as e:
    print(f"Error creating LLM: {e}")