#!/usr/bin/env python3
"""
Test the RAG system with real queries
"""

from src.rag_service import RAGService


def test_rag_queries():
    """Test RAG with different queries"""

    print("🔍 Testing RAG System")
    print("=" * 50)

    rag = RAGService()

    # Test queries
    test_queries = [
        "What is slack node",
        "What is an AI agent node",
        "How do trigger nodes work",
        "What types of memory nodes are available",
    ]

    for query in test_queries:
        print(f"\n📝 Query: {query}")
        print("-" * 30)

        try:
            # Get context from RAG
            context = rag.get_relevant_context(query)

            if "No relevant context found" in context:
                print("❌ No context found")
            else:
                print("✅ Context retrieved!")
                # Show first 200 characters
                preview = context[:200] + "..." if len(context) > 200 else context
                print(f"Preview: {preview}")

        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n🎯 Summary:")
    print("If you see '✅ Context retrieved!' for any query, your RAG system is working!")


if __name__ == "__main__":
    test_rag_queries()
