#!/bin/bash

echo "🚀 创建人工触发的网站监控 Workflow（使用名称连接）..."
echo "================================================"

# 创建 workflow - 使用节点名称作为连接引用
RESPONSE=$(curl -s -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "网站监控-手动触发版",
    "description": "手动触发的网站监控，使用名称作为连接引用",
    "user_id": "00000000-0000-0000-0000-000000000123",
    "nodes": [
      {
        "name": "手动触发器",
        "type": "TRIGGER_NODE",
        "subtype": "TRIGGER_MANUAL",
        "position": {"x": 100, "y": 100}
      },
      {
        "name": "检查Google网站状态",
        "type": "ACTION_NODE",
        "subtype": "HTTP_REQUEST",
        "parameters": {
          "url": "https://www.google.com",
          "method": "GET",
          "headers": "{\"User-Agent\": \"Website-Monitor-Bot/1.0\"}",
          "timeout": "10",
          "retry_attempts": "3"
        },
        "position": {"x": 300, "y": 100}
      },
      {
        "name": "判断网站状态",
        "type": "FLOW_NODE",
        "subtype": "IF",
        "parameters": {
          "condition": "response.status_code == 200"
        },
        "position": {"x": 500, "y": 100}
      },
      {
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
        "name": "异常情况过滤器",
        "type": "FLOW_NODE",
        "subtype": "FILTER",
        "parameters": {
          "filter_expression": "status == \"error\" or response_time > 5000"
        },
        "position": {"x": 900, "y": 100}
      },
      {
        "name": "记录监控结果",
        "type": "ACTION_NODE",
        "subtype": "RUN_CODE",
        "parameters": {
          "code": "# 记录监控结果\\nimport json\\nfrom datetime import datetime\\n\\nevent = {\\n    \"title\": \"网站监控事件\",\\n    \"timestamp\": datetime.now().isoformat(),\\n    \"status\": input_data.get(\"status\", \"unknown\"),\\n    \"response_time\": input_data.get(\"response_time\", 0)\\n}\\n\\nprint(f\"监控事件: {json.dumps(event, ensure_ascii=False)}\")\\nreturn {\"logged\": True, \"event\": event}",
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
                "node": "记录监控结果",
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
    "tags": ["monitoring", "manual", "name-based"]
  }')

# 打印结果
echo "$RESPONSE" | jq '.'

# 检查是否成功
if echo "$RESPONSE" | jq -e '.success == true' > /dev/null 2>&1; then
    WORKFLOW_ID=$(echo "$RESPONSE" | jq -r '.workflow.id')
    echo ""
    echo "✅ Workflow 创建成功！"
    echo "🆔 Workflow ID: $WORKFLOW_ID"
    echo ""
    echo "📋 特点："
    echo "   1. 触发器：TRIGGER_MANUAL（手动触发）"
    echo "   2. 节点 ID：系统自动生成"
    echo "   3. 连接：创建时使用名称，存储时自动转换为 ID"
    echo ""
    echo "🔍 生成的节点信息："
    echo "$RESPONSE" | jq '.workflow.nodes[] | {name: .name, id: .id}'
    echo ""
    echo "📊 连接映射结果（应该使用生成的 ID）："
    echo "$RESPONSE" | jq '.workflow.connections | to_entries[0:2]'
else
    echo ""
    echo "❌ Workflow 创建失败"
fi