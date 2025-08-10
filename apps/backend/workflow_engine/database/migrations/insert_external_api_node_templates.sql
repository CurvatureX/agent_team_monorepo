-- ============================================================================
-- External API Integration Node Templates
-- 基于shared/node_specs/definitions/external_action_nodes.py的规范定义
-- 插入我们已实现的外部API集成节点模板
-- ============================================================================

-- 删除可能存在的旧版本外部节点模板（避免重复）
DELETE FROM public.node_templates 
WHERE node_type = 'EXTERNAL_ACTION_NODE' 
AND node_subtype IN ('GOOGLE_CALENDAR', 'GITHUB', 'SLACK', 'EMAIL', 'API_CALL');

-- ============================================================================
-- Google Calendar Integration - 完全实现
-- ============================================================================
INSERT INTO public.node_templates (
    template_id, 
    name, 
    description, 
    category, 
    node_type, 
    node_subtype, 
    default_parameters, 
    required_parameters, 
    parameter_schema, 
    is_system_template
) VALUES (
    'external_google_calendar',
    'Google Calendar',
    'Interact with Google Calendar API - create, list, update, delete events',
    'integrations',
    'EXTERNAL_ACTION_NODE',
    'GOOGLE_CALENDAR',
    '{
        "action": "list_events",
        "calendar_id": "primary",
        "max_results": "10"
    }'::jsonb,
    ARRAY['action'],
    '{
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_events", "create_event", "update_event", "delete_event", "get_event"],
                "description": "Google Calendar action type"
            },
            "calendar_id": {
                "type": "string",
                "default": "primary",
                "description": "Calendar ID"
            },
            "summary": {
                "type": "string",
                "description": "Event title/summary"
            },
            "description": {
                "type": "string",
                "description": "Event description"
            },
            "location": {
                "type": "string",
                "description": "Event location"
            },
            "start_datetime": {
                "type": "string",
                "description": "Event start datetime (ISO format)"
            },
            "end_datetime": {
                "type": "string",
                "description": "Event end datetime (ISO format)"
            },
            "event_id": {
                "type": "string",
                "description": "Event ID for update/delete operations"
            },
            "max_results": {
                "type": "string",
                "default": "10",
                "description": "Maximum number of events to return"
            }
        },
        "required": ["action"],
        "additionalProperties": false
    }'::jsonb,
    true
);

-- ============================================================================
-- GitHub Integration - 节点规范已完善，适配器需要实现
-- ============================================================================
INSERT INTO public.node_templates (
    template_id, 
    name, 
    description, 
    category, 
    node_type, 
    node_subtype, 
    default_parameters, 
    required_parameters, 
    parameter_schema, 
    is_system_template
) VALUES (
    'external_github_advanced',
    'GitHub Advanced',
    'Execute GitHub operations via GitHub API - create issues, PRs, comments',
    'integrations',
    'EXTERNAL_ACTION_NODE',
    'GITHUB',
    '{
        "branch": "main",
        "labels": [],
        "assignees": []
    }'::jsonb,
    ARRAY['action', 'repository', 'auth_token'],
    '{
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create_issue", "create_pull_request", "add_comment", "close_issue", "merge_pr", "list_issues", "get_issue"],
                "description": "GitHub action type"
            },
            "repository": {
                "type": "string",
                "description": "Repository name (owner/repo format)"
            },
            "auth_token": {
                "type": "string",
                "description": "GitHub access token (sensitive)",
                "format": "password"
            },
            "branch": {
                "type": "string",
                "default": "main",
                "description": "Branch name"
            },
            "title": {
                "type": "string",
                "description": "Title for issues or pull requests"
            },
            "body": {
                "type": "string",
                "description": "Body content for issues or pull requests"
            },
            "issue_number": {
                "type": "number",
                "description": "Issue or PR number for operations"
            },
            "labels": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
                "description": "Labels to apply (array of strings)"
            },
            "assignees": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
                "description": "Assignees (array of usernames)"
            },
            "milestone": {
                "type": "number",
                "description": "Milestone number"
            }
        },
        "required": ["action", "repository", "auth_token"],
        "additionalProperties": false
    }'::jsonb,
    true
);

