#!/usr/bin/env python3
"""
RAG Comparison Demo

This script demonstrates the difference between using RAG (Retrieval-Augmented Generation)
and not using RAG when answering questions about workflow nodes.

The demo uses a LangGraph workflow that:
1. Processes the same query through a RAG-enabled node
2. Processes the same query through a non-RAG node
3. Compares the two responses

Usage:
    python demo.py
"""

import asyncio

from src.workflow import RAGComparisonWorkflow


def print_separator(title: str):
    """Print a formatted separator"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_subsection(title: str):
    """Print a formatted subsection"""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")


def main():
    print_separator("RAG Comparison Demo")
    print("This demo compares responses from RAG-enabled vs non-RAG nodes")

    # Sample queries to test
    sample_queries = [
        {"query": "What is an AI_AGENT_NODE and how does it work?", "node_type": "AI_AGENT_NODE"},
        {
            "query": "How do I configure a trigger node for chat messages?",
            "node_type": "TRIGGER_NODE",
        },
        {"query": "What are the capabilities of a memory node?", "node_type": "MEMORY_NODE"},
    ]

    # Initialize workflow
    workflow = RAGComparisonWorkflow()

    # Process each query
    for i, query_data in enumerate(sample_queries, 1):
        print_separator(f"Query {i}")
        print(f"Question: {query_data['query']}")
        print(f"Node Type Filter: {query_data['node_type']}")

        try:
            # Run the workflow
            result = workflow.run(query_data["query"], query_data["node_type"])

            # Display results
            print_subsection("Response WITH RAG")
            print(result.get("response_with_rag", "No response generated"))

            print_subsection("Response WITHOUT RAG")
            print(result.get("response_without_rag", "No response generated"))

            print_subsection("Retrieved Context")
            context = result.get("context", "No context retrieved")
            if len(context) > 500:
                print(f"{context[:500]}...")
            else:
                print(context)

            print_subsection("Comparison Analysis")
            print(result.get("comparison", "No comparison available"))

        except Exception as e:
            print(f"Error processing query: {e}")
            print("Please check your environment variables and Supabase setup")

    print_separator("Demo Complete")
    print("Key takeaways:")
    print("1. RAG provides more specific, contextual information")
    print("2. Non-RAG responses rely on general training data")
    print("3. RAG responses are more accurate for domain-specific queries")


if __name__ == "__main__":
    main()
