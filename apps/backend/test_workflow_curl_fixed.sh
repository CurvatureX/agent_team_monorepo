#!/bin/bash

# Direct workflow creation CURL request with FIXED parameter types
# Boolean and integer parameters should not be strings

curl -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
  "name": "Scheduled HTTP Request to Google (Fixed Types)",
  "description": "Sends an HTTP GET request to https://google.com every 5 minutes using a cron trigger.",
  "nodes": [
    {
      "id": "cron-trigger-001",
      "name": "cron-trigger-every-5-minutes",
      "type": "TRIGGER_NODE",
      "subtype": "TRIGGER_CRON",
      "type_version": 1,
      "position": {"x": 100.0, "y": 100.0},
      "parameters": {
        "cron_expression": "*/5 * * * *",
        "timezone": "UTC",
        "enabled": true
      },
      "credentials": {},
      "disabled": false,
      "on_error": "continue",
      "retry_policy": {
        "max_tries": 3,
        "wait_between_tries": 10
      },
      "notes": {},
      "webhooks": []
    },
    {
      "id": "http-request-001",
      "name": "http-request-to-google",
      "type": "ACTION_NODE",
      "subtype": "HTTP_REQUEST",
      "type_version": 1,
      "position": {"x": 400.0, "y": 100.0},
      "parameters": {
        "url": "https://google.com",
        "method": "GET",
        "headers": "{}",
        "authentication": "none",
        "timeout": 30,
        "retry_attempts": 3
      },
      "credentials": {},
      "disabled": false,
      "on_error": "continue",
      "retry_policy": {
        "max_tries": 3,
        "wait_between_tries": 10
      },
      "notes": {},
      "webhooks": []
    }
  ],
  "connections": {
    "cron-trigger-every-5-minutes": {
      "main": [
        {
          "node": "http-request-to-google",
          "type": "main",
          "index": 0
        }
      ]
    }
  },
  "settings": {
    "timezone": {"name": "UTC"},
    "save_execution_progress": true,
    "save_manual_executions": true,
    "timeout": 3600,
    "error_policy": "continue",
    "caller_policy": "workflow"
  },
  "static_data": {},
  "tags": ["http", "cron", "automation", "google"],
  "user_id": "7ba36345-a2bb-4ec9-a001-bb46d79d629d"
}' | jq .