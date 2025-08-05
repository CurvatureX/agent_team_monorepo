#!/bin/bash

echo "=== 创建天气预警 Workflow ==="
echo "描述：每天8点检查天气，如果温度超过30度就发送高温警告"
echo ""

# 创建 workflow
RESPONSE=$(curl -s -X POST "http://localhost:8002/v1/workflows" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "00000000-0000-0000-0000-000000000123",
  "name": "Daily Weather Alert System",
  "description": "每天早上8点获取天气信息，根据天气状况发送不同的提醒",
  "nodes": [
    {
      "name": "每日触发器",
      "type": "TRIGGER",
      "subtype": "CRON",
      "parameters": {
        "cron_expression": "0 8 * * *",
        "timezone": "Asia/Shanghai"
      },
      "position": {
        "x": 100,
        "y": 200
      }
    },
    {
      "name": "获取天气信息",
      "type": "ACTION",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "GET",
        "url": "https://api.openweathermap.org/data/2.5/weather",
        "query_params": "{\"q\": \"Shanghai\", \"appid\": \"YOUR_API_KEY\", \"units\": \"metric\"}",
        "headers": "{\"Accept\": \"application/json\"}"
      },
      "position": {
        "x": 300,
        "y": 200
      }
    },
    {
      "name": "检查温度",
      "type": "FLOW",
      "subtype": "IF",
      "parameters": {
        "condition": "${nodes.获取天气信息.output.main.temp} > 30"
      },
      "position": {
        "x": 500,
        "y": 200
      }
    },
    {
      "name": "准备高温警告",
      "type": "ACTION",
      "subtype": "DATA_TRANSFORMATION",
      "parameters": {
        "transform_type": "jmespath",
        "expression": "{alert: '高温警告！温度超过30°C，请注意防暑', level: 'warning'}"
      },
      "position": {
        "x": 700,
        "y": 150
      }
    },
    {
      "name": "准备正常消息",
      "type": "ACTION",
      "subtype": "DATA_TRANSFORMATION",
      "parameters": {
        "transform_type": "jmespath",
        "expression": "{alert: '今日温度适宜，适合外出', level: 'info'}"
      },
      "position": {
        "x": 700,
        "y": 250
      }
    },
    {
      "name": "合并消息",
      "type": "FLOW",
      "subtype": "MERGE",
      "parameters": {
        "merge_strategy": "merge_objects"
      },
      "position": {
        "x": 900,
        "y": 200
      }
    },
    {
      "name": "发送通知",
      "type": "ACTION",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "POST",
        "url": "https://webhook.site/your-unique-url",
        "headers": "{\"Content-Type\": \"application/json\"}",
        "body": "{\"message\": \"${nodes.合并消息.output.alert}\", \"level\": \"${nodes.合并消息.output.level}\", \"timestamp\": \"${Date.now()}\"}"
      },
      "position": {
        "x": 1100,
        "y": 200
      }
    }
  ],
  "connections": {
    "每日触发器": {
      "main": [{
        "node": "获取天气信息",
        "port": "main"
      }]
    },
    "获取天气信息": {
      "success": [{
        "node": "检查温度",
        "port": "main"
      }]
    },
    "检查温度": {
      "true": [{
        "node": "准备高温警告",
        "port": "main"
      }],
      "false": [{
        "node": "准备正常消息",
        "port": "main"
      }]
    },
    "准备高温警告": {
      "main": [{
        "node": "合并消息",
        "port": "input1"
      }]
    },
    "准备正常消息": {
      "main": [{
        "node": "合并消息",
        "port": "input2"
      }]
    },
    "合并消息": {
      "main": [{
        "node": "发送通知",
        "port": "main"
      }]
    }
  },
  "settings": {
    "error_handling": {
      "retry_failed_nodes": true,
      "max_retries": 3,
      "retry_delay": 60
    },
    "execution": {
      "timeout": 300,
      "save_execution_data": true
    }
  }
}')

# 格式化输出
echo "$RESPONSE" | jq '.'

# 提取 workflow ID
WORKFLOW_ID=$(echo "$RESPONSE" | jq -r '.workflow.id // empty')

if [ -n "$WORKFLOW_ID" ]; then
    echo ""
    echo "✅ Workflow 创建成功!"
    echo "Workflow ID: $WORKFLOW_ID"
    echo ""
    echo "查看 Workflow 详情："
    echo "curl http://localhost:8002/v1/workflows/$WORKFLOW_ID?user_id=00000000-0000-0000-0000-000000000123"
fi