-- Align database schema with shared models
-- Description: Update database constraints and enums to match our shared models
-- This migration ensures database schema consistency with /apps/backend/shared/models/
-- Created: 2025-09-28

BEGIN;

-- ============================================================================
-- 1. Fix deployment_status constraint to match our models
-- ============================================================================

-- Drop existing constraint
ALTER TABLE workflows DROP CONSTRAINT IF EXISTS valid_deployment_status;

-- Add new constraint that matches our WorkflowDeploymentStatus enum
ALTER TABLE workflows ADD CONSTRAINT valid_deployment_status CHECK (
    deployment_status IN ('pending', 'deployed', 'failed', 'undeployed')
);

-- Update existing records to use lowercase values
UPDATE workflows
SET deployment_status = CASE
    WHEN deployment_status = 'DRAFT' THEN 'pending'
    WHEN deployment_status = 'DEPLOYED' THEN 'deployed'
    WHEN deployment_status = 'DEPLOYMENT_FAILED' THEN 'failed'
    WHEN deployment_status = 'UNDEPLOYED' THEN 'undeployed'
    WHEN deployment_status = 'DEPLOYING' THEN 'pending'
    WHEN deployment_status = 'UNDEPLOYING' THEN 'pending'
    WHEN deployment_status = 'DEPRECATED' THEN 'undeployed'
    ELSE 'pending'
END
WHERE deployment_status IS NOT NULL;

-- Set default to 'pending' to match our models
ALTER TABLE workflows ALTER COLUMN deployment_status SET DEFAULT 'pending';

-- ============================================================================
-- 2. Fix execution status constraints to match ExecutionStatus enum
-- ============================================================================

-- Drop existing execution status constraint if exists
ALTER TABLE workflow_executions DROP CONSTRAINT IF EXISTS valid_execution_status;

-- Add constraint that matches our ExecutionStatus enum from execution_new.py
ALTER TABLE workflow_executions ADD CONSTRAINT valid_execution_status CHECK (
    status IN ('NEW', 'PENDING', 'RUNNING', 'PAUSED', 'SUCCESS', 'ERROR', 'CANCELED', 'WAITING', 'TIMEOUT', 'WAITING_FOR_HUMAN', 'SKIPPED', 'COMPLETED', 'CANCELLED')
);

-- Update latest_execution_status in workflows to match
UPDATE workflows
SET latest_execution_status = CASE
    WHEN latest_execution_status = 'DRAFT' THEN 'NEW'
    ELSE latest_execution_status
END
WHERE latest_execution_status IS NOT NULL;

-- Set default for latest_execution_status to 'NEW'
ALTER TABLE workflows ALTER COLUMN latest_execution_status SET DEFAULT 'NEW';

-- ============================================================================
-- 3. Add missing core tables from shared models
-- ============================================================================

-- Create users table (referenced by workflows.user_id but missing)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100),
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create user_sessions table for session management
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create external_connections table for OAuth/integrations
CREATE TABLE IF NOT EXISTS external_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    connection_id VARCHAR(255) UNIQUE NOT NULL,
    provider VARCHAR(100) NOT NULL,
    provider_user_id VARCHAR(255),
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMPTZ,
    scopes JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Note: workflow_deployment_history table already created in 20250806190000_add_workflow_deployment_fields.sql

-- ============================================================================
-- 4. Add proper foreign key constraints
-- ============================================================================

-- Add foreign key constraint for workflows.user_id (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'workflows_user_id_fkey'
        AND table_name = 'workflows'
    ) THEN
        ALTER TABLE workflows ADD CONSTRAINT workflows_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;

-- ============================================================================
-- 5. Add indexes for performance
-- ============================================================================

-- User table indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Session table indexes
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);

-- External connections indexes
CREATE INDEX IF NOT EXISTS idx_external_connections_user_id ON external_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_external_connections_provider ON external_connections(provider);
CREATE INDEX IF NOT EXISTS idx_external_connections_is_active ON external_connections(is_active);

-- Note: Deployment history indexes created in 20250806190000_add_workflow_deployment_fields.sql

-- ============================================================================
-- 6. Add comments for documentation
-- ============================================================================

COMMENT ON TABLE users IS 'User accounts and profiles';
COMMENT ON TABLE user_sessions IS 'User session management for authentication';
COMMENT ON TABLE external_connections IS 'OAuth and external service connections';
-- Note: workflow_deployment_history comments in 20250806190000_add_workflow_deployment_fields.sql

COMMENT ON COLUMN workflows.deployment_status IS 'Current deployment status: pending, deployed, failed, undeployed';
COMMENT ON COLUMN workflows.latest_execution_status IS 'Status of the most recent execution';

-- ============================================================================
-- 7. Update triggers for timestamp management
-- ============================================================================

-- Create updated_at trigger function if not exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add updated_at triggers for new tables
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_sessions_updated_at
    BEFORE UPDATE ON user_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_external_connections_updated_at
    BEFORE UPDATE ON external_connections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT;
