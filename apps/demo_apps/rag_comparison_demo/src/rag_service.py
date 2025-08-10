import os
from typing import Any, Dict, List

import openai
from src.config import Config

from supabase import Client, create_client


class RAGService:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        self.supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for the given text using OpenAI"""
        response = self.openai_client.embeddings.create(model=Config.EMBEDDING_MODEL, input=text)
        return response.data[0].embedding

    def similarity_search(self, query: str, node_type: str = None) -> List[Dict[str, Any]]:
        """Search for similar node knowledge using vector similarity"""
        query_embedding = self.generate_embedding(query)

        # Build the RPC call for similarity search
        rpc_params = {
            "query_embedding": query_embedding,
            "match_threshold": Config.SIMILARITY_THRESHOLD,
            "match_count": Config.MAX_RESULTS,
        }

        if node_type:
            rpc_params["node_type_filter"] = node_type

        # Use Supabase RPC for vector similarity search
        try:
            response = self.supabase.rpc("match_node_knowledge", rpc_params).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error in similarity search: {e}")
            return []

    def get_relevant_context(self, query: str, node_type: str = None) -> str:
        """Get relevant context for the query from the knowledge base"""
        search_results = self.similarity_search(query, node_type)

        if not search_results:
            return "No relevant context found in the knowledge base."

        context_parts = []
        for result in search_results:
            context_parts.append(
                f"Node Type: {result.get('node_type', 'Unknown')}\n"
                f"Title: {result.get('title', 'Unknown')}\n"
                f"Description: {result.get('description', 'No description')}\n"
                f"Content: {result.get('content', 'No content')}\n"
                f"Similarity: {result.get('similarity', 0):.3f}\n"
                f"---"
            )

        return "\n".join(context_parts)
