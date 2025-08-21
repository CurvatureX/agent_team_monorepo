-- Migration: Expand deployment actions for better tracking
-- Description: Add more granular deployment action types for better lifecycle tracking
-- Created: 2025-08-17

-- Drop the existing constraint
ALTER TABLE workflow_deployment_history
DROP CONSTRAINT valid_deployment_action;

-- Add the new constraint with expanded action types
ALTER TABLE workflow_deployment_history
ADD CONSTRAINT valid_deployment_action CHECK (
    deployment_action IN (
        'DEPLOY',
        'UNDEPLOY',
        'UPDATE',
        'ROLLBACK',
        'DEPLOY_STARTED',
        'DEPLOY_COMPLETED',
        'DEPLOY_FAILED',
        'UNDEPLOY_STARTED',
        'UNDEPLOY_COMPLETED',
        'UNDEPLOY_FAILED',
        'UPDATE_STARTED',
        'UPDATE_COMPLETED',
        'UPDATE_FAILED',
        'ROLLBACK_STARTED',
        'ROLLBACK_COMPLETED',
        'ROLLBACK_FAILED'
    )
);

-- Update comment to reflect the expanded actions
COMMENT ON COLUMN workflow_deployment_history.deployment_action IS 'Deployment action type - supports both high-level (DEPLOY, UNDEPLOY, UPDATE, ROLLBACK) and granular tracking (_STARTED, _COMPLETED, _FAILED)';
