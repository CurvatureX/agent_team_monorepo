-- Migration: Remove Integrations Table
-- Description: Remove integrations table and update oauth_tokens to remove dependency
-- Created: 2025-09-28
-- Author: Claude Code Assistant

-- =============================================================================
-- REMOVE INTEGRATIONS TABLE AND UPDATE DEPENDENCIES
-- =============================================================================

-- This migration removes the integrations table and updates any dependent tables
-- to remove foreign key constraints that reference it.

-- =============================================================================
-- 1. UPDATE OAUTH_TOKENS TABLE TO REMOVE INTEGRATIONS DEPENDENCY
-- =============================================================================

-- First, drop the foreign key constraint from oauth_tokens to integrations
ALTER TABLE oauth_tokens DROP CONSTRAINT IF EXISTS oauth_tokens_integration_id_fkey;

-- Remove the integration_id column from oauth_tokens since integrations table will be removed
-- The provider column already exists to identify the OAuth provider
ALTER TABLE oauth_tokens DROP COLUMN IF EXISTS integration_id;

-- =============================================================================
-- 2. REMOVE INTEGRATIONS TABLE INDEXES
-- =============================================================================

-- Drop indexes associated with integrations table
DROP INDEX IF EXISTS idx_integrations_type;
DROP INDEX IF EXISTS idx_integrations_active;
DROP INDEX IF EXISTS idx_oauth_tokens_integration_id;

-- =============================================================================
-- 3. REMOVE INTEGRATIONS TABLE
-- =============================================================================

-- Drop the integrations table
DROP TABLE IF EXISTS integrations CASCADE;

-- =============================================================================
-- 4. VERIFICATION AND CLEANUP
-- =============================================================================

-- Log the removal results
DO $$
BEGIN
    RAISE NOTICE '🗑️  Integrations table removal completed successfully';
    RAISE NOTICE 'Removed:';
    RAISE NOTICE '  - integrations table';
    RAISE NOTICE '  - oauth_tokens.integration_id column';
    RAISE NOTICE '  - Foreign key constraint: oauth_tokens_integration_id_fkey';
    RAISE NOTICE '  - Indexes: idx_integrations_type, idx_integrations_active, idx_oauth_tokens_integration_id';
    RAISE NOTICE '';
    RAISE NOTICE '✅ OAuth tokens table now simplified with only provider-based identification';
END $$;

-- =============================================================================
-- 5. VERIFY CORE FUNCTIONALITY REMAINS INTACT
-- =============================================================================

-- Quick verification that oauth_tokens table still exists and is functional
DO $$
DECLARE
    table_exists BOOLEAN;
    column_exists BOOLEAN;
BEGIN
    -- Check oauth_tokens table exists
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'oauth_tokens'
    ) INTO table_exists;

    IF NOT table_exists THEN
        RAISE EXCEPTION 'CRITICAL: oauth_tokens table was accidentally removed!';
    END IF;

    -- Check integration_id column was removed
    SELECT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'oauth_tokens'
        AND column_name = 'integration_id'
    ) INTO column_exists;

    IF column_exists THEN
        RAISE EXCEPTION 'WARNING: integration_id column still exists in oauth_tokens!';
    END IF;

    -- Check integrations table was removed
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'integrations'
    ) INTO table_exists;

    IF table_exists THEN
        RAISE EXCEPTION 'WARNING: integrations table still exists!';
    END IF;

    RAISE NOTICE '✅ All verifications passed - integrations table and dependencies removed successfully';
END $$;

-- =============================================================================
-- MIGRATION COMPLETION
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '🎉 Integrations table removal migration completed successfully';
    RAISE NOTICE 'OAuth tokens now use provider field for identification instead of integration_id';
END $$;
