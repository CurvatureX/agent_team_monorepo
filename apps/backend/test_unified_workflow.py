#\!/usr/bin/env python3
"""
测试统一的工作流模型
"""
import json
import requests

# 测试直接调用 Workflow Engine (绕过认证)
workflow_data = {
    "name": "My Unified Workflow",
    "description": "A workflow using unified model",
    "nodes": [
        {
            "name": "Manual Trigger",
            "type": "TRIGGER_NODE",
            "subtype": "TRIGGER_MANUAL",
            "position": {"x": 100, "y": 100},
            "parameters": {}
        },
        {
            "name": "HTTP Request",
            "type": "ACTION_NODE", 
            "subtype": "HTTP_REQUEST",
            "position": {"x": 300, "y": 100},
            "parameters": {
                "method": "GET",
                "url": "https://api.example.com/data"
            }
        }
    ],
    "connections": {
        "Manual Trigger": {
            "main": [{"node": "HTTP Request", "port": "main"}]
        }
    },
    "settings": {
        "timezone": {"name": "UTC"},
        "save_execution_progress": True,
        "timeout": 3600
    },
    "static_data": {},
    "tags": ["test", "unified"],
    "user_id": "test-user-123"
}

# 直接测试 Workflow Engine
print("Testing Workflow Engine directly...")
response = requests.post(
    "http://localhost:8002/v1/workflows",
    json=workflow_data,
    headers={"Content-Type": "application/json"}
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code == 200:
    workflow_id = response.json().get("workflow", {}).get("id")
    print(f"\nWorkflow created successfully with ID: {workflow_id}")
