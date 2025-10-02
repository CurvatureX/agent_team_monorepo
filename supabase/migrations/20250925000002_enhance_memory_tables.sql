-- Migration: Enhance Memory Tables for Production Persistence
-- Description: Add proper structure, indexes, and constraints to memory tables
-- Created: 2025-09-25
-- Author: Claude Code Assistant

-- =============================================================================
-- ENHANCE MEMORY TABLES FOR PROPER PERSISTENCE
-- =============================================================================

-- This migration enhances the existing memory tables to support proper
-- persistence for all memory node types, replacing the current in-memory
-- implementation with database-backed storage.

-- =============================================================================
-- 1. ENHANCE CONVERSATION_BUFFERS TABLE
-- =============================================================================

-- Add missing columns for conversation buffer functionality
ALTER TABLE conversation_buffers ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE conversation_buffers ADD COLUMN IF NOT EXISTS memory_node_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE conversation_buffers ADD COLUMN IF NOT EXISTS message_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE conversation_buffers ADD COLUMN IF NOT EXISTS role VARCHAR(50) NOT NULL DEFAULT 'user';
ALTER TABLE conversation_buffers ADD COLUMN IF NOT EXISTS content TEXT NOT NULL DEFAULT '';
ALTER TABLE conversation_buffers ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Add unique constraint for ordering
ALTER TABLE conversation_buffers DROP CONSTRAINT IF EXISTS unique_conversation_order;
ALTER TABLE conversation_buffers ADD CONSTRAINT unique_conversation_order
    UNIQUE(user_id, memory_node_id, message_order);

-- Add indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_conversation_buffers_user_memory ON conversation_buffers(user_id, memory_node_id);
CREATE INDEX IF NOT EXISTS idx_conversation_buffers_created_at ON conversation_buffers(created_at);

-- =============================================================================
-- 2. ENHANCE CONVERSATION_SUMMARIES TABLE
-- =============================================================================

-- Add missing columns for conversation summary functionality
ALTER TABLE conversation_summaries ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE conversation_summaries ADD COLUMN IF NOT EXISTS memory_node_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE conversation_summaries ADD COLUMN IF NOT EXISTS summary_text TEXT NOT NULL DEFAULT '';
ALTER TABLE conversation_summaries ADD COLUMN IF NOT EXISTS message_count INTEGER DEFAULT 0;
ALTER TABLE conversation_summaries ADD COLUMN IF NOT EXISTS last_message_order INTEGER DEFAULT 0;
ALTER TABLE conversation_summaries ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Add unique constraint
ALTER TABLE conversation_summaries DROP CONSTRAINT IF EXISTS unique_conversation_summary;
ALTER TABLE conversation_summaries ADD CONSTRAINT unique_conversation_summary
    UNIQUE(user_id, memory_node_id);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_user_memory ON conversation_summaries(user_id, memory_node_id);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_updated_at ON conversation_summaries(updated_at);

-- =============================================================================
-- 3. ENHANCE EPISODIC_MEMORY TABLE
-- =============================================================================

-- Add missing columns for episodic memory functionality
ALTER TABLE episodic_memory ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE episodic_memory ADD COLUMN IF NOT EXISTS memory_node_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE episodic_memory ADD COLUMN IF NOT EXISTS episode_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE episodic_memory ADD COLUMN IF NOT EXISTS context TEXT NOT NULL DEFAULT '';
ALTER TABLE episodic_memory ADD COLUMN IF NOT EXISTS importance_score DECIMAL(3, 2) DEFAULT 0.5;
ALTER TABLE episodic_memory ADD COLUMN IF NOT EXISTS temporal_context JSONB DEFAULT '{}';

-- Add unique constraint
ALTER TABLE episodic_memory DROP CONSTRAINT IF EXISTS unique_episodic_memory;
ALTER TABLE episodic_memory ADD CONSTRAINT unique_episodic_memory
    UNIQUE(user_id, memory_node_id, episode_id);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_episodic_memory_user_memory ON episodic_memory(user_id, memory_node_id);
