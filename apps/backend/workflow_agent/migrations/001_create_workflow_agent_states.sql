-- Create workflow_agent_states table
-- This is the complete schema for the unified WorkflowState

CREATE TABLE IF NOT EXISTS workflow_agent_states (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core identity fields
    session_id UUID NOT NULL UNIQUE,
    user_id UUID,
    
    -- Timestamps
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    
    -- Stage management
    stage VARCHAR(50) NOT NULL CHECK (stage IN (
        'clarification', 
        'gap_analysis', 
        'workflow_generation', 
        'debug', 
        'end'
    )),
    previous_stage VARCHAR(50) CHECK (previous_stage IN (
        'clarification', 
        'gap_analysis', 
        'workflow_generation', 
        'debug', 
        'end'
    )),
    execution_history JSONB DEFAULT '[]',
    
    -- User interaction
    user_message TEXT DEFAULT '',
    conversations JSONB NOT NULL DEFAULT '[]',
    
    -- Clarification stage fields
    intent_summary TEXT DEFAULT '',
    clarification_context JSONB DEFAULT '{
        "purpose": "initial_intent",
        "questions_asked": [],
        "questions_pending": [],
        "info_collected": {},
        "round_count": 0
    }',
    clarification_questions JSONB DEFAULT '[]',
    
    -- Gap analysis stage fields
    gap_status VARCHAR(20) DEFAULT 'no_gap' CHECK (gap_status IN (
        'no_gap', 
        'has_alternatives', 
        'blocking'
    )),
    identified_gaps JSONB DEFAULT '[]',
    alternative_solutions JSONB DEFAULT '[]',
    selected_alternative_index INTEGER,
    
    -- Workflow generation stage fields
    workflow_context JSONB DEFAULT '{
        "origin": "create",
        "requirements": {}
    }',
    current_workflow_json TEXT DEFAULT '',
    template_workflow JSONB,
    
    -- Debug stage fields
    debug_result JSONB,
    debug_loop_count INTEGER DEFAULT 0,
    previous_errors JSONB DEFAULT '[]'
);

-- Create indexes for performance
CREATE INDEX idx_workflow_agent_states_session_id ON workflow_agent_states(session_id);
CREATE INDEX idx_workflow_agent_states_user_id ON workflow_agent_states(user_id);
CREATE INDEX idx_workflow_agent_states_stage ON workflow_agent_states(stage);
CREATE INDEX idx_workflow_agent_states_gap_status ON workflow_agent_states(gap_status);
CREATE INDEX idx_workflow_agent_states_updated_at ON workflow_agent_states(updated_at DESC);

-- Add table comment
COMMENT ON TABLE workflow_agent_states IS 
'Unified state storage for workflow agent. Matches WorkflowState TypedDict in agents/state.py';

-- Add column comments
COMMENT ON COLUMN workflow_agent_states.session_id IS 'Unique session identifier';
COMMENT ON COLUMN workflow_agent_states.user_id IS 'User identifier (nullable for anonymous)';
COMMENT ON COLUMN workflow_agent_states.stage IS 'Current workflow processing stage';
COMMENT ON COLUMN workflow_agent_states.previous_stage IS 'Previous stage for backtracking';
COMMENT ON COLUMN workflow_agent_states.user_message IS 'Latest user message in conversation';
COMMENT ON COLUMN workflow_agent_states.conversations IS 'Full conversation history';
COMMENT ON COLUMN workflow_agent_states.intent_summary IS 'Summarized user intent from clarification';
COMMENT ON COLUMN workflow_agent_states.clarification_context IS 'Metadata for clarification process';
COMMENT ON COLUMN workflow_agent_states.clarification_questions IS 'Current questions pending user response';
COMMENT ON COLUMN workflow_agent_states.gap_status IS 'Overall gap analysis status';
COMMENT ON COLUMN workflow_agent_states.identified_gaps IS 'List of capability gaps found';
COMMENT ON COLUMN workflow_agent_states.alternative_solutions IS 'Proposed alternative solutions';
COMMENT ON COLUMN workflow_agent_states.selected_alternative_index IS 'User-selected alternative (if any)';
COMMENT ON COLUMN workflow_agent_states.workflow_context IS 'Context for workflow generation';
COMMENT ON COLUMN workflow_agent_states.current_workflow_json IS 'Generated workflow JSON as text';
COMMENT ON COLUMN workflow_agent_states.template_workflow IS 'Template workflow if using one';
COMMENT ON COLUMN workflow_agent_states.debug_result IS 'Latest debug validation results';
COMMENT ON COLUMN workflow_agent_states.debug_loop_count IS 'Number of debug iterations';
COMMENT ON COLUMN workflow_agent_states.previous_errors IS 'Errors from previous debug attempts';