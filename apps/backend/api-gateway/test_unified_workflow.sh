#!/bin/bash

echo "=== 测试统一格式的 Workflow 创建 ==="
echo "通过 API Gateway 格式创建，但直接发送到 Workflow Engine"
echo ""

# 创建 workflow - 使用 API Gateway 格式，但需要手动转换
curl -X POST "http://localhost:8002/v1/workflows" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "00000000-0000-0000-0000-000000000123",
  "name": "Weather Check Workflow (Unified)",
  "description": "定时检查天气并发送通知 - 使用统一格式",
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
      "true": [{"node": "高温通知", "port": "main"}]
    }
  },
  "settings": {
    "error_handling": {
      "retry_failed_nodes": true,
      "max_retries": 3
    },
    "execution": {
      "timeout": 300,
      "save_execution_data": true
    }
  }
}' | jq '.'