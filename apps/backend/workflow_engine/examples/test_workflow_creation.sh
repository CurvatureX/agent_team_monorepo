#!/bin/bash

# 测试 Workflow 创建的 curl 命令

echo "=== 1. 通过 API Gateway 创建 Workflow (需要JWT认证) ==="
curl -X POST "http://localhost:8000/api/v1/app/workflows" \
-H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
-H "Content-Type: application/json" \
-d '{
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
      }
    },
    {
      "name": "获取天气信息",
      "type": "ACTION_NODE",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "GET",
        "url": "https://api.openweathermap.org/data/2.5/weather",
        "query_params": {
          "q": "Shanghai",
          "appid": "YOUR_API_KEY",
          "units": "metric"
        }
      }
    },
    {
      "name": "检查天气",
      "type": "FLOW_NODE",
      "subtype": "IF",
      "parameters": {
        "condition": "${nodes.获取天气信息.output.main.temp} > 30"
      }
    },
    {
      "name": "高温警告",
      "type": "ACTION_NODE",
      "subtype": "TRANSFORM_DATA",
      "parameters": {
        "transform_script": "return { alert: \"高温警告！温度: \" + input.temp + \"°C\" };"
      }
    },
    {
      "name": "发送通知",
      "type": "ACTION_NODE",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "POST",
        "url": "https://api.example.com/notify",
        "body": {
          "message": "${nodes.高温警告.output.alert}"
        }
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
      }]
    },
    "高温警告": {
      "main": [{
        "node": "发送通知",
        "port": "main"
      }]
    }
  }
}' | jq '.'

echo -e "\n\n=== 2. 直接调用 Workflow Engine 创建 Workflow ==="
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
      }
    },
    {
      "name": "获取天气信息",
      "type": "ACTION_NODE",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "GET",
        "url": "https://api.openweathermap.org/data/2.5/weather",
        "query_params": {
          "q": "Shanghai",
          "appid": "YOUR_API_KEY",
          "units": "metric"
        }
      }
    },
    {
      "name": "检查天气",
      "type": "FLOW_NODE",
      "subtype": "IF",
      "parameters": {
        "condition": "${nodes.获取天气信息.output.main.temp} > 30"
      }
    },
    {
      "name": "高温警告",
      "type": "ACTION_NODE",
      "subtype": "TRANSFORM_DATA",
      "parameters": {
        "transform_script": "return { alert: \"高温警告！温度: \" + input.temp + \"°C\" };"
      }
    },
    {
      "name": "发送通知",
      "type": "ACTION_NODE",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "POST",
        "url": "https://api.example.com/notify",
        "body": {
          "message": "${nodes.高温警告.output.alert}"
        }
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
      }]
    },
    "高温警告": {
      "main": [{
        "node": "发送通知",
        "port": "main"
      }]
    }
  }
}' | jq '.'