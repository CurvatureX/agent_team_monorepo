#!/usr/bin/env python3
"""
Test script specifically for service role key validation
"""

import base64
import json
import os

from dotenv import load_dotenv

from supabase import create_client

load_dotenv()


def decode_jwt_role(token):
    """Decode JWT token to check the role"""
    try:
        # JWT has 3 parts separated by dots
        parts = token.split(".")
        if len(parts) != 3:
            return "Invalid JWT format"

        # Decode the payload (second part)
        payload = parts[1]
        # Add padding if needed
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.b64decode(payload)
        data = json.loads(decoded)
        return data.get("role", "unknown")
    except Exception as e:
        return f"Error decoding: {e}"


def test_service_role_key():
    """Test the service role key functionality"""

    print("🔧 Service Role Key Test")
    print("=" * 50)

    # Check environment variables
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("❌ Missing environment variables")
        return False

    # Check key type
    role = decode_jwt_role(key)
    print(f"🔑 Key role: {role}")

    if role != "service_role":
        print("⚠️ WARNING: You're not using a service_role key!")
        print("For server-side operations, service_role key is recommended.")
        if role == "anon":
            print("Current key is 'anon' - this might work but has limitations.")
    else:
        print("✅ Perfect! Using service_role key for full database access.")

    # Test connection
    try:
        print("\n🔌 Testing database connection...")
        supabase = create_client(url, key)

        # Test table access
        print("📊 Testing table access...")
        response = supabase.table("node_knowledge_vectors").select("*").limit(1).execute()

        if response.data is not None:
            count = len(response.data)
            print(f"✅ Table access successful! Sample size: {count}")
        else:
            print("❌ No data returned - table might be empty or not exist")

        # Test if we can create the table (service role should have this permission)
        print("🔧 Testing admin permissions...")
        try:
            # Try to query table schema
            schema_query = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'node_knowledge_vectors'
            LIMIT 5;
            """
            response = supabase.rpc("exec", {"sql": schema_query}).execute()
            print("✅ Admin permissions confirmed - can query schema")
        except Exception as e:
            print(f"ℹ️ Admin check result: {e}")

        # Test the vector search function
        print("🔍 Testing vector search function...")
        try:
            test_embedding = [0.1] * 1536  # Dummy embedding
            response = supabase.rpc(
                "match_node_knowledge",
                {
                    "query_embedding": test_embedding,
                    "match_threshold": 0.1,
                    "match_count": 1,
                },
            ).execute()
            print("✅ Vector search function exists and is callable!")
            return True

        except Exception as func_error:
            print(f"❌ Vector search function error: {func_error}")
            print("💡 You need to create the match_node_knowledge function")
            return False

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    success = test_service_role_key()

    if not success:
        print("\n🛠️ Next steps:")
        print("1. Make sure you're using the SERVICE_ROLE key from Supabase dashboard")
        print("2. Verify the node_knowledge_vectors table exists")
        print("3. Create the match_node_knowledge function (SQL provided in README)")
    else:
        print("\n🎉 Service role key is working correctly!")
