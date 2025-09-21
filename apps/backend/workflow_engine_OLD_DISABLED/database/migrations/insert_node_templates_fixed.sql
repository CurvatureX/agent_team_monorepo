-- 清空现有数据
TRUNCATE TABLE public.node_templates CASCADE;

-- 插入 TRIGGER_NODE 类型的模板
INSERT INTO public.node_templates (template_id, name, description, category, node_type, node_subtype, default_parameters, required_parameters, parameter_schema, is_system_template) VALUES
('trigger_cron', 'Cron Trigger', 'Schedule workflow execution using cron expressions', 'triggers', 'TRIGGER_NODE', 'TRIGGER_CRON',
 '{"cron_expression": "0 9 * * *", "timezone": "UTC"}'::jsonb,
 ARRAY['cron_expression'],
 '{"type": "object", "properties": {"cron_expression": {"type": "string", "description": "Cron expression for scheduling"}, "timezone": {"type": "string", "description": "Timezone for the cron job", "default": "UTC"}}}'::jsonb,
 true),

('trigger_webhook', 'Webhook Trigger', 'Trigger workflow via webhook endpoint', 'triggers', 'TRIGGER_NODE', 'TRIGGER_WEBHOOK',
 '{"method": "POST", "auth_required": false}'::jsonb,
 ARRAY['method'],
 '{"type": "object", "properties": {"method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]}, "auth_required": {"type": "boolean", "default": false}}}'::jsonb,
 true),

('trigger_manual', 'Manual Trigger', 'Manually trigger workflow execution', 'triggers', 'TRIGGER_NODE', 'TRIGGER_MANUAL',
 '{}'::jsonb,
 ARRAY[]::text[],
 '{"type": "object", "properties": {}}'::jsonb,
 true);

-- 插入 ACTION_NODE 类型的模板
INSERT INTO public.node_templates (template_id, name, description, category, node_type, node_subtype, default_parameters, required_parameters, parameter_schema, is_system_template) VALUES
('action_http_request', 'HTTP Request', 'Make HTTP requests to external APIs', 'actions', 'ACTION_NODE', 'HTTP_REQUEST',
 '{"method": "GET", "headers": {}, "timeout": 30}'::jsonb,
 ARRAY['method', 'url'],
 '{"type": "object", "properties": {"method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]}, "url": {"type": "string"}, "headers": {"type": "object"}, "body": {"type": "string"}, "query_params": {"type": "string"}, "timeout": {"type": "number", "default": 30}}}'::jsonb,
 true),

('action_data_transform', 'Data Transformation', 'Transform data using JMESPath or JSONPath', 'actions', 'ACTION_NODE', 'DATA_TRANSFORMATION',
 '{"transform_type": "jmespath", "expression": ""}'::jsonb,
 ARRAY['transform_type', 'expression'],
 '{"type": "object", "properties": {"transform_type": {"type": "string", "enum": ["jmespath", "jsonpath"]}, "expression": {"type": "string"}}}'::jsonb,
 true),

('action_code_exec', 'Code Execution', 'Execute Python or JavaScript code', 'actions', 'ACTION_NODE', 'CODE_EXECUTION',
 '{"language": "python", "timeout": 30}'::jsonb,
 ARRAY['code'],
 '{"type": "object", "properties": {"code": {"type": "string"}, "language": {"type": "string", "enum": ["python", "javascript"]}, "timeout": {"type": "number", "default": 30}}}'::jsonb,
 true),

('action_send_email', 'Send Email', 'Send email notifications', 'actions', 'ACTION_NODE', 'SEND_EMAIL',
 '{"from": "noreply@example.com", "content_type": "text/html"}'::jsonb,
 ARRAY['to', 'subject', 'body'],
 '{"type": "object", "properties": {"to": {"type": "array", "items": {"type": "string"}}, "cc": {"type": "array", "items": {"type": "string"}}, "subject": {"type": "string"}, "body": {"type": "string"}, "from": {"type": "string"}, "content_type": {"type": "string", "enum": ["text/plain", "text/html"]}}}'::jsonb,
 true);

