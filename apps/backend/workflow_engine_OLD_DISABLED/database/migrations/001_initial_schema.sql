-- Migration: 001_initial_schema
-- Description: Initial database schema for workflow engine
-- Created: 2024-01-01
-- Author: Workflow Engine Team

-- This migration creates the initial database schema
-- Run this migration using: alembic upgrade head

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_workflows_user_id ON workflows(user_id);
CREATE INDEX idx_workflows_active ON workflows(active);
CREATE INDEX idx_executions_workflow_id ON workflow_executions(workflow_id);
CREATE INDEX idx_executions_status ON workflow_executions(status);
