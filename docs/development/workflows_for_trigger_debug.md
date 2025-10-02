# Trigger Node Debug Testing Plan

This document defines test workflows for validating all trigger node types in the Workflow Engine. Each trigger type has two workflow examples: a basic test and an advanced scenario.

## Overview

Based on the trigger node definitions in `apps/backend/shared/node_specs/definitions/trigger_nodes.py` and implementation in `apps/backend/workflow_engine/workflow_engine/nodes/trigger_node.py`, we have identified 6 main trigger types:

1. **MANUAL** - User-initiated triggers
2. **CRON** - Scheduled triggers
3. **WEBHOOK** - HTTP endpoint triggers
4. **SLACK** - Slack event triggers
5. **EMAIL** - Email monitoring triggers
6. **GITHUB** - GitHub repository event triggers

## Testing Strategy

### Test Goals
-  Validate trigger node parameter parsing and validation
-  Test trigger activation and data flow to next nodes
-  Verify error handling for invalid configurations
-  Test trigger-specific output data formats
-  Validate integration with workflow scheduler service

### Test Environment Requirements
- Workflow Engine running on port 8002
- Workflow Scheduler running on port 8003
- API Gateway running on port 8000
- Test authentication tokens for API access
- Mock external services (Slack, GitHub, Email) for integration testing

---

## 1. MANUAL Trigger Test Workflows

Manual triggers are activated by user requests through the API Gateway.

### 1.1 Basic Manual Trigger Test

**Purpose**: Test simple manual trigger activation without confirmation.

```json
{
  "name": "Basic Manual Trigger Test",
  "description": "Simple manual trigger that logs activation",
  "nodes": [
    {
      "id": "manual-trigger-basic",
      "name": "basic-manual-trigger",
      "type": "TRIGGER",
      "subtype": "MANUAL",
      "type_version": 1,
      "parameters": {
        "trigger_name": "Basic Manual Test",
        "description": "Test manual trigger without confirmation",
        "require_confirmation": false
      },
      "position": {"x": 100.0, "y": 100.0},
      "credentials": {},
      "disabled": false,
      "on_error": "stop",
      "retry_policy": {"max_tries": 1, "wait_between_tries": 0},
      "notes": "Basic manual trigger for testing",
      "webhooks": []
    },
    {
      "id": "log-action-basic",
      "name": "basic-log-action",
      "type": "ACTION",
      "subtype": "RUN_CODE",
      "type_version": 1,
      "parameters": {
        "language": "python",
        "code": "print('Manual trigger activated! Data:', input_data)"
      },
      "position": {"x": 300.0, "y": 100.0},
      "credentials": {},
      "disabled": false,
      "on_error": "stop",
      "retry_policy": {"max_tries": 3, "wait_between_tries": 1},
      "notes": "Log action to record trigger activation",
      "webhooks": []
    }
  ],
  "connections": {
    "basic-manual-trigger": {
      "main": [{"node": "basic-log-action", "type": "main", "index": 0}]
    }
  },
  "settings": {
    "timeout": 30,
    "timezone": {"name": "UTC"},
    "save_execution_progress": true,
    "save_manual_executions": true,
    "error_policy": "stop_on_error",
    "caller_policy": "sequential"
  },
  "static_data": {},
  "pin_data": {}
}
```

**Test Steps**:
1. Create workflow via `POST /api/v1/workflows`
2. Trigger manually via `POST /api/v1/workflows/{id}/trigger/manual`
3. Verify execution starts and completes successfully
4. Check log output contains trigger data (user_id, trigger_time, execution_id)

### 1.2 Advanced Manual Trigger with Confirmation

**Purpose**: Test manual trigger requiring user confirmation.

