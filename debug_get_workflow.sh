#!/bin/bash

# 获取最新创建的 workflow ID
WORKFLOW_ID="aeaa9ffd-969c-42fe-b3c4-51d7ed656632"
USER_ID="00000000-0000-0000-0000-000000000123"

echo "🔍 查询刚创建的 Workflow..."
echo "================================================"

# 查询 workflow
echo "📡 GET 请求结果："
curl -s -X GET "http://localhost:8002/v1/workflows/${WORKFLOW_ID}?user_id=${USER_ID}" | jq '.workflow.connections'

echo ""
echo "================================================"
echo "🔍 完整的 workflow 数据："
curl -s -X GET "http://localhost:8002/v1/workflows/${WORKFLOW_ID}?user_id=${USER_ID}" | jq '.'