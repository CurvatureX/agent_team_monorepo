-- Migration: Add missing tables from cloud database
-- Description: Captures all tables that were created manually in cloud but not tracked in migrations
-- Created: 2025-08-06

-- API Provider Configurations table - REMOVED (not needed in current implementation)
-- Table api_provider_configs was removed as OAuth2 flow is handled differently

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
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

-- OAuth2 Authorization States table - REMOVED (not needed in current implementation)
-- Table oauth2_authorization_states was removed as OAuth2 state management is handled differently

-- Indexes for removed tables are also not created
CREATE INDEX idx_node_templates_template_id ON node_templates(template_id);
CREATE INDEX idx_external_api_call_logs_user_id ON external_api_call_logs(user_id);
CREATE INDEX idx_user_external_credentials_user_provider ON user_external_credentials(user_id, provider);
