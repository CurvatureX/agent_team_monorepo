-- Migration: Align with Latest Design
-- Description: Update database schema to align with latest node_specs architecture
-- Created: 2025-01-25
-- Author: Claude Code Assistant

-- =============================================================================
-- 1. UPDATE NODE TYPE CONSTRAINTS TO MATCH LATEST ENUMS
-- =============================================================================

-- Drop existing constraint and add updated one
ALTER TABLE nodes DROP CONSTRAINT IF EXISTS valid_node_type;
ALTER TABLE nodes ADD CONSTRAINT valid_node_type CHECK (
    node_type IN ('TRIGGER', 'AI_AGENT', 'EXTERNAL_ACTION', 'ACTION', 'FLOW', 'HUMAN_IN_THE_LOOP', 'TOOL', 'MEMORY')
);

-- Update node_connections constraint for latest connection types
ALTER TABLE node_connections DROP CONSTRAINT IF EXISTS valid_connection_type;
ALTER TABLE node_connections ADD CONSTRAINT valid_connection_type CHECK (
    connection_type IN (
        'MAIN', 'ERROR', 'SUCCESS', 'CONDITIONAL',
        -- AI Agent connection types
        'AI_AGENT', 'AI_CHAIN', 'AI_DOCUMENT', 'AI_EMBEDDING',
        'AI_LANGUAGE_MODEL', 'AI_MEMORY', 'AI_OUTPUT_PARSER', 'AI_RETRIEVER',
        'AI_RERANKER', 'AI_TEXT_SPLITTER', 'AI_TOOL', 'AI_VECTOR_STORE',
        -- Memory connection types (for attached nodes)
        'MEMORY_ATTACHMENT', 'CONTEXT_PROVIDER'
    )
);

-- =============================================================================
-- 2. ADD ATTACHED NODES SUPPORT FOR MEMORY SYSTEM
-- =============================================================================

-- Add attached_nodes column to nodes table for memory node attachments
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS attached_nodes JSONB DEFAULT '[]';

-- Add comment explaining attached_nodes usage
COMMENT ON COLUMN nodes.attached_nodes IS 'Array of memory node IDs attached to this node for context enhancement';

-- =============================================================================
-- 3. CREATE NODE SPECIFICATIONS TABLE
-- =============================================================================

-- Table to store dynamic node specifications
CREATE TABLE IF NOT EXISTS node_specifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_type VARCHAR(50) NOT NULL,
    node_subtype VARCHAR(100) NOT NULL,
    specification_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    specification_data JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_system_spec BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure unique combination
    UNIQUE(node_type, node_subtype, specification_version),

    -- Validate node types match enum
    CONSTRAINT valid_spec_node_type CHECK (
        node_type IN ('TRIGGER', 'AI_AGENT', 'EXTERNAL_ACTION', 'ACTION', 'FLOW', 'HUMAN_IN_THE_LOOP', 'TOOL', 'MEMORY')
    )
);

-- Index for fast lookups
CREATE INDEX idx_node_specifications_type_subtype ON node_specifications(node_type, node_subtype);
CREATE INDEX idx_node_specifications_active ON node_specifications(is_active) WHERE is_active = true;

-- RLS policy for node specifications
ALTER TABLE node_specifications ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can read system specifications
CREATE POLICY "Anyone can read active system node specifications" ON node_specifications
    FOR SELECT
    USING (is_active = true AND is_system_spec = true);

-- =============================================================================
-- 4. UPDATE AI MODELS TABLE WITH LATEST MODELS
-- =============================================================================

-- Add new model columns for enhanced AI model support
ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS cost_per_input_token DECIMAL(10, 8);
ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS cost_per_output_token DECIMAL(10, 8);
ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS cost_per_cached_token DECIMAL(10, 8);
ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS max_context_tokens INTEGER;
ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS supports_vision BOOLEAN DEFAULT false;
ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS supports_function_calling BOOLEAN DEFAULT false;
ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS supports_streaming BOOLEAN DEFAULT true;
ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS model_capabilities JSONB DEFAULT '{}';

