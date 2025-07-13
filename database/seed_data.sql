-- ==============================================================================
-- Seed Data for Workflow Engine
-- This file contains initial data for development and testing
-- ==============================================================================

-- Insert default AI models
INSERT INTO ai_models (name, provider, model_id, version, config, is_active, is_default) VALUES
('GPT-4', 'openai', 'gpt-4', 'latest', '{"max_tokens": 4096, "temperature": 0.7}', true, true),
('GPT-3.5 Turbo', 'openai', 'gpt-3.5-turbo', 'latest', '{"max_tokens": 4096, "temperature": 0.7}', true, false),
('Claude-3 Sonnet', 'anthropic', 'claude-3-sonnet-20240229', 'latest', '{"max_tokens": 4096, "temperature": 0.7}', true, false),
('Claude-3 Haiku', 'anthropic', 'claude-3-haiku-20240307', 'latest', '{"max_tokens": 4096, "temperature": 0.7}', true, false);

-- Insert default system settings
INSERT INTO system_settings (setting_key, setting_value, description, is_public) VALUES
('max_workflow_nodes', '100', 'Maximum number of nodes allowed in a workflow', true),
('max_execution_time', '3600', 'Maximum execution time in seconds', true),
('default_retry_count', '3', 'Default number of retries for failed nodes', true),
('enable_debug_mode', 'true', 'Enable debug mode for development', false),
('workflow_auto_save', 'true', 'Enable automatic saving of workflows', true),
('max_concurrent_executions', '10', 'Maximum number of concurrent workflow executions', true),
('default_timeout', '300', 'Default timeout for node execution in seconds', true),
('enable_ai_suggestions', 'true', 'Enable AI-powered workflow suggestions', true),
('max_workflow_size', '10485760', 'Maximum workflow size in bytes (10MB)', true),
('enable_workflow_sharing', 'true', 'Enable workflow sharing between users', true);

-- Insert common integrations
INSERT INTO integrations (integration_id, integration_type, name, description, version, configuration, credential_config, supported_operations, required_scopes, active, verified) VALUES
-- Google Services
('google_calendar', 'API', 'Google Calendar', 'Google Calendar API integration for event management', '1.0.0', 
 '{"base_url": "https://www.googleapis.com/calendar/v3", "auth_type": "oauth2", "rate_limit": 100}', 
 '{"oauth2": {"client_id": "", "client_secret": "", "scopes": ["https://www.googleapis.com/auth/calendar"]}}',
 ARRAY['create_event', 'update_event', 'delete_event', 'list_events', 'get_event'],
 ARRAY['https://www.googleapis.com/auth/calendar'], true, true),

('google_drive', 'API', 'Google Drive', 'Google Drive API integration for file management', '1.0.0',
 '{"base_url": "https://www.googleapis.com/drive/v3", "auth_type": "oauth2", "rate_limit": 100}',
 '{"oauth2": {"client_id": "", "client_secret": "", "scopes": ["https://www.googleapis.com/auth/drive"]}}',
 ARRAY['create_file', 'update_file', 'delete_file', 'list_files', 'download_file', 'upload_file'],
 ARRAY['https://www.googleapis.com/auth/drive'], true, true),

('gmail', 'API', 'Gmail', 'Gmail API integration for email management', '1.0.0',
 '{"base_url": "https://gmail.googleapis.com/gmail/v1", "auth_type": "oauth2", "rate_limit": 100}',
 '{"oauth2": {"client_id": "", "client_secret": "", "scopes": ["https://www.googleapis.com/auth/gmail.send"]}}',
 ARRAY['send_email', 'read_email', 'search_email', 'create_draft'],
 ARRAY['https://www.googleapis.com/auth/gmail.send'], true, true),

-- Communication Tools
('slack', 'API', 'Slack', 'Slack API integration for team communication', '1.0.0',
 '{"base_url": "https://slack.com/api", "auth_type": "oauth2", "rate_limit": 100}',
 '{"oauth2": {"client_id": "", "client_secret": "", "scopes": ["chat:write", "channels:read"]}}',
 ARRAY['send_message', 'create_channel', 'invite_user', 'upload_file', 'get_channel_info'],
 ARRAY['chat:write', 'channels:read'], true, true),

