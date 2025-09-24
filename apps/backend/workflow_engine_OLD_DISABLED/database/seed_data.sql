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
('google', 'API', 'Google Calendar', 'Google Calendar API integration', '1.0.0',
 '{"base_url": "https://www.googleapis.com/calendar/v3", "auth_type": "oauth2"}',
 ARRAY['create_event', 'update_event', 'delete_event', 'list_events']),
('slack', 'API', 'Slack', 'Slack API integration', '1.0.0',
 '{"base_url": "https://slack.com/api", "auth_type": "oauth2"}',
 ARRAY['send_message', 'create_channel', 'invite_user', 'upload_file']),
('github', 'API', 'GitHub', 'GitHub API integration', '1.0.0',
 '{"base_url": "https://api.github.com", "auth_type": "oauth2"}',
 ARRAY['create_issue', 'create_pr', 'merge_pr', 'create_repo']);

-- ==============================================================================
-- Seed Data for Node Templates
-- ==============================================================================

-- This script pre-populates the node_templates table with default system nodes
-- based on the implemented node executors.

-- The `is_system_template` flag is set to true for all these nodes,
-- indicating they are core components of the workflow engine.

-- The `template_id` is a unique identifier for each template,
-- which can be used to reference these templates in workflows.

-- The `default_parameters` and `parameter_schema` fields provide
-- default configurations and validation rules for each node.

DO $$
BEGIN

-- ==============================================================================
-- TRIGGER_NODE Templates
-- ==============================================================================

INSERT INTO node_templates (template_id, name, description, category, node_type, node_subtype, is_system_template, default_parameters, parameter_schema)
VALUES
  ('trigger-manual', 'Manual Trigger', 'Manually starts a workflow execution.', 'Trigger', 'TRIGGER', 'MANUAL', true,
 '{"require_confirmation": false}',
  '{"type": "object", "properties": {"require_confirmation": {"type": "boolean"}}}'),

  ('trigger-webhook', 'Webhook Trigger', 'Triggers a workflow via an HTTP webhook.', 'Trigger', 'TRIGGER', 'WEBHOOK', true,
  '{"method": "POST", "path": "/webhook"}',
  '{"type": "object", "properties": {"method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]}, "path": {"type": "string"}}}'),

  ('trigger-cron', 'Cron Schedule Trigger', 'Triggers a workflow on a recurring schedule.', 'Trigger', 'TRIGGER', 'CRON', true,
  '{"cron_expression": "0 9 * * MON", "timezone": "UTC"}',
  '{"type": "object", "properties": {"cron_expression": {"type": "string"}, "timezone": {"type": "string"}}}'),

  ('trigger-chat', 'Chat Message Trigger', 'Triggers a workflow when a chat message is received.', 'Trigger', 'TRIGGER', 'CHAT', true,
  '{"chat_platform": "general", "message_filter": ""}',
  '{"type": "object", "properties": {"chat_platform": {"type": "string"}, "message_filter": {"type": "string"}}}'),

  ('trigger-email', 'Email Trigger', 'Triggers a workflow when an email is received.', 'Trigger', 'TRIGGER', 'EMAIL', true,
  '{"email_provider": "gmail", "email_filter": ""}',
  '{"type": "object", "properties": {"email_provider": {"type": "string"}, "email_filter": {"type": "string"}}}'),

  ('trigger-form', 'Form Submission Trigger', 'Triggers a workflow when a form is submitted.', 'Trigger', 'TRIGGER', 'FORM', true,
  '{"form_id": ""}',
  '{"type": "object", "properties": {"form_id": {"type": "string"}}}'),

  ('trigger-calendar', 'Calendar Event Trigger', 'Triggers a workflow based on a calendar event.', 'Trigger', 'TRIGGER', 'CALENDAR', true,
  '{"calendar_id": "primary", "event_filter": ""}',
  '{"type": "object", "properties": {"calendar_id": {"type": "string"}, "event_filter": {"type": "string"}}}');

-- ==============================================================================
-- FLOW_NODE Templates
-- ==============================================================================

