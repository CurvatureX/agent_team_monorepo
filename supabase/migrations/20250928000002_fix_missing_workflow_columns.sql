-- Fix missing workflow columns
-- Description: Add all missing columns that should have been applied by previous migrations
-- This migration consolidates missing deployment and execution tracking columns
-- Created: 2025-09-28

BEGIN;

-- Add deployment status column if it doesn't exist
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS deployment_status TEXT DEFAULT 'DRAFT';
COMMENT ON COLUMN workflows.deployment_status IS 'Current deployment status of the workflow';

-- Add latest execution tracking columns if they don't exist
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS latest_execution_status VARCHAR(50) DEFAULT 'DRAFT';
COMMENT ON COLUMN workflows.latest_execution_status IS 'Status of the most recent execution (DRAFT, RUNNING, SUCCESS, ERROR, CANCELED, WAITING_FOR_HUMAN)';

ALTER TABLE workflows ADD COLUMN IF NOT EXISTS latest_execution_id VARCHAR(255);
COMMENT ON COLUMN workflows.latest_execution_id IS 'ID of the most recent execution';

ALTER TABLE workflows ADD COLUMN IF NOT EXISTS latest_execution_time TIMESTAMPTZ;
COMMENT ON COLUMN workflows.latest_execution_time IS 'Timestamp of the most recent execution';

-- Add icon URL column if it doesn't exist
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS icon_url VARCHAR(500);
COMMENT ON COLUMN workflows.icon_url IS 'URL to the workflow icon/image for visual identification in UI';

-- Add indexes for performance if they don't exist
CREATE INDEX IF NOT EXISTS idx_workflows_deployment_status ON workflows(deployment_status);
CREATE INDEX IF NOT EXISTS idx_workflows_latest_execution_status ON workflows(latest_execution_status);

-- Add deployment status constraint if it doesn't exist
ALTER TABLE workflows ADD CONSTRAINT IF NOT EXISTS valid_deployment_status CHECK (
    deployment_status IN ('DRAFT', 'DEPLOYING', 'DEPLOYED', 'DEPLOYMENT_FAILED', 'UNDEPLOYING', 'UNDEPLOYED', 'DEPRECATED')
);

-- Update existing workflows to have proper default values
UPDATE workflows
SET deployment_status = 'DRAFT'
WHERE deployment_status IS NULL;

UPDATE workflows
SET latest_execution_status = 'DRAFT'
WHERE latest_execution_status IS NULL;

COMMIT;