CREATE INDEX IF NOT EXISTS idx_episodic_memory_importance ON episodic_memory(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_episodic_memory_created_at ON episodic_memory(created_at);

-- =============================================================================
-- 4. ENHANCE KNOWLEDGE_FACTS TABLE
-- =============================================================================

-- Add missing columns for knowledge facts functionality
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS memory_node_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS fact_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS subject VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS predicate VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS object TEXT NOT NULL DEFAULT '';
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS confidence DECIMAL(3, 2) DEFAULT 0.8;
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS source VARCHAR(255);

-- Add unique constraint
ALTER TABLE knowledge_facts DROP CONSTRAINT IF EXISTS unique_knowledge_fact;
ALTER TABLE knowledge_facts ADD CONSTRAINT unique_knowledge_fact
    UNIQUE(user_id, memory_node_id, fact_id);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_user_memory ON knowledge_facts(user_id, memory_node_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_subject ON knowledge_facts(subject);
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_predicate ON knowledge_facts(predicate);
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_confidence ON knowledge_facts(confidence DESC);

-- =============================================================================
-- 5. ENHANCE KNOWLEDGE_RULES TABLE
-- =============================================================================

-- Add missing columns for knowledge rules functionality
ALTER TABLE knowledge_rules ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE knowledge_rules ADD COLUMN IF NOT EXISTS memory_node_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE knowledge_rules ADD COLUMN IF NOT EXISTS rule_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE knowledge_rules ADD COLUMN IF NOT EXISTS condition_pattern TEXT NOT NULL DEFAULT '';
ALTER TABLE knowledge_rules ADD COLUMN IF NOT EXISTS action_pattern TEXT NOT NULL DEFAULT '';
ALTER TABLE knowledge_rules ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 1;
ALTER TABLE knowledge_rules ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

-- Add unique constraint
ALTER TABLE knowledge_rules DROP CONSTRAINT IF EXISTS unique_knowledge_rule;
ALTER TABLE knowledge_rules ADD CONSTRAINT unique_knowledge_rule
    UNIQUE(user_id, memory_node_id, rule_id);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_rules_user_memory ON knowledge_rules(user_id, memory_node_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_rules_priority ON knowledge_rules(priority DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_rules_active ON knowledge_rules(is_active) WHERE is_active = true;

-- =============================================================================
-- 6. ENHANCE GRAPH_NODES TABLE
-- =============================================================================

-- Add missing columns for graph nodes functionality
ALTER TABLE graph_nodes ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE graph_nodes ADD COLUMN IF NOT EXISTS memory_node_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE graph_nodes ADD COLUMN IF NOT EXISTS node_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE graph_nodes ADD COLUMN IF NOT EXISTS node_type VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE graph_nodes ADD COLUMN IF NOT EXISTS properties JSONB DEFAULT '{}';
ALTER TABLE graph_nodes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Add unique constraint
ALTER TABLE graph_nodes DROP CONSTRAINT IF EXISTS unique_graph_node;
ALTER TABLE graph_nodes ADD CONSTRAINT unique_graph_node
    UNIQUE(user_id, memory_node_id, node_id);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_graph_nodes_user_memory ON graph_nodes(user_id, memory_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_node_type ON graph_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_updated_at ON graph_nodes(updated_at);

-- =============================================================================
-- 7. ENHANCE GRAPH_RELATIONSHIPS TABLE
-- =============================================================================

-- Add missing columns for graph relationships functionality
ALTER TABLE graph_relationships ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE graph_relationships ADD COLUMN IF NOT EXISTS memory_node_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE graph_relationships ADD COLUMN IF NOT EXISTS relationship_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE graph_relationships ADD COLUMN IF NOT EXISTS source_node_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE graph_relationships ADD COLUMN IF NOT EXISTS target_node_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE graph_relationships ADD COLUMN IF NOT EXISTS relationship_type VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE graph_relationships ADD COLUMN IF NOT EXISTS properties JSONB DEFAULT '{}';
ALTER TABLE graph_relationships ADD COLUMN IF NOT EXISTS weight DECIMAL(5, 3) DEFAULT 1.0;

-- Add unique constraint
ALTER TABLE graph_relationships DROP CONSTRAINT IF EXISTS unique_graph_relationship;
ALTER TABLE graph_relationships ADD CONSTRAINT unique_graph_relationship
    UNIQUE(user_id, memory_node_id, relationship_id);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_graph_relationships_user_memory ON graph_relationships(user_id, memory_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_relationships_source ON graph_relationships(source_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_relationships_target ON graph_relationships(target_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_relationships_type ON graph_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_graph_relationships_weight ON graph_relationships(weight DESC);

-- =============================================================================
-- 8. ENHANCE DOCUMENT_STORE TABLE
-- =============================================================================

-- Add missing columns for document store functionality
ALTER TABLE document_store ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE document_store ADD COLUMN IF NOT EXISTS memory_node_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE document_store ADD COLUMN IF NOT EXISTS document_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE document_store ADD COLUMN IF NOT EXISTS title VARCHAR(500) NOT NULL DEFAULT '';
ALTER TABLE document_store ADD COLUMN IF NOT EXISTS content TEXT NOT NULL DEFAULT '';
ALTER TABLE document_store ADD COLUMN IF NOT EXISTS document_type VARCHAR(100) DEFAULT 'text';
ALTER TABLE document_store ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';
ALTER TABLE document_store ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Add unique constraint
ALTER TABLE document_store DROP CONSTRAINT IF EXISTS unique_document;
ALTER TABLE document_store ADD CONSTRAINT unique_document
    UNIQUE(user_id, memory_node_id, document_id);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_document_store_user_memory ON document_store(user_id, memory_node_id);
CREATE INDEX IF NOT EXISTS idx_document_store_document_type ON document_store(document_type);
CREATE INDEX IF NOT EXISTS idx_document_store_title ON document_store(title);
CREATE INDEX IF NOT EXISTS idx_document_store_updated_at ON document_store(updated_at);

-- Add full-text search index for content
CREATE INDEX IF NOT EXISTS idx_document_store_content_search ON document_store USING gin(to_tsvector('english', title || ' ' || content));

-- =============================================================================
-- 9. ADD ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================

-- Enable RLS on all memory tables
ALTER TABLE conversation_buffers ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodic_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_store ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for user data isolation
CREATE POLICY "Users can manage their own conversation buffers" ON conversation_buffers
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own conversation summaries" ON conversation_summaries
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own episodic memory" ON episodic_memory
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own knowledge facts" ON knowledge_facts
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own knowledge rules" ON knowledge_rules
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own graph nodes" ON graph_nodes
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own graph relationships" ON graph_relationships
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own documents" ON document_store
    FOR ALL USING (auth.uid() = user_id);

-- =============================================================================
-- 10. CREATE HELPER FUNCTIONS FOR MEMORY OPERATIONS
-- =============================================================================

-- Function to cleanup expired memory data
CREATE OR REPLACE FUNCTION cleanup_expired_memory()
RETURNS INTEGER AS $$
DECLARE
    total_cleaned INTEGER := 0;
    cleaned_count INTEGER;
BEGIN
    -- Clean up expired entries from memory_data table (if expires_at is set)
    DELETE FROM memory_data
    WHERE expires_at IS NOT NULL AND expires_at < NOW();

    GET DIAGNOSTICS cleaned_count = ROW_COUNT;
    total_cleaned := total_cleaned + cleaned_count;

    RAISE NOTICE 'Cleaned up % expired memory entries', total_cleaned;

    RETURN total_cleaned;
END;
$$ LANGUAGE plpgsql;

-- Function to get conversation buffer messages in order
CREATE OR REPLACE FUNCTION get_conversation_buffer(
    p_user_id UUID,
    p_memory_node_id VARCHAR(255),
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    role VARCHAR(50),
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cb.role,
        cb.content,
        cb.metadata,
        cb.created_at
    FROM conversation_buffers cb
    WHERE cb.user_id = p_user_id
      AND cb.memory_node_id = p_memory_node_id
    ORDER BY cb.message_order ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function for semantic search in document store
CREATE OR REPLACE FUNCTION search_documents(
    p_user_id UUID,
    p_memory_node_id VARCHAR(255),
    p_query TEXT,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    document_id VARCHAR(255),
    title VARCHAR(500),
    content TEXT,
    similarity REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ds.document_id,
        ds.title,
        ds.content,
        ts_rank_cd(to_tsvector('english', ds.title || ' ' || ds.content), to_tsquery('english', p_query)) AS similarity
    FROM document_store ds
    WHERE ds.user_id = p_user_id
      AND ds.memory_node_id = p_memory_node_id
      AND to_tsvector('english', ds.title || ' ' || ds.content) @@ to_tsquery('english', p_query)
    ORDER BY similarity DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 11. GRANT NECESSARY PERMISSIONS
-- =============================================================================

-- Grant permissions for new functions
GRANT EXECUTE ON FUNCTION cleanup_expired_memory TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION get_conversation_buffer TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION search_documents TO authenticated, service_role;

-- =============================================================================
-- MIGRATION COMPLETION
-- =============================================================================

-- Log successful migration
DO $$
BEGIN
    RAISE NOTICE '🧠 Memory Tables Enhancement completed successfully';
    RAISE NOTICE 'Enhanced tables for memory persistence:';
    RAISE NOTICE '  ✅ conversation_buffers - Ready for CONVERSATION_BUFFER memory type';
    RAISE NOTICE '  ✅ conversation_summaries - Ready for CONVERSATION_SUMMARY memory type';
    RAISE NOTICE '  ✅ episodic_memory - Ready for EPISODIC_MEMORY memory type';
    RAISE NOTICE '  ✅ knowledge_facts - Ready for KNOWLEDGE_BASE memory type';
    RAISE NOTICE '  ✅ knowledge_rules - Ready for KNOWLEDGE_BASE memory type';
    RAISE NOTICE '  ✅ graph_nodes - Ready for GRAPH_MEMORY memory type';
    RAISE NOTICE '  ✅ graph_relationships - Ready for GRAPH_MEMORY memory type';
    RAISE NOTICE '  ✅ document_store - Ready for DOCUMENT_STORE memory type';
    RAISE NOTICE '';
    RAISE NOTICE '🔒 Security features added:';
    RAISE NOTICE '  ✅ Row Level Security (RLS) policies';
    RAISE NOTICE '  ✅ User data isolation';
    RAISE NOTICE '  ✅ Proper foreign key constraints';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 Performance features added:';
    RAISE NOTICE '  ✅ Optimized indexes for memory operations';
    RAISE NOTICE '  ✅ Full-text search for documents';
    RAISE NOTICE '  ✅ Helper functions for common operations';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Next steps:';
    RAISE NOTICE '  1. Update memory implementations to use database storage';
    RAISE NOTICE '  2. Migrate from in-memory to persistent storage';
    RAISE NOTICE '  3. Test memory operations with real data';
END $$;