```json
{
  "name": "Manual Trigger with Confirmation",
  "description": "Manual trigger requiring confirmation before execution",
  "nodes": [
    {
      "id": "manual-trigger-confirm",
      "name": "confirmation-manual-trigger",
      "type": "TRIGGER",
      "subtype": "MANUAL",
      "type_version": 1,
      "parameters": {
        "trigger_name": "Confirmation Required Trigger",
        "description": "This trigger requires user confirmation due to potential impact",
        "require_confirmation": true
      },
      "position": {"x": 100.0, "y": 100.0},
      "credentials": {},
      "disabled": false,
      "on_error": "stop",
      "retry_policy": {"max_tries": 1, "wait_between_tries": 0},
      "notes": "Manual trigger requiring confirmation",
      "webhooks": []
    },
    {
      "id": "conditional-flow-confirm",
      "name": "confirmation-flow-check",
      "type": "FLOW",
      "subtype": "IF",
      "type_version": 1,
      "parameters": {
        "condition": "{{trigger_data.require_confirmation}} == true",
        "condition_type": "expression"
      },
      "position": {"x": 300.0, "y": 100.0},
      "credentials": {},
      "disabled": false,
      "on_error": "stop",
      "retry_policy": {"max_tries": 1, "wait_between_tries": 0},
      "notes": "Check if confirmation is required",
      "webhooks": []
    },
    {
      "id": "confirmation-action",
      "name": "confirmed-execution-log",
      "type": "ACTION",
      "subtype": "RUN_CODE",
      "type_version": 1,
      "parameters": {
        "language": "python",
        "code": "print(f'Confirmed trigger execution for user: {input_data.get(\"trigger_data\", {}).get(\"user_id\", \"unknown\")}')"
      },
      "position": {"x": 500.0, "y": 50.0},
      "credentials": {},
      "disabled": false,
      "on_error": "stop",
      "retry_policy": {"max_tries": 3, "wait_between_tries": 1},
      "notes": "Log confirmed execution",
      "webhooks": []
    },
    {
      "id": "denied-action",
      "name": "denied-execution-log",
      "type": "ACTION",
      "subtype": "RUN_CODE",
      "type_version": 1,
      "parameters": {
        "language": "python",
        "code": "print('WARNING: Trigger execution denied - confirmation not provided')"
      },
      "position": {"x": 500.0, "y": 150.0},
      "credentials": {},
      "disabled": false,
      "on_error": "stop",
      "retry_policy": {"max_tries": 3, "wait_between_tries": 1},
      "notes": "Log denied execution",
      "webhooks": []
    }
  ],
  "connections": {
    "confirmation-manual-trigger": {
      "main": [{"node": "confirmation-flow-check", "type": "main", "index": 0}]
    },
    "confirmation-flow-check": {
      "true": [{"node": "confirmed-execution-log", "type": "main", "index": 0}],
      "false": [{"node": "denied-execution-log", "type": "main", "index": 0}]
    }
  },
  "settings": {
    "timeout": 60,
    "timezone": {"name": "UTC"},
    "save_execution_progress": true,
    "save_manual_executions": true,
    "error_policy": "stop_on_error",
    "caller_policy": "sequential"
  },
  "static_data": {},
  "pin_data": {}
}
```

**Test Steps**:
1. Create workflow requiring confirmation
2. Attempt trigger without confirmation � expect 403 error with confirmation_required
3. Retry trigger with confirmation=true � expect successful execution
4. Verify conditional logic handles confirmation state correctly

---

## 2. CRON Trigger Test Workflows

Cron triggers activate on scheduled intervals using cron expressions.

### 2.1 Basic Cron Trigger Test

**Purpose**: Test simple scheduled trigger with standard cron expression.

```json
{
  "name": "Basic Cron Trigger Test",
  "description": "Trigger every minute for testing",
  "nodes": [
    {
      "id": "cron-trigger-basic",
      "name": "basic-cron-trigger",
      "type": "TRIGGER",
      "subtype": "CRON",
      "type_version": 1,
      "parameters": {
        "cron_expression": "* * * * *",
        "timezone": "UTC",
        "enabled": true
      },
      "position": {"x": 100.0, "y": 100.0},
      "credentials": {},
      "disabled": false,
      "on_error": "stop",
      "retry_policy": {"max_tries": 1, "wait_between_tries": 0},
      "notes": "Basic cron trigger firing every minute",
      "webhooks": []
    },
    {
      "id": "timestamp-action",
      "name": "cron-timestamp-logger",
      "type": "ACTION",
      "subtype": "RUN_CODE",
      "type_version": 1,
      "parameters": {
        "language": "python",
        "code": "print(f'Cron triggered at: {input_data.get(\"trigger_data\", {}).get(\"triggered_at\", \"unknown\")} | Next run: {input_data.get(\"trigger_data\", {}).get(\"next_run\", \"unknown\")}')"
      },
      "position": {"x": 300.0, "y": 100.0},
      "credentials": {},
      "disabled": false,
      "on_error": "stop",
      "retry_policy": {"max_tries": 3, "wait_between_tries": 1},
      "notes": "Log cron trigger timestamps",
      "webhooks": []
    }
  ],
  "connections": {
    "basic-cron-trigger": {
      "main": [{"node": "cron-timestamp-logger", "type": "main", "index": 0}]
    }
  },
  "settings": {
    "timeout": 60,
    "timezone": {"name": "UTC"},
    "save_execution_progress": true,
    "save_manual_executions": true,
    "error_policy": "stop_on_error",
    "caller_policy": "sequential"
  },
  "static_data": {},
  "pin_data": {}
}
```

**Test Steps**:
1. Create workflow with every-minute cron trigger
2. Deploy workflow to scheduler service
3. Wait for automatic trigger activation
4. Verify execution occurs approximately every minute
5. Check trigger_data includes cron_expression, timezone, current_time, next_run

### 2.2 Advanced Cron Trigger - Business Hours

