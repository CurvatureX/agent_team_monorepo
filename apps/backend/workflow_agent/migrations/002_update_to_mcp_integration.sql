-- Update workflow_agent_states table for MCP integration
-- Aligns with state.py after removing RAG and adopting MCP

-- 1. Update stage enum to use 'completed' instead of 'end'
ALTER TABLE workflow_agent_states 
DROP CONSTRAINT IF EXISTS workflow_agent_states_stage_check;

ALTER TABLE workflow_agent_states 
ADD CONSTRAINT workflow_agent_states_stage_check 
CHECK (stage IN ('clarification', 'gap_analysis', 'workflow_generation', 'debug', 'completed'));

ALTER TABLE workflow_agent_states 
DROP CONSTRAINT IF EXISTS workflow_agent_states_previous_stage_check;

ALTER TABLE workflow_agent_states 
ADD CONSTRAINT workflow_agent_states_previous_stage_check 
CHECK (previous_stage IN ('clarification', 'gap_analysis', 'workflow_generation', 'debug', 'completed'));

-- 2. Update gap_status values to match current usage
ALTER TABLE workflow_agent_states 
DROP CONSTRAINT IF EXISTS workflow_agent_states_gap_status_check;

ALTER TABLE workflow_agent_states 
ADD CONSTRAINT workflow_agent_states_gap_status_check 
CHECK (gap_status IN ('no_gap', 'has_gap', 'gap_resolved', 'blocking'));

-- 3. Remove unused columns that don't exist in state.py
ALTER TABLE workflow_agent_states DROP COLUMN IF EXISTS user_message;
ALTER TABLE workflow_agent_states DROP COLUMN IF EXISTS clarification_questions;
ALTER TABLE workflow_agent_states DROP COLUMN IF EXISTS alternative_solutions;
ALTER TABLE workflow_agent_states DROP COLUMN IF EXISTS selected_alternative_index;
ALTER TABLE workflow_agent_states DROP COLUMN IF EXISTS current_workflow_json;
ALTER TABLE workflow_agent_states DROP COLUMN IF EXISTS previous_errors;

-- 4. Add missing columns from state.py
ALTER TABLE workflow_agent_states 
ADD COLUMN IF NOT EXISTS current_workflow JSONB;

ALTER TABLE workflow_agent_states 
ADD COLUMN IF NOT EXISTS template_id VARCHAR(255);

-- 5. Update column comments to reflect MCP integration
COMMENT ON TABLE workflow_agent_states IS 
'State storage for workflow agent with MCP integration. Matches WorkflowState TypedDict in agents/state.py';

COMMENT ON COLUMN workflow_agent_states.stage IS 'Current workflow processing stage (completed, not end)';
COMMENT ON COLUMN workflow_agent_states.current_workflow IS 'Generated workflow JSON object';
COMMENT ON COLUMN workflow_agent_states.template_id IS 'Template ID if using template';
COMMENT ON COLUMN workflow_agent_states.debug_result IS 'Structured debug result with success, errors, warnings, suggestions';

-- 6. Migrate existing data if necessary
UPDATE workflow_agent_states 
SET stage = 'completed' 
WHERE stage = 'end';

UPDATE workflow_agent_states 
SET previous_stage = 'completed' 
WHERE previous_stage = 'end';