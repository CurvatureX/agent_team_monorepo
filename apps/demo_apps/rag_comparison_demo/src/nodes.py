from typing import Any, Dict, TypedDict

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from src.config import Config
from src.rag_service import RAGService


class GraphState(TypedDict):
    query: str
    response_with_rag: str
    response_without_rag: str
    context: str
    node_type: str


class NodeProcessor:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.LLM_MODEL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS,
            openai_api_key=Config.OPENAI_API_KEY,
        )
        self.rag_service = RAGService()

    def node_with_rag(self, state: GraphState) -> GraphState:
        """Process query with RAG - retrieves relevant context before answering"""
        query = state["query"]
        node_type = state.get("node_type")

        # Get relevant context from knowledge base
        context = self.rag_service.get_relevant_context(query, node_type)

        # Create system message with context
        system_message = SystemMessage(
            content=f"""You are an expert assistant helping with workflow node questions.
Use the following context from the knowledge base to answer the user's question:

CONTEXT:
{context}

Provide a detailed and accurate answer based on the context provided. If the context doesn't contain sufficient information, mention that limitation."""
        )

        human_message = HumanMessage(content=query)

        # Generate response with RAG
        response = self.llm.invoke([system_message, human_message])

        return {**state, "response_with_rag": response.content, "context": context}

    def node_without_rag(self, state: GraphState) -> GraphState:
        """Process query without RAG - only using LLM's training data"""
        query = state["query"]

        # Create system message without context
        system_message = SystemMessage(
            content="""You are an expert assistant helping with workflow node questions.
Answer the user's question based only on your training data and general knowledge.
Be honest about limitations in your knowledge."""
        )

        human_message = HumanMessage(content=query)

        # Generate response without RAG
        response = self.llm.invoke([system_message, human_message])

        return {**state, "response_without_rag": response.content}

    def comparison_node(self, state: GraphState) -> GraphState:
        """Generate a comparison between the two responses"""
        rag_response = state["response_with_rag"]
        no_rag_response = state["response_without_rag"]

        comparison_prompt = f"""Compare these two responses to the same question:

RESPONSE WITH RAG:
{rag_response}

RESPONSE WITHOUT RAG:
{no_rag_response}

Analyze the differences in:
1. Accuracy and specificity
2. Completeness of information
3. Relevance to the query
4. Confidence level

Provide a brief analysis of which response is better and why."""

        comparison_message = HumanMessage(content=comparison_prompt)
        comparison_response = self.llm.invoke([comparison_message])

        return {**state, "comparison": comparison_response.content}
