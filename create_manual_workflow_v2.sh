#!/bin/bash

echo "🚀 创建人工触发的网站监控 Workflow（简化连接结构）..."
echo "================================================"

curl -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -d '{
    "name": "网站监控-手动触发版",
    "description": "手动触发的网站监控，使用简化的单层连接结构",
    "user_id": "00000000-0000-0000-0000-000000000123",
    "nodes": [
      {
        "id": "manual_trigger",
        "name": "手动触发器",
        "type": "TRIGGER_NODE",
        "subtype": "TRIGGER_MANUAL",
        "position": {"x": 100, "y": 100}
      },
      {
        "id": "http_check",
        "name": "检查网站",
        "type": "ACTION_NODE",
        "subtype": "HTTP_REQUEST",
        "parameters": {
          "url": "https://www.google.com",
          "method": "GET",
          "timeout": "10"
        },
        "position": {"x": 300, "y": 100}
      },
      {
        "id": "status_check",
        "name": "判断状态",
        "type": "FLOW_NODE",
        "subtype": "IF",
        "parameters": {
          "condition": "response.status_code == 200"
        },
        "position": {"x": 500, "y": 100}
      },
      {
        "id": "log_result",
        "name": "记录结果",
        "type": "ACTION_NODE",
        "subtype": "CODE_EXECUTION",
        "parameters": {
          "code": "print(f\"Website check result: {input_data}\")\nreturn {\"logged\": True}",
          "language": "python"
        },
        "position": {"x": 700, "y": 100}
      }
    ],
    "connections": {
      "手动触发器": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "检查网站",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "检查网站": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "判断状态",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "判断状态": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "记录结果",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      }
    },
    "settings": {
      "timeout": 300,
      "error_policy": "continue"
    },
    "tags": ["monitoring", "manual", "simplified"]
  }' | jq '.'

echo ""
echo "✅ 完成修改："
echo "   1. 触发器：TRIGGER_CRON → TRIGGER_MANUAL"
echo "   2. connections：保持了简化的单层结构"