**Purpose**: Test complex cron expression for business hours only.

```json
{
  "name": "Business Hours Cron Trigger",
  "description": "Trigger weekdays 9-5 EST for business operations",
  "nodes": [
    {
      "id": "business_cron_trigger",
      "type": "TRIGGER",
      "subtype": "CRON",
      "parameters": {
        "cron_expression": "0 9-17 * * MON-FRI",
        "timezone": "America/New_York",
        "enabled": true
      },
      "position": {"x": 100, "y": 100}
    },
    {
      "id": "business_hours_check",
      "type": "FLOW",
      "subtype": "IF",
      "parameters": {
        "condition": "{{trigger_data.should_trigger}} == true",
        "condition_type": "expression"
      },
      "position": {"x": 300, "y": 100}
    },
    {
      "id": "business_action",
      "type": "ACTION",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "url": "https://api.example.com/business-hours-ping",
        "method": "POST",
        "body": {
          "timestamp": "{{trigger_data.triggered_at}}",
          "timezone": "{{trigger_data.timezone}}",
          "cron_expression": "{{trigger_data.cron_expression}}"
        }
      },
      "position": {"x": 500, "y": 50}
    },
    {
      "id": "off_hours_log",
      "type": "ACTION",
      "subtype": "RUN_CODE",
      "parameters": {
        "language": "python",
        "code": "print('Trigger fired outside business hours - skipping action')"
      },
      "position": {"x": 500, "y": 150}
    }
  ],
  "connections": {
    "business_cron_trigger": {
      "main": [{"node": "business_hours_check", "type": "main", "index": 0}]
    },
    "business_hours_check": {
      "true": [{"node": "business_action", "type": "main", "index": 0}],
      "false": [{"node": "off_hours_log", "type": "main", "index": 0}]
    }
  }
}
```

**Test Steps**:
1. Create workflow with business hours cron expression
2. Test cron validation accepts complex expressions
3. Verify timezone handling (EST vs UTC)
4. Test should_trigger logic for business/off hours
5. Validate HTTP action only executes during business hours

---

## 3. WEBHOOK Trigger Test Workflows

Webhook triggers respond to HTTP requests on dynamically created endpoints.

### 3.1 Basic Webhook Trigger Test

**Purpose**: Test simple POST webhook endpoint.

```json
{
  "name": "Basic Webhook Trigger Test",
  "description": "Simple webhook accepting POST data",
  "nodes": [
    {
      "id": "webhook_trigger_1",
      "type": "TRIGGER",
      "subtype": "WEBHOOK",
      "parameters": {
        "webhook_path": "/test-webhook",
        "http_method": "POST",
        "authentication_required": false,
        "response_format": "json"
      },
      "position": {"x": 100, "y": 100}
    },
    {
      "id": "webhook_processor",
      "type": "ACTION",
      "subtype": "RUN_CODE",
      "parameters": {
        "language": "python",
        "code": "print(f'Webhook received: Method={input_data.get(\"trigger_data\", {}).get(\"method\")} Path={input_data.get(\"trigger_data\", {}).get(\"path\")} Body={input_data.get(\"trigger_data\", {}).get(\"body\")}')"
      },
      "position": {"x": 300, "y": 100}
    }
  ],
  "connections": {
    "webhook_trigger_1": {
      "main": [{"node": "webhook_processor", "input": "main"}]
    }
  }
}
```

**Test Steps**:
1. Create webhook workflow
2. Deploy to scheduler to register webhook endpoint
3. Send POST to `/api/v1/public/webhook/workflow/{workflow_id}`
4. Verify trigger activates with request data
5. Check trigger_data includes headers, body, query_params, method, path

### 3.2 Advanced Webhook with Authentication

**Purpose**: Test authenticated webhook with data processing.

```json
{
  "name": "Authenticated Webhook Trigger",
  "description": "Secure webhook with authentication and data transformation",
  "nodes": [
    {
      "id": "secure_webhook_trigger",
      "type": "TRIGGER",
      "subtype": "WEBHOOK",
      "parameters": {
        "webhook_path": "/secure-webhook",
        "http_method": "POST",
        "authentication_required": true,
        "response_format": "json"
      },
      "position": {"x": 100, "y": 100}
    },
    {
      "id": "auth_validation",
      "type": "FLOW",
      "subtype": "IF",
      "parameters": {
        "condition": "{{trigger_data.headers.authorization}} != null",
        "condition_type": "expression"
      },
      "position": {"x": 300, "y": 100}
    },
    {
      "id": "process_payload",
      "type": "ACTION",
      "subtype": "DATA_TRANSFORMATION",
      "parameters": {
        "transformation_type": "json_extract",
        "source_field": "trigger_data.body",
        "target_fields": ["user_id", "action", "timestamp"]
      },
      "position": {"x": 500, "y": 50}
    },
    {
      "id": "auth_denied",
      "type": "ACTION",
      "subtype": "RUN_CODE",
      "parameters": {
        "language": "python",
        "code": "print('WARNING: Webhook authentication failed - missing authorization header')"
      },
      "position": {"x": 500, "y": 150}
    },
    {
      "id": "final_action",
      "type": "ACTION",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "url": "https://api.example.com/webhook-processed",
        "method": "POST",
        "body": {
          "processed_data": "{{processed_payload}}",
          "original_webhook": "{{trigger_data}}"
        }
      },
      "position": {"x": 700, "y": 50}
    }
  ],
  "connections": {
    "secure_webhook_trigger": {
      "main": [{"node": "auth_validation", "input": "main"}]
    },
    "auth_validation": {
      "true": [{"node": "process_payload", "input": "main"}],
      "false": [{"node": "auth_denied", "input": "main"}]
    },
    "process_payload": {
      "main": [{"node": "final_action", "input": "main"}]
    }
  }
}
```

