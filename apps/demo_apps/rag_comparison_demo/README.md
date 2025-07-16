# RAG Comparison Demo

This LangGraph project demonstrates the difference between using RAG (Retrieval-Augmented Generation) and not using RAG when answering questions about workflow nodes.

## Overview

The demo creates a workflow that processes the same query through two different nodes:
1. **RAG Node**: Retrieves relevant context from the Supabase vector database before answering
2. **Non-RAG Node**: Answers based only on the LLM's training data
3. **Comparison Node**: Analyzes the differences between both responses

## Architecture

```
Query Input
    ↓
RAG Node (retrieves context) → Response with RAG
    ↓
Non-RAG Node (no context) → Response without RAG
    ↓
Comparison Node → Analysis of differences
```

## Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```

4. **Set up Supabase**:
   - Run the migration in `supabase/migrations/20250715000002_node_knowledge_vectors.sql`
   - Execute the function in `src/supabase_functions.sql` in your Supabase SQL editor
   - Populate the `node_knowledge_vectors` table with node knowledge data

5. **Run the demo**:
   ```bash
   uv run demo.py
   ```

## Key Components

### RAG Service (`src/rag_service.py`)
- Handles vector similarity search using Supabase
- Generates embeddings using OpenAI's text-embedding-ada-002
- Retrieves relevant context based on cosine similarity

### Nodes (`src/nodes.py`)
- `node_with_rag`: Processes queries with retrieved context
- `node_without_rag`: Processes queries without additional context
- `comparison_node`: Analyzes differences between responses

### Workflow (`src/workflow.py`)
- LangGraph workflow that orchestrates the comparison process
- Runs both nodes and generates a comparison analysis

## Database Schema

The demo uses the `node_knowledge_vectors` table with:
- `node_type`: Main node type (e.g., AI_AGENT_NODE, TRIGGER_NODE)
- `node_subtype`: Specific subtype
- `title`: Human-readable title
- `description`: Brief description
- `content`: Full knowledge content
- `embedding`: Vector embedding (1536 dimensions)
- `metadata`: Additional JSON metadata

## Sample Queries

The demo includes sample queries for:
- AI Agent Node capabilities
- Trigger Node configuration
- Memory Node functionality

## Expected Results

The RAG-enabled responses should be:
- More specific and accurate
- Include relevant technical details
- Reference actual node capabilities
- Provide actionable information

The non-RAG responses will be:
- More general
- Based on training data patterns
- Less specific to the actual implementation
- May contain outdated or generic information
