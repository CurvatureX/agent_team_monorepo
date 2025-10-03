-- Simplify deployment_status to 4 clear statuses
-- Description: Remove IDLE, DRAFT, UNDEPLOYING, DEPRECATED - keep only 4 clear statuses
-- Created: 2025-10-03

BEGIN;

-- ============================================================================
-- 1. Migrate existing data
-- ============================================================================

-- Update IDLE and DRAFT to UNDEPLOYED (default state for non-deployed workflows)
UPDATE workflows
SET deployment_status = 'UNDEPLOYED'
WHERE deployment_status IN ('IDLE', 'DRAFT');

-- Update UNDEPLOYING to DEPLOYING (transitional state)
UPDATE workflows
SET deployment_status = 'DEPLOYING'
WHERE deployment_status = 'UNDEPLOYING';

-- Update DEPRECATED to UNDEPLOYED (archived workflows)
UPDATE workflows
SET deployment_status = 'UNDEPLOYED'
WHERE deployment_status = 'DEPRECATED';

-- Update workflow_data JSONB metadata as well
UPDATE workflows
SET workflow_data = jsonb_set(workflow_data, '{metadata,deployment_status}', '"UNDEPLOYED"'::jsonb)
WHERE workflow_data->'metadata'->>'deployment_status' IN ('IDLE', 'DRAFT', 'DEPRECATED');

UPDATE workflows
SET workflow_data = jsonb_set(workflow_data, '{metadata,deployment_status}', '"DEPLOYING"'::jsonb)
WHERE workflow_data->'metadata'->>'deployment_status' = 'UNDEPLOYING';

-- ============================================================================
-- 2. Update CHECK constraint to only allow 4 statuses
-- ============================================================================

-- Drop old constraint
ALTER TABLE workflows DROP CONSTRAINT IF EXISTS valid_deployment_status;

-- Add new simplified constraint
ALTER TABLE workflows ADD CONSTRAINT valid_deployment_status CHECK (
    deployment_status IN ('UNDEPLOYED', 'DEPLOYING', 'DEPLOYED', 'DEPLOYMENT_FAILED')
);

-- Update default value
ALTER TABLE workflows ALTER COLUMN deployment_status SET DEFAULT 'UNDEPLOYED';

-- Update column comment
COMMENT ON COLUMN workflows.deployment_status IS 'Current deployment status: UNDEPLOYED (default), DEPLOYING (in progress), DEPLOYED (active), DEPLOYMENT_FAILED (error)';

COMMIT;