**Test Steps**:
1. Create authenticated webhook workflow
2. Test webhook without auth headers � expect auth validation failure
3. Test webhook with valid auth � expect data processing success
4. Verify data transformation extracts fields correctly
5. Validate final HTTP action receives processed data

---

## 4. SLACK Trigger Test Workflows

Slack triggers respond to Slack events and interactions.

### 4.1 Basic Slack Message Trigger

**Purpose**: Test Slack app mention trigger.

```json
{
  "name": "Basic Slack Trigger Test",
  "description": "Respond to app mentions in Slack",
  "nodes": [
    {
      "id": "slack_trigger_1",
      "type": "TRIGGER",
      "subtype": "SLACK",
      "parameters": {
        "workspace_id": null,
        "channel_filter": null,
        "event_types": ["app_mention"],
        "mention_required": true,
        "command_prefix": null,
        "user_filter": null,
        "ignore_bots": true,
        "require_thread": false
      },
      "position": {"x": 100, "y": 100}
    },
    {
      "id": "slack_responder",
      "type": "EXTERNAL_ACTION",
      "subtype": "SLACK_ACTION",
      "parameters": {
        "action_type": "send_message",
        "channel": "{{trigger_data.channel_id}}",
        "message": "Hello {{trigger_data.user_id}}! I received your mention: {{trigger_data.message}}",
        "thread_ts": "{{trigger_data.thread_ts}}"
      },
      "position": {"x": 300, "y": 100}
    }
  ],
  "connections": {
    "slack_trigger_1": {
      "main": [{"node": "slack_responder", "input": "main"}]
    }
  }
}
```

**Test Steps**:
1. Create Slack trigger workflow
2. Deploy to scheduler with Slack integration
3. Send app mention in Slack channel
4. Verify trigger activates with Slack event data
5. Check response is sent back to correct channel/thread

### 4.2 Advanced Slack Command Trigger

**Purpose**: Test Slack slash command with user filtering.

```json
{
  "name": "Advanced Slack Command Trigger",
  "description": "Handle slash commands with user-based permissions",
  "nodes": [
    {
      "id": "slack_command_trigger",
      "type": "TRIGGER",
      "subtype": "SLACK",
      "parameters": {
        "workspace_id": "T1234567890",
        "channel_filter": "^(general|dev-team)$",
        "event_types": ["slash_command"],
        "mention_required": false,
        "command_prefix": "/deploy",
        "user_filter": "^(admin|devops)",
        "ignore_bots": true,
        "require_thread": false
      },
      "position": {"x": 100, "y": 100}
    },
    {
      "id": "user_permission_check",
      "type": "FLOW",
      "subtype": "IF",
      "parameters": {
        "condition": "{{trigger_data.user_id}} matches '{{slack_command_trigger.parameters.user_filter}}'",
        "condition_type": "regex"
      },
      "position": {"x": 300, "y": 100}
    },
    {
      "id": "deploy_action",
      "type": "EXTERNAL_ACTION",
      "subtype": "GITHUB_ACTION",
      "parameters": {
        "action_type": "trigger_workflow",
        "repository": "company/app",
        "workflow_file": "deploy.yml",
        "inputs": {
          "environment": "{{trigger_data.event_data.text}}"
        }
      },
      "position": {"x": 500, "y": 50}
    },
    {
      "id": "permission_denied",
      "type": "EXTERNAL_ACTION",
      "subtype": "SLACK_ACTION",
      "parameters": {
        "action_type": "send_ephemeral",
        "channel": "{{trigger_data.channel_id}}",
        "user": "{{trigger_data.user_id}}",
        "message": "L You don't have permission to use this command"
      },
      "position": {"x": 500, "y": 150}
    },
    {
      "id": "deploy_confirmation",
      "type": "EXTERNAL_ACTION",
      "subtype": "SLACK_ACTION",
      "parameters": {
        "action_type": "send_message",
        "channel": "{{trigger_data.channel_id}}",
        "message": "=� Deployment started for environment: {{trigger_data.event_data.text}}"
      },
      "position": {"x": 700, "y": 50}
    }
  ],
  "connections": {
    "slack_command_trigger": {
      "main": [{"node": "user_permission_check", "input": "main"}]
    },
    "user_permission_check": {
      "true": [{"node": "deploy_action", "input": "main"}],
      "false": [{"node": "permission_denied", "input": "main"}]
    },
    "deploy_action": {
      "main": [{"node": "deploy_confirmation", "input": "main"}]
    }
  }
}
```

