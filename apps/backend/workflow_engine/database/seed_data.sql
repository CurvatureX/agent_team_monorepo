-- ==============================================================================
-- Seed Data for Workflow Engine
-- This file contains initial data for development and testing
-- ==============================================================================

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
INSERT INTO integrations (integration_id, integration_type, name, description, version, configuration, supported_operations) VALUES
('google_calendar', 'API', 'Google Calendar', 'Google Calendar API integration', '1.0.0', 
 '{"base_url": "https://www.googleapis.com/calendar/v3", "auth_type": "oauth2"}', 
 ARRAY['create_event', 'update_event', 'delete_event', 'list_events']),
('slack', 'API', 'Slack', 'Slack API integration', '1.0.0',
 '{"base_url": "https://slack.com/api", "auth_type": "oauth2"}',
 ARRAY['send_message', 'create_channel', 'invite_user', 'upload_file']),
('github', 'API', 'GitHub', 'GitHub API integration', '1.0.0',
 '{"base_url": "https://api.github.com", "auth_type": "oauth2"}',
 ARRAY['create_issue', 'create_pr', 'merge_pr', 'create_repo']);

-- Insert node templates for 8 core node types
INSERT INTO node_templates (template_id, name, description, category, node_type, node_subtype, default_parameters, required_parameters, parameter_schema, is_system_template) VALUES

-- TRIGGER node templates
('trigger_webhook', 'Webhook Trigger', 'Triggers workflow when webhook is called', 'Triggers', 'TRIGGER', 'WEBHOOK', 
 '{"method": "POST", "path": "/webhook", "authentication": "none"}', 
 ARRAY['path'], 
 '{"type": "object", "properties": {"method": {"type": "string", "enum": ["GET", "POST"]}, "path": {"type": "string"}}}', 
 true),

('trigger_cron', 'Cron Trigger', 'Triggers workflow on schedule', 'Triggers', 'TRIGGER', 'CRON', 
 '{"cron_expression": "0 9 * * MON", "timezone": "UTC"}', 
 ARRAY['cron_expression'], 
 '{"type": "object", "properties": {"cron_expression": {"type": "string"}, "timezone": {"type": "string"}}}', 
 true),

('trigger_manual', 'Manual Trigger', 'Manually triggered workflow', 'Triggers', 'TRIGGER', 'MANUAL', 
 '{"require_confirmation": false}', 
 ARRAY[], 
 '{"type": "object", "properties": {"require_confirmation": {"type": "boolean"}}}', 
 true),

-- AI_AGENT node templates
('ai_router_agent', 'Router Agent', 'AI agent that routes requests to appropriate handlers', 'AI Agents', 'AI_AGENT', 'ROUTER_AGENT', 
 '{"model": "gpt-4", "temperature": 0.7, "max_tokens": 1000}', 
 ARRAY['model'], 
 '{"type": "object", "properties": {"model": {"type": "string"}, "temperature": {"type": "number"}, "max_tokens": {"type": "integer"}}}', 
 true),

('ai_task_analyzer', 'Task Analyzer', 'AI agent that analyzes and breaks down tasks', 'AI Agents', 'AI_AGENT', 'TASK_ANALYZER', 
 '{"model": "gpt-4", "analysis_depth": "detailed"}', 
 ARRAY['model'], 
 '{"type": "object", "properties": {"model": {"type": "string"}, "analysis_depth": {"type": "string", "enum": ["basic", "detailed"]}}}', 
 true),

-- EXTERNAL_ACTION node templates
('external_slack', 'Slack Action', 'Send messages to Slack channels', 'External Actions', 'EXTERNAL_ACTION', 'SLACK', 
 '{"action_type": "send_message", "channel": "#general"}', 
 ARRAY['action_type'], 
 '{"type": "object", "properties": {"action_type": {"type": "string", "enum": ["send_message", "create_channel"]}, "channel": {"type": "string"}}}', 
 true),

('external_github', 'GitHub Action', 'Interact with GitHub repositories', 'External Actions', 'EXTERNAL_ACTION', 'GITHUB', 
 '{"action_type": "create_issue", "repository": "owner/repo"}', 
 ARRAY['action_type', 'repository'], 
 '{"type": "object", "properties": {"action_type": {"type": "string", "enum": ["create_issue", "create_pr"]}, "repository": {"type": "string"}}}', 
 true),

