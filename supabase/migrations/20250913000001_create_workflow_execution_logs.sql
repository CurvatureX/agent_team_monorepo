-- Migration: Create workflow_execution_logs table
-- Description: Creates the unified workflow execution logs table for storing both technical and user-friendly logs
-- Created: 2025-09-13
-- Author: Agent Team

-- Enable required extensions if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types for log categorization
DO $$
BEGIN
    -- Log level enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'log_level_enum') THEN
        CREATE TYPE log_level_enum AS ENUM ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL');
    END IF;

    -- Log event type enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'log_event_type_enum') THEN
        CREATE TYPE log_event_type_enum AS ENUM (
            'workflow_started',
            'workflow_completed',
            'workflow_progress',
            'step_started',
            'step_input',
            'step_output',
            'step_completed',
            'step_error',
            'separator'
        );
    END IF;
END
$$;

-- Create the workflow_execution_logs table
CREATE TABLE workflow_execution_logs (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Execution reference
    execution_id VARCHAR(255) NOT NULL,

    -- Log categorization (technical vs business/user-friendly)
    -- Using VARCHAR to match workflow_engine migration compatibility
    log_category VARCHAR(20) NOT NULL DEFAULT 'technical',

    -- Core log content
    event_type log_event_type_enum NOT NULL,
    level log_level_enum NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,

    -- Structured data
    data JSONB DEFAULT '{}',

    -- Node context information
    node_id VARCHAR(255),
    node_name VARCHAR(255),
    node_type VARCHAR(100),

    -- Execution progress tracking
    step_number INTEGER,
    total_steps INTEGER,
    progress_percentage DECIMAL(5,2),

    -- Performance metrics
    duration_seconds INTEGER,

    -- User-friendly display fields
    user_friendly_message TEXT,
    display_priority INTEGER NOT NULL DEFAULT 5,
    is_milestone BOOLEAN NOT NULL DEFAULT FALSE,

    -- Technical debugging information
    technical_details JSONB DEFAULT '{}',
    stack_trace TEXT,
    performance_metrics JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for optimal query performance
CREATE INDEX idx_execution_logs_execution_id ON workflow_execution_logs(execution_id);
CREATE INDEX idx_execution_logs_category ON workflow_execution_logs(log_category);
CREATE INDEX idx_execution_logs_event_type ON workflow_execution_logs(event_type);
CREATE INDEX idx_execution_logs_level ON workflow_execution_logs(level);
CREATE INDEX idx_execution_logs_priority ON workflow_execution_logs(display_priority);
CREATE INDEX idx_execution_logs_milestone ON workflow_execution_logs(is_milestone);
CREATE INDEX idx_execution_logs_created_at ON workflow_execution_logs(created_at);

-- Composite indexes for common query patterns
CREATE INDEX idx_execution_logs_business_query
ON workflow_execution_logs(execution_id, log_category, display_priority)
WHERE log_category = 'business';

CREATE INDEX idx_execution_logs_technical_query
ON workflow_execution_logs(execution_id, log_category, level)
WHERE log_category = 'technical';

CREATE INDEX idx_execution_logs_milestones
ON workflow_execution_logs(execution_id, is_milestone, display_priority)
WHERE is_milestone = TRUE;

-- Create a partial index for recent logs (last 30 days) for faster queries
CREATE INDEX idx_execution_logs_recent
ON workflow_execution_logs(execution_id, created_at, log_category)
WHERE created_at >= NOW() - INTERVAL '30 days';

-- Add comments for documentation
COMMENT ON TABLE workflow_execution_logs IS 'Unified table for storing workflow execution logs, supporting both technical debugging and user-friendly business logs';
COMMENT ON COLUMN workflow_execution_logs.log_category IS 'Categorizes logs as technical (debugging) or business (user-friendly)';
COMMENT ON COLUMN workflow_execution_logs.user_friendly_message IS 'Human-readable message for display in user interfaces';
COMMENT ON COLUMN workflow_execution_logs.display_priority IS 'Priority for display (1=lowest, 10=highest), default 5';
COMMENT ON COLUMN workflow_execution_logs.is_milestone IS 'Marks important milestone events for progress tracking';
COMMENT ON COLUMN workflow_execution_logs.technical_details IS 'Additional technical debugging information';
COMMENT ON COLUMN workflow_execution_logs.performance_metrics IS 'Performance and timing metrics for optimization';

-- Enable Row Level Security (RLS)
ALTER TABLE workflow_execution_logs ENABLE ROW LEVEL SECURITY;

-- Create RLS policy to allow users to see logs from their own workflow executions
-- Note: This assumes workflow_executions table exists and has proper RLS policies
CREATE POLICY "Users can view their own execution logs" ON workflow_execution_logs
FOR SELECT USING (
    EXISTS (
        SELECT 1
        FROM workflow_executions we
        JOIN workflows w ON w.id = we.workflow_id
        WHERE we.execution_id = workflow_execution_logs.execution_id
        AND w.user_id = auth.uid()
    )
);

-- Create RLS policy for inserting logs (service role only)
CREATE POLICY "Service can insert execution logs" ON workflow_execution_logs
FOR INSERT WITH CHECK (
    auth.role() = 'service_role'
);

-- Create RLS policy for updating logs (service role only)
CREATE POLICY "Service can update execution logs" ON workflow_execution_logs
FOR UPDATE USING (
    auth.role() = 'service_role'
);

-- Grant appropriate permissions
GRANT SELECT ON workflow_execution_logs TO anon, authenticated;
GRANT ALL ON workflow_execution_logs TO service_role;
