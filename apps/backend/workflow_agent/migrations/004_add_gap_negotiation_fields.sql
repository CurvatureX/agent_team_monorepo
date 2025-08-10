-- Migration to add gap negotiation tracking fields
-- Adds fields for enhanced gap analysis negotiation features
-- Note: clarification_ready is not included as it can be derived from state

-- Add gap_negotiation_count column
ALTER TABLE workflow_agent_states 
ADD COLUMN IF NOT EXISTS gap_negotiation_count INTEGER DEFAULT 0;

-- Add selected_alternative column
ALTER TABLE workflow_agent_states 
ADD COLUMN IF NOT EXISTS selected_alternative TEXT;

-- Add comments for new columns
COMMENT ON COLUMN workflow_agent_states.gap_negotiation_count IS 'Number of gap negotiation rounds with user';
COMMENT ON COLUMN workflow_agent_states.selected_alternative IS 'User-selected alternative from gap analysis';

-- Create index for gap_negotiation_count to optimize queries
CREATE INDEX IF NOT EXISTS idx_workflow_agent_states_gap_negotiation_count 
ON workflow_agent_states(gap_negotiation_count);

-- Note: clarification_ready is derived from state and not stored in database
-- It can be calculated as: no pending questions + has intent summary + not in gap negotiation