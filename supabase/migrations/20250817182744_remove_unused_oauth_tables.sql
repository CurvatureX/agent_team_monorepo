-- Migration: Remove unused OAuth2 tables
-- Description: Remove oauth2_authorization_states and api_provider_configs tables
-- These tables are not needed as the OAuth2 flow is handled differently in the current implementation
-- Date: 2025-08-17

-- Drop indexes first
DROP INDEX IF EXISTS idx_oauth2_states_state_value CASCADE;
DROP INDEX IF EXISTS idx_oauth2_states_user_provider CASCADE;
DROP INDEX IF EXISTS idx_oauth2_states_expires_at CASCADE;
DROP INDEX IF EXISTS idx_oauth2_states_valid CASCADE;

DROP INDEX IF EXISTS idx_provider_configs_provider CASCADE;
DROP INDEX IF EXISTS idx_provider_configs_active CASCADE;

-- Drop triggers
DROP TRIGGER IF EXISTS update_api_provider_configs_updated_at ON api_provider_configs;

-- Drop tables
DROP TABLE IF EXISTS oauth2_authorization_states CASCADE;
DROP TABLE IF EXISTS api_provider_configs CASCADE;

-- Log the removal
DO $$
BEGIN
    RAISE NOTICE 'Tables oauth2_authorization_states and api_provider_configs have been removed';
    RAISE NOTICE 'These tables were unused in the current OAuth2 implementation';
END $$;