**Test Steps**:
1. Create Slack command workflow with user restrictions
2. Test command from unauthorized user � expect permission denied
3. Test command from authorized user � expect deployment trigger
4. Verify channel/workspace filtering works correctly
5. Test regex user filtering functionality

---

## 5. EMAIL Trigger Test Workflows

Email triggers monitor email inboxes for new messages.

### 5.1 Basic Email Trigger Test

**Purpose**: Test simple email monitoring.

```json
{
  "name": "Basic Email Trigger Test",
  "description": "Monitor inbox for new emails",
  "nodes": [
    {
      "id": "email_trigger_1",
      "type": "TRIGGER",
      "subtype": "EMAIL",
      "parameters": {
        "email_filter": "from:support@example.com",
        "folder": "INBOX",
        "mark_as_read": true,
        "attachment_processing": "include"
      },
      "position": {"x": 100, "y": 100}
    },
    {
      "id": "email_processor",
      "type": "ACTION",
      "subtype": "RUN_CODE",
      "parameters": {
        "language": "python",
        "code": "print(f'Email received from: {input_data.get(\"trigger_data\", {}).get(\"from\")} | Subject: {input_data.get(\"trigger_data\", {}).get(\"subject\")} | Attachments: {len(input_data.get(\"trigger_data\", {}).get(\"attachments\", []))}')"
      },
      "position": {"x": 300, "y": 100}
    }
  ],
  "connections": {
    "email_trigger_1": {
      "main": [{"node": "email_processor", "input": "main"}]
    }
  }
}
```

**Test Steps**:
1. Create email monitoring workflow
2. Configure IMAP connection for test mailbox
3. Send test email matching filter criteria
4. Verify trigger activates with email data
5. Check email marked as read if configured

### 5.2 Advanced Email Processing Workflow

**Purpose**: Test email with attachment processing and conditional routing.

```json
{
  "name": "Advanced Email Processing",
  "description": "Process emails with attachments and route based on content",
  "nodes": [
    {
      "id": "support_email_trigger",
      "type": "TRIGGER",
      "subtype": "EMAIL",
      "parameters": {
        "email_filter": "to:support@company.com AND (subject:urgent OR subject:critical)",
        "folder": "INBOX",
        "mark_as_read": false,
        "attachment_processing": "include"
      },
      "position": {"x": 100, "y": 100}
    },
    {
      "id": "attachment_check",
      "type": "FLOW",
      "subtype": "IF",
      "parameters": {
        "condition": "{{trigger_data.attachments.length}} > 0",
        "condition_type": "expression"
      },
      "position": {"x": 300, "y": 100}
    },
    {
      "id": "process_attachments",
      "type": "ACTION",
      "subtype": "DATA_TRANSFORMATION",
      "parameters": {
        "transformation_type": "file_analysis",
        "source_field": "trigger_data.attachments",
        "analysis_types": ["virus_scan", "content_extraction"]
      },
      "position": {"x": 500, "y": 50}
    },
    {
      "id": "text_only_processing",
      "type": "AI_AGENT",
      "subtype": "OPENAI_CHATGPT",
      "parameters": {
        "model_version": "gpt-4",
        "system_prompt": "Analyze this support email and categorize the urgency level and issue type.",
        "user_prompt": "Email from: {{trigger_data.from}}\nSubject: {{trigger_data.subject}}\nBody: {{trigger_data.body}}"
      },
      "position": {"x": 500, "y": 150}
    },
    {
      "id": "create_ticket",
      "type": "EXTERNAL_ACTION",
      "subtype": "JIRA_ACTION",
      "parameters": {
        "action_type": "create_issue",
        "project": "SUPPORT",
        "issue_type": "Bug",
        "summary": "{{trigger_data.subject}}",
        "description": "Email from: {{trigger_data.from}}\n\nBody: {{trigger_data.body}}\n\nAnalysis: {{ai_analysis}}",
        "priority": "{{ai_analysis.urgency_level}}"
      },
      "position": {"x": 700, "y": 100}
    }
  ],
  "connections": {
    "support_email_trigger": {
      "main": [{"node": "attachment_check", "input": "main"}]
    },
    "attachment_check": {
      "true": [{"node": "process_attachments", "input": "main"}],
      "false": [{"node": "text_only_processing", "input": "main"}]
    },
    "process_attachments": {
      "main": [{"node": "create_ticket", "input": "main"}]
    },
    "text_only_processing": {
      "main": [{"node": "create_ticket", "input": "main"}]
    }
  }
}
```

