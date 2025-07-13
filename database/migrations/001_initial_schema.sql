-- Migration: 001_initial_schema
-- Description: Initial database schema for workflow engine
-- Created: 2024-01-01
-- Author: Workflow Engine Team

-- This migration creates the initial database schema
-- Run this migration using: alembic upgrade head

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create all tables (copy from schema.sql)
-- This is the initial migration that sets up the complete database structure

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User settings
CREATE TABLE user_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workflows table
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT true,
    workflow_data JSONB NOT NULL,
    settings JSONB,
    static_data JSONB,
    pin_data JSONB,
    version VARCHAR(50) DEFAULT '1.0.0',
    tags TEXT[],
    is_template BOOLEAN DEFAULT false,
    template_category VARCHAR(100),
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    CONSTRAINT workflows_name_not_empty CHECK (length(name) > 0),
    CONSTRAINT workflows_valid_workflow_data CHECK (workflow_data IS NOT NULL)
);

-- Node definitions - stores individual node configurations
CREATE TABLE nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id VARCHAR(255) NOT NULL,
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    node_type VARCHAR(50) NOT NULL,
    node_subtype VARCHAR(100) NOT NULL,
    type_version INTEGER DEFAULT 1,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    disabled BOOLEAN DEFAULT false,
    position_x FLOAT DEFAULT 0,
    position_y FLOAT DEFAULT 0,
    parameters JSONB DEFAULT '{}',
    credentials JSONB DEFAULT '{}',
    error_handling VARCHAR(50) DEFAULT 'STOP_WORKFLOW_ON_ERROR',
    max_retries INTEGER DEFAULT 3,
    retry_wait_time INTEGER DEFAULT 5,
    notes TEXT,
    webhooks TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_node_type CHECK (
        node_type IN ('TRIGGER', 'AI_AGENT', 'EXTERNAL_ACTION', 'ACTION', 'FLOW', 'HUMAN_IN_THE_LOOP', 'TOOL', 'MEMORY')
    ),
    CONSTRAINT valid_error_handling CHECK (
        error_handling IN ('STOP_WORKFLOW_ON_ERROR', 'CONTINUE_REGULAR_OUTPUT_ON_ERROR', 'CONTINUE_ERROR_OUTPUT_ON_ERROR')
    ),
    CONSTRAINT node_name_not_empty CHECK (length(name) > 0),
    UNIQUE(workflow_id, node_id)
);

-- Node connections
CREATE TABLE node_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    source_node_id VARCHAR(255) NOT NULL,
    target_node_id VARCHAR(255) NOT NULL,
    connection_type VARCHAR(50) NOT NULL DEFAULT 'MAIN',
    connection_index INTEGER DEFAULT 0,
    label VARCHAR(255),
    conditions JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_connection_type CHECK (
        connection_type IN ('MAIN', 'AI_AGENT', 'AI_CHAIN', 'AI_DOCUMENT', 'AI_EMBEDDING', 
                           'AI_LANGUAGE_MODEL', 'AI_MEMORY', 'AI_OUTPUT_PARSER', 'AI_RETRIEVER', 
                           'AI_RERANKER', 'AI_TEXT_SPLITTER', 'AI_TOOL', 'AI_VECTOR_STORE')
    ),
    CONSTRAINT source_target_different CHECK (source_node_id != target_node_id),
    FOREIGN KEY (workflow_id, source_node_id) REFERENCES nodes(workflow_id, node_id) ON DELETE CASCADE,
    FOREIGN KEY (workflow_id, target_node_id) REFERENCES nodes(workflow_id, node_id) ON DELETE CASCADE
);

-- Workflow versions
CREATE TABLE workflow_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,
    workflow_data JSONB NOT NULL,
    change_summary TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workflow_id, version)
);

-- Workflow executions
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'NEW',
    mode VARCHAR(50) NOT NULL DEFAULT 'MANUAL',
    triggered_by VARCHAR(255),
    parent_execution_id VARCHAR(255),
    start_time BIGINT,
    end_time BIGINT,
    run_data JSONB,
    metadata JSONB DEFAULT '{}',
    error_message TEXT,
    error_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_execution_status CHECK (
        status IN ('NEW', 'RUNNING', 'SUCCESS', 'ERROR', 'CANCELED', 'WAITING')
    ),
    CONSTRAINT valid_execution_mode CHECK (
        mode IN ('MANUAL', 'TRIGGER', 'WEBHOOK', 'RETRY')
    )
);

-- Node executions
CREATE TABLE node_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(255) REFERENCES workflow_executions(execution_id) ON DELETE CASCADE,
    node_id VARCHAR(255) NOT NULL,
    node_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    start_time BIGINT,
    end_time BIGINT,
    input_data JSONB,
    output_data JSONB,
    error_data JSONB,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_node_status CHECK (
        status IN ('PENDING', 'RUNNING', 'SUCCESS', 'ERROR', 'SKIPPED', 'CANCELED')
    )
);

-- AI generation history
CREATE TABLE ai_generation_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    generated_workflow JSONB,
    suggestions TEXT[],
    missing_info TEXT[],
    feedback TEXT,
    iteration_count INTEGER DEFAULT 1,
    parent_generation_id UUID REFERENCES ai_generation_history(id),
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT description_not_empty CHECK (length(description) > 0)
);