('discord', 'API', 'Discord', 'Discord API integration for community management', '1.0.0',
 '{"base_url": "https://discord.com/api/v10", "auth_type": "bot_token", "rate_limit": 50}',
 '{"bot_token": {"token": ""}}',
 ARRAY['send_message', 'create_channel', 'manage_roles', 'get_guild_info'],
 ARRAY[], true, true),

-- Development Tools
('github', 'API', 'GitHub', 'GitHub API integration for code management', '1.0.0',
 '{"base_url": "https://api.github.com", "auth_type": "oauth2", "rate_limit": 100}',
 '{"oauth2": {"client_id": "", "client_secret": "", "scopes": ["repo", "user"]}}',
 ARRAY['create_issue', 'create_pr', 'merge_pr', 'create_repo', 'get_repo_info', 'create_branch'],
 ARRAY['repo', 'user'], true, true),

('gitlab', 'API', 'GitLab', 'GitLab API integration for code management', '1.0.0',
 '{"base_url": "https://gitlab.com/api/v4", "auth_type": "oauth2", "rate_limit": 100}',
 '{"oauth2": {"client_id": "", "client_secret": "", "scopes": ["api", "read_user"]}}',
 ARRAY['create_issue', 'create_mr', 'merge_mr', 'create_project', 'get_project_info'],
 ARRAY['api', 'read_user'], true, true),

-- Project Management
('trello', 'API', 'Trello', 'Trello API integration for project management', '1.0.0',
 '{"base_url": "https://api.trello.com/1", "auth_type": "oauth2", "rate_limit": 100}',
 '{"oauth2": {"client_id": "", "client_secret": "", "scopes": ["read", "write"]}}',
 ARRAY['create_card', 'update_card', 'create_board', 'create_list', 'move_card'],
 ARRAY['read', 'write'], true, true),

('notion', 'API', 'Notion', 'Notion API integration for knowledge management', '1.0.0',
 '{"base_url": "https://api.notion.com/v1", "auth_type": "oauth2", "rate_limit": 100}',
 '{"oauth2": {"client_id": "", "client_secret": "", "scopes": ["read", "write"]}}',
 ARRAY['create_page', 'update_page', 'create_database', 'query_database', 'get_page'],
 ARRAY['read', 'write'], true, true),

-- Data & Analytics
('airtable', 'API', 'Airtable', 'Airtable API integration for database management', '1.0.0',
 '{"base_url": "https://api.airtable.com/v0", "auth_type": "api_key", "rate_limit": 100}',
 '{"api_key": {"key": ""}}',
 ARRAY['create_record', 'update_record', 'delete_record', 'list_records', 'get_base_info'],
 ARRAY[], true, true),

-- Utility Services
('http_request', 'UTILITY', 'HTTP Request', 'Generic HTTP request utility for API calls', '1.0.0',
 '{"supports_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"], "timeout": 30}',
 '{"auth_types": ["none", "basic", "bearer", "api_key", "oauth2"]}',
 ARRAY['get', 'post', 'put', 'delete', 'patch', 'head', 'options'],
 ARRAY[], true, true),

('webhook', 'UTILITY', 'Webhook', 'Webhook utility for receiving HTTP callbacks', '1.0.0',
 '{"supported_methods": ["GET", "POST"], "timeout": 30}',
 '{}',
 ARRAY['receive_webhook', 'validate_signature', 'parse_payload'],
 ARRAY[], true, true),

-- File Processing
('file_processor', 'UTILITY', 'File Processor', 'File processing utility for various file operations', '1.0.0',
 '{"supported_formats": ["txt", "json", "csv", "xml", "pdf", "docx"], "max_size": 10485760}',
 '{}',
 ARRAY['read_file', 'write_file', 'convert_format', 'extract_text', 'validate_format'],
 ARRAY[], true, true),

-- AI Services
('openai', 'AI', 'OpenAI', 'OpenAI API integration for AI capabilities', '1.0.0',
 '{"base_url": "https://api.openai.com/v1", "auth_type": "api_key", "rate_limit": 100}',
 '{"api_key": {"key": ""}}',
 ARRAY['chat_completion', 'text_completion', 'image_generation', 'text_embedding', 'speech_to_text'],
 ARRAY[], true, true),