**Test Steps**:
1. Create advanced email processing workflow
2. Send test email with urgent subject and attachments
3. Verify attachment processing and virus scanning
4. Test AI analysis of email content
5. Validate ticket creation with proper classification

---

## 6. GITHUB Trigger Test Workflows

GitHub triggers respond to repository events via webhooks.

### 6.1 Basic GitHub Pull Request Trigger

**Purpose**: Test GitHub pull request events.

```json
{
  "name": "Basic GitHub PR Trigger",
  "description": "Respond to pull request events",
  "nodes": [
    {
      "id": "github_pr_trigger",
      "type": "TRIGGER",
      "subtype": "GITHUB",
      "parameters": {
        "github_app_installation_id": "12345678",
        "repository": "company/webapp",
        "event_config": {
          "pull_request": {
            "actions": ["opened", "closed", "synchronize"],
            "branches": ["main", "develop"],
            "draft_handling": "ignore"
          }
        },
        "ignore_bots": true,
        "require_signature_verification": true
      },
      "position": {"x": 100, "y": 100}
    },
    {
      "id": "pr_action_router",
      "type": "FLOW",
      "subtype": "IF",
      "parameters": {
        "expression": "trigger_data.action == 'opened'"
      },
      "position": {"x": 300, "y": 100}
    },
    {
      "id": "pr_opened",
      "type": "EXTERNAL_ACTION",
      "subtype": "GITHUB_ACTION",
      "parameters": {
        "action_type": "add_comment",
        "repository": "{{trigger_data.repository.full_name}}",
        "issue_number": "{{trigger_data.payload.number}}",
        "body": "=K Thanks for your pull request! Our CI pipeline will review your changes."
      },
      "position": {"x": 500, "y": 50}
    },
    {
      "id": "pr_closed",
      "type": "FLOW",
      "subtype": "IF",
      "parameters": {
        "condition": "{{trigger_data.payload.merged}} == true",
        "condition_type": "expression"
      },
      "position": {"x": 500, "y": 100}
    },
    {
      "id": "pr_updated",
      "type": "EXTERNAL_ACTION",
      "subtype": "GITHUB_ACTION",
      "parameters": {
        "action_type": "trigger_workflow",
        "repository": "{{trigger_data.repository.full_name}}",
        "workflow_file": "ci.yml",
        "ref": "{{trigger_data.payload.head.ref}}"
      },
      "position": {"x": 500, "y": 150}
    },
    {
      "id": "pr_merged_celebration",
      "type": "EXTERNAL_ACTION",
      "subtype": "SLACK_ACTION",
      "parameters": {
        "action_type": "send_message",
        "channel": "#dev-team",
        "message": "<� PR merged: {{trigger_data.payload.title}} by {{trigger_data.sender.login}}"
      },
      "position": {"x": 700, "y": 80}
    },
    {
      "id": "pr_closed_log",
      "type": "ACTION",
      "subtype": "RUN_CODE",
      "parameters": {
        "language": "python",
        "code": "print(f'PR closed without merge: {input_data.get(\"trigger_data\", {}).get(\"payload\", {}).get(\"title\", \"unknown\")}')"
      },
      "position": {"x": 700, "y": 120}
    }
  ],
  "connections": {
    "github_pr_trigger": {
      "main": [{"node": "pr_action_router", "input": "main"}]
    },
    "pr_action_router": {
      "pr_opened": [{"node": "pr_opened", "input": "main"}],
      "pr_closed": [{"node": "pr_closed", "input": "main"}],
      "pr_updated": [{"node": "pr_updated", "input": "main"}]
    },
    "pr_closed": {
      "true": [{"node": "pr_merged_celebration", "input": "main"}],
      "false": [{"node": "pr_closed_log", "input": "main"}]
    }
  }
}
```

**Test Steps**:
1. Create GitHub PR trigger workflow
2. Set up GitHub App with webhook permissions
3. Create test pull request � verify "opened" trigger
4. Push commits to PR � verify "synchronize" trigger
5. Merge PR � verify "closed" + merged celebration

### 6.2 Advanced GitHub Push Trigger with Path Filtering

**Purpose**: Test GitHub push events with file path filtering.

