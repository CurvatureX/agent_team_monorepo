#!/bin/bash

echo "🔍 调试验证问题..."
echo "================================================"

# 只创建3个节点的简单流程
RESPONSE=$(curl -s -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "调试验证",
    "description": "调试端口验证问题",
    "user_id": "00000000-0000-0000-0000-000000000123",
    "nodes": [
      {
        "name": "触发器",
        "type": "TRIGGER_NODE",
        "subtype": "TRIGGER_MANUAL",
        "position": {"x": 100, "y": 100}
      },
      {
        "name": "HTTP请求",
        "type": "ACTION_NODE",
        "subtype": "HTTP_REQUEST",
        "parameters": {
          "url": "https://example.com",
          "method": "GET"
        },
        "position": {"x": 300, "y": 100}
      },
      {
        "name": "判断条件",
        "type": "FLOW_NODE",
        "subtype": "IF",
        "parameters": {
          "condition": "true"
        },
        "position": {"x": 500, "y": 100}
      }
    ],
    "connections": {
      "触发器": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "HTTP请求",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "HTTP请求": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "判断条件",
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

if echo "$RESPONSE" | jq -e '.success == true' > /dev/null 2>&1; then
    echo "✅ 成功创建"
else
    echo "❌ 失败 - 检查哪个节点报错"
    echo "$RESPONSE" | jq -r '.detail'
fi