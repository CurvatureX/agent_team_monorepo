-- Recreate integrations table that was removed
-- Description: Recreate the integrations table and restore oauth_tokens relationships
-- Created: 2025-09-29

BEGIN;

-- Create integrations table
CREATE TABLE IF NOT EXISTS integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_id VARCHAR(255) UNIQUE NOT NULL,
    integration_type VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50) NOT NULL DEFAULT '1.0',
    configuration JSONB NOT NULL DEFAULT '{}',
    credential_config JSONB,
    supported_operations TEXT[],
    required_scopes TEXT[],
    active BOOLEAN DEFAULT true,
    verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT integration_name_not_empty CHECK (length(name) > 0)
);

-- Create indexes for integrations
CREATE INDEX IF NOT EXISTS idx_integrations_type ON integrations(integration_type);
CREATE INDEX IF NOT EXISTS idx_integrations_active ON integrations(active);
CREATE INDEX IF NOT EXISTS idx_integrations_integration_id ON integrations(integration_id);

-- Add integration_id column to oauth_tokens if it doesn't exist
ALTER TABLE oauth_tokens ADD COLUMN IF NOT EXISTS integration_id VARCHAR(255);

-- Create index on oauth_tokens.integration_id
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_integration_id ON oauth_tokens(integration_id);

-- Insert standard integrations
INSERT INTO integrations (integration_id, integration_type, name, description, version, configuration, supported_operations, required_scopes, active, verified)
VALUES
    ('slack', 'slack', 'Slack Integration', 'Slack workspace integration for channels, messages, and events', '1.0',
     '{"oauth_url": "https://slack.com/oauth/v2/authorize", "token_url": "https://slack.com/api/oauth.v2.access"}',
     ARRAY['send_message', 'read_messages', 'manage_channels'],
     ARRAY['channels:read', 'chat:write', 'users:read'], true, true),

    ('github', 'github', 'GitHub Integration', 'GitHub integration for repositories, issues, and pull requests', '1.0',
     '{"oauth_url": "https://github.com/login/oauth/authorize", "token_url": "https://github.com/login/oauth/access_token"}',
     ARRAY['read_repos', 'create_issues', 'manage_pull_requests'],
     ARRAY['repo', 'user', 'write:repo_hook'], true, true),

    ('notion', 'notion', 'Notion Integration', 'Notion workspace integration for pages, databases, and blocks', '1.0',
     '{"oauth_url": "https://api.notion.com/v1/oauth/authorize", "token_url": "https://api.notion.com/v1/oauth/token"}',
     ARRAY['read_content', 'write_content', 'manage_databases'],
     ARRAY['read', 'update', 'insert'], true, true),

    ('google_calendar', 'google', 'Google Calendar Integration', 'Google Calendar integration for calendar events and scheduling', '1.0',
     '{"oauth_url": "https://accounts.google.com/o/oauth2/auth", "token_url": "https://oauth2.googleapis.com/token"}',
     ARRAY['read_events', 'create_events', 'update_events'],
     ARRAY['https://www.googleapis.com/auth/calendar'], true, true)
ON CONFLICT (integration_id) DO NOTHING;

-- Update existing oauth_tokens to link with integrations
UPDATE oauth_tokens
SET integration_id =
    CASE
        WHEN provider = 'slack' THEN 'slack'
        WHEN provider = 'github' THEN 'github'
        WHEN provider = 'notion' THEN 'notion'
        WHEN provider = 'google' THEN 'google_calendar'
        ELSE provider
    END
WHERE integration_id IS NULL;

-- Add foreign key constraint (only after data is populated)
ALTER TABLE oauth_tokens
ADD CONSTRAINT IF NOT EXISTS oauth_tokens_integration_id_fkey
FOREIGN KEY (integration_id) REFERENCES integrations(integration_id)
ON DELETE SET NULL;

-- Add unique constraint on user_id and integration_id
ALTER TABLE oauth_tokens
ADD CONSTRAINT IF NOT EXISTS oauth_tokens_user_id_integration_id_key
UNIQUE(user_id, integration_id);

COMMIT;