```json
{
  "name": "Advanced GitHub Push Trigger",
  "description": "Deploy on pushes to specific files",
  "nodes": [
    {
      "id": "github_push_trigger",
      "type": "TRIGGER",
      "subtype": "GITHUB",
      "parameters": {
        "github_app_installation_id": "12345678",
        "repository": "company/webapp",
        "event_config": {
          "push": {
            "branches": ["main"],
            "paths": ["src/**", "package.json", "Dockerfile"]
          }
        },
        "author_filter": "^(?!dependabot)",
        "ignore_bots": true,
        "require_signature_verification": true
      },
      "position": {"x": 100, "y": 100}
    },
    {
      "id": "change_analyzer",
      "type": "ACTION",
      "subtype": "DATA_TRANSFORMATION",
      "parameters": {
        "transformation_type": "git_diff_analysis",
        "source_field": "trigger_data.payload.commits",
        "analysis_types": ["affected_services", "change_impact"]
      },
      "position": {"x": 300, "y": 100}
    },
    {
      "id": "deployment_decision",
      "type": "FLOW",
      "subtype": "IF",
      "parameters": {
        "condition": "{{change_analysis.requires_deployment}} == true",
        "condition_type": "expression"
      },
      "position": {"x": 500, "y": 100}
    },
    {
      "id": "trigger_deployment",
      "type": "EXTERNAL_ACTION",
      "subtype": "GITHUB_ACTION",
      "parameters": {
        "action_type": "create_deployment",
        "repository": "{{trigger_data.repository.full_name}}",
        "ref": "{{trigger_data.payload.after}}",
        "environment": "production",
        "description": "Auto-deployment for commit {{trigger_data.payload.head_commit.id}}"
      },
      "position": {"x": 700, "y": 50}
    },
    {
      "id": "skip_deployment_log",
      "type": "ACTION",
      "subtype": "RUN_CODE",
      "parameters": {
        "language": "python",
        "code": "print(f'Skipping deployment - no significant changes detected in push {input_data.get(\"trigger_data\", {}).get(\"payload\", {}).get(\"after\", \"unknown\")}')"
      },
      "position": {"x": 700, "y": 150}
    },
    {
      "id": "notify_deployment",
      "type": "EXTERNAL_ACTION",
      "subtype": "SLACK_ACTION",
      "parameters": {
        "action_type": "send_message",
        "channel": "#deployments",
        "message": "=� Deploying {{trigger_data.repository.name}} commit {{trigger_data.payload.head_commit.id}} by {{trigger_data.payload.head_commit.author.name}}"
      },
      "position": {"x": 900, "y": 50}
    }
  ],
  "connections": {
    "github_push_trigger": {
      "main": [{"node": "change_analyzer", "input": "main"}]
    },
    "change_analyzer": {
      "main": [{"node": "deployment_decision", "input": "main"}]
    },
    "deployment_decision": {
      "true": [{"node": "trigger_deployment", "input": "main"}],
      "false": [{"node": "skip_deployment_log", "input": "main"}]
    },
    "trigger_deployment": {
      "main": [{"node": "notify_deployment", "input": "main"}]
    }
  }
}
```

**Test Steps**:
1. Create GitHub push trigger with path filtering
2. Push changes to non-matching paths � expect no trigger
3. Push changes to `src/` directory � expect trigger activation
4. Test author filtering (exclude dependabot)
5. Verify deployment creation and Slack notification

---

## Test Execution Plan

### Phase 1: Basic Trigger Validation (Week 1)
- [ ] Create and test all 6 basic trigger workflows
- [ ] Validate parameter parsing and node specifications
- [ ] Test trigger activation and data flow
- [ ] Verify error handling for invalid configurations

### Phase 2: Advanced Trigger Scenarios (Week 2)
- [ ] Create and test all 6 advanced trigger workflows
- [ ] Test complex conditional logic and data transformations
- [ ] Validate integration with external services (mock/sandbox)
- [ ] Test workflow scheduler deployment and management

### Phase 3: Integration Testing (Week 3)
- [ ] Test trigger combinations and chaining
- [ ] Validate authentication and security features
- [ ] Performance testing with high trigger volumes
- [ ] End-to-end testing with real external services

### Phase 4: Documentation and Tooling (Week 4)
- [ ] Document test results and findings
- [ ] Create debugging tools and utilities
- [ ] Set up continuous integration for trigger testing
- [ ] Create trigger monitoring and alerting dashboards

## Testing Environment Setup

### Local Development Setup
```bash
# 1. Start core services
cd apps/backend/workflow_engine && python main.py
cd apps/backend/workflow_scheduler && python main.py
cd apps/backend/api-gateway && python main.py

# 2. Create test workflows via API
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d @trigger_test_workflow.json

# 3. Test manual trigger
curl -X POST http://localhost:8000/api/v1/workflows/{id}/trigger/manual \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"require_confirmation": false, "enabled": true}'
```

### Mock Service Configuration
For testing external integrations, set up mock services:
- **Mock Slack API**: Webhook endpoints and event simulation
- **Mock GitHub API**: Repository event simulation
- **Mock Email Server**: IMAP/SMTP test server
- **Mock HTTP Endpoints**: For webhook and HTTP action testing

