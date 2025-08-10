-- Add refresh_token_expires_at column to user_external_credentials
-- Migration: 20250810000001_add_refresh_token_expiration.sql
-- Description: Add support for tracking refresh token expiration times

-- Add refresh token expiration timestamp column
ALTER TABLE user_external_credentials 
ADD COLUMN refresh_token_expires_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Add client_id column if it doesn't exist (for better OAuth2 tracking)
ALTER TABLE user_external_credentials 
ADD COLUMN IF NOT EXISTS client_id VARCHAR(255) DEFAULT NULL;

-- Add validation error column for detailed error tracking
ALTER TABLE user_external_credentials 
ADD COLUMN IF NOT EXISTS validation_error TEXT DEFAULT NULL;

-- Add comment for the new columns
COMMENT ON COLUMN user_external_credentials.refresh_token_expires_at IS 'Expiration time for the refresh token (provider-specific, NULL means no expiration)';
COMMENT ON COLUMN user_external_credentials.client_id IS 'OAuth2 client ID used for this authorization (for tracking and debugging)';
COMMENT ON COLUMN user_external_credentials.validation_error IS 'Detailed error message when credentials are marked as invalid';

-- Create index for efficient querying by refresh token expiration times
CREATE INDEX IF NOT EXISTS idx_user_external_credentials_refresh_expires 
ON user_external_credentials(refresh_token_expires_at) 
WHERE refresh_token_expires_at IS NOT NULL;

-- Create index for efficient querying by client_id
CREATE INDEX IF NOT EXISTS idx_user_external_credentials_client_id 
ON user_external_credentials(client_id) 
WHERE client_id IS NOT NULL;

-- Create index for validation error queries
CREATE INDEX IF NOT EXISTS idx_user_external_credentials_validation_error 
ON user_external_credentials(validation_error) 
WHERE validation_error IS NOT NULL;

-- Update provider constraint to include new providers
ALTER TABLE user_external_credentials 
DROP CONSTRAINT IF EXISTS valid_provider;

ALTER TABLE user_external_credentials 
ADD CONSTRAINT valid_provider CHECK (
    provider IN ('google_calendar', 'github', 'slack', 'email', 'api_call', 'custom_http')
);