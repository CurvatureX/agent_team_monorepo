-- Optimized workflow_agent_states table schema
-- Simplified to store only essential persistent state
-- Derived fields are computed at runtime

-- Drop old table
DROP TABLE IF EXISTS workflow_agent_states CASCADE;

CREATE TABLE workflow_agent_states (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core identity (REQUIRED - can't be derived)
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255),
    
    -- Timestamps (REQUIRED for tracking)
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    
    -- Stage tracking (REQUIRED - core state)
    stage VARCHAR(50) NOT NULL CHECK (stage IN (
        'clarification', 
        'gap_analysis', 
        'workflow_generation', 
        'debug', 
        'completed',
        'failed'  -- Added for failure state
    )),
    previous_stage VARCHAR(50) CHECK (previous_stage IN (
        'clarification', 
        'gap_analysis', 
        'workflow_generation', 
        'debug', 
        'completed',
        'failed'
    )),
    
    -- Core persistent data (REQUIRED - can't be regenerated)
    intent_summary TEXT DEFAULT '',  -- User's intent, established during clarification
    conversations JSONB NOT NULL DEFAULT '[]',  -- Full conversation history
    
    -- Workflow result (REQUIRED - the main output)
    current_workflow JSONB,  -- The generated/edited workflow
    
    -- Debug state (MINIMAL - only what's needed for retry logic)
    debug_loop_count INTEGER DEFAULT 0,  -- Track retry attempts
    
    -- Failure state (MINIMAL - only for failed workflows)
    final_error_message TEXT  -- Error message when stage='failed'
);

-- Performance indexes
CREATE INDEX idx_workflow_agent_states_session_id ON workflow_agent_states(session_id);
CREATE INDEX idx_workflow_agent_states_user_id ON workflow_agent_states(user_id);
CREATE INDEX idx_workflow_agent_states_stage ON workflow_agent_states(stage);
CREATE INDEX idx_workflow_agent_states_updated_at ON workflow_agent_states(updated_at DESC);

-- JSONB GIN indexes for queries
CREATE INDEX idx_workflow_agent_states_conversations ON workflow_agent_states USING GIN (conversations);
CREATE INDEX idx_workflow_agent_states_current_workflow ON workflow_agent_states USING GIN (current_workflow);

-- Table documentation
COMMENT ON TABLE workflow_agent_states IS 
'Optimized state storage for workflow agent. Stores only essential persistent data.';

-- Column documentation
COMMENT ON COLUMN workflow_agent_states.session_id IS 'Unique session identifier';
COMMENT ON COLUMN workflow_agent_states.user_id IS 'User identifier (nullable for anonymous)';
COMMENT ON COLUMN workflow_agent_states.stage IS 'Current workflow stage';
COMMENT ON COLUMN workflow_agent_states.previous_stage IS 'Previous stage for backtracking and debugging';
COMMENT ON COLUMN workflow_agent_states.intent_summary IS 'User intent from clarification';
COMMENT ON COLUMN workflow_agent_states.conversations IS 'Full conversation history [{role, text, timestamp}]';
COMMENT ON COLUMN workflow_agent_states.current_workflow IS 'Generated workflow JSON';
COMMENT ON COLUMN workflow_agent_states.debug_loop_count IS 'Number of debug retry attempts (max 2)';
COMMENT ON COLUMN workflow_agent_states.final_error_message IS 'Error message when generation fails';

-- Auto-update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = EXTRACT(EPOCH FROM NOW()) * 1000;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_workflow_agent_states_updated_at 
    BEFORE UPDATE ON workflow_agent_states
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- REMOVED/DERIVED FIELDS (computed at runtime)
-- ============================================
-- 
-- previous_stage: Can be derived from stage transitions in code
-- execution_history: Not used in simplified flow
-- clarification_context: Transient, rebuilt from conversations
-- gap_status: Transient, computed during gap_analysis
-- identified_gaps: Transient, computed during gap_analysis
-- gap_negotiation_count: Transient, computed from conversations
-- selected_alternative: Can be extracted from conversations
-- template_workflow: Not needed in simplified flow
-- workflow_context: Can be derived from conversations
-- debug_result: Transient, only last error matters
-- debug_error_for_regeneration: Transient, passed between nodes
-- workflow_generation_failed: Redundant with stage='failed'
-- template_id: Not used in simplified flow
--
-- ============================================

-- Migration helper: Copy essential data from old schema if exists
-- DO $$
-- BEGIN
--     IF EXISTS (SELECT 1 FROM information_schema.tables 
--                WHERE table_name = 'workflow_agent_states_old') THEN
--         INSERT INTO workflow_agent_states (
--             session_id, user_id, created_at, updated_at,
--             stage, intent_summary, conversations, 
--             current_workflow, debug_loop_count
--         )
--         SELECT 
--             session_id, user_id, created_at, updated_at,
--             stage, intent_summary, conversations,
--             current_workflow, debug_loop_count
--         FROM workflow_agent_states_old;
--     END IF;
-- END $$;