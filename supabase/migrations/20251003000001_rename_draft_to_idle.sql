-- Rename DRAFT to IDLE for workflow status
-- Description: Update workflow status enum from DRAFT to IDLE for better semantic clarity
-- DRAFT implied a temporary state, while IDLE better represents a workflow that's ready but not running
-- Created: 2025-10-03

BEGIN;

-- ============================================================================
-- 1. Update CHECK constraint to include IDLE
-- ============================================================================

-- Drop old constraint that only allows DRAFT
ALTER TABLE workflows DROP CONSTRAINT IF EXISTS valid_deployment_status;

-- Add new constraint that allows both IDLE and DRAFT (for transition period)
ALTER TABLE workflows ADD CONSTRAINT valid_deployment_status CHECK (
    deployment_status IN ('IDLE', 'DRAFT', 'DEPLOYING', 'DEPLOYED', 'DEPLOYMENT_FAILED', 'UNDEPLOYING', 'UNDEPLOYED', 'DEPRECATED')
);

-- ============================================================================
-- 2. Update workflows.deployment_status: DRAFT -> IDLE
-- ============================================================================

-- Update existing DRAFT values to IDLE in workflows table
UPDATE workflows
SET deployment_status = 'IDLE'
WHERE deployment_status = 'DRAFT';

-- Update default value for deployment_status column
ALTER TABLE workflows ALTER COLUMN deployment_status SET DEFAULT 'IDLE';

-- Update column comment to reflect new status name
COMMENT ON COLUMN workflows.deployment_status IS 'Current deployment status: IDLE (never deployed), pending, deployed, failed, undeployed';

-- ============================================================================
-- 3. Update workflows.latest_execution_status: DRAFT -> IDLE
-- ============================================================================

-- Update existing DRAFT values to IDLE in latest_execution_status
UPDATE workflows
SET latest_execution_status = 'IDLE'
WHERE latest_execution_status = 'DRAFT';

-- Update default value for latest_execution_status column
ALTER TABLE workflows ALTER COLUMN latest_execution_status SET DEFAULT 'IDLE';

-- Update column comment to reflect new status name
COMMENT ON COLUMN workflows.latest_execution_status IS 'Status of the most recent execution (IDLE, RUNNING, SUCCESS, ERROR, CANCELED, WAITING_FOR_HUMAN)';

-- ============================================================================
-- 4. Update workflow_executions status if using DRAFT (unlikely but for safety)
-- ============================================================================

-- Check if workflow_executions has any DRAFT statuses and update them
-- This is a safety measure as executions typically use NEW, not DRAFT
UPDATE workflow_executions
SET status = 'IDLE'
WHERE status = 'DRAFT';

COMMIT;
