#!/bin/bash

echo "=== 创建天气检查 Workflow (修正版) ==="
echo "使用与数据库一致的 subtype 格式"
echo ""

# 创建 workflow - 使用正确的 subtype
curl -X POST "http://localhost:8002/v1/workflows" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "00000000-0000-0000-0000-000000000123",
  "name": "Weather Check Workflow",
  "description": "定时检查天气并发送通知",
  "nodes": [
    {
      "name": "定时触发",
      "type": "TRIGGER_NODE",
      "subtype": "TRIGGER_CRON",
      "parameters": {
        "cron_expression": "0 8 * * *",
        "timezone": "Asia/Shanghai"
      },
      "position": {"x": 100, "y": 200}
    },
    {
      "name": "获取天气",
      "type": "ACTION_NODE",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "GET",
        "url": "https://api.openweathermap.org/data/2.5/weather",
        "query_params": "{\"q\": \"Shanghai\", \"units\": \"metric\", \"appid\": \"YOUR_API_KEY\"}"
      },
      "position": {"x": 300, "y": 200}
    },
    {
      "name": "条件判断",
      "type": "FLOW_NODE",
      "subtype": "IF",
      "parameters": {
        "condition": "output.main.temp > 30"
      },
      "position": {"x": 500, "y": 200}
    },
    {
      "name": "高温通知",
      "type": "ACTION_NODE",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "POST",
        "url": "https://webhook.site/your-webhook-url",
        "headers": "{\"Content-Type\": \"application/json\"}",
        "body": "{\"alert\": \"高温警告！当前温度超过30度\"}"
      },
      "position": {"x": 700, "y": 150}
    },
    {
      "name": "正常通知",
      "type": "ACTION_NODE",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "POST",
        "url": "https://webhook.site/your-webhook-url",
        "headers": "{\"Content-Type\": \"application/json\"}",
        "body": "{\"info\": \"温度正常\"}"
      },
      "position": {"x": 700, "y": 250}
    }
  ],
  "connections": {
    "定时触发": {
      "main": [{"node": "获取天气", "port": "main"}]
    },
    "获取天气": {
      "success": [{"node": "条件判断", "port": "main"}]
    },
    "条件判断": {
      "true": [{"node": "高温通知", "port": "main"}],
      "false": [{"node": "正常通知", "port": "main"}]
    }
  }
}' | jq '.'