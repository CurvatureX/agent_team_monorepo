#!/bin/bash

echo "=== 创建简单的 Workflow ==="
echo "通过 API Gateway 创建（需要JWT认证）"
echo ""

# 通过 API Gateway 创建
curl -X POST "http://localhost:8000/api/v1/app/workflows" \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsImtpZCI6InZydnZmclVOdi9HUXFRT2oiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL21rcmN6emdqZWR1cnV3eHBhbmJqLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3YmEzNjM0NS1hMmJiLTRlYzktYTAwMS1iYjQ2ZDc5ZDYyOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU0MzE5OTE2LCJpYXQiOjE3NTQzMTYzMTYsImVtYWlsIjoiZGFtaW5nLmx1QHN0YXJtYXRlcy5haSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzU0MzE2MzE2fV0sInNlc3Npb25faWQiOiIyODdjNTY2Yi0wZWMyLTQ1OTYtYjY2Yi03OWJhNzFiMDIzNjQiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.9q51zMXgcpcexkiL2qj2d1ouwn6eONll_kVlddbXszM" \
-H "Content-Type: application/json" \
-d '{
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
      "name": "获取天气",
      "type": "ACTION",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "GET",
        "url": "https://api.openweathermap.org/data/2.5/weather",
        "query_params": "{\"q\": \"Shanghai\", \"units\": \"metric\"}"
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
        "condition": "output.main.temp > 30"
      },
      "position": {
        "x": 500,
        "y": 200
      }
    },
    {
      "name": "高温提醒",
      "type": "ACTION",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "POST",
        "url": "https://webhook.site/test",
        "body": "{\"alert\": \"高温警告！\"}"
      },
      "position": {
        "x": 700,
        "y": 150
      }
    }
  ],
  "connections": {
    "每日触发器": {
      "main": [{
        "node": "获取天气",
        "port": "main"
      }]
    },
    "获取天气": {
      "success": [{
        "node": "检查温度",
        "port": "main"
      }]
    },
    "检查温度": {
      "true": [{
        "node": "高温提醒",
        "port": "main"
      }]
    }
  }
}' | jq '.'