-- Insert latest AI models if they don't exist
INSERT INTO ai_models (name, provider, model_id, version, cost_per_input_token, cost_per_output_token, cost_per_cached_token, max_context_tokens, supports_vision, supports_function_calling, config) VALUES
-- OpenAI GPT-5 Series
('GPT-5', 'openai', 'gpt-5', '1.0', 1.25, 10.00, 0.125, 128000, true, true, '{"family": "gpt5", "reasoning": true}'),
('GPT-5 Mini', 'openai', 'gpt-5-mini', '1.0', 0.25, 2.00, 0.025, 128000, true, true, '{"family": "gpt5", "reasoning": true}'),
('GPT-5 Nano', 'openai', 'gpt-5-nano', '1.0', 0.05, 0.40, 0.005, 128000, false, true, '{"family": "gpt5", "reasoning": false}'),

-- Anthropic Claude Sonnet 4
('Claude Sonnet 4', 'anthropic', 'claude-sonnet-4-20250514', '1.0', 3.00, 15.00, NULL, 200000, true, true, '{"family": "claude", "thinking_mode": true}'),
('Claude Haiku 3.5', 'anthropic', 'claude-3-5-haiku-20241022', '1.0', 1.00, 4.00, NULL, 200000, true, true, '{"family": "claude", "thinking_mode": false}'),

-- Google Gemini 2.5 Series
('Gemini 2.5 Pro', 'google', 'gemini-2.5-pro', '1.0', 1.25, 10.00, 0.31, 1000000, true, true, '{"family": "gemini", "reasoning": true}'),
('Gemini 2.5 Flash', 'google', 'gemini-2.5-flash', '1.0', 0.30, 2.50, 0.075, 1000000, true, true, '{"family": "gemini", "reasoning": true}'),
('Gemini 2.5 Flash Lite', 'google', 'gemini-2.5-flash-lite', '1.0', 0.10, 0.40, 0.025, 1000000, true, true, '{"family": "gemini", "reasoning": false}')

ON CONFLICT (name, version) DO UPDATE SET
    cost_per_input_token = EXCLUDED.cost_per_input_token,
    cost_per_output_token = EXCLUDED.cost_per_output_token,
    cost_per_cached_token = EXCLUDED.cost_per_cached_token,
    max_context_tokens = EXCLUDED.max_context_tokens,
    supports_vision = EXCLUDED.supports_vision,
    supports_function_calling = EXCLUDED.supports_function_calling,
    config = EXCLUDED.config;

-- =============================================================================
-- 5. CREATE MCP TOOLS REGISTRY
-- =============================================================================

-- Table for MCP (Model Context Protocol) tools
CREATE TABLE IF NOT EXISTS mcp_tools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tool_name VARCHAR(255) NOT NULL,
    tool_type VARCHAR(100) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    description TEXT,
    tool_schema JSONB NOT NULL,
    configuration_schema JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    is_system_tool BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(tool_name, provider, version)
);

-- Index for fast MCP tool lookups
CREATE INDEX idx_mcp_tools_name ON mcp_tools(tool_name);
CREATE INDEX idx_mcp_tools_type ON mcp_tools(tool_type);
CREATE INDEX idx_mcp_tools_active ON mcp_tools(is_active) WHERE is_active = true;

-- RLS for MCP tools
ALTER TABLE mcp_tools ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can read active system tools
CREATE POLICY "Anyone can read active MCP tools" ON mcp_tools
    FOR SELECT
    USING (is_active = true AND is_system_tool = true);

-- =============================================================================
-- 6. CREATE MEMORY NODES TABLE FOR ENHANCED MEMORY SYSTEM
-- =============================================================================

-- Table for memory node instances and their configurations
CREATE TABLE IF NOT EXISTS memory_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_node_id VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL,
    memory_subtype VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    configuration JSONB NOT NULL DEFAULT '{}',
    storage_backend VARCHAR(100),
    storage_config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure unique memory node IDs per user
    UNIQUE(user_id, memory_node_id),

    -- Validate memory types
    CONSTRAINT valid_memory_type CHECK (memory_type = 'MEMORY'),
    CONSTRAINT valid_memory_subtype CHECK (
        memory_subtype IN (
            'CONVERSATION_BUFFER', 'CONVERSATION_SUMMARY', 'VECTOR_DATABASE',
            'KEY_VALUE_STORE', 'DOCUMENT_STORE', 'ENTITY_MEMORY',
            'EPISODIC_MEMORY', 'KNOWLEDGE_BASE', 'GRAPH_MEMORY', 'WORKING_MEMORY'
        )
    )
);

