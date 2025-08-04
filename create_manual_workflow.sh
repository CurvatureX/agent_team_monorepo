#!/bin/bash

echo "🚀 创建人工触发的网站监控 Workflow（简化连接结构）..."
echo "================================================"

curl -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -d '{
    "name": "网站监控和通知系统-手动版",
    "description": "手动触发的网站监控，使用简化的单层连接结构",
    "user_id": "00000000-0000-0000-0000-000000000123",
    "nodes": [
      {
        "id": "manual_trigger_1",
        "name": "手动触发器",
        "type": "TRIGGER_NODE",
        "subtype": "TRIGGER_MANUAL",
        "position": {"x": 100, "y": 100},
        "parameters": {}
      },
      {
        "id": "http_check_1",
        "name": "检查Google网站状态",
        "type": "ACTION_NODE",
        "subtype": "HTTP_REQUEST",
        "parameters": {
          "url": "https://www.google.com",
          "method": "GET",
          "headers": "{\"User-Agent\": \"Website-Monitor-Bot/1.0\"}",
          "timeout": "10",
          "retry_attempts": "3",
          "authentication": "none",
          "data": "{}"
        },
        "position": {"x": 300, "y": 100}
      },
      {
        "id": "status_check_1",
        "name": "判断网站状态",
        "type": "FLOW_NODE",
        "subtype": "IF",
        "parameters": {
          "condition": "response.status_code == 200"
        },
        "position": {"x": 500, "y": 100}
      },
      {
        "id": "data_transform_1",
        "name": "格式化监控数据",
        "type": "ACTION_NODE",
        "subtype": "DATA_TRANSFORMATION",
        "parameters": {
          "transformation_type": "map",
          "transformation_rule": "format_monitoring_data"
        },
        "position": {"x": 700, "y": 100}
      },
      {
        "id": "alert_filter_1",
        "name": "异常情况过滤器",
        "type": "FLOW_NODE",
        "subtype": "FILTER",
        "parameters": {
          "filter_expression": "status == 'error' or response_time > 5000"
        },
        "position": {"x": 900, "y": 100}
      },
      {
        "id": "calendar_log_1",
        "name": "记录监控事件",
        "type": "ACTION_NODE",
        "subtype": "CODE_EXECUTION",
        "parameters": {
          "code": "# 记录监控事件到日历\nimport datetime\nevent = {\n    'title': '网站监控告警',\n    'time': datetime.datetime.now().isoformat(),\n    'details': input_data\n}\nprint(f'Event recorded: {event}')\nreturn {'event': event}",
          "language": "python"
        },
        "position": {"x": 1100, "y": 100}
      }
    ],
    "connections": {
      "手动触发器": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "检查Google网站状态",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "检查Google网站状态": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "判断网站状态",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "判断网站状态": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "格式化监控数据",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "格式化监控数据": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "异常情况过滤器",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "异常情况过滤器": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "记录监控事件",
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
      "error_policy": "continue",
      "save_execution_progress": true,
      "save_manual_executions": true
    },
    "static_data": {
      "monitoring_config": "{\"check_interval\": \"manual\", \"alert_threshold\": 5000, \"notification_channels\": [\"email\", \"calendar\"]}"
    },
    "tags": ["monitoring", "automation", "google", "health-check", "manual"]
  }' | jq '.'

echo ""
echo "✅ 修改说明："
echo "   1. 触发器从 TRIGGER_CRON 改为 TRIGGER_MANUAL"
echo "   2. connections 结构已简化为单层（移除了外层的 connections 包装）"
echo "   3. 使用节点名称（而非ID）作为连接的键"