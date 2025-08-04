#!/bin/bash

echo "🚀 创建人工触发的网站监控 Workflow（简化连接结构）..."
echo "================================================"

# 创建 workflow
RESPONSE=$(curl -s -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "网站监控和通知系统-手动版",
    "description": "手动触发的网站监控，监控Google网站状态",
    "user_id": "00000000-0000-0000-0000-000000000123",
    "nodes": [
      {
        "id": "manual_trigger_1",
        "name": "手动触发器",
        "type": "TRIGGER_NODE",
        "subtype": "TRIGGER_MANUAL",
        "position": {"x": 100, "y": 100}
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
          "filter_expression": "status == \"error\" or response_time > 5000"
        },
        "position": {"x": 900, "y": 100}
      },
      {
        "id": "log_result_1",
        "name": "记录监控结果",
        "type": "ACTION_NODE",
        "subtype": "RUN_CODE",
        "parameters": {
          "code": "# 记录监控结果\\nimport json\\nfrom datetime import datetime\\n\\nevent = {\\n    \"title\": \"网站监控事件\",\\n    \"timestamp\": datetime.now().isoformat(),\\n    \"status\": input_data.get(\"status\", \"unknown\"),\\n    \"response_time\": input_data.get(\"response_time\", 0),\\n    \"details\": input_data\\n}\\n\\nprint(f\"监控事件记录: {json.dumps(event, ensure_ascii=False)}\")\\nreturn {\"event_logged\": True, \"event\": event}",
          "language": "python"
        },
        "position": {"x": 1100, "y": 100}
      }
    ],
    "connections": {
      "manual_trigger_1": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "http_check_1",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "http_check_1": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "status_check_1",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "status_check_1": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "data_transform_1",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "data_transform_1": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "alert_filter_1",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "alert_filter_1": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "log_result_1",
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
      "monitoring_config": "{\"check_interval\": \"manual\", \"alert_threshold\": 5000, \"notification_channels\": [\"log\"]}"
    },
    "tags": ["monitoring", "automation", "google", "health-check", "manual"]
  }')

# 打印结果
echo "$RESPONSE" | jq '.'

# 检查是否成功
if echo "$RESPONSE" | jq -e '.success == true' > /dev/null; then
    WORKFLOW_ID=$(echo "$RESPONSE" | jq -r '.workflow.id')
    echo ""
    echo "✅ Workflow 创建成功！"
    echo "🆔 Workflow ID: $WORKFLOW_ID"
    echo ""
    echo "📋 主要修改："
    echo "   1. 触发器类型：TRIGGER_CRON → TRIGGER_MANUAL"
    echo "   2. 连接结构：已使用简化的单层结构（无外层 connections 包装）"
    echo "   3. 日历节点：改为 RUN_CODE 节点记录日志"
else
    echo ""
    echo "❌ Workflow 创建失败"
fi