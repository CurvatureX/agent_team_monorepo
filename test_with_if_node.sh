#!/bin/bash

echo "🔍 测试添加 IF 节点..."
echo "================================================"

# 添加一个 IF 节点
RESPONSE=$(curl -s -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试IF节点",
    "description": "测试IF节点的输入端口",
    "user_id": "00000000-0000-0000-0000-000000000123",
    "nodes": [
      {
        "name": "开始",
        "type": "TRIGGER_NODE",
        "subtype": "TRIGGER_MANUAL",
        "position": {"x": 100, "y": 100}
      },
      {
        "name": "判断",
        "type": "FLOW_NODE",
        "subtype": "IF",
        "parameters": {
          "condition": "true"
        },
        "position": {"x": 300, "y": 100}
      },
      {
        "name": "结束",
        "type": "ACTION_NODE",
        "subtype": "HTTP_REQUEST",
        "parameters": {
          "url": "https://example.com",
          "method": "GET"
        },
        "position": {"x": 500, "y": 100}
      }
    ],
    "connections": {
      "开始": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "判断",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "判断": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "结束",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      }
    },
    "settings": {
      "timeout": 300
    }
  }')

echo "$RESPONSE" | jq '.'