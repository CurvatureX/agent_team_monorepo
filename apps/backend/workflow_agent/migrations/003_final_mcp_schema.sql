-- Final workflow_agent_states table schema after MCP integration
-- This is the complete schema matching state.py in the MCP-integrated version

-- Drop and recreate table with correct structure
DROP TABLE IF EXISTS workflow_agent_states CASCADE;

CREATE TABLE workflow_agent_states (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core identity fields (from WorkflowState)
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255),
    
    -- Timestamps
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    
    -- Stage management
    stage VARCHAR(50) NOT NULL CHECK (stage IN (
        'clarification', 
        'gap_analysis', 
        'workflow_generation', 
        'debug', 
        'completed'  -- Note: 'completed' not 'end'
    )),
    previous_stage VARCHAR(50) CHECK (previous_stage IN (
        'clarification', 
        'gap_analysis', 
        'workflow_generation', 
        'debug', 
        'completed'
    )),
    
    -- Core workflow data
    intent_summary TEXT DEFAULT '',
    conversations JSONB NOT NULL DEFAULT '[]',
    execution_history JSONB DEFAULT '[]',
    
    -- Clarification context
    clarification_context JSONB DEFAULT '{
        "purpose": "initial_intent",
        "collected_info": {},
        "pending_questions": [],
        "origin": "create"
    }',
    
    -- Gap analysis results
    gap_status VARCHAR(20) DEFAULT 'no_gap' CHECK (gap_status IN (
        'no_gap', 
        'has_gap',
        'gap_resolved',
        'blocking'
    )),
    identified_gaps JSONB DEFAULT '[]',
    
    -- Workflow data
    current_workflow JSONB,
    template_workflow JSONB,
    workflow_context JSONB DEFAULT '{
        "origin": "create",
        "requirements": {}
    }',
    
    -- Debug information
    debug_result JSONB,
    debug_loop_count INTEGER DEFAULT 0,
    
    -- Template information
    template_id VARCHAR(255)
);

-- Create indexes for performance
CREATE INDEX idx_workflow_agent_states_session_id ON workflow_agent_states(session_id);
CREATE INDEX idx_workflow_agent_states_user_id ON workflow_agent_states(user_id);
CREATE INDEX idx_workflow_agent_states_stage ON workflow_agent_states(stage);
CREATE INDEX idx_workflow_agent_states_gap_status ON workflow_agent_states(gap_status);
CREATE INDEX idx_workflow_agent_states_updated_at ON workflow_agent_states(updated_at DESC);
CREATE INDEX idx_workflow_agent_states_template_id ON workflow_agent_states(template_id);

-- JSONB GIN indexes for complex queries
CREATE INDEX idx_workflow_agent_states_conversations ON workflow_agent_states USING GIN (conversations);
CREATE INDEX idx_workflow_agent_states_current_workflow ON workflow_agent_states USING GIN (current_workflow);
CREATE INDEX idx_workflow_agent_states_identified_gaps ON workflow_agent_states USING GIN (identified_gaps);

-- Add table comment
COMMENT ON TABLE workflow_agent_states IS 
'State storage for workflow agent with MCP integration. Matches WorkflowState TypedDict in agents/state.py';

-- Add column comments
COMMENT ON COLUMN workflow_agent_states.session_id IS 'Unique session identifier';
COMMENT ON COLUMN workflow_agent_states.user_id IS 'User identifier (nullable for anonymous)';
COMMENT ON COLUMN workflow_agent_states.stage IS 'Current workflow processing stage (completed, not end)';
COMMENT ON COLUMN workflow_agent_states.previous_stage IS 'Previous stage for backtracking';
COMMENT ON COLUMN workflow_agent_states.intent_summary IS 'Summarized user intent from clarification';
COMMENT ON COLUMN workflow_agent_states.conversations IS 'Full conversation history as List[Conversation]';
COMMENT ON COLUMN workflow_agent_states.execution_history IS 'Execution history for debugging';
COMMENT ON COLUMN workflow_agent_states.clarification_context IS 'Context for clarification process (ClarificationContext)';
COMMENT ON COLUMN workflow_agent_states.gap_status IS 'Overall gap analysis status';
COMMENT ON COLUMN workflow_agent_states.identified_gaps IS 'List of GapDetail objects';
COMMENT ON COLUMN workflow_agent_states.current_workflow IS 'Generated workflow JSON object';
COMMENT ON COLUMN workflow_agent_states.template_workflow IS 'Template workflow if editing';
COMMENT ON COLUMN workflow_agent_states.workflow_context IS 'Workflow generation metadata';
COMMENT ON COLUMN workflow_agent_states.debug_result IS 'Structured debug result Dict[str, Any]';
COMMENT ON COLUMN workflow_agent_states.debug_loop_count IS 'Number of debug iterations';
COMMENT ON COLUMN workflow_agent_states.template_id IS 'Template ID if using template';

-- Updated timestamp trigger
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

-- Example data types for JSONB fields:

-- conversations: List[Conversation]
-- [{
--     "role": "user",
--     "text": "Create a daily notification workflow",
--     "timestamp": 1234567890000,
--     "metadata": {}
-- }]

-- clarification_context: ClarificationContext
-- {
--     "purpose": "initial_intent",
--     "collected_info": {"key": "value"},
--     "pending_questions": ["What time?", "Which channel?"],
--     "origin": "create"
-- }

-- identified_gaps: List[GapDetail]
-- [{
--     "required_capability": "slack_api",
--     "missing_component": "api_key",
--     "alternatives": ["webhook", "manual"]
-- }]

-- debug_result: Dict[str, Any]
-- {
--     "success": true,
--     "errors": [],
--     "warnings": ["Consider adding error handling"],
--     "suggestions": ["Add retry logic"],
--     "iteration_count": 1,
--     "timestamp": 1234567890000
-- }

-- workflow_context: Dict[str, Any]
-- {
--     "origin": "create",
--     "requirements": {
--         "platform": "slack",
--         "frequency": "daily"
--     }
-- }