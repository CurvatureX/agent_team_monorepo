-- Remove unnecessary workflow columns
-- Description: Remove legacy fields that are no longer needed in the new workflow architecture
-- The new workflow system stores all configuration in workflow_data as JSON
-- Created: 2025-09-28

BEGIN;

-- Remove legacy static_data column (data now stored in workflow_data JSON)
ALTER TABLE workflows DROP COLUMN IF EXISTS static_data;
COMMENT ON TABLE workflows IS 'static_data column removed - data now in workflow_data JSON';

-- Remove legacy pin_data column (pinning handled differently in new system)
ALTER TABLE workflows DROP COLUMN IF EXISTS pin_data;

-- Remove legacy settings column (settings now stored in workflow_data JSON)
ALTER TABLE workflows DROP COLUMN IF EXISTS settings;

-- Add comment about the schema cleanup
COMMENT ON TABLE workflows IS 'Workflows table - cleaned up legacy columns, using workflow_data JSON for configuration';

COMMIT;
