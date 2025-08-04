#!/bin/bash

# 创建使用简化连接结构的 workflow
# 直接调用 workflow_engine API (端口 8002)

echo "🚀 创建使用简化连接结构的网站监控 Workflow..."
echo "================================================"

# 使用正确的 user_id (UUID 格式)
USER_ID="7ba36345-a2bb-4ec9-a001-bb46d79d629d"

curl -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -d '{
    "name": "简化连接结构-网站监控系统",
    "description": "使用新的简化连接格式的监控workflow",
    "user_id": "'$USER_ID'",
    "nodes": [
      {
        "id": "cron_trigger_1",
        "name": "定时监控触发器",
        "type": "TRIGGER_NODE",
        "subtype": "TRIGGER_CRON",
        "parameters": {
          "cron_expression": "0 * * * *",
          "timezone": "UTC"
        },
        "position": {"x": 100, "y": 100}
      },
      {
        "id": "http_check_1",
        "name": "检查Google网站",
        "type": "ACTION_NODE",
        "subtype": "HTTP_REQUEST",
        "parameters": {
          "method": "GET",
          "url": "https://www.google.com",
          "headers": "{\"User-Agent\": \"Monitor-Bot/2.0\"}",
          "timeout": "10",
          "retry_attempts": "3",
          "authentication": "none",
          "data": "{}"
        },
        "position": {"x": 300, "y": 100}
      },
      {
        "id": "status_check_1",
        "name": "状态判断",
        "type": "FLOW_NODE",
        "subtype": "IF",
        "parameters": {
          "condition": "response.status_code == 200"
        },
        "position": {"x": 500, "y": 100}
      },
      {
        "id": "log_result_1",
        "name": "记录结果",
        "type": "TOOL_NODE",
        "subtype": "TOOL_CALENDAR",
        "parameters": {
          "calendar_id": "monitoring@example.com",
          "operation": "create_event"
        },
        "position": {"x": 700, "y": 100}
      }
    ],
    "connections": {
      "定时监控触发器": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "检查Google网站",
                "index": 0,
                "type": "MAIN"
              }
            ]
          }
        }
      },
      "检查Google网站": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "状态判断",
                "index": 0,
                "type": "MAIN"
              }
            ]
          }
        }
      },
      "状态判断": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "记录结果",
                "index": 0,
                "type": "MAIN"
              }
            ]
          }
        }
      }
    },
    "settings": {
      "retry_policy": {
        "max_retries": 3,
        "retry_delay": 5
      },
      "timeout": 300,
      "parallel_execution": false
    },
    "tags": ["monitoring", "simplified", "google"]
  }'

echo ""
echo "✅ Workflow 创建请求已发送"
echo "📋 特点："
echo "   - 使用简化的连接结构（无双层 connections）"
echo "   - 包含4个节点：触发器→HTTP请求→条件判断→日志记录"
echo "   - 完整的执行流程"