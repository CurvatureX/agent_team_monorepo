-- Deploy workflow_execution_logs table to remote Supabase
-- This script can be executed in the Supabase SQL Editor

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
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
CREATE TABLE IF NOT EXISTS workflow_execution_logs (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Execution reference
    execution_id VARCHAR(255) NOT NULL,

    -- Log categorization (using VARCHAR for compatibility)
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
CREATE INDEX IF NOT EXISTS idx_execution_logs_execution_id ON workflow_execution_logs(execution_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_category ON workflow_execution_logs(log_category);
CREATE INDEX IF NOT EXISTS idx_execution_logs_event_type ON workflow_execution_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_execution_logs_level ON workflow_execution_logs(level);
CREATE INDEX IF NOT EXISTS idx_execution_logs_priority ON workflow_execution_logs(display_priority);
CREATE INDEX IF NOT EXISTS idx_execution_logs_milestone ON workflow_execution_logs(is_milestone);
CREATE INDEX IF NOT EXISTS idx_execution_logs_created_at ON workflow_execution_logs(created_at);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_execution_logs_business_query
ON workflow_execution_logs(execution_id, log_category, display_priority)
WHERE log_category = 'business';

CREATE INDEX IF NOT EXISTS idx_execution_logs_technical_query
ON workflow_execution_logs(execution_id, log_category, level)
WHERE log_category = 'technical';

CREATE INDEX IF NOT EXISTS idx_execution_logs_milestones
ON workflow_execution_logs(execution_id, is_milestone, display_priority)
WHERE is_milestone = TRUE;

-- Create a partial index for recent logs (last 30 days)
CREATE INDEX IF NOT EXISTS idx_execution_logs_recent
ON workflow_execution_logs(execution_id, created_at, log_category)
WHERE created_at >= NOW() - INTERVAL '30 days';

-- Enable Row Level Security (RLS)
ALTER TABLE workflow_execution_logs ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
DROP POLICY IF EXISTS "Users can view their own execution logs" ON workflow_execution_logs;
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

DROP POLICY IF EXISTS "Service can insert execution logs" ON workflow_execution_logs;
CREATE POLICY "Service can insert execution logs" ON workflow_execution_logs
FOR INSERT WITH CHECK (
    auth.role() = 'service_role'
);

DROP POLICY IF EXISTS "Service can update execution logs" ON workflow_execution_logs;
CREATE POLICY "Service can update execution logs" ON workflow_execution_logs
FOR UPDATE USING (
    auth.role() = 'service_role'
);

-- Grant permissions
GRANT SELECT ON workflow_execution_logs TO anon, authenticated;
GRANT ALL ON workflow_execution_logs TO service_role;

-- Add table comments
COMMENT ON TABLE workflow_execution_logs IS 'Unified table for storing workflow execution logs, supporting both technical debugging and user-friendly business logs';

-- Test insert to verify everything works
INSERT INTO workflow_execution_logs (
    execution_id,
    log_category,
    event_type,
    level,
    message,
    user_friendly_message,
    display_priority,
    is_milestone
) VALUES (
    'deployment-test-' || extract(epoch from now())::text,
    'business',
    'workflow_started',
    'INFO',
    'Testing deployment of execution logs table',
    '✅ Execution logs table deployed successfully!',
    10,
    true
);

-- Verify the table was created correctly
SELECT
    'Table created successfully! Row count: ' || COUNT(*)::text as status
FROM workflow_execution_logs;
