"""
Tools for the Workflow Agent, including RAG tools.
"""
import asyncio
from typing import Any, Dict, List

import structlog

from ..core.vector_store import SupabaseVectorStore
from .state import RAGContext, RetrievedDocument, WorkflowState

logger = structlog.get_logger()


class RAGTool:
    """A tool for Retrieval-Augmented Generation that updates the workflow state."""

    def __init__(self):
        self.vector_store = SupabaseVectorStore()

    async def retrieve_knowledge(
        self, state: WorkflowState, query: str, top_k: int = 5
    ) -> WorkflowState:
        """
        Retrieves knowledge from a vector store and updates the state.

        Args:
            state: The current workflow state.
            query: The query to search for.
            top_k: The number of documents to retrieve.

        Returns:
            The updated workflow state.
        """
        logger.info("Retrieving knowledge from Supabase", query=query)

        # 1. Call the real vector store function
        retrieved_entries = await self.vector_store.similarity_search(query, max_results=top_k)

        # 2. Convert NodeKnowledgeEntry objects to RetrievedDocument typed dicts
        retrieved_docs = [
            RetrievedDocument(
                id=entry.id,
                content=entry.content,
                metadata=entry.metadata,
                similarity=entry.similarity,
            )
            for entry in retrieved_entries
        ]

        # 3. Update the WorkflowState
        if "rag" not in state or state["rag"] is None:
            state["rag"] = RAGContext(query="", results=[])

        state["rag"]["query"] = query
        state["rag"]["results"] = retrieved_docs

        logger.info("Updated state with RAG context", num_retrieved=len(retrieved_docs))

        return state
