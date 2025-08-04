#!/bin/bash

echo "🔍 测试带 ID 的 Workflow 创建..."
echo "================================================"

# 创建 workflow - 明确指定节点 ID
RESPONSE=$(curl -s -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试-明确ID版",
    "description": "测试使用明确指定的节点ID",
    "user_id": "00000000-0000-0000-0000-000000000123",
    "nodes": [
      {
        "id": "trigger_1",
        "name": "手动触发器",
        "type": "TRIGGER_NODE",
        "subtype": "TRIGGER_MANUAL",
        "position": {"x": 100, "y": 100}
      },
      {
        "id": "action_1",
        "name": "HTTP请求",
        "type": "ACTION_NODE",
        "subtype": "HTTP_REQUEST",
        "parameters": {
          "url": "https://www.google.com",
          "method": "GET"
        },
        "position": {"x": 300, "y": 100}
      }
    ],
    "connections": {
      "trigger_1": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "action_1",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      }
    },
    "settings": {
      "timeout": 300
    },
    "tags": ["test", "id-based"]
  }')

# 打印结果
echo "$RESPONSE" | jq '.'

# 如果成功，获取并显示连接信息
if echo "$RESPONSE" | jq -e '.success == true' > /dev/null; then
    WORKFLOW_ID=$(echo "$RESPONSE" | jq -r '.workflow.id')
    echo ""
    echo "✅ 创建成功！现在获取 workflow 查看连接信息..."
    echo ""
    
    # 获取 workflow
    GET_RESPONSE=$(curl -s -X GET "http://localhost:8002/v1/workflows/${WORKFLOW_ID}?user_id=00000000-0000-0000-0000-000000000123")
    
    echo "📋 返回的连接信息："
    echo "$GET_RESPONSE" | jq '.workflow.connections'
    
    echo ""
    echo "🔍 节点信息："
    echo "$GET_RESPONSE" | jq '.workflow.nodes[] | {id: .id, name: .name}'
fi