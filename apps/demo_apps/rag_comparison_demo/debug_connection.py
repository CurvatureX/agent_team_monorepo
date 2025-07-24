#!/usr/bin/env python3
"""
Debug script to test Supabase connection and diagnose RAG issues
"""

import os

from dotenv import load_dotenv

from supabase import create_client

load_dotenv()


def test_supabase_connection():
    """Test Supabase connection and diagnose issues"""

    print("🔧 Supabase Connection Debug")
    print("=" * 50)

    # Check environment variables
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    print(f"SUPABASE_URL: {url[:50]}... (truncated)" if url else "❌ SUPABASE_URL not set")
    print(f"SUPABASE_KEY: {key[:20]}... (truncated)" if key else "❌ SUPABASE_KEY not set")
    print()

    if not url or not key:
        print("❌ Missing environment variables. Please check your .env file.")
        return False

    # Test connection
    try:
        print("🔌 Testing Supabase connection...")
        supabase = create_client(url, key)

        # Test basic query
        print("📊 Testing database query...")
        response = supabase.table("node_knowledge_vectors").select("*").execute()

        count = len(response.data) if response.data else 0
        print(f"✅ Connection successful! Found {count} records in node_knowledge_vectors table")

        # Test if the match function exists
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
            print("✅ Vector search function is working!")
            return True

        except Exception as func_error:
            print(f"❌ Vector search function error: {func_error}")
            print("💡 You may need to create the match_node_knowledge function in Supabase")
            return False

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("1. Check your SUPABASE_URL - it should look like: https://your-project.supabase.co")
        print("2. Check your SUPABASE_KEY - use the 'anon public' key from your Supabase dashboard")
        print("3. Make sure your Supabase project is active and not paused")
        print("4. Verify the node_knowledge_vectors table exists in your database")
        return False


def test_openai_connection():
    """Test OpenAI connection"""
    print("\n🤖 OpenAI Connection Debug")
    print("=" * 50)

    api_key = os.getenv("OPENAI_API_KEY")
    print(
        f"OPENAI_API_KEY: {api_key[:20]}... (truncated)" if api_key else "❌ OPENAI_API_KEY not set"
    )

    if not api_key:
        print("❌ Missing OpenAI API key")
        return False

    try:
        import openai

        client = openai.OpenAI(api_key=api_key)

        # Test embedding generation
        print("🔮 Testing embedding generation...")
        response = client.embeddings.create(model="text-embedding-ada-002", input="test")
        print("✅ OpenAI connection successful!")
        return True

    except Exception as e:
        print(f"❌ OpenAI connection failed: {e}")
        return False


if __name__ == "__main__":
    supabase_ok = test_supabase_connection()
    openai_ok = test_openai_connection()

    print("\n📋 Summary:")
    print(f"Supabase: {'✅ Working' if supabase_ok else '❌ Issues found'}")
    print(f"OpenAI: {'✅ Working' if openai_ok else '❌ Issues found'}")

    if supabase_ok and openai_ok:
        print("\n🎉 All connections working! Your RAG system should work now.")
    else:
        print("\n🛠️ Please fix the issues above for the RAG system to work properly.")
