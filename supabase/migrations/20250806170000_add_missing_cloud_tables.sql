-- Migration: Add missing tables from cloud database
-- Description: Captures all tables that were created manually in cloud but not tracked in migrations
-- Created: 2025-08-06

-- API Provider Configurations table
CREATE TABLE api_provider_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    auth_url TEXT NOT NULL,
    token_url TEXT NOT NULL,
    revoke_url TEXT,
    client_id_env_var VARCHAR(255),
    client_secret_env_var VARCHAR(255),
    base_api_url TEXT NOT NULL,
    default_scopes TEXT[] DEFAULT '{}',
    required_scopes TEXT[] DEFAULT '{}',
    rate_limit_per_minute INTEGER DEFAULT 1000,
    max_retries INTEGER DEFAULT 3,
    backoff_factor DECIMAL DEFAULT 2.0,
    is_active BOOLEAN DEFAULT true,
    supports_refresh_token BOOLEAN DEFAULT true,
    supports_revocation BOOLEAN DEFAULT true,
    documentation_url TEXT,
    setup_instructions TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id UUID NOT NULL DEFAULT auth.uid(),
    source_workflow_id VARCHAR(255),
    action_type VARCHAR(255)
);

-- Chats table
CREATE TABLE chats (
    id BIGINT PRIMARY KEY,
    session_id UUID DEFAULT gen_random_uuid(),
    user_id UUID DEFAULT auth.uid(),
    message_type VARCHAR(255),
    content TEXT DEFAULT '',
    sequence_number INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Workflow Agent States table
CREATE TABLE workflow_agent_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL DEFAULT (EXTRACT(epoch FROM now()) * 1000),
    stage VARCHAR(255) NOT NULL DEFAULT 'clarification',
    previous_stage VARCHAR(255),
    execution_history TEXT[],
    intent_summary TEXT DEFAULT '',
    clarification_context JSONB NOT NULL DEFAULT '{}',
    workflow_context JSONB DEFAULT '{}',
    conversations JSONB NOT NULL DEFAULT '[]',
    gaps TEXT[],
    alternatives JSONB DEFAULT '[]',
    current_workflow_json TEXT DEFAULT '',
    debug_result TEXT DEFAULT '',
    debug_loop_count INTEGER DEFAULT 0,
    rag_context JSONB,
    gap_status VARCHAR(255) DEFAULT 'no_gap',
    identified_gaps JSONB DEFAULT '[]'
);

-- External API Call Logs table
CREATE TABLE external_api_call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    workflow_execution_id UUID,
    node_id UUID,
    provider VARCHAR(255) NOT NULL,
    operation VARCHAR(255) NOT NULL,
    api_endpoint TEXT,
    http_method VARCHAR(255) DEFAULT 'POST',
    request_data JSONB,
    response_data JSONB,
    request_headers JSONB DEFAULT '{}',
    response_headers JSONB DEFAULT '{}',
    success BOOLEAN NOT NULL,
    status_code INTEGER,
    error_type VARCHAR(255),
    error_message TEXT,
    response_time_ms INTEGER,
    retry_count INTEGER DEFAULT 0,
    rate_limit_remaining INTEGER,
    rate_limit_reset_at TIMESTAMP WITH TIME ZONE,
    called_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User External Credentials table
CREATE TABLE user_external_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    provider VARCHAR(255) NOT NULL,
    credential_type VARCHAR(255) NOT NULL DEFAULT 'oauth2',
    encrypted_access_token TEXT,
    encrypted_refresh_token TEXT,
    encrypted_additional_data JSONB DEFAULT '{}',
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scope TEXT[] DEFAULT '{}',
    token_type VARCHAR(255) DEFAULT 'Bearer',
    is_valid BOOLEAN DEFAULT true,
    last_validated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    validation_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Node Templates table
CREATE TABLE node_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(255),
    node_type VARCHAR(255) NOT NULL,
    node_subtype VARCHAR(255) NOT NULL,
    default_parameters JSONB DEFAULT '{}',
    required_parameters TEXT[],
    parameter_schema JSONB,
    version VARCHAR(255) DEFAULT '1.0.0',
    is_system_template BOOLEAN DEFAULT false,
    created_by UUID,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- OAuth2 Authorization States table
CREATE TABLE oauth2_authorization_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    state_value VARCHAR(255) NOT NULL,
    user_id UUID NOT NULL,
    provider VARCHAR(255) NOT NULL,
    scopes TEXT[] DEFAULT '{}',
    redirect_uri TEXT,
    code_challenge VARCHAR(255),
    code_challenge_method VARCHAR(255) DEFAULT 'S256',
    nonce VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    is_valid BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_oauth2_authorization_states_state_value ON oauth2_authorization_states(state_value);
CREATE INDEX idx_oauth2_authorization_states_user_id ON oauth2_authorization_states(user_id);
CREATE INDEX idx_node_templates_template_id ON node_templates(template_id);
CREATE INDEX idx_external_api_call_logs_user_id ON external_api_call_logs(user_id);
CREATE INDEX idx_user_external_credentials_user_provider ON user_external_credentials(user_id, provider);
