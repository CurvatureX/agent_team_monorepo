-- Optional cleanup migration to remove clarification_ready column
-- This is only needed if clarification_ready was already added to your database
-- The column is no longer needed as the value is derived from state

-- Drop the column if it exists
ALTER TABLE workflow_agent_states 
DROP COLUMN IF EXISTS clarification_ready;

-- Note: This migration is optional and only needed for databases that
-- previously had clarification_ready column added.
-- New deployments should use 004_add_gap_negotiation_fields.sql directly.