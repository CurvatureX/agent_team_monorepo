#!/bin/bash

# 1. 通过 API Gateway 创建 workflow (需要认证)
echo "=== 通过 API Gateway 创建 Workflow ==="
curl -X POST "http://localhost:8000/api/v1/app/workflows" \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsImtpZCI6InZydnZmclVOdi9HUXFRT2oiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL21rcmN6emdqZWR1cnV3eHBhbmJqLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3YmEzNjM0NS1hMmJiLTRlYzktYTAwMS1iYjQ2ZDc5ZDYyOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU0MzE5OTE2LCJpYXQiOjE3NTQzMTYzMTYsImVtYWlsIjoiZGFtaW5nLmx1QHN0YXJtYXRlcy5haSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzU0MzE2MzE2fV0sInNlc3Npb25faWQiOiIyODdjNTY2Yi0wZWMyLTQ1OTYtYjY2Yi03OWJhNzFiMDIzNjQiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.9q51zMXgcpcexkiL2qj2d1ouwn6eONll_kVlddbXszM" \
-H "Content-Type: application/json" \
-d @daily_weather_workflow.json

echo -e "\n\n=== 直接调用 Workflow Engine 创建 Workflow ==="
# 2. 直接调用 workflow-engine (需要添加 user_id)
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
      "position": { "x": 100, "y": 100 }
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
          "appid": "${WEATHER_API_KEY}",
          "units": "metric"
        },
        "headers": {
          "Accept": "application/json"
        }
      },
      "position": { "x": 300, "y": 100 }
    },
    {
      "name": "检查天气状况",
      "type": "FLOW_NODE",
      "subtype": "SWITCH",
      "parameters": {
        "switch_value": "${fetch_weather.output.weather[0].main}",
        "cases": [
          {
            "case": "Rain",
            "output_port": "rain"
          },
          {
            "case": "Clear",
            "output_port": "clear"
          },
          {
            "case": "Clouds",
            "output_port": "cloudy"
          }
        ],
        "default_output_port": "other"
      },
      "position": { "x": 500, "y": 100 }
    },
    {
      "name": "雨天提醒",
      "type": "ACTION_NODE",
      "subtype": "TRANSFORM_DATA",
      "parameters": {
        "transform_script": "return { message: `今天${input.fetch_weather.output.name}有雨，记得带伞！当前温度：${input.fetch_weather.output.main.temp}°C`, weather_type: \"rainy\" };"
      },
      "position": { "x": 700, "y": 50 }
    },
    {
      "name": "晴天提醒",
      "type": "ACTION_NODE",
      "subtype": "TRANSFORM_DATA",
      "parameters": {
        "transform_script": "return { message: `今天${input.fetch_weather.output.name}天气晴朗！当前温度：${input.fetch_weather.output.main.temp}°C，适合户外活动`, weather_type: \"sunny\" };"
      },
      "position": { "x": 700, "y": 150 }
    },
    {
      "name": "多云提醒",
      "type": "ACTION_NODE",
      "subtype": "TRANSFORM_DATA",
      "parameters": {
        "transform_script": "return { message: `今天${input.fetch_weather.output.name}多云，当前温度：${input.fetch_weather.output.main.temp}°C`, weather_type: \"cloudy\" };"
      },
      "position": { "x": 700, "y": 250 }
    },
    {
      "name": "其他天气提醒",
      "type": "ACTION_NODE",
      "subtype": "TRANSFORM_DATA",
      "parameters": {
        "transform_script": "return { message: `今天${input.fetch_weather.output.name}天气状况：${input.fetch_weather.output.weather[0].main}，当前温度：${input.fetch_weather.output.main.temp}°C`, weather_type: \"other\" };"
      },
      "position": { "x": 700, "y": 350 }
    },
    {
      "name": "合并提醒信息",
      "type": "FLOW_NODE",
      "subtype": "MERGE",
      "parameters": {
        "merge_strategy": "first_complete"
      },
      "position": { "x": 900, "y": 200 }
    },
    {
      "name": "检查温度",
      "type": "FLOW_NODE",
      "subtype": "IF",
      "parameters": {
        "condition": "${fetch_weather.output.main.temp} < 10 || ${fetch_weather.output.main.temp} > 35"
      },
      "position": { "x": 1100, "y": 200 }
    },
    {
      "name": "添加温度警告",
      "type": "ACTION_NODE",
      "subtype": "TRANSFORM_DATA",
      "parameters": {
        "transform_script": "return { ...input.merge_alerts.output, message: input.merge_alerts.output.message + \" ⚠️ 温度异常，请注意防护！\", has_warning: true };"
      },
      "position": { "x": 1300, "y": 150 }
    },
    {
      "name": "最终合并",
      "type": "FLOW_NODE",
      "subtype": "MERGE",
      "parameters": {
        "merge_strategy": "first_complete"
      },
      "position": { "x": 1500, "y": 200 }
    },
    {
      "name": "发送通知",
      "type": "ACTION_NODE",
      "subtype": "HTTP_REQUEST",
      "parameters": {
        "method": "POST",
        "url": "https://api.example.com/notifications",
        "headers": {
          "Content-Type": "application/json",
          "Authorization": "Bearer ${NOTIFICATION_API_KEY}"
        },
        "body": {
          "channel": "weather_alerts",
          "message": "${final_merge.output.message}",
          "priority": "${final_merge.output.has_warning ? \"high\" : \"normal\"}",
          "metadata": {
            "weather_type": "${final_merge.output.weather_type}",
            "temperature": "${fetch_weather.output.main.temp}",
            "city": "${fetch_weather.output.name}"
          }
        }
      },
      "position": { "x": 1700, "y": 200 }
    }
  ],
  "connections": {
    "每日触发器": {
      "main": [
        {
          "node": "获取天气信息",
          "port": "main"
        }
      ]
    },
    "获取天气信息": {
      "success": [
        {
          "node": "检查天气状况",
          "port": "main"
        }
      ]
    },
    "检查天气状况": {
      "rain": [
        {
          "node": "雨天提醒",
          "port": "main"
        }
      ],
      "clear": [
        {
          "node": "晴天提醒",
          "port": "main"
        }
      ],
      "cloudy": [
        {
          "node": "多云提醒",
          "port": "main"
        }
      ],
      "other": [
        {
          "node": "其他天气提醒",
          "port": "main"
        }
      ]
    },
    "雨天提醒": {
      "main": [
        {
          "node": "合并提醒信息",
          "port": "input1"
        }
      ]
    },
    "晴天提醒": {
      "main": [
        {
          "node": "合并提醒信息",
          "port": "input2"
        }
      ]
    },
    "多云提醒": {
      "main": [
        {
          "node": "合并提醒信息",
          "port": "input3"
        }
      ]
    },
    "其他天气提醒": {
      "main": [
        {
          "node": "合并提醒信息",
          "port": "input4"
        }
      ]
    },
    "合并提醒信息": {
      "main": [
        {
          "node": "检查温度",
          "port": "main"
        }
      ]
    },
    "检查温度": {
      "true": [
        {
          "node": "添加温度警告",
          "port": "main"
        }
      ],
      "false": [
        {
          "node": "最终合并",
          "port": "input2"
        }
      ]
    },
    "添加温度警告": {
      "main": [
        {
          "node": "最终合并",
          "port": "input1"
        }
      ]
    },
    "最终合并": {
      "main": [
        {
          "node": "发送通知",
          "port": "main"
        }
      ]
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
  },
  "static_data": {
    "WEATHER_API_KEY": "your-openweather-api-key",
    "NOTIFICATION_API_KEY": "your-notification-api-key"
  }
}'