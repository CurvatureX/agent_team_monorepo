-- ==============================================================================
-- Workflow Engine Database Schema - Complete Version
-- Based on protobuf definitions and planning.md requirements
-- Database: PostgreSQL 14+
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============================================================================
-- User Management
-- ==============================================================================

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

-- ==============================================================================
-- Workflow Management (Based on Workflow protobuf)
-- ==============================================================================

-- Workflows table - stores complete workflow definitions
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT true,
    
    -- Core workflow data (based on Workflow protobuf)
    workflow_data JSONB NOT NULL,  -- Complete Workflow protobuf JSON
    settings JSONB,                -- WorkflowSettings
    static_data JSONB,             -- Static data for nodes
    pin_data JSONB,                -- Debug/test data
    
    -- Metadata
    version VARCHAR(50) DEFAULT '1.0.0',
    tags TEXT[],
    is_template BOOLEAN DEFAULT false,
    template_category VARCHAR(100),
    
    -- Timestamps (Unix timestamp for consistency with protobuf)
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    
    -- Constraints
    CONSTRAINT workflows_name_not_empty CHECK (length(name) > 0),
    CONSTRAINT workflows_valid_workflow_data CHECK (workflow_data IS NOT NULL)
);

-- ==============================================================================
-- Node System (Based on Node protobuf - 8 Core Node Types)
-- ==============================================================================

-- Node definitions - stores individual node configurations
CREATE TABLE nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id VARCHAR(255) NOT NULL,  -- Unique identifier within workflow
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    
    -- Node type information (based on NodeType and NodeSubtype enums)
    node_type VARCHAR(50) NOT NULL,     -- TRIGGER, AI_AGENT, EXTERNAL_ACTION, ACTION, FLOW, HUMAN_IN_THE_LOOP, TOOL, MEMORY
    node_subtype VARCHAR(100) NOT NULL, -- Specific implementation type
    type_version INTEGER DEFAULT 1,
    
    -- Basic node properties
    name VARCHAR(255) NOT NULL,
    description TEXT,
    disabled BOOLEAN DEFAULT false,
    
    -- Position and UI information
    position_x FLOAT DEFAULT 0,
    position_y FLOAT DEFAULT 0,
    
    -- Node configuration (based on Node protobuf)
    parameters JSONB DEFAULT '{}',    -- Node-specific parameters
    credentials JSONB DEFAULT '{}',   -- Authentication/credential data
    
    -- Error handling and retry configuration
    error_handling VARCHAR(50) DEFAULT 'STOP_WORKFLOW_ON_ERROR',
    max_retries INTEGER DEFAULT 3,
    retry_wait_time INTEGER DEFAULT 5,  -- seconds
    
    -- Additional metadata
    notes TEXT,
    webhooks TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_node_type CHECK (
        node_type IN ('TRIGGER', 'AI_AGENT', 'EXTERNAL_ACTION', 'ACTION', 'FLOW', 'HUMAN_IN_THE_LOOP', 'TOOL', 'MEMORY')
    ),
    CONSTRAINT valid_error_handling CHECK (
        error_handling IN ('STOP_WORKFLOW_ON_ERROR', 'CONTINUE_REGULAR_OUTPUT_ON_ERROR', 'CONTINUE_ERROR_OUTPUT_ON_ERROR')
    ),
    CONSTRAINT node_name_not_empty CHECK (length(name) > 0),
    
    UNIQUE(workflow_id, node_id)
);

-- Node connections - stores connections between nodes
CREATE TABLE node_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    
    -- Source and target node information
    source_node_id VARCHAR(255) NOT NULL,
    target_node_id VARCHAR(255) NOT NULL,
    
    -- Connection type and configuration
    connection_type VARCHAR(50) NOT NULL DEFAULT 'MAIN',
    connection_index INTEGER DEFAULT 0,
    
    -- Connection metadata
    label VARCHAR(255),
    conditions JSONB DEFAULT '{}',  -- Conditional connection rules
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_connection_type CHECK (
        connection_type IN ('MAIN', 'AI_AGENT', 'AI_CHAIN', 'AI_DOCUMENT', 'AI_EMBEDDING', 
                           'AI_LANGUAGE_MODEL', 'AI_MEMORY', 'AI_OUTPUT_PARSER', 'AI_RETRIEVER', 
                           'AI_RERANKER', 'AI_TEXT_SPLITTER', 'AI_TOOL', 'AI_VECTOR_STORE')
    ),
    CONSTRAINT source_target_different CHECK (source_node_id != target_node_id),
    
    -- Foreign key constraints to ensure nodes exist in the same workflow
    FOREIGN KEY (workflow_id, source_node_id) REFERENCES nodes(workflow_id, node_id) ON DELETE CASCADE,
    FOREIGN KEY (workflow_id, target_node_id) REFERENCES nodes(workflow_id, node_id) ON DELETE CASCADE
);