### Test Data Management
- Use test-specific workflow IDs and names
- Clean up test workflows after execution
- Maintain separate test database/namespace
- Log all trigger events for debugging

## Success Criteria

### Functional Requirements
 All 12 test workflows create successfully without validation errors
 All trigger types activate correctly with proper input data
 Trigger output data matches expected schema and format
 Error handling works for invalid configurations and failed triggers
 Integration with workflow scheduler works for all trigger types

### Performance Requirements
 Manual triggers respond within 2 seconds
 Cron triggers activate within 10 seconds of scheduled time
 Webhook triggers handle 100 concurrent requests
 Email triggers process messages within 30 seconds
 GitHub/Slack triggers handle webhook payloads under 5 seconds

### Security Requirements
 Authentication required where configured
 Webhook signature verification working
 User permission filtering functional
 No sensitive data exposed in logs
 All external API calls use secure authentication

This comprehensive testing plan ensures all trigger node types are thoroughly validated and ready for production deployment.

---

## ⚠️ **CRITICAL VALIDATION FIXES APPLIED**

### **Fixed Issues in All Workflows:**

1. **✅ Node Structure Compliance**:
   - Added all required fields: `id`, `name`, `type`, `subtype`, `type_version`, `position`, `parameters`, `credentials`, `disabled`, `on_error`, `retry_policy`, `notes`, `webhooks`
   - Fixed node naming: Using semantic hyphenated names like `basic-manual-trigger` instead of IDs
   - Updated positions to float coordinates: `{"x": 100.0, "y": 100.0}`
   - Added proper `type_version: 1` for all nodes

2. **✅ Connection Structure Compliance**:
   - Updated connections to use node names instead of IDs
   - Fixed connection format: `{"node": "target-name", "type": "main", "index": 0}`
   - Removed old `"input"` field, replaced with proper `"type"` and `"index"`
   - Ensured TRIGGER nodes only use `"main"` connections (no `error`, `success`, `true`, `false`)
   - FLOW nodes (IF subtype) correctly use `"true"` and `"false"` connections

3. **✅ Workflow Settings Compliance**:
   - Added complete settings: `timeout`, `timezone`, `save_execution_progress`, `save_manual_executions`, `error_policy`, `caller_policy`
   - Added required `static_data: {}` and `pin_data: {}` fields
   - Timezone format: `{"name": "UTC"}` instead of string

4. **✅ Parameter Compliance**:
   - All parameters match node specification requirements
   - Trigger nodes use correct parameter names from MCP specifications
   - Required parameters have non-null values

### **Remaining Workflows to Fix:**

The following 8 workflows still need the same validation fixes applied:

- **Advanced Cron Trigger - Business Hours** (lines 280-380)
- **Basic Webhook Trigger Test** (lines 390-450)
- **Advanced Webhook with Authentication** (lines 460-580)
- **Basic Slack Message Trigger** (lines 590-650)
- **Advanced Slack Command Trigger** (lines 660-780)
- **Basic Email Trigger Test** (lines 790-850)
- **Advanced Email Processing Workflow** (lines 860-980)
- **Basic GitHub Pull Request Trigger** (lines 990-1150)
- **Advanced GitHub Push Trigger** (lines 1160-1320)

### **Fix Template for Remaining Workflows:**

```json
{
  "id": "descriptive-kebab-case-id",
  "name": "descriptive-kebab-case-name",
  "type": "TRIGGER|ACTION|FLOW|etc",
  "subtype": "SPECIFIC_SUBTYPE",
  "type_version": 1,
  "parameters": {
    // Exact parameter names from MCP specifications
  },
  "position": {"x": 100.0, "y": 100.0},
  "credentials": {},
  "disabled": false,
  "on_error": "stop",
  "retry_policy": {"max_tries": 3, "wait_between_tries": 1},
  "notes": "Descriptive note about node function",
  "webhooks": []
}
```

### **Connection Format Template:**

```json
"connections": {
  "source-node-name": {
    "main": [{"node": "target-node-name", "type": "main", "index": 0}]
  },
  "flow-node-name": {
    "true": [{"node": "success-target", "type": "main", "index": 0}],
    "false": [{"node": "failure-target", "type": "main", "index": 0}]
  }
}
```

### **Complete Workflow Settings Template:**

```json
"settings": {
  "timeout": 60,
  "timezone": {"name": "UTC"},
  "save_execution_progress": true,
  "save_manual_executions": true,
  "error_policy": "stop_on_error",
  "caller_policy": "sequential"
},
"static_data": {},
"pin_data": {}
```

**Note**: The first 3 workflows (2 MANUAL + 1 CRON) have been fully corrected as examples. The remaining workflows need identical fixes applied following the templates above.
