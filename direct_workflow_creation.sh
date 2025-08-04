#!/bin/bash

# Direct workflow creation via workflow_engine API
# No authentication required - direct service call

echo "🚀 Creating workflow directly via workflow_engine API..."

curl -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -d '{
    "name": "网站监控和通知系统",
    "description": "定时监控Google网站状态，记录监控结果并在异常时通知",
    "user_id": "7ba36345-a2bb-4ec9-a001-bb46d79d629d",
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
        "name": "检查Google网站状态",
        "type": "ACTION_NODE",
        "subtype": "HTTP_REQUEST",
        "parameters": {
          "method": "GET",
          "url": "https://www.google.com",
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
          "filter_condition": "{\"status\": \"error\", \"response_time\": \">5000\"}"
        },
        "position": {"x": 900, "y": 100}
      },
      {
        "id": "calendar_log_1",
        "name": "记录监控事件",
        "type": "TOOL_NODE",
        "subtype": "TOOL_CALENDAR",
        "parameters": {
          "calendar_id": "monitoring@company.com",
          "operation": "create_event"
        },
        "position": {"x": 1100, "y": 100}
      }
    ],
    "connections": {
      "定时监控触发器": {
          "connection_types": {
            "main": {
              "connections": [
                {
                  "node": "检查Google网站状态",
                  "index": 0,
                  "type": "MAIN"
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
                  "index": 0,
                  "type": "MAIN"
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
                  "index": 0, 
                  "type": "MAIN"
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
                  "index": 0,
                  "type": "MAIN"
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
    "static_data": {
      "monitoring_config": "{\"check_interval\": \"1h\", \"alert_threshold\": 5000, \"notification_channels\": [\"email\", \"calendar\"]}"
    },
    "tags": ["monitoring", "automation", "google", "health-check"]
  }'

echo ""
echo "✅ Workflow creation request sent to workflow_engine:8002"
echo "📋 Workflow contains:"
echo "   - 1个TRIGGER节点 (TRIGGER_CRON)"
echo "   - 2个ACTION节点 (HTTP_REQUEST + DATA_TRANSFORMATION)"
echo "   - 2个FLOW节点 (IF + FILTER)"
echo "   - 1个TOOL节点 (TOOL_CALENDAR)"
echo "   - 完整的逻辑连接关系"