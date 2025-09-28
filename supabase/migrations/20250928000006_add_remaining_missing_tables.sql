-- Add Remaining Missing Tables (Conflict-Free)
-- Description: Create only the tables that are truly missing and not defined in previous migrations
-- Replaces: 20250928000005_add_missing_tables_cleaned_models.sql (which had conflicts)
-- Tables to create: workflow_deployments, trigger_executions, trigger_status, email_messages
-- Created: 2025-09-28

BEGIN;

-- ============================================================================
-- 1. Create workflow_deployments table (scheduler service)
-- ============================================================================

CREATE TABLE IF NOT EXISTS workflow_deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deployment_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_id VARCHAR(255) NOT NULL,

    -- Deployment metadata
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'deployed', 'failed', 'undeployed')),
    workflow_spec JSONB NOT NULL DEFAULT '{}',
    trigger_specs JSONB NOT NULL DEFAULT '{}',

    -- Audit fields
    deployed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Optional user context
    deployed_by VARCHAR(255)
);

-- ============================================================================
-- 2. Create trigger_executions table
-- ============================================================================

CREATE TABLE IF NOT EXISTS trigger_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_id VARCHAR(255) NOT NULL,

    -- Trigger information
    trigger_type VARCHAR(50) NOT NULL CHECK (trigger_type IN ('CRON', 'MANUAL', 'WEBHOOK', 'EMAIL', 'GITHUB', 'SLACK')),
    trigger_data JSONB DEFAULT '{}',

    -- Execution status
    status VARCHAR(50) NOT NULL,
    message TEXT,

    -- Timing information
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,

    -- Engine response
    engine_response JSONB DEFAULT '{}'
);

-- ============================================================================
-- 3. Create trigger_status table
-- ============================================================================

CREATE TABLE IF NOT EXISTS trigger_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id VARCHAR(255) NOT NULL UNIQUE,
    trigger_type VARCHAR(50) NOT NULL CHECK (trigger_type IN ('CRON', 'MANUAL', 'WEBHOOK', 'EMAIL', 'GITHUB', 'SLACK')),

    -- Status information
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'paused', 'error', 'stopped')),
    last_execution TIMESTAMPTZ,
    next_execution TIMESTAMPTZ,

    -- Configuration
    trigger_config JSONB NOT NULL DEFAULT '{}',

    -- Health information
    error_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    last_error_at TIMESTAMPTZ,

    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 4. Create email_messages table (for email triggers)
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id VARCHAR(255) UNIQUE NOT NULL,

    -- Email metadata
    subject TEXT,
    sender VARCHAR(500),
    recipient VARCHAR(500),
    date_received TIMESTAMPTZ,

    -- Content
    body_text TEXT,
    body_html TEXT,
    attachments JSONB DEFAULT '[]',

    -- Processing information
    workflow_id VARCHAR(255),
    processed_at TIMESTAMPTZ,
    processing_status VARCHAR(50),

    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 5. Create indexes for performance
-- ============================================================================

-- Workflow deployments indexes
CREATE INDEX IF NOT EXISTS idx_workflow_deployments_deployment_id ON workflow_deployments(deployment_id);
CREATE INDEX IF NOT EXISTS idx_workflow_deployments_workflow_id ON workflow_deployments(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_deployments_status ON workflow_deployments(status);
CREATE INDEX IF NOT EXISTS idx_workflow_deployments_deployed_at ON workflow_deployments(deployed_at);

-- Trigger executions indexes
CREATE INDEX IF NOT EXISTS idx_trigger_executions_execution_id ON trigger_executions(execution_id);
CREATE INDEX IF NOT EXISTS idx_trigger_executions_workflow_id ON trigger_executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_trigger_executions_trigger_type ON trigger_executions(trigger_type);
CREATE INDEX IF NOT EXISTS idx_trigger_executions_status ON trigger_executions(status);
CREATE INDEX IF NOT EXISTS idx_trigger_executions_triggered_at ON trigger_executions(triggered_at);

-- Trigger status indexes
CREATE INDEX IF NOT EXISTS idx_trigger_status_workflow_id ON trigger_status(workflow_id);
CREATE INDEX IF NOT EXISTS idx_trigger_status_trigger_type ON trigger_status(trigger_type);
CREATE INDEX IF NOT EXISTS idx_trigger_status_status ON trigger_status(status);
CREATE INDEX IF NOT EXISTS idx_trigger_status_next_execution ON trigger_status(next_execution);

-- Email messages indexes
CREATE INDEX IF NOT EXISTS idx_email_messages_message_id ON email_messages(message_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_sender ON email_messages(sender);
CREATE INDEX IF NOT EXISTS idx_email_messages_recipient ON email_messages(recipient);
CREATE INDEX IF NOT EXISTS idx_email_messages_workflow_id ON email_messages(workflow_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_processing_status ON email_messages(processing_status);
CREATE INDEX IF NOT EXISTS idx_email_messages_date_received ON email_messages(date_received);

-- ============================================================================
-- 6. Add updated_at triggers for timestamp management
-- ============================================================================

-- Create triggers for automatic updated_at management
CREATE TRIGGER update_workflow_deployments_updated_at
    BEFORE UPDATE ON workflow_deployments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trigger_status_updated_at
    BEFORE UPDATE ON trigger_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 7. Add table comments for documentation
-- ============================================================================

COMMENT ON TABLE workflow_deployments IS 'Workflow deployment records for scheduler service';
COMMENT ON TABLE trigger_executions IS 'Trigger execution history and results';
COMMENT ON TABLE trigger_status IS 'Current status of active triggers per workflow';
COMMENT ON TABLE email_messages IS 'Email messages for email trigger processing';

-- Column comments for key fields
COMMENT ON COLUMN workflow_deployments.status IS 'Deployment status: pending, deployed, failed, undeployed';
COMMENT ON COLUMN trigger_status.workflow_id IS 'Unique workflow ID - one trigger status per workflow';
COMMENT ON COLUMN email_messages.processing_status IS 'Email processing status for workflow triggers';

COMMIT;
