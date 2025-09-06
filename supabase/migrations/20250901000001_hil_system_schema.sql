-- HIL (Human-in-the-Loop) System Database Schema
-- Migration: 20250901000001_hil_system_schema.sql
-- Created: 2025-09-01
-- Description: Adds tables for HIL node system with workflow pause/resume functionality

-- Human Interactions Table
-- Stores the state and configuration of HIL interactions
CREATE TABLE IF NOT EXISTS human_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Workflow context
    workflow_id UUID NOT NULL,
    execution_id UUID,
    node_id VARCHAR(255) NOT NULL,

    -- Interaction details
    interaction_type VARCHAR(50) NOT NULL, -- approval, input, selection, etc.
    channel_type VARCHAR(50) NOT NULL,     -- slack, email, webhook, app, etc.
    status VARCHAR(20) DEFAULT 'pending',  -- pending, responded, timeout, error, cancelled
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, critical

    -- Request data (stored as JSONB for flexibility)
    request_data JSONB NOT NULL,           -- Complete HILInputData structure
    response_data JSONB,                   -- Response when completed

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    responded_at TIMESTAMP WITH TIME ZONE,
    timeout_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Metadata
    correlation_id VARCHAR(255),
    tags TEXT[]
);

-- HIL Responses Table
-- Captures all incoming responses from communication channels
CREATE TABLE IF NOT EXISTS hil_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Incoming response data
    workflow_id UUID NOT NULL,
    source_channel VARCHAR(50) NOT NULL,  -- 'slack', 'email', 'webhook', etc.
    raw_payload JSONB NOT NULL,           -- Complete response payload
    headers JSONB,                        -- HTTP headers if applicable

    -- Processing status
    status VARCHAR(20) DEFAULT 'unprocessed', -- 'unprocessed', 'matched', 'filtered_out', 'error'
    processed_at TIMESTAMP WITH TIME ZONE,

    -- AI classification results
    matched_interaction_id UUID REFERENCES human_interactions(id),
    ai_relevance_score DECIMAL(3,2),      -- 0.00-1.00 confidence from AI classifier
    ai_reasoning TEXT,                     -- AI explanation of relevance decision

    -- Timing
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workflow Execution Pauses Table
-- Tracks workflow executions that are paused waiting for human input
CREATE TABLE IF NOT EXISTS workflow_execution_pauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL,

    -- Pause details
    paused_at TIMESTAMP WITH TIME ZONE NOT NULL,
    paused_node_id VARCHAR(255) NOT NULL,
    pause_reason VARCHAR(100) NOT NULL,    -- 'human_interaction', 'timeout', 'error'

    -- Resume conditions (stored as JSONB for flexibility)
    resume_conditions JSONB NOT NULL,     -- Conditions required to resume
    resumed_at TIMESTAMP WITH TIME ZONE,
    resume_trigger VARCHAR(100),          -- What triggered the resume

    -- Status
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'resumed', 'timeout'

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_human_interactions_workflow ON human_interactions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_human_interactions_status ON human_interactions(status);
CREATE INDEX IF NOT EXISTS idx_human_interactions_pending_timeout ON human_interactions(timeout_at)
    WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_human_interactions_correlation ON human_interactions(correlation_id)
    WHERE correlation_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_hil_responses_workflow ON hil_responses(workflow_id);
CREATE INDEX IF NOT EXISTS idx_hil_responses_status ON hil_responses(status);
CREATE INDEX IF NOT EXISTS idx_hil_responses_unprocessed ON hil_responses(received_at)
    WHERE status = 'unprocessed';
CREATE INDEX IF NOT EXISTS idx_hil_responses_matched ON hil_responses(matched_interaction_id)
    WHERE matched_interaction_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_workflow_execution_pauses_execution ON workflow_execution_pauses(execution_id);
CREATE INDEX IF NOT EXISTS idx_workflow_execution_pauses_active ON workflow_execution_pauses(status)
    WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_workflow_execution_pauses_node ON workflow_execution_pauses(paused_node_id);

-- Add updated_at trigger for human_interactions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_human_interactions_updated_at
    BEFORE UPDATE ON human_interactions
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_workflow_execution_pauses_updated_at
    BEFORE UPDATE ON workflow_execution_pauses
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE human_interactions IS 'Stores HIL interaction state and configuration';
COMMENT ON TABLE hil_responses IS 'Captures all incoming responses from communication channels';
COMMENT ON TABLE workflow_execution_pauses IS 'Tracks workflow executions paused for human input';

COMMENT ON COLUMN human_interactions.request_data IS 'Complete HILInputData structure as JSON';
COMMENT ON COLUMN human_interactions.response_data IS 'Human response data when interaction completes';
COMMENT ON COLUMN hil_responses.ai_relevance_score IS 'AI confidence score (0.0-1.0) for response relevance';
COMMENT ON COLUMN workflow_execution_pauses.resume_conditions IS 'JSON conditions required to resume workflow';
