#!/bin/bash

echo "=== 创建天气预警 Workflow ==="
curl -X POST "http://localhost:8002/v1/workflows" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "00000000-0000-0000-0000-000000000123",
  "name": "Daily Weather Alert System",
  "description": "每天早上8点获取天气信息，根据天气状况发送不同的提醒",
  "nodes": [
    {
      "name": "每日触发器",
      "type": "TRIGGER_NODE",
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
      "type": "ACTION_NODE",
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
      "name": "检查天气",
      "type": "FLOW_NODE",
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
      "name": "高温警告",
      "type": "ACTION_NODE",
      "subtype": "TRANSFORM_DATA",
      "parameters": {
        "transform_script": "return { alert: \"高温警告！温度超过30°C，请注意防暑\" };"
      },
      "position": {
        "x": 700,
        "y": 150
      }
    },
    {
      "name": "正常提醒",
      "type": "ACTION_NODE",
      "subtype": "TRANSFORM_DATA",
      "parameters": {
        "transform_script": "return { alert: \"今日温度适宜，适合外出\" };"
      },
      "position": {
        "x": 700,
        "y": 250
      }
    },
    {
      "name": "合并消息",
      "type": "FLOW_NODE",
      "subtype": "MERGE",
      "parameters": {
        "merge_strategy": "first_complete"
      },
      "position": {
        "x": 900,
        "y": 200
      }
    },
    {
      "name": "发送通知",
      "type": "ACTION_NODE",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "POST",
        "url": "https://api.example.com/notify",
        "headers": "{\"Content-Type\": \"application/json\"}",
        "body": "{\"message\": \"${nodes.合并消息.output.alert}\", \"timestamp\": \"${Date.now()}\"}"
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
        "node": "检查天气",
        "port": "main"
      }]
    },
    "检查天气": {
      "true": [{
        "node": "高温警告",
        "port": "main"
      }],
      "false": [{
        "node": "正常提醒",
        "port": "main"
      }]
    },
    "高温警告": {
      "main": [{
        "node": "合并消息",
        "port": "input1"
      }]
    },
    "正常提醒": {
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
}' | jq '.'