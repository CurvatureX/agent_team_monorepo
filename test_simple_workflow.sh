#!/bin/bash

echo "🔍 创建简单的测试 Workflow..."

# 创建一个最简单的 workflow，只有两个节点和一个连接
curl -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -d '{
    "name": "测试连接",
    "description": "测试 connections 是否正常保存",
    "user_id": "00000000-0000-0000-0000-000000000123",
    "nodes": [
      {
        "id": "node1",
        "name": "节点1",
        "type": "TRIGGER_NODE",
        "subtype": "TRIGGER_MANUAL",
        "position": {"x": 100, "y": 100}
      },
      {
        "id": "node2",
        "name": "节点2",
        "type": "ACTION_NODE",
        "subtype": "HTTP_REQUEST",
        "parameters": {
          "url": "https://example.com",
          "method": "GET"
        },
        "position": {"x": 300, "y": 100}
      }
    ],
    "connections": {
      "节点1": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "节点2",
                "index": 0,
                "type": "MAIN"
              }
            ]
          }
        }
      }
    },
    "settings": {
      "timeout": 300
    },
    "tags": ["test"]
  }' | jq '.'