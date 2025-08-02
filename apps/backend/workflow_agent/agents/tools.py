"""
Tools for the Workflow Agent, including RAG tools.
"""
import asyncio
from typing import Any, Dict, List

from .state import RAGContext, RetrievedDocument, WorkflowState
from core.logging_config import get_logger
from core.vector_store import SupabaseVectorStore

logger = get_logger(__name__)


class RAGTool:
    """A tool for Retrieval-Augmented Generation that updates the workflow state."""

    def __init__(self):
        try:
            self.vector_store = SupabaseVectorStore()
            self.rag_available = True
            logger.info("RAG system initialized successfully")
        except Exception as e:
            logger.warning(f"RAG system unavailable: {e}")
            self.vector_store = None
            self.rag_available = False

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
        if not self.rag_available:
            logger.warning("RAG system unavailable, returning empty results", query=query)
            # Initialize empty RAG context
            if "rag" not in state or state["rag"] is None:
                state["rag"] = RAGContext(query="", results=[])
            state["rag"]["query"] = query
            state["rag"]["results"] = []
            return state

        logger.info("Retrieving knowledge from Supabase", query=query)

        try:
            # 1. Call the real vector store function with cancellation protection
            # Create a task for the similarity search
            search_task = asyncio.create_task(
                self.vector_store.similarity_search(query, max_results=top_k)
            )
            
            try:
                # Shield the search from cancellation to ensure it completes
                retrieved_entries = await asyncio.shield(search_task)
                logger.info(f"Successfully retrieved {len(retrieved_entries)} entries")
            except asyncio.CancelledError:
                logger.warning("Main context was cancelled during RAG retrieval, waiting for search to complete...")
                # Try to get the result even if cancelled
                try:
                    retrieved_entries = await asyncio.wait_for(search_task, timeout=3.0)
                    logger.info(f"Retrieved {len(retrieved_entries)} entries despite cancellation")
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    logger.warning("Could not complete RAG search after cancellation")
                    # Cancel the task if still running
                    if not search_task.done():
                        search_task.cancel()
                    # Re-raise to maintain cancellation semantics
                    raise asyncio.CancelledError()
                    
        except asyncio.CancelledError:
            # Re-raise cancellation errors
            logger.warning("RAG retrieval cancelled")
            raise
        except Exception as e:
            logger.warning(f"Failed to retrieve knowledge, continuing without RAG: {e}", query=query, error_type=type(e).__name__)
            # Return empty results on error - this is not a fatal error
            if "rag" not in state or state["rag"] is None:
                state["rag"] = RAGContext(query="", results=[])
            state["rag"]["query"] = query
            state["rag"]["results"] = []
            return state

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
