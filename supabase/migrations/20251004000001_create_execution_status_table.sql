-- Migration: Create execution_status table for real-time execution tracking
-- Description: Separate table for caching execution status without full execution data
-- Created: 2025-10-04
-- Author: Claude Code Assistant

BEGIN;

-- Create execution_status table for lightweight status tracking
CREATE TABLE IF NOT EXISTS execution_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'NEW',
    current_node_id VARCHAR(255),
    progress_data JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure status matches valid values
    CONSTRAINT valid_status CHECK (
        status IN ('NEW', 'PENDING', 'RUNNING', 'PAUSED', 'SUCCESS', 'ERROR',
                   'CANCELED', 'WAITING', 'TIMEOUT', 'WAITING_FOR_HUMAN',
                   'SKIPPED', 'COMPLETED', 'CANCELLED', 'IDLE')
    )
);

-- Index for fast lookups by execution_id
CREATE INDEX IF NOT EXISTS idx_execution_status_execution_id ON execution_status(execution_id);

-- Index for querying by workflow_id
CREATE INDEX IF NOT EXISTS idx_execution_status_workflow_id ON execution_status(workflow_id);

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_execution_status_status ON execution_status(status);

-- Index for latest status by updated_at
CREATE INDEX IF NOT EXISTS idx_execution_status_updated_at ON execution_status(updated_at DESC);

-- Composite index for workflow status queries
CREATE INDEX IF NOT EXISTS idx_execution_status_workflow_updated
    ON execution_status(workflow_id, updated_at DESC);

-- Auto-update updated_at timestamp
CREATE TRIGGER update_execution_status_updated_at
    BEFORE UPDATE ON execution_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS policies
ALTER TABLE execution_status ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view execution status for their workflows
CREATE POLICY "Users can view their workflow execution status" ON execution_status
    FOR SELECT
    USING (
        workflow_id IN (
            SELECT id FROM workflows WHERE user_id = auth.uid()
        )
    );

-- Policy: Service role can manage all execution status
CREATE POLICY "Service role can manage all execution status" ON execution_status
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- Add table comment
COMMENT ON TABLE execution_status IS 'Real-time execution status tracking with lightweight caching (separate from full workflow_executions)';
COMMENT ON COLUMN execution_status.execution_id IS 'Unique execution identifier';
COMMENT ON COLUMN execution_status.workflow_id IS 'Reference to parent workflow';
COMMENT ON COLUMN execution_status.status IS 'Current execution status';
COMMENT ON COLUMN execution_status.current_node_id IS 'Currently executing node ID';
COMMENT ON COLUMN execution_status.progress_data IS 'Execution progress metadata';
COMMENT ON COLUMN execution_status.error_message IS 'Latest error message if status is ERROR';

COMMIT;

-- Log migration success
DO $$
BEGIN
    RAISE NOTICE 'Successfully created execution_status table for real-time status tracking';
END $$;