-- AI models
CREATE TABLE ai_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model_id VARCHAR(100) NOT NULL,
    version VARCHAR(50),
    config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, version)
);

-- Integrations
CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_id VARCHAR(255) UNIQUE NOT NULL,
    integration_type VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50) NOT NULL,
    configuration JSONB NOT NULL DEFAULT '{}',
    credential_config JSONB,
    supported_operations TEXT[],
    required_scopes TEXT[],
    active BOOLEAN DEFAULT true,
    verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT integration_name_not_empty CHECK (length(name) > 0)
);

-- OAuth tokens
CREATE TABLE oauth_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    integration_id VARCHAR(255) REFERENCES integrations(integration_id) ON DELETE CASCADE,
    provider VARCHAR(100) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at TIMESTAMP WITH TIME ZONE,
    credential_data JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, integration_id)
);

-- Workflow triggers
CREATE TABLE workflow_triggers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    trigger_type VARCHAR(100) NOT NULL,
    trigger_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    trigger_count INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Validation logs
CREATE TABLE validation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    validation_type VARCHAR(50) NOT NULL,
    validation_result JSONB NOT NULL,
    errors JSONB DEFAULT '[]',
    warnings JSONB DEFAULT '[]',
    is_valid BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_validation_type CHECK (
        validation_type IN ('workflow', 'node', 'connection', 'integration')
    )
);

-- Debug sessions
CREATE TABLE debug_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_name VARCHAR(255),
    session_type VARCHAR(50) NOT NULL DEFAULT 'manual',
    debug_data JSONB DEFAULT '{}',
    breakpoints JSONB DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_debug_status CHECK (
        status IN ('active', 'paused', 'completed', 'canceled')
    )
);

-- Workflow memory
CREATE TABLE workflow_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    execution_id VARCHAR(255) REFERENCES workflow_executions(execution_id) ON DELETE CASCADE,
    memory_key VARCHAR(255) NOT NULL,
    memory_value JSONB,
    memory_type VARCHAR(50) DEFAULT 'runtime',
    node_id VARCHAR(255),
    created_by VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workflow_id, execution_id, memory_key)
);

-- System settings
CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    setting_key VARCHAR(255) UNIQUE NOT NULL,
    setting_value JSONB,
    description TEXT,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_workflows_user_id ON workflows(user_id);
CREATE INDEX idx_workflows_active ON workflows(active);
CREATE INDEX idx_workflows_created_at ON workflows(created_at);
CREATE INDEX idx_workflows_tags ON workflows USING GIN(tags);
CREATE INDEX idx_nodes_workflow_id ON nodes(workflow_id);
CREATE INDEX idx_nodes_type ON nodes(node_type);
CREATE INDEX idx_nodes_subtype ON nodes(node_subtype);
CREATE INDEX idx_node_connections_workflow_id ON node_connections(workflow_id);
CREATE INDEX idx_node_connections_source ON node_connections(source_node_id);
CREATE INDEX idx_node_connections_target ON node_connections(target_node_id);
CREATE INDEX idx_executions_workflow_id ON workflow_executions(workflow_id);
CREATE INDEX idx_executions_status ON workflow_executions(status);
CREATE INDEX idx_executions_created_at ON workflow_executions(created_at);
CREATE INDEX idx_executions_execution_id ON workflow_executions(execution_id);
CREATE INDEX idx_node_executions_execution_id ON node_executions(execution_id);
CREATE INDEX idx_node_executions_node_id ON node_executions(node_id);
CREATE INDEX idx_node_executions_status ON node_executions(status);
CREATE INDEX idx_ai_generation_user_id ON ai_generation_history(user_id);
CREATE INDEX idx_ai_generation_created_at ON ai_generation_history(created_at);
CREATE INDEX idx_integrations_type ON integrations(integration_type);
CREATE INDEX idx_integrations_active ON integrations(active);
CREATE INDEX idx_oauth_tokens_user_id ON oauth_tokens(user_id);
CREATE INDEX idx_oauth_tokens_integration_id ON oauth_tokens(integration_id);
CREATE INDEX idx_triggers_workflow_id ON workflow_triggers(workflow_id);
CREATE INDEX idx_triggers_type ON workflow_triggers(trigger_type);
CREATE INDEX idx_triggers_active ON workflow_triggers(is_active);
CREATE INDEX idx_validation_workflow_id ON validation_logs(workflow_id);
CREATE INDEX idx_validation_type ON validation_logs(validation_type);
CREATE INDEX idx_validation_created_at ON validation_logs(created_at);
CREATE INDEX idx_memory_workflow_id ON workflow_memory(workflow_id);
CREATE INDEX idx_memory_execution_id ON workflow_memory(execution_id);
CREATE INDEX idx_memory_key ON workflow_memory(memory_key);
CREATE INDEX idx_memory_expires_at ON workflow_memory(expires_at);

-- Create triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_settings_updated_at BEFORE UPDATE ON user_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_oauth_tokens_updated_at BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_workflow_triggers_updated_at BEFORE UPDATE ON workflow_triggers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_debug_sessions_updated_at BEFORE UPDATE ON debug_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_workflow_memory_updated_at BEFORE UPDATE ON workflow_memory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_settings_updated_at BEFORE UPDATE ON system_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 