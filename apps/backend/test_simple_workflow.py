#!/usr/bin/env python3
"""Test simple workflow creation to verify parameter type fixes"""

import json
import sys

# Test workflow that should work with our fixes
test_workflow = {
    "name": "Simple Cron Test",
    "description": "Test workflow with cron trigger",
    "nodes": [
        {
            "id": "cron-trigger-001",
            "name": "hourly-trigger",
            "type": "TRIGGER_NODE",
            "subtype": "TRIGGER_CRON",
            "position": {"x": 100.0, "y": 100.0},
            "parameters": {
                "cron_expression": "*/5 * * * *",  # Every 5 minutes
                "enabled": True,  # Boolean, not string
                "timezone": "UTC"
            },
            "credentials": {},
            "disabled": False,
            "on_error": "stop",
            "notes": "Triggers every 5 minutes"
        },
        {
            "id": "http-action-001",
            "name": "http-request",
            "type": "ACTION_NODE",
            "subtype": "HTTP_REQUEST",
            "position": {"x": 300.0, "y": 100.0},
            "parameters": {
                "url": "https://google.com",
                "method": "GET",
                "timeout": 30,  # Integer, not string
                "retry_count": 3  # Integer, not string
            },
            "credentials": {},
            "disabled": False,
            "on_error": "stop",
            "notes": "Send GET request to Google"
        }
    ],
    "connections": {
        "hourly-trigger": {
            "main": [
                {
                    "node": "http-request",
                    "type": "main",
                    "index": 0
                }
            ]
        }
    },
    "settings": {
        "timezone": {"name": "UTC"},
        "save_execution_progress": True,
        "save_manual_executions": True,
        "timeout": 300,
        "error_policy": "continue"
    }
}

# Print as JSON for testing
print(json.dumps(test_workflow, indent=2))

# Try to validate with croniter
try:
    from croniter import croniter
    cron_expr = test_workflow["nodes"][0]["parameters"]["cron_expression"]
    croniter(cron_expr)
    print(f"\n✅ Cron expression '{cron_expr}' is valid", file=sys.stderr)
except Exception as e:
    print(f"\n❌ Cron validation failed: {e}", file=sys.stderr)

# Check parameter types
cron_params = test_workflow["nodes"][0]["parameters"]
http_params = test_workflow["nodes"][1]["parameters"]

print(f"\n✅ Parameter type checks:", file=sys.stderr)
print(f"  - enabled is boolean: {isinstance(cron_params['enabled'], bool)}", file=sys.stderr)
print(f"  - timeout is integer: {isinstance(http_params['timeout'], int)}", file=sys.stderr)
print(f"  - retry_count is integer: {isinstance(http_params['retry_count'], int)}", file=sys.stderr)