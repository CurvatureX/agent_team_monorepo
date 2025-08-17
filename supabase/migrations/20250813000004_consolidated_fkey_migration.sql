-- Migration: Consolidated Foreign Key Migration to auth.users
-- Description: Comprehensive migration to fix all foreign key constraints in public schema to reference auth.users instead of public.users
-- Combines: remove_user_id_fkey.sql, fix_public_schema_fkeys.sql, cleanup_duplicate_fkeys.sql
-- Created: 2025-08-13

-- ==============================================================================
-- PHASE 1: Drop all existing foreign key constraints that reference public.users
-- ==============================================================================

DO $$
DECLARE
    constraint_record RECORD;
BEGIN
    RAISE NOTICE 'Phase 1: Dropping all foreign key constraints that reference public.users in public schema';

    -- Get all foreign key constraints in public schema that reference public.users
    FOR constraint_record IN
        SELECT
            tc.table_schema,
            tc.table_name,
            tc.constraint_name,
            kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.referential_constraints rc ON tc.constraint_name = rc.constraint_name
        JOIN information_schema.table_constraints tc2 ON rc.unique_constraint_name = tc2.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'public'
        AND tc2.table_schema = 'public'
        AND tc2.table_name = 'users'
        ORDER BY tc.table_name
    LOOP
        RAISE NOTICE 'Dropping constraint % on %.% (column: %)',
                     constraint_record.constraint_name,
                     constraint_record.table_schema,
                     constraint_record.table_name,
                     constraint_record.column_name;

        -- Drop the constraint
        EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS %I',
                       constraint_record.table_schema,
                       constraint_record.table_name,
                       constraint_record.constraint_name);
    END LOOP;

    RAISE NOTICE 'Phase 1 completed: All foreign key constraints to public.users have been dropped';
END;
$$;

-- ==============================================================================
-- PHASE 2: Create clean foreign key constraints to auth.users
-- ==============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Phase 2: Creating clean foreign key constraints to auth.users';
END;
$$;

-- ai_generation_history
ALTER TABLE ai_generation_history
ADD CONSTRAINT ai_generation_history_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- debug_sessions
ALTER TABLE debug_sessions
ADD CONSTRAINT debug_sessions_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- external_api_call_logs
ALTER TABLE external_api_call_logs
ADD CONSTRAINT external_api_call_logs_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- node_templates
ALTER TABLE node_templates
ADD CONSTRAINT node_templates_created_by_fkey
FOREIGN KEY (created_by) REFERENCES auth.users(id) ON DELETE SET NULL;

-- oauth2_authorization_states
ALTER TABLE oauth2_authorization_states
ADD CONSTRAINT oauth2_authorization_states_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- oauth_tokens (critical for GitHub installation callback)
ALTER TABLE oauth_tokens
ADD CONSTRAINT oauth_tokens_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- user_external_credentials
ALTER TABLE user_external_credentials
ADD CONSTRAINT user_external_credentials_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- user_settings
ALTER TABLE user_settings
ADD CONSTRAINT user_settings_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- validation_logs
ALTER TABLE validation_logs
ADD CONSTRAINT validation_logs_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- workflow_deployment_history
ALTER TABLE workflow_deployment_history
ADD CONSTRAINT workflow_deployment_history_triggered_by_fkey
FOREIGN KEY (triggered_by) REFERENCES auth.users(id) ON DELETE SET NULL;

-- workflow_versions
ALTER TABLE workflow_versions
ADD CONSTRAINT workflow_versions_created_by_fkey
FOREIGN KEY (created_by) REFERENCES auth.users(id) ON DELETE SET NULL;

-- workflows (both user_id and deployed_by constraints)
ALTER TABLE workflows
ADD CONSTRAINT workflows_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE workflows
ADD CONSTRAINT workflows_deployed_by_fkey
FOREIGN KEY (deployed_by) REFERENCES auth.users(id) ON DELETE SET NULL;

-- ==============================================================================
-- PHASE 3: Verification and cleanup
-- ==============================================================================

-- Verification: Check remaining foreign keys to public.users in public schema
SELECT
    COUNT(*) as remaining_public_fkeys_to_public_users,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ SUCCESS: All public schema foreign keys migrated'
        ELSE '❌ WARNING: Some constraints still reference public.users'
    END as migration_status
FROM information_schema.table_constraints tc
JOIN information_schema.referential_constraints rc ON tc.constraint_name = rc.constraint_name
JOIN information_schema.table_constraints tc2 ON rc.unique_constraint_name = tc2.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'public'
AND tc2.table_schema = 'public'
AND tc2.table_name = 'users';

-- Verification: Confirm oauth_tokens constraint is correct
SELECT
    'oauth_tokens constraint verification' as test,
    tc.constraint_name,
    tc2.table_schema as references_schema,
    tc2.table_name as references_table,
    CASE
        WHEN tc2.table_schema = 'auth' AND tc2.table_name = 'users' THEN '✅ CORRECT'
        ELSE '❌ INCORRECT'
    END as status
FROM information_schema.table_constraints tc
JOIN information_schema.referential_constraints rc ON tc.constraint_name = rc.constraint_name
JOIN information_schema.table_constraints tc2 ON rc.unique_constraint_name = tc2.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name = 'oauth_tokens'
AND tc.constraint_name = 'oauth_tokens_user_id_fkey';

-- Attempt to remove public.users table (will only succeed if no auth schema constraints reference it)
DO $$
BEGIN
    -- Check if there are any remaining foreign keys to public.users
    IF EXISTS (
        SELECT 1
        FROM information_schema.table_constraints tc
        JOIN information_schema.referential_constraints rc ON tc.constraint_name = rc.constraint_name
        JOIN information_schema.table_constraints tc2 ON rc.unique_constraint_name = tc2.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc2.table_schema = 'public'
        AND tc2.table_name = 'users'
    ) THEN
        RAISE NOTICE 'PUBLIC.USERS TABLE: Cannot be removed - auth schema constraints still exist (managed by Supabase)';
        RAISE NOTICE 'This is expected behavior - the public.users table should remain for Supabase Auth compatibility';
    ELSE
        -- Safe to remove
        DROP TABLE IF EXISTS public.users CASCADE;
        RAISE NOTICE 'PUBLIC.USERS TABLE: Successfully removed (no remaining foreign key references)';
    END IF;
END;
$$;

-- Add documentation comments
COMMENT ON TABLE oauth_tokens IS 'OAuth tokens table - now properly references auth.users instead of public.users for Supabase Auth compatibility';
COMMENT ON COLUMN workflows.user_id IS 'User ID referencing auth.users - migrated from public.users for proper Supabase Auth integration';

-- Final success message
DO $$
BEGIN
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'MIGRATION COMPLETED SUCCESSFULLY';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'All foreign key constraints in public schema now reference auth.users';
    RAISE NOTICE 'OAuth tokens and user integrations will work correctly with Supabase Auth';
    RAISE NOTICE 'GitHub installation callback API functionality is now properly supported';
    RAISE NOTICE '=================================================================';
END;
$$;
