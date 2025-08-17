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

-- OAuth2 State Management Table
-- Temporary storage for OAuth2 authorization state parameters
CREATE TABLE oauth2_authorization_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    state_value VARCHAR(255) NOT NULL UNIQUE, -- Random state parameter
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    scopes TEXT[] DEFAULT '{}',
    redirect_uri TEXT,

    -- Additional OAuth2 parameters
    code_challenge VARCHAR(255), -- For PKCE (Proof Key for Code Exchange)
    code_challenge_method VARCHAR(10) DEFAULT 'S256', -- 'plain' or 'S256'
    nonce VARCHAR(255), -- For OpenID Connect

    -- Expiration and validation
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE, -- When the state was consumed
    is_valid BOOLEAN DEFAULT true,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_provider_state CHECK (
        provider IN ('google_calendar', 'github', 'slack')
    ),
    CONSTRAINT valid_code_challenge_method CHECK (
        code_challenge_method IN ('plain', 'S256')
    )
);

-- API Provider Configuration Table
-- Store configuration for different API providers
CREATE TABLE api_provider_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,

    -- OAuth2 Configuration
    auth_url TEXT NOT NULL,
    token_url TEXT NOT NULL,
    revoke_url TEXT,
    client_id_env_var VARCHAR(100), -- Environment variable name for client_id
    client_secret_env_var VARCHAR(100), -- Environment variable name for client_secret

    -- API Configuration
    base_api_url TEXT NOT NULL,
    default_scopes TEXT[] DEFAULT '{}',
    required_scopes TEXT[] DEFAULT '{}',

    -- Rate limiting and retries
    rate_limit_per_minute INTEGER DEFAULT 1000,
    max_retries INTEGER DEFAULT 3,
    backoff_factor DECIMAL(3,2) DEFAULT 2.0,

    -- Status and features
    is_active BOOLEAN DEFAULT true,
    supports_refresh_token BOOLEAN DEFAULT true,
    supports_revocation BOOLEAN DEFAULT true,

    -- Documentation and help
    documentation_url TEXT,
    setup_instructions TEXT,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_provider_config CHECK (
        provider IN ('google_calendar', 'github', 'slack', 'custom_http')
    )
);

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

CREATE INDEX idx_oauth2_states_state_value ON oauth2_authorization_states(state_value);
CREATE INDEX idx_oauth2_states_user_provider ON oauth2_authorization_states(user_id, provider);
CREATE INDEX idx_oauth2_states_expires_at ON oauth2_authorization_states(expires_at);
CREATE INDEX idx_oauth2_states_valid ON oauth2_authorization_states(is_valid);

CREATE INDEX idx_provider_configs_provider ON api_provider_configs(provider);
CREATE INDEX idx_provider_configs_active ON api_provider_configs(is_active);

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

CREATE TRIGGER update_api_provider_configs_updated_at
    BEFORE UPDATE ON api_provider_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default API provider configurations
INSERT INTO api_provider_configs (
    provider, display_name, auth_url, token_url, revoke_url,
    client_id_env_var, client_secret_env_var, base_api_url,
    default_scopes, required_scopes, documentation_url
) VALUES
-- Google Calendar
(
    'google_calendar',
    'Google Calendar',
    'https://accounts.google.com/o/oauth2/v2/auth',
    'https://oauth2.googleapis.com/token',
    'https://oauth2.googleapis.com/revoke',
    'GOOGLE_CLIENT_ID',
    'GOOGLE_CLIENT_SECRET',
    'https://www.googleapis.com/calendar/v3',
    ARRAY['https://www.googleapis.com/auth/calendar'],
    ARRAY['https://www.googleapis.com/auth/calendar'],
    'https://developers.google.com/calendar/api'
),
-- GitHub
(
    'github',
    'GitHub',
    'https://github.com/login/oauth/authorize',
    'https://github.com/login/oauth/access_token',
    'https://github.com/settings/connections/applications',
    'GITHUB_CLIENT_ID',
    'GITHUB_CLIENT_SECRET',
    'https://api.github.com',
    ARRAY['repo', 'read:user'],
    ARRAY['repo'],
    'https://docs.github.com/en/rest'
),
-- Slack
(
    'slack',
    'Slack',
    'https://slack.com/oauth/v2/authorize',
    'https://slack.com/api/oauth.v2.access',
    'https://slack.com/api/auth.revoke',
    'SLACK_CLIENT_ID',
    'SLACK_CLIENT_SECRET',
    'https://slack.com/api',
    ARRAY['chat:write', 'channels:read'],
    ARRAY['chat:write'],
    'https://api.slack.com/web'
);

-- Add comments for documentation
COMMENT ON TABLE sessions IS 'Session context for workflow executions and API interactions';
COMMENT ON TABLE user_external_credentials IS 'Stores encrypted OAuth2 tokens and API credentials for each user';
COMMENT ON TABLE external_api_call_logs IS 'Tracks all external API calls for monitoring, debugging, and analytics';
COMMENT ON TABLE oauth2_authorization_states IS 'Temporary storage for OAuth2 authorization state parameters';
COMMENT ON TABLE api_provider_configs IS 'Configuration for different API providers';

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
