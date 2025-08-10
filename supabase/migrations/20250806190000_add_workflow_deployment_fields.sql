-- Migration: Add workflow deployment management fields
-- Description: Enhance workflows table to support proper deployment lifecycle
-- Created: 2025-08-06

-- Add deployment-related fields to workflows table
ALTER TABLE workflows
ADD COLUMN deployment_status TEXT DEFAULT 'DRAFT',
ADD COLUMN deployed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN deployed_by UUID REFERENCES users(id),
ADD COLUMN undeployed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN deployment_version INTEGER DEFAULT 1,
ADD COLUMN deployment_config JSONB DEFAULT '{}';

-- Add deployment status constraint
ALTER TABLE workflows
ADD CONSTRAINT valid_deployment_status CHECK (
    deployment_status IN ('DRAFT', 'DEPLOYING', 'DEPLOYED', 'DEPLOYMENT_FAILED', 'UNDEPLOYING', 'UNDEPLOYED', 'DEPRECATED')
);

-- Create deployment history table for tracking deployment events
CREATE TABLE workflow_deployment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    deployment_action TEXT NOT NULL, -- 'DEPLOY', 'UNDEPLOY', 'UPDATE', 'ROLLBACK'
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    deployment_version INTEGER NOT NULL,
    deployment_config JSONB DEFAULT '{}',
    triggered_by UUID REFERENCES users(id),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    deployment_logs JSONB DEFAULT '{}',

    CONSTRAINT valid_deployment_action CHECK (
        deployment_action IN ('DEPLOY', 'UNDEPLOY', 'UPDATE', 'ROLLBACK')
    )
);

-- Indexes for performance
CREATE INDEX idx_workflows_deployment_status ON workflows(deployment_status);
CREATE INDEX idx_workflows_deployed_at ON workflows(deployed_at);
CREATE INDEX idx_workflows_deployed_by ON workflows(deployed_by);
CREATE INDEX idx_deployment_history_workflow_id ON workflow_deployment_history(workflow_id);
CREATE INDEX idx_deployment_history_action ON workflow_deployment_history(deployment_action);
CREATE INDEX idx_deployment_history_started_at ON workflow_deployment_history(started_at);

-- Comments for clarity
COMMENT ON COLUMN workflows.deployment_status IS 'Current deployment status of the workflow';
COMMENT ON COLUMN workflows.deployed_at IS 'Timestamp when workflow was last successfully deployed';
COMMENT ON COLUMN workflows.deployed_by IS 'User who deployed this workflow';
COMMENT ON COLUMN workflows.deployment_version IS 'Incremental deployment version number';
COMMENT ON COLUMN workflows.deployment_config IS 'Deployment-specific configuration and metadata';

COMMENT ON TABLE workflow_deployment_history IS 'Historical log of all deployment actions for workflows';
