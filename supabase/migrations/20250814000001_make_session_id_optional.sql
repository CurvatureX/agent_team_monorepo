-- Migration: Make session_id optional in workflows table
-- Description: Remove foreign key constraint on session_id and allow NULL values
-- Created: 2025-08-14

-- Start transaction
BEGIN;

-- Check if workflows_session_id_fkey exists and drop it
DO $$
DECLARE
    constraint_exists BOOLEAN;
BEGIN
    -- Check if the constraint exists
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints tc
        WHERE tc.constraint_name = 'workflows_session_id_fkey'
        AND tc.table_name = 'workflows'
        AND tc.table_schema = 'public'
    ) INTO constraint_exists;

    -- If constraint exists, drop it
    IF constraint_exists THEN
        ALTER TABLE workflows DROP CONSTRAINT workflows_session_id_fkey;
        RAISE NOTICE 'Dropped foreign key constraint workflows_session_id_fkey';
    ELSE
        RAISE NOTICE 'Foreign key constraint workflows_session_id_fkey does not exist, skipping drop';
    END IF;
END;
$$;

-- Make session_id column nullable (if it isn't already)
ALTER TABLE workflows ALTER COLUMN session_id DROP NOT NULL;

-- Add comment to document the change
COMMENT ON COLUMN workflows.session_id IS 'Optional session ID - workflows can exist without being associated with a session';

-- Verification query to confirm changes
SELECT
    'workflows.session_id' as column_name,
    CASE
        WHEN is_nullable = 'YES' THEN '✅ NULLABLE'
        ELSE '❌ NOT NULL'
    END as nullable_status,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'workflows'
    AND column_name = 'session_id';

-- Check remaining foreign key constraints on workflows table
SELECT
    'Remaining FK constraints on workflows table' as info,
    tc.constraint_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'workflows'
    AND tc.table_schema = 'public'
ORDER BY tc.constraint_name;

COMMIT;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '================================================================';
    RAISE NOTICE 'MIGRATION COMPLETED SUCCESSFULLY';
    RAISE NOTICE '================================================================';
    RAISE NOTICE 'workflows.session_id is now optional and can be NULL';
    RAISE NOTICE 'Foreign key constraint to sessions table has been removed';
    RAISE NOTICE 'Workflows can now be created without requiring a session_id';
    RAISE NOTICE '================================================================';
END;
$$;
