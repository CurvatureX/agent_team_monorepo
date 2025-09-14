-- Add latest execution status tracking fields to workflows table
-- This allows quick access to workflow execution health without joins

-- Add latest execution status columns
ALTER TABLE workflows
ADD COLUMN latest_execution_status VARCHAR(50) DEFAULT 'DRAFT',
ADD COLUMN latest_execution_id VARCHAR(255),
ADD COLUMN latest_execution_time TIMESTAMPTZ;

-- Add index on latest_execution_status for efficient filtering
CREATE INDEX idx_workflows_latest_execution_status ON workflows (latest_execution_status);

-- Update existing workflows to have DRAFT status if they have never been executed
UPDATE workflows
SET latest_execution_status = 'DRAFT'
WHERE latest_execution_status IS NULL;

-- Add comment for documentation
COMMENT ON COLUMN workflows.latest_execution_status IS 'Status of the most recent execution (DRAFT, RUNNING, SUCCESS, ERROR, CANCELED, WAITING_FOR_HUMAN)';
COMMENT ON COLUMN workflows.latest_execution_id IS 'ID of the most recent execution';
COMMENT ON COLUMN workflows.latest_execution_time IS 'Timestamp of the most recent execution';
