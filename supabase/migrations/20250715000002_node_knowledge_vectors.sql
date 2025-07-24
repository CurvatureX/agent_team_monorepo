-- Migration: 002_node_knowledge_vectors
-- Description: Create table for storing node type knowledge vectors
-- Created: 2025-07-15
-- Author: Workflow Engine Team

-- This migration creates a table to store vector embeddings for node type knowledge

-- Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Create node knowledge vectors table
CREATE TABLE node_knowledge_vectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_type VARCHAR(50) NOT NULL,
    node_subtype VARCHAR(100) NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX idx_node_knowledge_vectors_node_type ON node_knowledge_vectors(node_type);
CREATE INDEX idx_node_knowledge_vectors_node_subtype ON node_knowledge_vectors(node_subtype);
CREATE INDEX idx_node_knowledge_vectors_embedding ON node_knowledge_vectors USING ivfflat (embedding vector_cosine_ops);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_node_knowledge_vectors_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_node_knowledge_vectors_updated_at
    BEFORE UPDATE ON node_knowledge_vectors
    FOR EACH ROW
    EXECUTE FUNCTION update_node_knowledge_vectors_updated_at();

-- Add comments for documentation
COMMENT ON TABLE node_knowledge_vectors IS 'Stores vector embeddings for node type knowledge and descriptions';
COMMENT ON COLUMN node_knowledge_vectors.node_type IS 'Main node type (e.g., TRIGGER_NODE, AI_AGENT_NODE, etc.)';
COMMENT ON COLUMN node_knowledge_vectors.node_subtype IS 'Specific subtype of the node (e.g., TRIGGER_CHAT, AI_ROUTER_AGENT, etc.)';
COMMENT ON COLUMN node_knowledge_vectors.title IS 'Human-readable title for the node knowledge';
COMMENT ON COLUMN node_knowledge_vectors.description IS 'Brief description of the node functionality';
COMMENT ON COLUMN node_knowledge_vectors.content IS 'Full content/knowledge text for the node';
COMMENT ON COLUMN node_knowledge_vectors.embedding IS 'Vector embedding (1536 dimensions for OpenAI text-embedding-ada-002)';
COMMENT ON COLUMN node_knowledge_vectors.metadata IS 'Additional metadata as JSON (capabilities, examples, etc.)';

-- Create the vector similarity search function for RAG
CREATE OR REPLACE FUNCTION match_node_knowledge(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.3,
    match_count int DEFAULT 5,
    node_type_filter text DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    node_type varchar,
    node_subtype varchar,
    title varchar,
    description text,
    content text,
    similarity float,
    metadata jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        nkv.id,
        nkv.node_type,
        nkv.node_subtype,
        nkv.title,
        nkv.description,
        nkv.content,
        1 - (nkv.embedding <=> query_embedding) as similarity,
        nkv.metadata
    FROM node_knowledge_vectors nkv
    WHERE
        (node_type_filter IS NULL OR nkv.node_type = node_type_filter)
        AND 1 - (nkv.embedding <=> query_embedding) > match_threshold
    ORDER BY nkv.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Add comment for the function
COMMENT ON FUNCTION match_node_knowledge IS 'Vector similarity search function for finding relevant node knowledge based on query embeddings';

-- Note: Initial data with embeddings should be inserted via application code
-- after generating vector embeddings for the node knowledge content
