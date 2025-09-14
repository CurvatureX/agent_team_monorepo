-- Add icon_url field to workflows table
-- This allows workflows to have custom icons for better visual identification

-- Add icon_url column to workflows table
ALTER TABLE workflows
ADD COLUMN icon_url VARCHAR(500);

-- Add comment for documentation
COMMENT ON COLUMN workflows.icon_url IS 'URL to the workflow icon/image for visual identification in UI';