INSERT INTO node_templates (template_id, name, description, category, node_type, node_subtype, is_system_template, default_parameters, parameter_schema)
VALUES
  ('flow-if', 'If Condition', 'Executes a branch based on a boolean condition.', 'Flow Control', 'FLOW', 'IF', true,
  '{"condition": "true"}',
  '{"type": "object", "properties": {"condition": {"type": "string"}}}'),

  ('flow-filter', 'Filter Data', 'Filters data based on a specified condition.', 'Flow Control', 'FLOW', 'FILTER', true,
  '{"filter_condition": {}}',
  '{"type": "object", "properties": {"filter_condition": {"type": "object"}}}'),

  ('flow-loop', 'Loop', 'Executes a branch multiple times (for-each, while, times).', 'Flow Control', 'FLOW', 'LOOP', true,
 '{"loop_type": "for_each", "max_iterations": 100}',
  '{"type": "object", "properties": {"loop_type": {"type": "string", "enum": ["for_each", "while", "times"]}, "max_iterations": {"type": "integer"}}}'),

  ('flow-merge', 'Merge', 'Merges data from multiple branches.', 'Flow Control', 'FLOW', 'MERGE', true,
  '{"merge_strategy": "combine"}',
  '{"type": "object", "properties": {"merge_strategy": {"type": "string", "enum": ["combine", "union", "intersection"]}}}'),

  ('flow-switch', 'Switch', 'Routes execution to a branch based on a value.', 'Flow Control', 'FLOW', 'SWITCH', true,
  '{"switch_cases": []}',
  '{"type": "object", "properties": {"switch_cases": {"type": "array"}}}'),

  ('flow-wait', 'Wait', 'Pauses execution for a duration, condition, or event.', 'Flow Control', 'FLOW', 'WAIT', true,
  '{"wait_type": "time", "duration": 1}',
  '{"type": "object", "properties": {"wait_type": {"type": "string", "enum": ["time", "condition", "event"]}, "duration": {"type": "integer"}}}');

-- ==============================================================================
-- HUMAN_IN_THE_LOOP_NODE Templates
-- ==============================================================================

INSERT INTO node_templates (template_id, name, description, category, node_type, node_subtype, is_system_template, default_parameters, parameter_schema)
VALUES
  ('human-gmail', 'Gmail Interaction', 'Sends an email via Gmail and waits for a response.', 'Human Interaction', 'HUMAN_IN_THE_LOOP', 'GMAIL', true,
  '{"subject": "Action Required", "recipients": []}',
  '{"type": "object", "properties": {"subject": {"type": "string"}, "recipients": {"type": "array"}}}'),

  ('human-slack', 'Slack Interaction', 'Sends a message to a Slack channel and waits for a response.', 'Human Interaction', 'HUMAN_IN_THE_LOOP', 'SLACK', true,
  '{"channel": "", "message_template": ""}',
  '{"type": "object", "properties": {"channel": {"type": "string"}, "message_template": {"type": "string"}}}'),

  ('human-discord', 'Discord Interaction', 'Sends a message to a Discord channel and waits for a response.', 'Human Interaction', 'HUMAN_IN_THE_LOOP', 'DISCORD', true,
  '{"channel_id": "", "message_template": ""}',
  '{"type": "object", "properties": {"channel_id": {"type": "string"}, "message_template": {"type": "string"}}}'),

  ('human-telegram', 'Telegram Interaction', 'Sends a message to a Telegram chat and waits for a response.', 'Human Interaction', 'HUMAN_IN_THE_LOOP', 'TELEGRAM', true,
  '{"chat_id": "", "message_template": ""}',
  '{"type": "object", "properties": {"chat_id": {"type": "string"}, "message_template": {"type": "string"}}}'),

  ('human-app', 'In-App Interaction', 'Sends an in-app notification and waits for a response.', 'Human Interaction', 'HUMAN_IN_THE_LOOP', 'APP', true,
  '{"notification_type": "approval", "title": "Action Required"}',
  '{"type": "object", "properties": {"notification_type": {"type": "string", "enum": ["approval", "input", "review", "confirmation"]}, "title": {"type": "string"}}}');

-- ==============================================================================
-- MEMORY_NODE Templates
-- ==============================================================================

INSERT INTO node_templates (template_id, name, description, category, node_type, node_subtype, is_system_template, default_parameters, parameter_schema)
VALUES
  ('memory-vector-db', 'Vector Database', 'Performs operations on a vector database.', 'Memory', 'MEMORY', 'VECTOR_DB', true,
  '{"operation": "search", "collection_name": "default"}',
  '{"type": "object", "properties": {"operation": {"type": "string", "enum": ["store", "search", "delete", "update"]}, "collection_name": {"type": "string"}}}'),

  ('memory-key-value', 'Key-Value Store', 'Performs operations on a key-value store.', 'Memory', 'MEMORY', 'KEY_VALUE', true,
  '{"operation": "get", "key": ""}',
  '{"type": "object", "properties": {"operation": {"type": "string", "enum": ["get", "set", "delete", "exists"]}, "key": {"type": "string"}}}'),

  ('memory-document', 'Document Store', 'Performs operations on a document store.', 'Memory', 'MEMORY', 'DOCUMENT', true,
  '{"operation": "retrieve", "document_id": ""}',
  '{"type": "object", "properties": {"operation": {"type": "string", "enum": ["store", "retrieve", "update", "delete", "search"]}, "document_id": {"type": "string"}}}');

-- ==============================================================================
-- TOOL_NODE Templates
-- ==============================================================================

