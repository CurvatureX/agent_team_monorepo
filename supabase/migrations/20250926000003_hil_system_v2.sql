-- Human-in-the-Loop (HIL) System Schema for workflow_engine_v2
-- Comprehensive HIL functionality with AI classification and timeout management

-- HIL Interactions Table - Core HIL interaction tracking
CREATE TABLE IF NOT EXISTS hil_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL,
    execution_id UUID,
    node_id VARCHAR(255) NOT NULL,
    user_id UUID,

    -- Interaction classification
    interaction_type VARCHAR(50) NOT NULL, -- approval, input, selection, review
    channel_type VARCHAR(50) NOT NULL,     -- slack, email, webhook, in_app

    -- Status and lifecycle
    status VARCHAR(20) DEFAULT 'pending',  -- pending, responded, timeout, cancelled

    -- Request data and response
    request_data JSONB NOT NULL,           -- Original request content
    response_data JSONB,                   -- Human response when received

    -- Timeout management
    timeout_seconds INTEGER DEFAULT 3600,  -- Timeout in seconds
    timeout_at TIMESTAMP WITH TIME ZONE NOT NULL,
    warning_sent BOOLEAN DEFAULT FALSE,    -- 15-min warning sent flag

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    responded_at TIMESTAMP WITH TIME ZONE,

    -- Workflow context
    workflow_context JSONB,               -- Template variables for messages

    CONSTRAINT valid_status CHECK (status IN ('pending', 'responded', 'timeout', 'cancelled')),
    CONSTRAINT valid_interaction_type CHECK (interaction_type IN ('approval', 'input', 'selection', 'review')),
    CONSTRAINT valid_channel_type CHECK (channel_type IN ('slack', 'email', 'webhook', 'in_app'))
);

-- HIL Responses Table - AI classification and response tracking
CREATE TABLE IF NOT EXISTS hil_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source webhook/response data
    raw_payload JSONB NOT NULL,           -- Original webhook payload
    source_channel VARCHAR(50),           -- slack, email, etc.
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- AI Classification results
    matched_interaction_id UUID REFERENCES hil_interactions(id),
    ai_relevance_score DECIMAL(3,2),      -- 0.00-1.00 relevance score
    ai_reasoning TEXT,                    -- AI explanation for classification
    ai_classification VARCHAR(20),        -- relevant, filtered, uncertain

    -- Processing status
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,

    -- Human verification (if needed)
    human_verified BOOLEAN,
    human_verification_notes TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workflow Execution Pauses Table - Pause/resume state management
CREATE TABLE IF NOT EXISTS workflow_execution_pauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL,
    node_id VARCHAR(255) NOT NULL,

    -- Pause details
    pause_reason VARCHAR(100) NOT NULL,   -- human_interaction, timeout, error, manual
    pause_data JSONB,                     -- Context data for pause

    -- Resume conditions
    resume_conditions JSONB NOT NULL,     -- Conditions required to resume
    resume_reason VARCHAR(100),           -- human_response, timeout_reached, manual_resume
    resume_data JSONB,                    -- Data provided on resume

    -- Status and lifecycle
    status VARCHAR(20) DEFAULT 'active',  -- active, resumed, cancelled

    -- Timestamps
    paused_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resumed_at TIMESTAMP WITH TIME ZONE,

    -- HIL integration
    hil_interaction_id UUID REFERENCES hil_interactions(id),

    CONSTRAINT valid_pause_status CHECK (status IN ('active', 'resumed', 'cancelled')),
    CONSTRAINT valid_pause_reason CHECK (pause_reason IN ('human_interaction', 'timeout', 'error', 'manual', 'system_maintenance'))
);

-- HIL Message Templates Table - Response message templates
CREATE TABLE IF NOT EXISTS hil_message_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Template identification
    template_name VARCHAR(100) NOT NULL,
    channel_type VARCHAR(50) NOT NULL,
    message_type VARCHAR(50) NOT NULL,    -- approved, rejected, timeout, warning

    -- Template content
    subject_template TEXT,                -- For email, Slack title
    body_template TEXT NOT NULL,         -- Main message content

    -- Template variables documentation
    available_variables JSONB,           -- List of available template variables

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,

    UNIQUE(template_name, channel_type, message_type)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_hil_interactions_status ON hil_interactions(status);
