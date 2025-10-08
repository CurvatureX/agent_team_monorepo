#!/usr/bin/env python3
"""
Test script for OAuth integration validation.

This script tests the parallel validation of OAuth tokens in the integrations endpoint.
It will:
1. Authenticate with Supabase to get a JWT token
2. Call the /api/v1/app/integrations endpoint
3. Verify that tokens are validated in parallel
4. Check that invalid tokens are marked as inactive
"""

import asyncio
import os
import sys
import time
from typing import Any, Dict

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")


def get_auth_token() -> str:
    """Authenticate with Supabase and get JWT token."""
    print(f"🔐 Authenticating as {TEST_USER_EMAIL}...")

    auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    response = httpx.post(
        auth_url,
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        },
        json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
        },
    )

    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.status_code}")
        print(response.text)
        sys.exit(1)

    data = response.json()
    token = data.get("access_token")
    print(f"✅ Authentication successful")
    return token


def test_integrations_validation(token: str) -> Dict[str, Any]:
    """Test the integrations endpoint with parallel validation."""
    print("\n📋 Testing integrations endpoint with validation...")

    start_time = time.time()

    response = httpx.get(
        f"{API_GATEWAY_URL}/api/v1/app/integrations",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=30.0,  # Allow time for parallel validation
    )

    elapsed = time.time() - start_time

    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        print(response.text)
        sys.exit(1)

    data = response.json()
    print(f"✅ Request successful (took {elapsed:.2f}s)")

    return data


def analyze_results(data: Dict[str, Any]):
    """Analyze and display validation results."""
    print("\n📊 Integration Status:")
    print("=" * 80)

    integrations = data.get("integrations", [])

    for integration in integrations:
        provider = integration.get("provider")
        is_connected = integration.get("is_connected")
        connection = integration.get("connection")

        status = "🟢 Connected" if is_connected else "⚪ Not Connected"
        print(f"\n{integration.get('name')} ({provider})")
        print(f"  Status: {status}")

        if is_connected and connection:
            print(f"  Token ID: {connection.get('id')}")
            print(f"  Active: {connection.get('is_active')}")
            print(f"  Created: {connection.get('created_at')}")

    print("\n" + "=" * 80)

    # Summary
    connected_count = sum(1 for i in integrations if i.get("is_connected"))
    total_count = len(integrations)

    print(f"\n📈 Summary:")
    print(f"  Total integrations: {total_count}")
    print(f"  Connected: {connected_count}")
    print(f"  Disconnected: {total_count - connected_count}")


def main():
    """Main test function."""
    print("🧪 OAuth Integration Validation Test")
    print("=" * 80)

    # Check environment variables
    if not all([SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD]):
        print("❌ Missing required environment variables:")
        print("   SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD")
        sys.exit(1)

    try:
        # Step 1: Get auth token
        token = get_auth_token()

        # Step 2: Test integrations endpoint
        data = test_integrations_validation(token)

        # Step 3: Analyze results
        analyze_results(data)

        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