-- 插入 FLOW_NODE 类型的模板
INSERT INTO public.node_templates (template_id, name, description, category, node_type, node_subtype, default_parameters, required_parameters, parameter_schema, is_system_template) VALUES
('flow_if', 'If Condition', 'Conditional branching based on expressions', 'flow_control', 'FLOW_NODE', 'IF',
 '{"condition": ""}'::jsonb,
 ARRAY['condition'],
 '{"type": "object", "properties": {"condition": {"type": "string", "description": "JavaScript expression that evaluates to true/false"}}}'::jsonb,
 true),

('flow_switch', 'Switch Case', 'Multi-way branching based on value', 'flow_control', 'FLOW_NODE', 'SWITCH',
 '{"expression": "", "cases": {}}'::jsonb,
 ARRAY['expression', 'cases'],
 '{"type": "object", "properties": {"expression": {"type": "string"}, "cases": {"type": "object", "additionalProperties": {"type": "string"}}}}'::jsonb,
 true),

('flow_loop', 'Loop', 'Iterate over arrays or repeat N times', 'flow_control', 'FLOW_NODE', 'FOR_EACH_LOOP',
 '{"loop_type": "for_each", "max_iterations": 1000}'::jsonb,
 ARRAY['loop_type'],
 '{"type": "object", "properties": {"loop_type": {"type": "string", "enum": ["for_each", "while", "times"]}, "items": {"type": "string"}, "condition": {"type": "string"}, "times": {"type": "number"}, "max_iterations": {"type": "number", "default": 1000}}}'::jsonb,
 true),

('flow_merge', 'Merge', 'Merge multiple execution branches', 'flow_control', 'FLOW_NODE', 'MERGE',
 '{"merge_strategy": "wait_all", "timeout": 300}'::jsonb,
 ARRAY['merge_strategy'],
 '{"type": "object", "properties": {"merge_strategy": {"type": "string", "enum": ["wait_all", "wait_any", "merge_objects"]}, "timeout": {"type": "number", "default": 300}}}'::jsonb,
 true);

-- 插入 AI_AGENT_NODE 类型的模板
INSERT INTO public.node_templates (template_id, name, description, category, node_type, node_subtype, default_parameters, required_parameters, parameter_schema, is_system_template) VALUES
('ai_openai', 'OpenAI Chat', 'Generate text using OpenAI models', 'ai', 'AI_AGENT_NODE', 'OPENAI_NODE',
 '{"model_version": "gpt-3.5-turbo", "temperature": 0.7, "max_tokens": 1000}'::jsonb,
 ARRAY['prompt'],
 '{"type": "object", "properties": {"prompt": {"type": "string"}, "model_version": {"type": "string"}, "temperature": {"type": "number", "minimum": 0, "maximum": 2}, "max_tokens": {"type": "number"}, "system_prompt": {"type": "string"}}}'::jsonb,
 true),

('ai_claude', 'Claude Chat', 'Generate text using Anthropic Claude', 'ai', 'AI_AGENT_NODE', 'CLAUDE_NODE',
 '{"model_version": "claude-3-sonnet-20240229", "temperature": 0.7, "max_tokens": 1000}'::jsonb,
 ARRAY['prompt'],
 '{"type": "object", "properties": {"prompt": {"type": "string"}, "model_version": {"type": "string"}, "temperature": {"type": "number", "minimum": 0, "maximum": 1}, "max_tokens": {"type": "number"}, "system_prompt": {"type": "string"}}}'::jsonb,
 true);

