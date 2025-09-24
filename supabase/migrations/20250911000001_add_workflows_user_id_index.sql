-- Add database index on workflows.user_id for performance
-- This should dramatically improve workflow listing performance

-- Add index on user_id column (most common query filter)
CREATE INDEX IF NOT EXISTS idx_workflows_user_id ON workflows(user_id);

-- Add composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_workflows_user_active ON workflows(user_id, active);

-- Add index on updated_at for ordering performance
CREATE INDEX IF NOT EXISTS idx_workflows_updated_at ON workflows(updated_at DESC);

-- Add composite index for the full query pattern used in listing
CREATE INDEX IF NOT EXISTS idx_workflows_listing ON workflows(user_id, active, updated_at DESC);