('anthropic', 'AI', 'Anthropic', 'Anthropic API integration for AI capabilities', '1.0.0',
 '{"base_url": "https://api.anthropic.com/v1", "auth_type": "api_key", "rate_limit": 100}',
 '{"api_key": {"key": ""}}',
 ARRAY['chat_completion', 'text_completion'],
 ARRAY[], true, true);

-- Insert sample workflow templates
INSERT INTO workflows (
    id, 
    user_id, 
    name, 
    description, 
    active, 
    workflow_data, 
    settings, 
    static_data, 
    version, 
    tags, 
    is_template, 
    template_category,
    created_at,
    updated_at
) VALUES
-- Template 1: Simple API to Slack notification
(
    uuid_generate_v4(),
    NULL,  -- System template
    'API to Slack Notification',
    'Monitor an API endpoint and send notifications to Slack when status changes',
    true,
    '{
        "nodes": {
            "trigger_1": {
                "id": "trigger_1",
                "type": "TRIGGER",
                "subtype": "WEBHOOK",
                "position": {"x": 100, "y": 100},
                "data": {
                    "name": "API Status Check",
                    "webhook_config": {
                        "method": "POST",
                        "path": "/api-status"
                    }
                }
            },
            "http_1": {
                "id": "http_1",
                "type": "EXTERNAL_ACTION",
                "subtype": "HTTP_REQUEST",
                "position": {"x": 300, "y": 100},
                "data": {
                    "name": "Check API Status",
                    "url": "https://api.example.com/health",
                    "method": "GET",
                    "headers": {}
                }
            },
            "slack_1": {
                "id": "slack_1",
                "type": "EXTERNAL_ACTION",
                "subtype": "SLACK_MESSAGE",
                "position": {"x": 500, "y": 100},
                "data": {
                    "name": "Send Slack Alert",
                    "channel": "#alerts",
                    "message": "API Status: {{http_1.response.status}}"
                }
            }
        },
        "connections": {
            "trigger_1": ["http_1"],
            "http_1": ["slack_1"]
        }
    }',
    '{"timeout": 300, "retry_count": 3}',
    '{}',
    '1.0.0',
    ARRAY['api', 'monitoring', 'slack', 'webhook'],
    true,
    'monitoring',
    extract(epoch from now()),
    extract(epoch from now())
),

-- Template 2: GitHub Issue to Trello Card
(
    uuid_generate_v4(),
    NULL,  -- System template
    'GitHub Issue to Trello Card',
    'Automatically create Trello cards when new GitHub issues are created',
    true,
    '{
        "nodes": {
            "trigger_1": {
                "id": "trigger_1",
                "type": "TRIGGER",
                "subtype": "WEBHOOK",
                "position": {"x": 100, "y": 100},
                "data": {
                    "name": "GitHub Issue Webhook",
                    "webhook_config": {
                        "method": "POST",
                        "path": "/github-issue"
                    }
                }
            },
            "condition_1": {
                "id": "condition_1",
                "type": "FLOW",
                "subtype": "IF_CONDITION",
                "position": {"x": 300, "y": 100},
                "data": {
                    "name": "Check Issue Action",
                    "condition": "{{trigger_1.body.action}} == ''opened''"
                }
            },
            "trello_1": {
                "id": "trello_1",
                "type": "EXTERNAL_ACTION",
                "subtype": "TRELLO_CREATE_CARD",
                "position": {"x": 500, "y": 100},
                "data": {
                    "name": "Create Trello Card",
                    "board_id": "{{settings.trello_board_id}}",
                    "list_id": "{{settings.trello_list_id}}",
                    "card_name": "{{trigger_1.body.issue.title}}",
                    "description": "{{trigger_1.body.issue.body}}"
                }
            }
        },
        "connections": {
            "trigger_1": ["condition_1"],
            "condition_1": ["trello_1"]
        }
    }',
    '{"timeout": 300, "retry_count": 3}',
    '{}',
    '1.0.0',
    ARRAY['github', 'trello', 'project-management', 'webhook'],
    true,
    'project-management',
    extract(epoch from now()),
    extract(epoch from now())
),

