-- Fix missing trigger_subtype column in trigger_index table
-- Description: The online database was missing the trigger_subtype column that should have been created by migration 20250929000002
-- Created: 2025-10-03

BEGIN;

-- Add trigger_subtype column if it doesn't exist
ALTER TABLE trigger_index ADD COLUMN IF NOT EXISTS trigger_subtype VARCHAR(100);

-- Populate trigger_subtype from trigger_type for existing rows (trigger_type was being used for subtype values)
UPDATE trigger_index
SET trigger_subtype = trigger_type
WHERE trigger_subtype IS NULL;

-- Set trigger_type to 'TRIGGER' for all rows (as per schema design)
UPDATE trigger_index
SET trigger_type = 'TRIGGER'
WHERE trigger_type != 'TRIGGER';

-- Make trigger_subtype NOT NULL after data migration
ALTER TABLE trigger_index ALTER COLUMN trigger_subtype SET NOT NULL;

-- Add constraints
ALTER TABLE trigger_index DROP CONSTRAINT IF EXISTS valid_trigger_type;
ALTER TABLE trigger_index ADD CONSTRAINT valid_trigger_type CHECK (trigger_type IN ('TRIGGER'));

ALTER TABLE trigger_index DROP CONSTRAINT IF EXISTS valid_trigger_subtype;
ALTER TABLE trigger_index ADD CONSTRAINT valid_trigger_subtype CHECK (
    trigger_subtype IN ('CRON', 'MANUAL', 'WEBHOOK', 'EMAIL', 'GITHUB', 'SLACK')
);

COMMIT;