-- ============================================================================
-- Slack Integration - 节点规范已完善，适配器需要实现
-- ============================================================================
INSERT INTO public.node_templates (
    template_id, 
    name, 
    description, 
    category, 
    node_type, 
    node_subtype, 
    default_parameters, 
    required_parameters, 
    parameter_schema, 
    is_system_template
) VALUES (
    'external_slack_advanced',
    'Slack Advanced',
    'Send messages and interact with Slack workspaces',
    'integrations',
    'EXTERNAL_ACTION_NODE',
    'SLACK',
    '{
        "attachments": [],
        "blocks": []
    }'::jsonb,
    ARRAY['channel', 'message', 'bot_token'],
    '{
        "type": "object",
        "properties": {
            "channel": {
                "type": "string",
                "description": "Channel ID or name"
            },
            "message": {
                "type": "string",
                "description": "Message content"
            },
            "bot_token": {
                "type": "string",
                "description": "Slack Bot token (sensitive)",
                "format": "password"
            },
            "attachments": {
                "type": "array",
                "default": [],
                "description": "Message attachments"
            },
            "thread_ts": {
                "type": "string",
                "description": "Thread timestamp for reply"
            },
            "username": {
                "type": "string",
                "description": "Custom username for bot message"
            },
            "icon_emoji": {
                "type": "string",
                "description": "Emoji icon for bot message"
            },
            "icon_url": {
                "type": "string",
                "description": "URL icon for bot message"
            },
            "blocks": {
                "type": "array",
                "default": [],
                "description": "Slack Block Kit blocks"
            }
        },
        "required": ["channel", "message", "bot_token"],
        "additionalProperties": false
    }'::jsonb,
    true
);

-- ============================================================================
-- Email Integration - 节点规范已定义，适配器需要实现
-- ============================================================================
INSERT INTO public.node_templates (
    template_id, 
    name, 
    description, 
    category, 
    node_type, 
    node_subtype, 
    default_parameters, 
    required_parameters, 
    parameter_schema, 
    is_system_template
) VALUES (
    'external_email_smtp',
    'Email SMTP',
    'Send emails via SMTP server',
    'integrations',
    'EXTERNAL_ACTION_NODE',
    'EMAIL',
    '{
        "smtp_server": "smtp.gmail.com",
        "port": 587,
        "use_tls": true,
        "content_type": "text/html"
    }'::jsonb,
    ARRAY['to', 'subject', 'body', 'smtp_server', 'username', 'password'],
    '{
        "type": "object",
        "properties": {
            "to": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Recipient email addresses"
            },
            "cc": {
                "type": "array",
                "items": {"type": "string"},
                "description": "CC email addresses"
            },
            "bcc": {
                "type": "array",
                "items": {"type": "string"},
                "description": "BCC email addresses"
            },
            "subject": {
                "type": "string",
                "description": "Email subject"
            },
            "body": {
                "type": "string",
                "description": "Email body content"
            },
            "smtp_server": {
                "type": "string",
                "description": "SMTP server hostname"
            },
            "port": {
                "type": "number",
                "default": 587,
                "description": "SMTP server port"
            },
            "username": {
                "type": "string",
                "description": "SMTP username"
            },
            "password": {
                "type": "string",
                "description": "SMTP password (sensitive)",
                "format": "password"
            },
            "use_tls": {
                "type": "boolean",
                "default": true,
                "description": "Use TLS encryption"
            },
            "content_type": {
                "type": "string",
                "enum": ["text/plain", "text/html"],
                "default": "text/html",
                "description": "Email content type"
            }
        },
        "required": ["to", "subject", "body", "smtp_server", "username", "password"],
        "additionalProperties": false
    }'::jsonb,
    true
);

-- ============================================================================
-- Generic API Call - 节点规范已定义，通用HTTP适配器需要实现
-- ============================================================================
INSERT INTO public.node_templates (
    template_id, 
    name, 
    description, 
    category, 
    node_type, 
    node_subtype, 
    default_parameters, 
    required_parameters, 
    parameter_schema, 
    is_system_template
) VALUES (
    'external_api_call_generic',
    'Generic API Call',
    'Make generic HTTP API calls to any endpoint',
    'integrations',
    'EXTERNAL_ACTION_NODE',
    'API_CALL',
    '{
        "method": "GET",
        "headers": {},
        "query_params": {},
        "timeout": 30,
        "authentication": "none"
    }'::jsonb,
    ARRAY['method', 'url'],
    '{
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                "default": "GET",
                "description": "HTTP method"
            },
            "url": {
                "type": "string",
                "format": "uri",
                "description": "API endpoint URL"
            },
            "headers": {
                "type": "object",
                "default": {},
                "description": "HTTP headers"
            },
            "query_params": {
                "type": "object",
                "default": {},
                "description": "Query parameters"
            },
            "body": {
                "type": "object",
                "description": "Request body data"
            },
            "timeout": {
                "type": "number",
                "default": 30,
                "description": "Timeout in seconds"
            },
            "authentication": {
                "type": "string",
                "enum": ["none", "bearer", "basic", "api_key"],
                "default": "none",
                "description": "Authentication method"
            },
            "auth_token": {
                "type": "string",
                "description": "Authentication token (when needed)",
                "format": "password"
            },
            "api_key_header": {
                "type": "string",
                "description": "API key header name (for api_key auth)"
            }
        },
        "required": ["method", "url"],
        "additionalProperties": false
    }'::jsonb,
    true
);

-- ============================================================================
-- 验证插入结果
-- ============================================================================
SELECT 
    template_id,
    name,
    node_type,
    node_subtype,
    category
FROM public.node_templates 
WHERE node_type = 'EXTERNAL_ACTION_NODE'
ORDER BY node_subtype;