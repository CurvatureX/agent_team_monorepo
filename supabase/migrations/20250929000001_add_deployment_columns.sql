-- Migration: Add missing deployment columns to workflows table
-- Description: Align workflows table schema with WorkflowDB data model
-- Created: 2025-09-29
-- Author: Claude Code

-- Add deployment-related columns that are missing from the workflows table
-- These columns are defined in shared/models/db_models.py but missing from the initial migration

ALTER TABLE workflows ADD COLUMN IF NOT EXISTS deployment_status VARCHAR(50) NOT NULL DEFAULT 'DRAFT';
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS deployed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS deployed_by UUID;
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS undeployed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS deployment_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS deployment_config JSON NOT NULL DEFAULT '{}';

-- Add indexes for deployment-related columns to improve query performance
CREATE INDEX IF NOT EXISTS idx_workflows_deployment_status ON workflows(deployment_status);
CREATE INDEX IF NOT EXISTS idx_workflows_deployed_at ON workflows(deployed_at);
CREATE INDEX IF NOT EXISTS idx_workflows_deployment_version ON workflows(deployment_version);

-- Add foreign key constraint for deployed_by referencing auth.users
-- Note: We don't add the constraint immediately to avoid issues with existing data
-- ALTER TABLE workflows ADD CONSTRAINT fk_workflows_deployed_by FOREIGN KEY (deployed_by) REFERENCES auth.users(id);

-- Verify the migration by checking that all columns exist
DO $$
DECLARE
    missing_columns TEXT[] := ARRAY[]::TEXT[];
    col TEXT;
BEGIN
    -- Check for required columns
    FOR col IN SELECT unnest(ARRAY['deployment_status', 'deployed_at', 'deployed_by', 'undeployed_at', 'deployment_version', 'deployment_config'])
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'workflows' AND column_name = col
        ) THEN
            missing_columns := array_append(missing_columns, col);
        END IF;
    END LOOP;

    IF array_length(missing_columns, 1) > 0 THEN
        RAISE EXCEPTION 'Migration failed: Missing columns: %', array_to_string(missing_columns, ', ');
    ELSE
        RAISE NOTICE 'Migration successful: All deployment columns added to workflows table';
    END IF;
END $$;
