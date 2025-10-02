-- Migration: Add missing tables for workflow scheduler service
-- Description: Add trigger_index and workflow_deployment_history tables
-- Created: 2025-09-29
-- Author: Claude Code

-- Create trigger_index table for workflow scheduler trigger management
CREATE TABLE IF NOT EXISTS trigger_index (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL,
    trigger_type VARCHAR(50) NOT NULL,
    trigger_subtype VARCHAR(100) NOT NULL,
    trigger_config JSON NOT NULL DEFAULT '{}',
    deployment_status VARCHAR(50) NOT NULL DEFAULT 'active',
    index_key VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_trigger_type CHECK (
        trigger_type IN ('TRIGGER')
    ),
    CONSTRAINT valid_trigger_subtype CHECK (
        trigger_subtype IN ('CRON', 'MANUAL', 'WEBHOOK', 'EMAIL', 'GITHUB', 'SLACK')
    ),
    CONSTRAINT valid_deployment_status CHECK (
        deployment_status IN ('active', 'inactive', 'pending', 'failed')
    ),

    -- Unique index key per workflow
    UNIQUE(workflow_id, index_key)
);

-- Create workflow_deployment_history table for deployment tracking
CREATE TABLE IF NOT EXISTS workflow_deployment_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL,
    deployment_action VARCHAR(50) NOT NULL,
    from_status VARCHAR(50) NOT NULL,
    to_status VARCHAR(50) NOT NULL,
    deployment_version INTEGER NOT NULL,
    deployment_config JSON NOT NULL DEFAULT '{}',
    triggered_by UUID,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    deployment_logs JSON DEFAULT '{}',

    -- Constraints
    CONSTRAINT valid_deployment_action CHECK (
        deployment_action IN ('DEPLOY', 'UNDEPLOY', 'UPDATE', 'ROLLBACK', 'DEPLOY_STARTED', 'DEPLOY_COMPLETED', 'DEPLOY_FAILED', 'UNDEPLOY_STARTED', 'UNDEPLOY_COMPLETED')
    ),
    CONSTRAINT valid_deployment_status CHECK (
        from_status IN ('DRAFT', 'PENDING', 'DEPLOYED', 'FAILED', 'UNDEPLOYED', 'UNDEPLOYING') AND
        to_status IN ('DRAFT', 'PENDING', 'DEPLOYED', 'FAILED', 'UNDEPLOYED', 'UNDEPLOYING')
    )
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_trigger_index_workflow_id ON trigger_index(workflow_id);
CREATE INDEX IF NOT EXISTS idx_trigger_index_type ON trigger_index(trigger_type, trigger_subtype);
CREATE INDEX IF NOT EXISTS idx_trigger_index_status ON trigger_index(deployment_status);
CREATE INDEX IF NOT EXISTS idx_trigger_index_active ON trigger_index(is_active);
CREATE INDEX IF NOT EXISTS idx_trigger_index_created_at ON trigger_index(created_at);

CREATE INDEX IF NOT EXISTS idx_deployment_history_workflow_id ON workflow_deployment_history(workflow_id);
CREATE INDEX IF NOT EXISTS idx_deployment_history_action ON workflow_deployment_history(deployment_action);
CREATE INDEX IF NOT EXISTS idx_deployment_history_status ON workflow_deployment_history(from_status, to_status);
CREATE INDEX IF NOT EXISTS idx_deployment_history_version ON workflow_deployment_history(deployment_version);
CREATE INDEX IF NOT EXISTS idx_deployment_history_started_at ON workflow_deployment_history(started_at);

-- Add triggers for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_trigger_index_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_trigger_index_updated_at
    BEFORE UPDATE ON trigger_index
    FOR EACH ROW EXECUTE FUNCTION update_trigger_index_updated_at();

-- Add Row Level Security (RLS) policies
ALTER TABLE trigger_index ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_deployment_history ENABLE ROW LEVEL SECURITY;

-- RLS policies for trigger_index (users can only see their own workflow triggers)
CREATE POLICY trigger_index_user_policy ON trigger_index
    FOR ALL USING (
        workflow_id IN (
            SELECT id FROM workflows WHERE user_id = auth.uid()
        )
    );

-- RLS policies for workflow_deployment_history (users can only see their own deployment history)
CREATE POLICY deployment_history_user_policy ON workflow_deployment_history
    FOR ALL USING (
        workflow_id IN (
            SELECT id FROM workflows WHERE user_id = auth.uid()
        )
    );

-- Verify migration success
DO $$
DECLARE
    missing_tables TEXT[] := ARRAY[]::TEXT[];
    missing_columns TEXT[] := ARRAY[]::TEXT[];
    table_name TEXT;
    col TEXT;
BEGIN
    -- Check for required tables
    FOR table_name IN SELECT unnest(ARRAY['trigger_index', 'workflow_deployment_history'])
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = table_name
        ) THEN
            missing_tables := array_append(missing_tables, table_name);
        END IF;
    END LOOP;

    -- Check for required columns in workflows table
    FOR col IN SELECT unnest(ARRAY['deployment_status', 'deployed_at', 'deployed_by', 'undeployed_at', 'deployment_version', 'deployment_config'])
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'workflows' AND column_name = col
        ) THEN
            missing_columns := array_append(missing_columns, col);
        END IF;
    END LOOP;

    IF array_length(missing_tables, 1) > 0 OR array_length(missing_columns, 1) > 0 THEN
        RAISE EXCEPTION 'Migration verification failed - Missing tables: %, Missing columns: %',
            COALESCE(array_to_string(missing_tables, ', '), 'none'),
            COALESCE(array_to_string(missing_columns, ', '), 'none');
    ELSE
        RAISE NOTICE '✅ Migration 20250929000002 completed successfully - All workflow scheduler tables and columns created';
    END IF;
END $$;
