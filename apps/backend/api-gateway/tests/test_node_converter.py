#!/usr/bin/env python3
"""
Test node converter logic
"""

from app.utils.node_converter import (
    convert_node_for_workflow_engine,
    convert_nodes_for_workflow_engine,
)

# Test data
test_nodes = [
    {
        "id": "trigger_1",
        "name": "定时触发",
        "type": "trigger",
        "subtype": "TRIGGER_CRON",
        "parameters": {"cron_expression": "0 8 * * *", "timezone": "Asia/Shanghai"},
        "position": {"x": 100, "y": 200},
    },
    {
        "id": "action_1",
        "name": "获取天气",
        "type": "action",
        "subtype": "HTTP_REQUEST",
        "parameters": {"method": "GET", "url": "https://api.openweathermap.org/data/2.5/weather"},
        "position": {"x": 300, "y": 200},
    },
    {
        "id": "condition_1",
        "name": "条件判断",
        "type": "condition",
        "subtype": "IF",
        "parameters": {"condition": "output.main.temp > 30"},
        "position": {"x": 500, "y": 200},
    },
]

# Convert nodes
converted_nodes = convert_nodes_for_workflow_engine(test_nodes)

# Print results
import json

print("Original nodes:")
print(json.dumps(test_nodes, indent=2, ensure_ascii=False))
print("\nConverted nodes:")
print(json.dumps(converted_nodes, indent=2, ensure_ascii=False))

# Verify conversion
for i, node in enumerate(converted_nodes):
    print(f"\nNode {i+1}:")
    print(f"  Name: {node['name']}")
    print(f"  Type: {node['type']} (was: {test_nodes[i]['type']})")
    print(f"  Subtype: {node['subtype']}")