CREATE INDEX IF NOT EXISTS idx_hil_interactions_timeout ON hil_interactions(timeout_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_hil_interactions_workflow ON hil_interactions(workflow_id, execution_id);
CREATE INDEX IF NOT EXISTS idx_hil_interactions_user ON hil_interactions(user_id);

CREATE INDEX IF NOT EXISTS idx_hil_responses_processed ON hil_responses(processed, received_at);
CREATE INDEX IF NOT EXISTS idx_hil_responses_interaction ON hil_responses(matched_interaction_id);

CREATE INDEX IF NOT EXISTS idx_workflow_pauses_status ON workflow_execution_pauses(status);
CREATE INDEX IF NOT EXISTS idx_workflow_pauses_execution ON workflow_execution_pauses(execution_id);
CREATE INDEX IF NOT EXISTS idx_workflow_pauses_hil ON workflow_execution_pauses(hil_interaction_id);

-- Row Level Security (RLS) for multi-tenant isolation
ALTER TABLE hil_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE hil_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_execution_pauses ENABLE ROW LEVEL SECURITY;
ALTER TABLE hil_message_templates ENABLE ROW LEVEL SECURITY;

-- RLS Policies for hil_interactions
CREATE POLICY "Users can view their own HIL interactions" ON hil_interactions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own HIL interactions" ON hil_interactions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own HIL interactions" ON hil_interactions
    FOR UPDATE USING (auth.uid() = user_id);

-- RLS Policies for hil_responses (admin/service access)
CREATE POLICY "Service role can manage HIL responses" ON hil_responses
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- RLS Policies for workflow_execution_pauses
CREATE POLICY "Users can view pauses for their executions" ON workflow_execution_pauses
    FOR SELECT USING (
        auth.uid() IN (
            SELECT user_id FROM executions WHERE execution_id = workflow_execution_pauses.execution_id
        )
    );

CREATE POLICY "Service role can manage workflow pauses" ON workflow_execution_pauses
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- RLS Policies for message templates (admin management)
CREATE POLICY "Service role can manage message templates" ON hil_message_templates
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Functions for HIL management
CREATE OR REPLACE FUNCTION get_pending_hil_interactions(p_user_id UUID DEFAULT NULL, p_limit INTEGER DEFAULT 50)
RETURNS TABLE(
    interaction_id UUID,
    workflow_id UUID,
    execution_id UUID,
    node_id VARCHAR(255),
    interaction_type VARCHAR(50),
    channel_type VARCHAR(50),
    request_data JSONB,
    timeout_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        hi.id,
        hi.workflow_id,
        hi.execution_id,
        hi.node_id,
        hi.interaction_type,
        hi.channel_type,
        hi.request_data,
        hi.timeout_at,
        hi.created_at
    FROM hil_interactions hi
    WHERE hi.status = 'pending'
    AND (p_user_id IS NULL OR hi.user_id = p_user_id)
    ORDER BY hi.created_at ASC
    LIMIT p_limit;
END;
$$;

CREATE OR REPLACE FUNCTION get_expired_hil_interactions(p_current_time TIMESTAMP WITH TIME ZONE DEFAULT NOW())
RETURNS TABLE(
    interaction_id UUID,
    workflow_id UUID,
    execution_id UUID,
    node_id VARCHAR(255),
    timeout_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        hi.id,
        hi.workflow_id,
        hi.execution_id,
        hi.node_id,
        hi.timeout_at
    FROM hil_interactions hi
    WHERE hi.status = 'pending'
    AND hi.timeout_at <= p_current_time
    ORDER BY hi.timeout_at ASC;
END;
$$;

-- Insert default message templates
INSERT INTO hil_message_templates (template_name, channel_type, message_type, subject_template, body_template, available_variables)
VALUES
    (
        'approval_request_slack',
        'slack',
        'request',
        'Workflow Approval Required: {{workflow_name}}',
        '🔔 **Workflow Approval Required**\n\n**Workflow:** {{workflow_name}}\n**Description:** {{description}}\n\nPlease respond with:\n• ✅ "approve" or "yes" to continue\n• ❌ "reject" or "no" to stop\n\n**Timeout:** {{timeout_minutes}} minutes\n**Request ID:** {{interaction_id}}',
        '["workflow_name", "description", "timeout_minutes", "interaction_id", "user_name", "execution_id"]'::jsonb
    ),
    (
        'approval_approved_slack',
        'slack',
        'approved',
        'Workflow Approved: {{workflow_name}}',
        '✅ **Workflow Approved**\n\n**Workflow:** {{workflow_name}}\n**Approved by:** {{responder_name}}\n**Response:** {{response_text}}\n\nWorkflow execution will continue.',
        '["workflow_name", "responder_name", "response_text", "interaction_id"]'::jsonb
    ),
    (
        'approval_rejected_slack',
        'slack',
        'rejected',
        'Workflow Rejected: {{workflow_name}}',
        '❌ **Workflow Rejected**\n\n**Workflow:** {{workflow_name}}\n**Rejected by:** {{responder_name}}\n**Response:** {{response_text}}\n\nWorkflow execution has been stopped.',
        '["workflow_name", "responder_name", "response_text", "interaction_id"]'::jsonb
    ),
    (
        'approval_timeout_slack',
        'slack',
        'timeout',
        'Workflow Timeout: {{workflow_name}}',
        '⏰ **Workflow Timed Out**\n\n**Workflow:** {{workflow_name}}\n**Timeout after:** {{timeout_minutes}} minutes\n\n{{timeout_action_description}}',
        '["workflow_name", "timeout_minutes", "timeout_action_description", "interaction_id"]'::jsonb
    )
ON CONFLICT (template_name, channel_type, message_type) DO UPDATE SET
    subject_template = EXCLUDED.subject_template,
    body_template = EXCLUDED.body_template,
    available_variables = EXCLUDED.available_variables,
    updated_at = NOW();

-- Comments for documentation
COMMENT ON TABLE hil_interactions IS 'Core HIL interaction tracking with timeout management and AI classification support';
COMMENT ON TABLE hil_responses IS 'AI-powered classification and tracking of webhook responses to HIL interactions';
COMMENT ON TABLE workflow_execution_pauses IS 'Workflow execution pause/resume state management for HIL and other interruptions';
COMMENT ON TABLE hil_message_templates IS 'Configurable message templates for HIL response notifications';