-- Template 3: AI Content Generation Workflow
(
    uuid_generate_v4(),
    NULL,  -- System template
    'AI Content Generation Pipeline',
    'Generate content using AI, review it, and publish to multiple platforms',
    true,
    '{
        "nodes": {
            "trigger_1": {
                "id": "trigger_1",
                "type": "TRIGGER",
                "subtype": "MANUAL",
                "position": {"x": 100, "y": 100},
                "data": {
                    "name": "Manual Start",
                    "inputs": {
                        "topic": "string",
                        "target_audience": "string",
                        "content_type": "string"
                    }
                }
            },
            "ai_1": {
                "id": "ai_1",
                "type": "AI_AGENT",
                "subtype": "TEXT_GENERATION",
                "position": {"x": 300, "y": 100},
                "data": {
                    "name": "Generate Content",
                    "prompt": "Create a {{trigger_1.content_type}} about {{trigger_1.topic}} for {{trigger_1.target_audience}}",
                    "model": "gpt-4",
                    "max_tokens": 1000
                }
            },
            "human_1": {
                "id": "human_1",
                "type": "HUMAN_IN_THE_LOOP",
                "subtype": "APPROVAL",
                "position": {"x": 500, "y": 100},
                "data": {
                    "name": "Review Content",
                    "message": "Please review the generated content",
                    "timeout": 3600
                }
            },
            "publish_1": {
                "id": "publish_1",
                "type": "EXTERNAL_ACTION",
                "subtype": "MULTI_PLATFORM_PUBLISH",
                "position": {"x": 700, "y": 100},
                "data": {
                    "name": "Publish Content",
                    "platforms": ["twitter", "linkedin", "blog"]
                }
            }
        },
        "connections": {
            "trigger_1": ["ai_1"],
            "ai_1": ["human_1"],
            "human_1": ["publish_1"]
        }
    }',
    '{"timeout": 7200, "retry_count": 1}',
    '{}',
    '1.0.0',
    ARRAY['ai', 'content', 'publishing', 'review'],
    true,
    'content-creation',
    extract(epoch from now()),
    extract(epoch from now())
);

-- Insert sample debug sessions (for development)
INSERT INTO debug_sessions (
    id,
    workflow_id,
    user_id,
    session_name,
    session_type,
    debug_data,
    breakpoints,
    status
) VALUES
(
    uuid_generate_v4(),
    (SELECT id FROM workflows WHERE name = 'API to Slack Notification' LIMIT 1),
    NULL,
    'Template Debug Session',
    'test',
    '{"test_data": {"api_response": {"status": 200, "message": "OK"}}}',
    '[{"node_id": "http_1", "type": "before"}]',
    'active'
);

-- Insert sample system configuration for different environments
INSERT INTO system_settings (setting_key, setting_value, description, is_public) VALUES
-- Development environment settings
('dev_mode', 'true', 'Enable development mode features', false),
('log_level', '"debug"', 'Application log level', false),
('enable_mock_integrations', 'true', 'Enable mock integrations for testing', false),

-- Production environment settings
('enable_metrics', 'true', 'Enable metrics collection', false),
('metrics_endpoint', '"/metrics"', 'Metrics endpoint path', false),
('health_check_interval', '30', 'Health check interval in seconds', false),

-- Feature flags
('enable_ai_workflow_generation', 'true', 'Enable AI-powered workflow generation', true),
('enable_advanced_debugging', 'true', 'Enable advanced debugging features', true),
('enable_workflow_templates', 'true', 'Enable workflow template system', true),
('enable_integration_marketplace', 'false', 'Enable integration marketplace', true),

-- Rate limiting
('api_rate_limit', '1000', 'API rate limit per hour', false),
('workflow_execution_rate_limit', '100', 'Workflow execution rate limit per hour', false),

-- Storage limits
('max_workflows_per_user', '50', 'Maximum workflows per user', true),
('max_executions_history', '1000', 'Maximum execution history to keep', true),
('cleanup_old_executions_days', '30', 'Days to keep old execution records', false); 