('external_google_calendar', 'Google Calendar Action', 'Manage Google Calendar events', 'External Actions', 'EXTERNAL_ACTION', 'GOOGLE_CALENDAR', 
 '{"action_type": "create_event", "calendar_id": "primary"}', 
 ARRAY['action_type'], 
 '{"type": "object", "properties": {"action_type": {"type": "string", "enum": ["create_event", "update_event", "delete_event"]}, "calendar_id": {"type": "string"}}}', 
 true),

-- ACTION node templates
('action_http_request', 'HTTP Request', 'Send HTTP requests to APIs', 'Actions', 'ACTION', 'SEND_HTTP_REQUEST', 
 '{"method": "GET", "timeout": 30, "follow_redirects": true}', 
 ARRAY['url'], 
 '{"type": "object", "properties": {"method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]}, "url": {"type": "string"}, "timeout": {"type": "integer"}}}', 
 true),

('action_run_code', 'Run Code', 'Execute code in various languages', 'Actions', 'ACTION', 'RUN_CODE', 
 '{"language": "python", "timeout": 60}', 
 ARRAY['language', 'code'], 
 '{"type": "object", "properties": {"language": {"type": "string", "enum": ["python", "javascript", "bash"]}, "code": {"type": "string"}, "timeout": {"type": "integer"}}}', 
 true),

-- FLOW node templates
('flow_if_condition', 'If Condition', 'Conditional branching in workflow', 'Flow Control', 'FLOW', 'IF', 
 '{"condition_type": "javascript"}', 
 ARRAY['condition_expression'], 
 '{"type": "object", "properties": {"condition_type": {"type": "string", "enum": ["javascript", "simple"]}, "condition_expression": {"type": "string"}}}', 
 true),

('flow_loop', 'Loop', 'Loop through data items', 'Flow Control', 'FLOW', 'LOOP', 
 '{"loop_type": "for_each", "max_iterations": 100}', 
 ARRAY['loop_type'], 
 '{"type": "object", "properties": {"loop_type": {"type": "string", "enum": ["for_each", "while", "times"]}, "max_iterations": {"type": "integer"}}}', 
 true),

-- HUMAN_IN_THE_LOOP node templates
('human_slack_approval', 'Slack Approval', 'Request approval via Slack', 'Human Interaction', 'HUMAN_IN_THE_LOOP', 'SLACK', 
 '{"timeout_minutes": 60, "auto_approve_after_timeout": false}', 
 ARRAY['approval_channel'], 
 '{"type": "object", "properties": {"approval_channel": {"type": "string"}, "timeout_minutes": {"type": "integer"}}}', 
 true),

('human_email_approval', 'Email Approval', 'Request approval via email', 'Human Interaction', 'HUMAN_IN_THE_LOOP', 'GMAIL', 
 '{"timeout_hours": 24, "auto_approve_after_timeout": false}', 
 ARRAY['approver_emails'], 
 '{"type": "object", "properties": {"approver_emails": {"type": "array", "items": {"type": "string"}}, "timeout_hours": {"type": "integer"}}}', 
 true),

-- TOOL node templates
('tool_google_calendar_mcp', 'Google Calendar MCP Tool', 'Google Calendar integration via MCP', 'Tools', 'TOOL', 'GOOGLE_CALENDAR_MCP', 
 '{"timezone": "UTC", "max_results": 50}', 
 ARRAY['google_credentials'], 
 '{"type": "object", "properties": {"google_credentials": {"type": "string"}, "timezone": {"type": "string"}, "max_results": {"type": "integer"}}}', 
 true),

('tool_http', 'HTTP Tool', 'Generic HTTP request tool', 'Tools', 'TOOL', 'HTTP', 
 '{"timeout": 30, "verify_ssl": true}', 
 ARRAY[], 
 '{"type": "object", "properties": {"timeout": {"type": "integer"}, "verify_ssl": {"type": "boolean"}}}', 
 true),

-- MEMORY node templates
('memory_buffer', 'Buffer Memory', 'Short-term conversation memory', 'Memory', 'MEMORY', 'BUFFER', 
 '{"max_token_limit": 2000, "return_messages": true}', 
 ARRAY[], 
 '{"type": "object", "properties": {"max_token_limit": {"type": "integer"}, "return_messages": {"type": "boolean"}}}', 
 true),

('memory_vector_store', 'Vector Store Memory', 'Long-term semantic memory with vector search', 'Memory', 'MEMORY', 'VECTOR_STORE', 
 '{"collection_name": "workflow_memory", "similarity_threshold": 0.8}', 
 ARRAY['collection_name'], 
 '{"type": "object", "properties": {"collection_name": {"type": "string"}, "similarity_threshold": {"type": "number"}}}', 
 true);
