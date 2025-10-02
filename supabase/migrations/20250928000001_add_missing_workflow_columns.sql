-- Add missing workflow columns for v2 engine compatibility
-- These columns are required by the workflow engine v2 for proper workflow persistence

-- Add deployment_status if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'workflows' AND column_name = 'deployment_status') THEN
        ALTER TABLE workflows ADD COLUMN deployment_status TEXT DEFAULT 'DRAFT';

        -- Add deployment status constraint
        ALTER TABLE workflows ADD CONSTRAINT valid_deployment_status CHECK (
            deployment_status IN ('DRAFT', 'DEPLOYING', 'DEPLOYED', 'DEPLOYMENT_FAILED', 'UNDEPLOYING', 'UNDEPLOYED', 'DEPRECATED')
        );

        -- Add index for performance
        CREATE INDEX idx_workflows_deployment_status ON workflows(deployment_status);
    END IF;
END $$;

-- Add latest_execution_status if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'workflows' AND column_name = 'latest_execution_status') THEN
        ALTER TABLE workflows ADD COLUMN latest_execution_status VARCHAR(50) DEFAULT 'DRAFT';
        CREATE INDEX idx_workflows_latest_execution_status ON workflows(latest_execution_status);
    END IF;
END $$;

-- Add latest_execution_time if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'workflows' AND column_name = 'latest_execution_time') THEN
        ALTER TABLE workflows ADD COLUMN latest_execution_time TIMESTAMPTZ;
    END IF;
END $$;

-- Add latest_execution_id if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'workflows' AND column_name = 'latest_execution_id') THEN
        ALTER TABLE workflows ADD COLUMN latest_execution_id VARCHAR(255);
    END IF;
END $$;

-- Add icon_url if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'workflows' AND column_name = 'icon_url') THEN
        ALTER TABLE workflows ADD COLUMN icon_url VARCHAR(500);
    END IF;
END $$;

-- Add comments for documentation
COMMENT ON COLUMN workflows.deployment_status IS 'Current deployment status of the workflow';
COMMENT ON COLUMN workflows.latest_execution_status IS 'Status of the most recent execution (DRAFT, RUNNING, SUCCESS, ERROR, CANCELED, WAITING_FOR_HUMAN)';
COMMENT ON COLUMN workflows.latest_execution_id IS 'ID of the most recent execution';
COMMENT ON COLUMN workflows.latest_execution_time IS 'Timestamp of the most recent execution';
COMMENT ON COLUMN workflows.icon_url IS 'URL to the workflow icon/image for visual identification in UI';
