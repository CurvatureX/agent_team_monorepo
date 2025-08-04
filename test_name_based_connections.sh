#!/bin/bash

echo "🚀 测试基于名称的连接引用（系统自动生成ID并映射）..."
echo "================================================"

# 创建 workflow - 不指定节点 ID，使用名称作为连接引用
RESPONSE=$(curl -s -X POST http://localhost:8002/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试名称连接-自动ID",
    "description": "测试使用节点名称创建连接，系统自动生成ID并映射",
    "user_id": "00000000-0000-0000-0000-000000000123",
    "nodes": [
      {
        "name": "手动触发",
        "type": "TRIGGER_NODE",
        "subtype": "TRIGGER_MANUAL",
        "position": {"x": 100, "y": 100}
      },
      {
        "name": "检查网站",
        "type": "ACTION_NODE",
        "subtype": "HTTP_REQUEST",
        "parameters": {
          "url": "https://example.com",
          "method": "GET"
        },
        "position": {"x": 300, "y": 100}
      },
      {
        "name": "判断状态",
        "type": "FLOW_NODE",
        "subtype": "IF",
        "parameters": {
          "condition": "response.status_code == 200"
        },
        "position": {"x": 500, "y": 100}
      }
    ],
    "connections": {
      "手动触发": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "检查网站",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "检查网站": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "判断状态",
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
    "tags": ["test", "name-based", "auto-id"]
  }')

# 打印完整响应以调试
echo "📋 完整响应："
echo "$RESPONSE" | jq '.'

# 如果成功，显示生成的ID和连接映射
if echo "$RESPONSE" | jq -e '.success == true' > /dev/null 2>&1; then
    WORKFLOW_ID=$(echo "$RESPONSE" | jq -r '.workflow.id')
    echo ""
    echo "✅ 创建成功！"
    echo ""
    echo "🔍 生成的节点 ID："
    echo "$RESPONSE" | jq '.workflow.nodes[] | {name: .name, id: .id}'
    echo ""
    echo "📋 连接信息（应该使用生成的ID）："
    echo "$RESPONSE" | jq '.workflow.connections'
    
    # 获取 workflow 验证返回值
    echo ""
    echo "🔄 重新获取 workflow 验证连接是否使用ID："
    GET_RESPONSE=$(curl -s -X GET "http://localhost:8002/v1/workflows/${WORKFLOW_ID}?user_id=00000000-0000-0000-0000-000000000123")
    echo "$GET_RESPONSE" | jq '.workflow.connections'
else
    echo ""
    echo "❌ 创建失败"
    
    # 显示错误详情
    echo ""
    echo "📝 错误详情："
    echo "$RESPONSE" | jq '.detail'
fi