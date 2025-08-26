-- =====================================================
-- MEMORY NODES DATABASE SCHEMA
-- Migration: 20250826000001_memory_implementations.sql
-- =====================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =====================================================
-- 1. CONVERSATION BUFFER MEMORY
-- =====================================================

-- Table for persistent conversation buffer storage
CREATE TABLE IF NOT EXISTS conversation_buffers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    message_index INTEGER NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    tokens_count INTEGER,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for efficient queries
    UNIQUE (session_id, message_index)
);

-- Indexes for conversation buffers
CREATE INDEX IF NOT EXISTS idx_conversation_buffers_session_id ON conversation_buffers(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_buffers_timestamp ON conversation_buffers(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_buffers_user_id ON conversation_buffers(user_id);

-- =====================================================
-- 2. CONVERSATION SUMMARY MEMORY
-- =====================================================

-- Table for conversation summaries
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    summary TEXT NOT NULL,
    key_points JSONB DEFAULT '[]',
    entities JSONB DEFAULT '[]',
    topics JSONB DEFAULT '[]',
    summary_type VARCHAR(50) DEFAULT 'progressive' CHECK (summary_type IN ('progressive', 'hierarchical', 'key_points')),
    message_count INTEGER NOT NULL DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    model_used VARCHAR(100),
    confidence_score FLOAT DEFAULT 0.0,
    previous_summary_id UUID REFERENCES conversation_summaries(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint to prevent duplicate summaries for same session
    UNIQUE (session_id, created_at)
);

-- Indexes for conversation summaries
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_session_id ON conversation_summaries(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_user_id ON conversation_summaries(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_created_at ON conversation_summaries(created_at DESC);

-- =====================================================
-- 3. ENTITY MEMORY
-- =====================================================

-- Table for entities
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    type VARCHAR(100) NOT NULL, -- person, organization, location, product, concept
    aliases TEXT[] DEFAULT '{}',
    attributes JSONB DEFAULT '{}',
    description TEXT,
    importance_score FLOAT DEFAULT 0.5 CHECK (importance_score >= 0.0 AND importance_score <= 1.0),
    first_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    mention_count INTEGER DEFAULT 1,
    user_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint on name and type combination
    UNIQUE (name, type, user_id)
);

-- Table for entity relationships
CREATE TABLE IF NOT EXISTS entity_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL, -- works_at, lives_in, related_to, etc.
    relationship_attributes JSONB DEFAULT '{}',
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source VARCHAR(255), -- where this relationship was extracted from
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Prevent duplicate relationships
    UNIQUE (source_entity_id, target_entity_id, relationship_type)
);

-- Indexes for entities
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_user_id ON entities(user_id);
CREATE INDEX IF NOT EXISTS idx_entities_importance ON entities(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_entities_last_seen ON entities(last_seen DESC);

-- Indexes for entity relationships
CREATE INDEX IF NOT EXISTS idx_entity_relationships_source ON entity_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_relationships_target ON entity_relationships(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_relationships_type ON entity_relationships(relationship_type);

-- =====================================================
-- 4. EPISODIC MEMORY
-- =====================================================

-- Table for episodic events
CREATE TABLE IF NOT EXISTS episodic_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor VARCHAR(255) NOT NULL,
    action VARCHAR(255) NOT NULL,
    object TEXT,
    context JSONB DEFAULT '{}',
    outcome JSONB DEFAULT '{}',
    importance DECIMAL(3,2) NOT NULL DEFAULT 0.5 CHECK (importance >= 0.0 AND importance <= 1.0),
    timestamp TIMESTAMPTZ NOT NULL,
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    event_description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for episodic memory
CREATE INDEX IF NOT EXISTS idx_episodic_memory_timestamp ON episodic_memory(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_episodic_memory_actor ON episodic_memory(actor);
CREATE INDEX IF NOT EXISTS idx_episodic_memory_action ON episodic_memory(action);
CREATE INDEX IF NOT EXISTS idx_episodic_memory_importance ON episodic_memory(importance DESC);
CREATE INDEX IF NOT EXISTS idx_episodic_memory_session ON episodic_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_episodic_memory_user ON episodic_memory(user_id);

-- =====================================================
-- 5. KNOWLEDGE BASE MEMORY
-- =====================================================

-- Table for knowledge facts
CREATE TABLE IF NOT EXISTS knowledge_facts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject VARCHAR(500) NOT NULL,
    predicate VARCHAR(255) NOT NULL,
    object JSONB NOT NULL,
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source VARCHAR(255),
    domain VARCHAR(100),
    fact_type VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    user_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMPTZ,

    -- Prevent duplicate facts
    UNIQUE (subject, predicate, object, user_id)
);

-- Table for knowledge rules
CREATE TABLE IF NOT EXISTS knowledge_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    conditions JSONB NOT NULL,
    actions JSONB NOT NULL,
    priority INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT true,
    user_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for knowledge facts
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_subject ON knowledge_facts(subject);
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_predicate ON knowledge_facts(predicate);
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_confidence ON knowledge_facts(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_domain ON knowledge_facts(domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_user_id ON knowledge_facts(user_id);

-- Indexes for knowledge rules
CREATE INDEX IF NOT EXISTS idx_knowledge_rules_priority ON knowledge_rules(priority DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_rules_active ON knowledge_rules(active);

-- =====================================================
-- 6. GRAPH MEMORY
-- =====================================================

-- Table for graph nodes
CREATE TABLE IF NOT EXISTS graph_nodes (
    id VARCHAR(255) PRIMARY KEY,
    label VARCHAR(500) NOT NULL,
    type VARCHAR(100) NOT NULL, -- person, organization, concept, location, event, topic
    properties JSONB DEFAULT '{}',
    user_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint on label and type per user
    UNIQUE (label, type, user_id)
);

-- Table for graph relationships
CREATE TABLE IF NOT EXISTS graph_relationships (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    source_node_id VARCHAR(255) NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_node_id VARCHAR(255) NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL, -- knows, works_at, related_to, part_of, causes, etc.
    properties JSONB DEFAULT '{}',
    weight FLOAT DEFAULT 1.0 CHECK (weight >= 0.0 AND weight <= 1.0),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Prevent duplicate relationships
    UNIQUE (source_node_id, target_node_id, relationship_type)
);

-- Indexes for graph nodes
CREATE INDEX IF NOT EXISTS idx_graph_nodes_label ON graph_nodes(label);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(type);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_user_id ON graph_nodes(user_id);

-- Indexes for graph relationships
CREATE INDEX IF NOT EXISTS idx_graph_relationships_source ON graph_relationships(source_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_relationships_target ON graph_relationships(target_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_relationships_type ON graph_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_graph_relationships_weight ON graph_relationships(weight DESC);

-- =====================================================
-- 7. DOCUMENT STORE MEMORY
-- =====================================================

-- Table for document store
CREATE TABLE IF NOT EXISTS document_store (
    id VARCHAR(255) PRIMARY KEY,
    collection_name VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    description TEXT,
    content TEXT NOT NULL,
    search_content TEXT NOT NULL, -- For tsvector indexing
    metadata JSONB DEFAULT '{}',
    category VARCHAR(100) DEFAULT 'general',
    tags TEXT[] DEFAULT '{}',
    user_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for document store
CREATE INDEX IF NOT EXISTS idx_document_store_collection ON document_store(collection_name);
CREATE INDEX IF NOT EXISTS idx_document_store_category ON document_store(category);
CREATE INDEX IF NOT EXISTS idx_document_store_tags ON document_store USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_document_store_created ON document_store(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_document_store_user_id ON document_store(user_id);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_document_store_search ON document_store USING GIN(to_tsvector('english', search_content));

-- =====================================================
-- 8. VECTOR DATABASE MEMORY
-- =====================================================

-- Table for vector embeddings
CREATE TABLE IF NOT EXISTS vector_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_name VARCHAR(255) NOT NULL,
    text_content TEXT NOT NULL,
    embedding vector(1536) NOT NULL, -- OpenAI ada-002 size
    metadata JSONB DEFAULT '{}',
    user_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Vector similarity indexes
CREATE INDEX IF NOT EXISTS idx_vector_embeddings_cosine ON vector_embeddings
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_vector_embeddings_euclidean ON vector_embeddings
USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- Regular indexes
CREATE INDEX IF NOT EXISTS idx_vector_embeddings_collection ON vector_embeddings(collection_name);
CREATE INDEX IF NOT EXISTS idx_vector_embeddings_user_id ON vector_embeddings(user_id);

-- =====================================================
-- Row Level Security (RLS) Policies
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE conversation_buffers ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodic_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_store ENABLE ROW LEVEL SECURITY;
ALTER TABLE vector_embeddings ENABLE ROW LEVEL SECURITY;

-- RLS policies for multi-tenant isolation
-- Users can only access their own memory data
CREATE POLICY "Users can access own conversation buffers" ON conversation_buffers
    FOR ALL USING (auth.uid()::text = user_id);

CREATE POLICY "Users can access own conversation summaries" ON conversation_summaries
    FOR ALL USING (auth.uid()::text = user_id);

CREATE POLICY "Users can access own entities" ON entities
    FOR ALL USING (auth.uid()::text = user_id);

CREATE POLICY "Users can access own entity relationships" ON entity_relationships
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM entities e1
            WHERE e1.id = entity_relationships.source_entity_id
            AND e1.user_id = auth.uid()::text
        )
    );

CREATE POLICY "Users can access own episodic memory" ON episodic_memory
    FOR ALL USING (auth.uid()::text = user_id);

CREATE POLICY "Users can access own knowledge facts" ON knowledge_facts
    FOR ALL USING (auth.uid()::text = user_id);

CREATE POLICY "Users can access own knowledge rules" ON knowledge_rules
    FOR ALL USING (auth.uid()::text = user_id);

CREATE POLICY "Users can access own graph nodes" ON graph_nodes
    FOR ALL USING (auth.uid()::text = user_id);

CREATE POLICY "Users can access own graph relationships" ON graph_relationships
    FOR ALL USING (auth.uid()::text = user_id);

CREATE POLICY "Users can access own document store" ON document_store
    FOR ALL USING (auth.uid()::text = user_id);

CREATE POLICY "Users can access own vector embeddings" ON vector_embeddings
    FOR ALL USING (auth.uid()::text = user_id);

-- =====================================================
-- UTILITY FUNCTIONS
-- =====================================================

-- Function to clean old conversation buffers
CREATE OR REPLACE FUNCTION cleanup_old_conversation_buffers(retention_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM conversation_buffers
    WHERE created_at < (CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL);

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update entity last_seen timestamp
CREATE OR REPLACE FUNCTION update_entity_last_seen()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_seen = CURRENT_TIMESTAMP;
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update entity timestamps
CREATE TRIGGER trigger_update_entity_last_seen
    BEFORE UPDATE ON entities
    FOR EACH ROW
    EXECUTE FUNCTION update_entity_last_seen();

-- Function for vector similarity search
CREATE OR REPLACE FUNCTION search_similar_vectors(
    query_embedding vector(1536),
    collection_name_param TEXT,
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    text_content TEXT,
    metadata JSONB,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.id,
        v.text_content,
        v.metadata,
        1 - (v.embedding <=> query_embedding) as similarity
    FROM vector_embeddings v
    WHERE v.collection_name = collection_name_param
        AND (1 - (v.embedding <=> query_embedding)) > similarity_threshold
    ORDER BY v.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;
