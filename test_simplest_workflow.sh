#!/bin/bash

echo "🚀 创建最简单的 Workflow（只有两个节点）..."
echo "================================================"

# 最简单的 workflow - 只有触发器和一个动作
RESPONSE=$(curl -s -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "最简单测试",
    "description": "只有两个节点的最简单测试",
    "user_id": "00000000-0000-0000-0000-000000000123",
    "nodes": [
      {
        "name": "开始",
        "type": "TRIGGER_NODE",
        "subtype": "TRIGGER_MANUAL",
        "position": {"x": 100, "y": 100}
      },
      {
        "name": "结束",
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
      "开始": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "结束",
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
    "tags": ["test", "simple"]
  }')

# 打印结果
echo "$RESPONSE" | jq '.'

# 分析结果
if echo "$RESPONSE" | jq -e '.success == true' > /dev/null 2>&1; then
    echo ""
    echo "✅ 成功！生成的信息："
    echo "$RESPONSE" | jq '{
      nodes: [.workflow.nodes[] | {name, id}],
      connections: .workflow.connections
    }'
else
    echo ""
    echo "❌ 失败"
fi