INSERT INTO node_templates (template_id, name, description, category, node_type, node_subtype, is_system_template, default_parameters, parameter_schema)
VALUES
  ('tool-mcp', 'MCP Tool', 'Executes a registered MCP tool.', 'Tools', 'TOOL', 'MCP', true,
  '{"tool_name": "", "operation": ""}',
  '{"type": "object", "properties": {"tool_name": {"type": "string"}, "operation": {"type": "string"}}}'),

  ('tool-calendar', 'Calendar Tool', 'Performs operations on a calendar.', 'Tools', 'TOOL', 'CALENDAR', true,
  '{"calendar_id": "primary", "operation": "list_events"}',
  '{"type": "object", "properties": {"calendar_id": {"type": "string"}, "operation": {"type": "string", "enum": ["list_events", "create_event", "update_event", "delete_event"]}}}'),

  ('tool-email', 'Email Tool', 'Performs email operations.', 'Tools', 'TOOL', 'EMAIL', true,
  '{"operation": "send"}',
  '{"type": "object", "properties": {"operation": {"type": "string", "enum": ["send", "read", "search", "delete"]}}}'),

  ('tool-http', 'HTTP Request', 'Makes an HTTP request to a URL.', 'Tools', 'TOOL', 'HTTP', true,
  '{"method": "GET", "url": ""}',
  '{"type": "object", "properties": {"method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]}, "url": {"type": "string"}}}');

-- ==============================================================================
-- ACTION_NODE Templates
-- ==============================================================================

INSERT INTO node_templates (template_id, name, description, category, node_type, node_subtype, is_system_template, default_parameters, parameter_schema)
VALUES
  ('action-run-code', 'Run Code', 'Executes code in Python, JavaScript, Bash, or SQL.', 'Actions', 'ACTION', 'RUN_CODE', true,
  '{"language": "python", "code": ""}',
  '{"type": "object", "properties": {"language": {"type": "string", "enum": ["python", "javascript", "bash", "sql"]}, "code": {"type": "string"}}}'),

  ('action-http-request', 'HTTP Request', 'Makes an HTTP request to a specified URL.', 'Actions', 'ACTION', 'HTTP_REQUEST', true,
  '{"method": "GET", "url": ""}',
  '{"type": "object", "properties": {"method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]}, "url": {"type": "string"}}}'),

  ('action-data-transform', 'Data Transformation', 'Transforms data using various methods.', 'Actions', 'ACTION', 'DATA_TRANSFORMATION', true,
  '{"transformation_type": "filter"}',
  '{"type": "object", "properties": {"transformation_type": {"type": "string", "enum": ["filter", "map", "reduce", "sort", "group", "join"]}}}'),

  ('action-file-operation', 'File Operation', 'Performs operations on files.', 'Actions', 'ACTION', 'FILE_OPERATION', true,
  '{"operation_type": "read", "file_path": ""}',
  '{"type": "object", "properties": {"operation_type": {"type": "string", "enum": ["read", "write", "copy", "move", "delete", "list"]}, "file_path": {"type": "string"}}}');

-- ==============================================================================
-- AI_AGENT_NODE Templates
-- ==============================================================================

INSERT INTO node_templates (template_id, name, description, category, node_type, node_subtype, is_system_template, default_parameters, parameter_schema)
VALUES
  ('ai-router-agent', 'Router Agent', 'Routes requests to appropriate handlers using an AI model.', 'AI Agents', 'AI_AGENT', 'ROUTER_AGENT', true,
  '{"model": "gpt-4", "system_prompt": "You are a router agent."}',
  '{"type": "object", "properties": {"model": {"type": "string"}, "system_prompt": {"type": "string"}}}'),

  ('ai-task-analyzer', 'Task Analyzer', 'Analyzes tasks for requirements, complexity, or dependencies.', 'AI Agents', 'AI_AGENT', 'TASK_ANALYZER', true,
  '{"model": "gpt-4", "analysis_type": "requirement"}',
  '{"type": "object", "properties": {"model": {"type": "string"}, "analysis_type": {"type": "string", "enum": ["requirement", "complexity", "dependency", "resource"]}}}'),

  ('ai-data-integrator', 'Data Integrator', 'Integrates data from multiple sources using an AI model.', 'AI Agents', 'AI_AGENT', 'DATA_INTEGRATOR', true,
  '{"model": "gpt-4", "integration_type": "merge"}',
  '{"type": "object", "properties": {"model": {"type": "string"}, "integration_type": {"type": "string", "enum": ["merge", "transform", "validate", "enrich"]}}}'),

  ('ai-report-generator', 'Report Generator', 'Generates reports from data using an AI model.', 'AI Agents', 'AI_AGENT', 'REPORT_GENERATOR', true,
  '{"model": "gpt-4", "report_type": "summary"}',
  '{"type": "object", "properties": {"model": {"type": "string"}, "report_type": {"type": "string", "enum": ["summary", "detailed", "executive", "technical"]}}}');

END $$;