-- Index for memory node lookups
CREATE INDEX idx_memory_nodes_user_id ON memory_nodes(user_id);
CREATE INDEX idx_memory_nodes_type_subtype ON memory_nodes(memory_type, memory_subtype);
CREATE INDEX idx_memory_nodes_active ON memory_nodes(is_active) WHERE is_active = true;

-- RLS for memory nodes
ALTER TABLE memory_nodes ENABLE ROW LEVEL SECURITY;

-- Policy: Users can manage their own memory nodes
CREATE POLICY "Users can manage their own memory nodes" ON memory_nodes
    FOR ALL
    USING (auth.uid() = user_id);

-- =============================================================================
-- 7. CREATE MEMORY DATA TABLE FOR ACTUAL MEMORY STORAGE
-- =============================================================================

-- Table for storing actual memory data
CREATE TABLE IF NOT EXISTS memory_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_node_id VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    data_key VARCHAR(500) NOT NULL,
    data_value JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    importance_score DECIMAL(3, 2) DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Link to memory nodes
    FOREIGN KEY (user_id, memory_node_id) REFERENCES memory_nodes(user_id, memory_node_id) ON DELETE CASCADE,

    -- Ensure unique keys within each memory node
    UNIQUE(user_id, memory_node_id, data_key)
);

-- Index for memory data efficient retrieval
CREATE INDEX idx_memory_data_user_memory_key ON memory_data(user_id, memory_node_id, data_key);
CREATE INDEX idx_memory_data_importance ON memory_data(importance_score DESC);
CREATE INDEX idx_memory_data_access_count ON memory_data(access_count DESC);
CREATE INDEX idx_memory_data_expires_at ON memory_data(expires_at) WHERE expires_at IS NOT NULL;

-- RLS for memory data
ALTER TABLE memory_data ENABLE ROW LEVEL SECURITY;

-- Policy: Users can manage their own memory data
CREATE POLICY "Users can manage their own memory data" ON memory_data
    FOR ALL
    USING (auth.uid() = user_id);

-- =============================================================================
-- 8. UPDATE WORKFLOWS TABLE WITH LATEST FEATURES
-- =============================================================================

-- Add new workflow features
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS workflow_type VARCHAR(50) DEFAULT 'STANDARD';
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS execution_mode VARCHAR(50) DEFAULT 'SEQUENTIAL';
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS memory_config JSONB DEFAULT '{}';
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS ai_context_config JSONB DEFAULT '{}';

-- Add constraint for workflow types
ALTER TABLE workflows DROP CONSTRAINT IF EXISTS valid_workflow_type;
ALTER TABLE workflows ADD CONSTRAINT valid_workflow_type CHECK (
    workflow_type IN ('STANDARD', 'AI_ASSISTANT', 'AUTOMATION', 'INTEGRATION', 'TEMPLATE')
);

-- Add constraint for execution modes
ALTER TABLE workflows DROP CONSTRAINT IF EXISTS valid_execution_mode;
ALTER TABLE workflows ADD CONSTRAINT valid_execution_mode CHECK (
    execution_mode IN ('SEQUENTIAL', 'PARALLEL', 'CONDITIONAL', 'EVENT_DRIVEN')
);

-- =============================================================================
-- 9. CREATE VECTOR EMBEDDINGS TABLE FOR SEMANTIC SEARCH
-- =============================================================================

-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Table for storing embeddings for semantic search across various content types
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    content_type VARCHAR(100) NOT NULL,
    content_id VARCHAR(255) NOT NULL,
    content_text TEXT NOT NULL,
    embedding vector(1536), -- OpenAI ada-002 dimensions
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint on content identification
    UNIQUE(user_id, content_type, content_id)
);