-- 插入 TOOL_NODE 类型的模板
INSERT INTO public.node_templates (template_id, name, description, category, node_type, node_subtype, default_parameters, required_parameters, parameter_schema, is_system_template) VALUES
('tool_code_interpreter', 'Code Interpreter', 'Execute Python code in sandboxed environment', 'tools', 'TOOL_NODE', 'CODE_INTERPRETER',
 '{"language": "python", "timeout": 30}'::jsonb,
 ARRAY['code'],
 '{"type": "object", "properties": {"code": {"type": "string"}, "language": {"type": "string", "enum": ["python", "javascript"]}, "timeout": {"type": "number", "default": 30}}}'::jsonb,
 true),

('tool_web_scraper', 'Web Scraper', 'Extract data from web pages', 'tools', 'TOOL_NODE', 'WEB_SCRAPER',
 '{"wait_for": "networkidle", "timeout": 30}'::jsonb,
 ARRAY['url'],
 '{"type": "object", "properties": {"url": {"type": "string"}, "selectors": {"type": "object"}, "wait_for": {"type": "string", "enum": ["load", "networkidle"]}, "timeout": {"type": "number", "default": 30}}}'::jsonb,
 true);

-- 插入 MEMORY_NODE 类型的模板
INSERT INTO public.node_templates (template_id, name, description, category, node_type, node_subtype, default_parameters, required_parameters, parameter_schema, is_system_template) VALUES
('memory_store', 'Store Memory', 'Store data in workflow memory', 'memory', 'MEMORY_NODE', 'STORE',
 '{"scope": "workflow", "ttl": null}'::jsonb,
 ARRAY['key', 'value'],
 '{"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "any"}, "scope": {"type": "string", "enum": ["workflow", "global"]}, "ttl": {"type": "number", "description": "Time to live in seconds"}}}'::jsonb,
 true),

('memory_retrieve', 'Retrieve Memory', 'Retrieve data from workflow memory', 'memory', 'MEMORY_NODE', 'RETRIEVE',
 '{"scope": "workflow", "default": null}'::jsonb,
 ARRAY['key'],
 '{"type": "object", "properties": {"key": {"type": "string"}, "scope": {"type": "string", "enum": ["workflow", "global"]}, "default": {"type": "any", "description": "Default value if key not found"}}}'::jsonb,
 true);

-- 插入 HUMAN_IN_THE_LOOP_NODE 类型的模板
INSERT INTO public.node_templates (template_id, name, description, category, node_type, node_subtype, default_parameters, required_parameters, parameter_schema, is_system_template) VALUES
('human_approval', 'Human Approval', 'Wait for human approval before proceeding', 'human_interaction', 'HUMAN_IN_THE_LOOP_NODE', 'APPROVAL',
 '{"timeout": 86400, "approval_type": "single"}'::jsonb,
 ARRAY['title', 'description'],
 '{"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}}, "timeout": {"type": "number", "default": 86400}, "approval_type": {"type": "string", "enum": ["single", "multiple"]}}}'::jsonb,
 true);

-- 插入 EXTERNAL_ACTION_NODE 类型的模板
INSERT INTO public.node_templates (template_id, name, description, category, node_type, node_subtype, default_parameters, required_parameters, parameter_schema, is_system_template) VALUES
('external_slack', 'Slack Integration', 'Send messages to Slack channels', 'integrations', 'EXTERNAL_ACTION_NODE', 'SLACK',
 '{"channel": "#general", "as_user": false}'::jsonb,
 ARRAY['message'],
 '{"type": "object", "properties": {"channel": {"type": "string"}, "message": {"type": "string"}, "as_user": {"type": "boolean", "default": false}, "attachments": {"type": "array"}}}'::jsonb,
 true),

('external_github', 'GitHub Integration', 'Interact with GitHub repositories', 'integrations', 'EXTERNAL_ACTION_NODE', 'GITHUB',
 '{"action": "create_issue"}'::jsonb,
 ARRAY['action', 'repository'],
 '{"type": "object", "properties": {"action": {"type": "string", "enum": ["create_issue", "create_pr", "add_comment", "close_issue"]}, "repository": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}}}'::jsonb,
 true);
