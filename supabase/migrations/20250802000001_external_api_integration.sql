-- External API Integration Schema
-- Migration: 20250802000001_external_api_integration.sql
-- Description: Add tables for external API integration, OAuth2 credentials, and API call logging

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Sessions table for workflow execution context
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Session metadata
    session_name VARCHAR(255),
    session_type VARCHAR(50) DEFAULT 'workflow', -- 'workflow', 'api', 'debug'

    -- Session data
    session_data JSONB DEFAULT '{}',

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT valid_session_type CHECK (
        session_type IN ('workflow', 'api', 'debug', 'test')
    )
);

-- User External API Credentials Table
-- Stores encrypted OAuth2 tokens and API credentials for each user
CREATE TABLE user_external_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL, -- 'google_calendar', 'github', 'slack', etc.
    credential_type VARCHAR(20) NOT NULL DEFAULT 'oauth2', -- 'oauth2', 'api_key', 'basic_auth'

    -- Encrypted credential data (using Fernet encryption)
    encrypted_access_token TEXT,
    encrypted_refresh_token TEXT,
    encrypted_additional_data JSONB DEFAULT '{}', -- For client_secret, api_keys, etc.

    -- Token metadata
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scope TEXT[] DEFAULT '{}', -- OAuth2 authorization scopes
    token_type VARCHAR(20) DEFAULT 'Bearer',

    -- Status and validation
    is_valid BOOLEAN DEFAULT true,
    last_validated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    validation_error TEXT, -- Store last validation error

    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_provider CHECK (
        provider IN ('google_calendar', 'github', 'slack', 'custom_http')
    ),
    CONSTRAINT valid_credential_type CHECK (
        credential_type IN ('oauth2', 'api_key', 'basic_auth', 'bearer_token')
    ),

    -- Ensure each user has only one credential per provider
    UNIQUE(user_id, provider)
);

-- External API Call Logs Table
-- Tracks all external API calls for monitoring, debugging, and analytics
CREATE TABLE external_api_call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    workflow_execution_id UUID REFERENCES workflow_executions(id) ON DELETE SET NULL,
    node_id UUID REFERENCES nodes(id) ON DELETE SET NULL,

    -- API call information
    provider VARCHAR(50) NOT NULL,
    operation VARCHAR(100) NOT NULL, -- 'create_event', 'list_issues', 'send_message', etc.
    api_endpoint TEXT, -- Full API endpoint URL
    http_method VARCHAR(10) DEFAULT 'POST', -- GET, POST, PUT, DELETE, etc.

    -- Request and response data (for debugging and analytics)
    request_data JSONB, -- Sanitized request parameters (no sensitive data)
    response_data JSONB, -- API response data
    request_headers JSONB DEFAULT '{}', -- Request headers (sanitized)
    response_headers JSONB DEFAULT '{}', -- Response headers

    -- Execution results
    success BOOLEAN NOT NULL,
    status_code INTEGER, -- HTTP status code
    error_type VARCHAR(50), -- 'AuthenticationError', 'RateLimitError', etc.
    error_message TEXT,

    -- Performance metrics
    response_time_ms INTEGER, -- Response time in milliseconds
    retry_count INTEGER DEFAULT 0, -- Number of retries attempted

    -- Rate limiting information
    rate_limit_remaining INTEGER, -- Remaining API calls
    rate_limit_reset_at TIMESTAMP WITH TIME ZONE, -- When rate limit resets

    -- Timestamp
    called_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_provider_log CHECK (
        provider IN ('google_calendar', 'github', 'slack', 'custom_http', 'webhook')
    ),
    CONSTRAINT valid_http_method CHECK (
        http_method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS')
    )
);

-- OAuth2 State Management Table - REMOVED
-- Table oauth2_authorization_states was removed as OAuth2 state management is handled differently in current implementation

-- API Provider Configuration Table - REMOVED  
-- Table api_provider_configs was removed as provider configuration is handled differently in current implementation

-- Create indexes for performance optimization
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_active ON sessions(is_active);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_sessions_type ON sessions(session_type);

CREATE INDEX idx_user_credentials_user_provider ON user_external_credentials(user_id, provider);
CREATE INDEX idx_user_credentials_provider ON user_external_credentials(provider);
CREATE INDEX idx_user_credentials_expires_at ON user_external_credentials(token_expires_at);
CREATE INDEX idx_user_credentials_valid ON user_external_credentials(is_valid);

CREATE INDEX idx_api_logs_user_provider ON external_api_call_logs(user_id, provider);
CREATE INDEX idx_api_logs_execution ON external_api_call_logs(workflow_execution_id);
CREATE INDEX idx_api_logs_node ON external_api_call_logs(node_id);
CREATE INDEX idx_api_logs_time ON external_api_call_logs(called_at);
CREATE INDEX idx_api_logs_success ON external_api_call_logs(success);
CREATE INDEX idx_api_logs_provider_operation ON external_api_call_logs(provider, operation);

-- Indexes for oauth2_authorization_states and api_provider_configs tables - REMOVED
-- These tables and their indexes were removed as they are not needed in current implementation

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply the trigger to relevant tables
CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_external_credentials_updated_at
    BEFORE UPDATE ON user_external_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for api_provider_configs table - REMOVED
-- Table api_provider_configs and its trigger were removed as they are not needed in current implementation

-- Default API provider configurations - REMOVED
-- INSERT statements for api_provider_configs were removed as the table no longer exists

-- Add comments for documentation
COMMENT ON TABLE sessions IS 'Session context for workflow executions and API interactions';
COMMENT ON TABLE user_external_credentials IS 'Stores encrypted OAuth2 tokens and API credentials for each user';
COMMENT ON TABLE external_api_call_logs IS 'Tracks all external API calls for monitoring, debugging, and analytics';
-- Comments for removed tables oauth2_authorization_states and api_provider_configs - REMOVED

COMMENT ON COLUMN user_external_credentials.encrypted_access_token IS 'Fernet-encrypted access token';
COMMENT ON COLUMN user_external_credentials.encrypted_refresh_token IS 'Fernet-encrypted refresh token';
COMMENT ON COLUMN user_external_credentials.encrypted_additional_data IS 'Encrypted additional credential data (client_secret, api_keys, etc.)';

COMMENT ON COLUMN external_api_call_logs.request_data IS 'Sanitized request parameters (no sensitive data)';
COMMENT ON COLUMN external_api_call_logs.response_data IS 'API response data for debugging';
COMMENT ON COLUMN external_api_call_logs.response_time_ms IS 'Response time in milliseconds for performance monitoring';

-- Grant appropriate permissions (adjust based on your user roles)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON user_external_credentials TO authenticated;
-- GRANT SELECT, INSERT ON external_api_call_logs TO authenticated;
-- GRANT SELECT ON oauth2_authorization_states TO authenticated;
-- GRANT SELECT ON api_provider_configs TO authenticated;
