#!/usr/bin/env python3
"""
Check your MCP API keys configuration
"""

import sys

sys.path.append(".")

from app.core.config import get_settings
from app.middleware.auth import mcp_authenticator


def check_mcp_configuration():
    """Check the current MCP API keys configuration."""
    print("🔍 Checking MCP API Key Configuration")
    print("=" * 50)

    settings = get_settings()

    # Check if MCP is enabled
    print(f"MCP API Enabled: {settings.MCP_API_ENABLED}")
    print(f"MCP API Key Required: {settings.MCP_API_KEY_REQUIRED}")
    print(f"Debug Mode: {settings.DEBUG}")

    # Show configured API keys from settings
    print(f"\n📋 Configured API Keys from Settings:")
    if hasattr(settings, "MCP_API_KEYS") and settings.MCP_API_KEYS:
        for key_id, config in settings.MCP_API_KEYS.items():
            print(f"   🔑 {key_id}:")
            print(f"      Client Name: {config.get('client_name', 'Unknown')}")
            print(f"      Scopes: {config.get('scopes', [])}")
            print(f"      Rate Limit Tier: {config.get('rate_limit_tier', 'standard')}")
            print(f"      Active: {config.get('active', True)}")
    else:
        print("   No API keys configured in settings")

    # Show loaded API keys from authenticator
    print(f"\n🔐 Loaded API Keys in Authenticator:")
    if mcp_authenticator.api_keys:
        for api_key, key_obj in mcp_authenticator.api_keys.items():
            print(f"   🔑 API Key: {api_key}")
            print(f"      Client Name: {key_obj.client_name}")
            print(f"      Scopes: {key_obj.scopes}")
            print(f"      Rate Limit Tier: {key_obj.rate_limit_tier}")
            print(f"      Active: {key_obj.active}")
            print()
    else:
        print("   No API keys loaded")

    # Test API key verification
    print("🧪 Testing API Key Verification:")
    test_keys = ["dev_default", "test-api-key-12345", "invalid-key"]

    for test_key in test_keys:
        result = mcp_authenticator.verify_api_key(test_key)
        if result:
            print(f"   ✅ '{test_key}' -> Valid ({result.client_name})")
        else:
            print(f"   ❌ '{test_key}' -> Invalid")

    # Show valid API keys for your usage
    print(f"\n🎯 Valid API Keys for MCP Usage:")
    valid_keys = list(mcp_authenticator.api_keys.keys())
    if valid_keys:
        print("   You can use any of these keys with X-API-Key header:")
        for key in valid_keys:
            key_obj = mcp_authenticator.api_keys[key]
            print(f"   🔑 {key} (scopes: {', '.join(key_obj.scopes)})")

        print(f"\n💡 Example curl command:")
        example_key = valid_keys[0]
        print(f'   curl -H "X-API-Key: {example_key}" \\')
        print(f"        http://localhost:8000/api/mcp/health")

        print(f"\n💡 Example MCP tool invocation:")
        print(f"   curl -X POST \\")
        print(f'        -H "X-API-Key: {example_key}" \\')
        print(f'        -H "Content-Type: application/json" \\')
        print(f"        -d '{{")
        print(f'          "name": "search_notion",')
        print(f'          "arguments": {{')
        print(f'            "access_token": "your-notion-token",')
        print(f'            "query": "test"')
        print(f"          }}")
        print(f"        }}' \\")
        print(f"        http://localhost:8000/api/mcp/invoke")
    else:
        print("   ❌ No valid API keys available!")
        print("   This means MCP authentication will fail.")


if __name__ == "__main__":
    check_mcp_configuration()