-- Node templates - reusable node configurations
CREATE TABLE node_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Template information
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    
    -- Node type information
    node_type VARCHAR(50) NOT NULL,
    node_subtype VARCHAR(100) NOT NULL,
    
    -- Template configuration
    default_parameters JSONB DEFAULT '{}',
    required_parameters TEXT[],
    parameter_schema JSONB,  -- JSON schema for parameter validation
    
    -- Template metadata
    version VARCHAR(50) DEFAULT '1.0.0',
    is_system_template BOOLEAN DEFAULT false,
    created_by UUID REFERENCES users(id),
    
    -- Usage statistics
    usage_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_template_node_type CHECK (
        node_type IN ('TRIGGER', 'AI_AGENT', 'EXTERNAL_ACTION', 'ACTION', 'FLOW', 'HUMAN_IN_THE_LOOP', 'TOOL', 'MEMORY')
    ),
    CONSTRAINT template_name_not_empty CHECK (length(name) > 0)
);

-- ==============================================================================
-- Execution System (Based on ExecutionData protobuf)
-- ==============================================================================

-- Workflow executions - main execution records
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    
    -- Execution status (based on ExecutionStatus enum)
    status VARCHAR(50) NOT NULL DEFAULT 'NEW',
    mode VARCHAR(50) NOT NULL DEFAULT 'MANUAL',  -- MANUAL, TRIGGER, WEBHOOK, RETRY
    
    -- Execution context
    triggered_by VARCHAR(255),
    parent_execution_id VARCHAR(255),  -- For sub-workflows
    
    -- Timing
    start_time BIGINT,
    end_time BIGINT,
    
    -- Execution data (based on ExecutionData protobuf)
    run_data JSONB,              -- RunData protobuf JSON
    metadata JSONB DEFAULT '{}',
    
    -- Error information
    error_message TEXT,
    error_details JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_execution_status CHECK (
        status IN ('NEW', 'RUNNING', 'SUCCESS', 'ERROR', 'CANCELED', 'WAITING')
    ),
    CONSTRAINT valid_execution_mode CHECK (
        mode IN ('MANUAL', 'TRIGGER', 'WEBHOOK', 'RETRY')
    )
);

-- ==============================================================================
-- Integration System (Based on Integration protobuf)
-- ==============================================================================

-- Available integrations
CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_id VARCHAR(255) UNIQUE NOT NULL,
    integration_type VARCHAR(100) NOT NULL,  -- API, MCP, WEBHOOK, etc.
    
    -- Basic info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50) NOT NULL,
    
    -- Configuration (based on Integration protobuf)
    configuration JSONB NOT NULL DEFAULT '{}',
    credential_config JSONB,  -- CredentialConfig protobuf JSON
    
    -- Capabilities
    supported_operations TEXT[],
    required_scopes TEXT[],
    
    -- Status
    active BOOLEAN DEFAULT true,
    verified BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT integration_name_not_empty CHECK (length(name) > 0)
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

-- ==============================================================================
-- Indexes for Performance
-- ==============================================================================

-- Users indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

-- Workflows indexes
CREATE INDEX idx_workflows_user_id ON workflows(user_id);
CREATE INDEX idx_workflows_active ON workflows(active);
CREATE INDEX idx_workflows_created_at ON workflows(created_at);
CREATE INDEX idx_workflows_tags ON workflows USING GIN(tags);

-- Nodes indexes
CREATE INDEX idx_nodes_workflow_id ON nodes(workflow_id);
CREATE INDEX idx_nodes_node_id ON nodes(node_id);
CREATE INDEX idx_nodes_type ON nodes(node_type);
CREATE INDEX idx_nodes_subtype ON nodes(node_subtype);
CREATE INDEX idx_nodes_disabled ON nodes(disabled);
CREATE INDEX idx_nodes_workflow_node_id ON nodes(workflow_id, node_id);

-- Node connections indexes
CREATE INDEX idx_node_connections_workflow_id ON node_connections(workflow_id);
CREATE INDEX idx_node_connections_source ON node_connections(source_node_id);
CREATE INDEX idx_node_connections_target ON node_connections(target_node_id);
CREATE INDEX idx_node_connections_type ON node_connections(connection_type);
CREATE INDEX idx_node_connections_source_target ON node_connections(workflow_id, source_node_id, target_node_id);

-- Node templates indexes
CREATE INDEX idx_node_templates_type ON node_templates(node_type);
CREATE INDEX idx_node_templates_subtype ON node_templates(node_subtype);
CREATE INDEX idx_node_templates_category ON node_templates(category);
CREATE INDEX idx_node_templates_system ON node_templates(is_system_template);
CREATE INDEX idx_node_templates_created_by ON node_templates(created_by);

-- Executions indexes
CREATE INDEX idx_executions_workflow_id ON workflow_executions(workflow_id);
CREATE INDEX idx_executions_status ON workflow_executions(status);
CREATE INDEX idx_executions_created_at ON workflow_executions(created_at);
CREATE INDEX idx_executions_execution_id ON workflow_executions(execution_id);

-- Integration indexes
CREATE INDEX idx_integrations_type ON integrations(integration_type);
CREATE INDEX idx_integrations_active ON integrations(active);

-- ==============================================================================
-- Triggers for Updated At Timestamps
-- ==============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at columns
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_settings_updated_at BEFORE UPDATE ON user_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_nodes_updated_at BEFORE UPDATE ON nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_node_templates_updated_at BEFORE UPDATE ON node_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_settings_updated_at BEFORE UPDATE ON system_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 