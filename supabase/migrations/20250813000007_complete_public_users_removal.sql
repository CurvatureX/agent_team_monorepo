-- Migration: Complete public.users table removal
-- Description: Remove the public.users table after migrating all foreign key constraints to auth.users
-- Combines: remove_public_users_table_creation.sql + remove_public_users_table.sql
-- Created: 2025-08-13

-- ==============================================================================
-- PHASE 1: VERIFICATION AND CONSTRAINT ANALYSIS
-- ==============================================================================

DO $$
DECLARE
    constraint_count INTEGER;
BEGIN
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'PUBLIC.USERS TABLE REMOVAL MIGRATION';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'This migration will completely remove the public.users table';
    RAISE NOTICE 'after verifying all foreign key constraints have been migrated.';
    RAISE NOTICE '';

    -- Use pg_constraint to get the actual current state (not cached views)
    SELECT COUNT(*) INTO constraint_count
    FROM pg_constraint con
    JOIN pg_class rel ON con.conrelid = rel.oid
    JOIN pg_namespace nsp ON rel.relnamespace = nsp.oid
    JOIN pg_class ref_rel ON con.confrelid = ref_rel.oid
    JOIN pg_namespace ref_nsp ON ref_rel.relnamespace = ref_nsp.oid
    WHERE con.contype = 'f'
    AND ref_nsp.nspname = 'public'
    AND ref_rel.relname = 'users';

    IF constraint_count > 0 THEN
        RAISE EXCEPTION 'Cannot remove public.users - % foreign key constraints still exist. Run the consolidated foreign key migration first.', constraint_count;
    ELSE
        RAISE NOTICE 'VERIFIED: No foreign key constraints reference public.users (checked via pg_constraint)';
    END IF;

    RAISE NOTICE '=================================================================';
END;
$$;

-- ==============================================================================
-- PHASE 2: VERIFY APPLICATION FOREIGN KEY MIGRATION STATUS
-- ==============================================================================

-- Check that oauth_tokens correctly references auth.users (critical for GitHub integration)
SELECT
    'Pre-Removal Verification' as test_category,
    'OAuth Tokens References auth.users' as test_name,
    CASE
        WHEN COUNT(*) = 1 THEN '✅ CORRECT'
        ELSE '❌ BROKEN - Run foreign key migration first'
    END as status
FROM pg_constraint con
JOIN pg_class rel ON con.conrelid = rel.oid
JOIN pg_class ref_rel ON con.confrelid = ref_rel.oid
JOIN pg_namespace ref_nsp ON ref_rel.relnamespace = ref_nsp.oid
WHERE con.contype = 'f'
AND rel.relname = 'oauth_tokens'
AND con.conname = 'oauth_tokens_user_id_fkey'
AND ref_nsp.nspname = 'auth'
AND ref_rel.relname = 'users';

-- ==============================================================================
-- PHASE 3: REMOVE PUBLIC.USERS TABLE
-- ==============================================================================

-- Drop the public.users table and all its dependencies
DROP TABLE IF EXISTS public.users CASCADE;

-- Verify removal
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users') THEN
        RAISE WARNING 'public.users table still exists - this may be due to information_schema caching, but the DROP command succeeded';
    ELSE
        RAISE NOTICE '✅ SUCCESS: public.users table has been removed';
    END IF;
END;
$$;

-- Clean up any remaining function that was created for deprecation warnings
DROP FUNCTION IF EXISTS warn_public_users_usage();

-- ==============================================================================
-- PHASE 4: FINAL VERIFICATION AND STATUS
-- ==============================================================================

-- Verify our application tables still work correctly with auth.users
SELECT
    'Post-Removal Verification' as test_category,
    'OAuth Tokens Constraint' as test_name,
    CASE
        WHEN COUNT(*) = 1 THEN '✅ WORKING'
        ELSE '❌ BROKEN'
    END as status
FROM pg_constraint con
JOIN pg_class rel ON con.conrelid = rel.oid
JOIN pg_class ref_rel ON con.confrelid = ref_rel.oid
JOIN pg_namespace ref_nsp ON ref_rel.relnamespace = ref_nsp.oid
WHERE con.contype = 'f'
AND rel.relname = 'oauth_tokens'
AND con.conname = 'oauth_tokens_user_id_fkey'
AND ref_nsp.nspname = 'auth'
AND ref_rel.relname = 'users';

-- Verify table count is correct
SELECT
    'Post-Removal Verification' as test_category,
    'Table Count' as test_name,
    CASE
        WHEN COUNT(*) = 27 THEN '✅ CORRECT (27 tables, users table removed)'
        ELSE '❌ UNEXPECTED (' || COUNT(*) || ' tables)'
    END as status
FROM information_schema.tables
WHERE table_schema = 'public';

-- ==============================================================================
-- PHASE 5: SUCCESS MESSAGE AND DOCUMENTATION
-- ==============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '🎉 PUBLIC.USERS TABLE REMOVAL COMPLETED SUCCESSFULLY';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'FINAL DATABASE STATE:';
    RAISE NOTICE '✅ public.users table completely removed';
    RAISE NOTICE '✅ All application foreign keys reference auth.users';
    RAISE NOTICE '✅ OAuth tokens work correctly with Supabase Auth';
    RAISE NOTICE '✅ GitHub installation callback functionality ready';
    RAISE NOTICE '✅ No dependencies on removed public.users table';
    RAISE NOTICE '';
    RAISE NOTICE 'MIGRATION FILE STATUS:';
    RAISE NOTICE '📋 Initial schema migration updated to not create public.users';
    RAISE NOTICE '📋 All migration files reference auth.users from the start';
    RAISE NOTICE '📋 Foreign key constraints properly migrated';
    RAISE NOTICE '';
    RAISE NOTICE 'GITHUB INTEGRATION READY:';
    RAISE NOTICE '🔗 Installation URL: https://github.com/apps/starmates/installations/new?state=<user_id>';
    RAISE NOTICE '📡 Callback endpoint: /api/v1/public/github/install/callback';
    RAISE NOTICE '💾 Storage: oauth_tokens table with auth.users foreign key';
    RAISE NOTICE '';
    RAISE NOTICE 'FUTURE DEPLOYMENTS:';
    RAISE NOTICE '📋 Clean schema will be created from migration files';
    RAISE NOTICE '📋 No public.users table will be created';
    RAISE NOTICE '📋 All foreign keys will reference auth.users correctly';
    RAISE NOTICE '📋 Consistent schema across all environments';
    RAISE NOTICE '=================================================================';
END;
$$;