-- Vector similarity search index
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_embeddings_content_type ON embeddings(content_type);
CREATE INDEX idx_embeddings_user_content ON embeddings(user_id, content_type);

-- RLS for embeddings
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

-- Policy: Users can manage their own embeddings
CREATE POLICY "Users can manage their own embeddings" ON embeddings
    FOR ALL
    USING (auth.uid() = user_id);

-- =============================================================================
-- 10. CREATE FUNCTIONS FOR ENHANCED FUNCTIONALITY
-- =============================================================================

-- Function to search similar embeddings
CREATE OR REPLACE FUNCTION search_similar_embeddings(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5,
    filter_user_id uuid DEFAULT NULL,
    filter_content_type text DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    content_text text,
    similarity float,
    metadata jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.content_text,
        (1 - (e.embedding <=> query_embedding)) as similarity,
        e.metadata
    FROM embeddings e
    WHERE
        (filter_user_id IS NULL OR e.user_id = filter_user_id)
        AND (filter_content_type IS NULL OR e.content_type = filter_content_type)
        AND (1 - (e.embedding <=> query_embedding)) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to cleanup expired memory data
CREATE OR REPLACE FUNCTION cleanup_expired_memory_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM memory_data
    WHERE expires_at IS NOT NULL AND expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RAISE NOTICE 'Cleaned up % expired memory entries', deleted_count;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 11. UPDATE EXISTING DATA TO MATCH NEW CONSTRAINTS
-- =============================================================================

-- Update any existing nodes that might have invalid types (if any exist)
UPDATE nodes SET node_type = 'ACTION' WHERE node_type NOT IN ('TRIGGER', 'AI_AGENT', 'EXTERNAL_ACTION', 'ACTION', 'FLOW', 'HUMAN_IN_THE_LOOP', 'TOOL', 'MEMORY');

-- Update workflow types for existing workflows
UPDATE workflows SET workflow_type = 'STANDARD' WHERE workflow_type IS NULL;
UPDATE workflows SET execution_mode = 'SEQUENTIAL' WHERE execution_mode IS NULL;

-- =============================================================================
-- 12. GRANT NECESSARY PERMISSIONS
-- =============================================================================

-- Grant permissions for new functions
GRANT EXECUTE ON FUNCTION search_similar_embeddings TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION cleanup_expired_memory_data TO service_role;

-- Grant usage on vector extension
GRANT USAGE ON SCHEMA extensions TO authenticated, service_role;

-- =============================================================================
-- 13. CREATE UPDATED INDEXES FOR PERFORMANCE
-- =============================================================================

-- Performance indexes for new columns
CREATE INDEX IF NOT EXISTS idx_workflows_workflow_type ON workflows(workflow_type);
CREATE INDEX IF NOT EXISTS idx_workflows_execution_mode ON workflows(execution_mode);
CREATE INDEX IF NOT EXISTS idx_nodes_attached_nodes ON nodes USING GIN(attached_nodes);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_nodes_type_subtype_active ON nodes(node_type, node_subtype) WHERE disabled = false;
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status_created ON workflow_executions(status, created_at DESC);

-- =============================================================================
-- MIGRATION COMPLETION
-- =============================================================================

-- Log successful migration
DO $$
BEGIN
    RAISE NOTICE 'Successfully completed migration: Align with Latest Design';
    RAISE NOTICE 'New features added:';
    RAISE NOTICE '- Updated node type constraints to match latest enums';
    RAISE NOTICE '- Added attached_nodes support for memory system';
    RAISE NOTICE '- Created node_specifications table for dynamic specs';
    RAISE NOTICE '- Updated AI models with latest GPT-5, Claude Sonnet 4, Gemini 2.5';
    RAISE NOTICE '- Added MCP tools registry';
    RAISE NOTICE '- Created comprehensive memory system tables';
    RAISE NOTICE '- Added vector embeddings for semantic search';
    RAISE NOTICE '- Enhanced workflows with new features';
    RAISE NOTICE '- Added performance indexes and utility functions';
END $$;
