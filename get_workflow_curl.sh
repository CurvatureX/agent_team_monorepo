#!/bin/bash

# 查询指定的 workflow
WORKFLOW_ID="2cff4b71-ba69-49da-9106-f6b4ac6d9d5f"
USER_ID="00000000-0000-0000-0000-000000000123"

echo "🔍 查询 Workflow 详情..."
echo "================================================"
echo "📋 Workflow ID: $WORKFLOW_ID"
echo "👤 User ID: $USER_ID"
echo ""
echo "📡 执行 GET 请求..."
echo ""

# 直接的 curl 命令
curl -X GET "http://localhost:8002/v1/workflows/${WORKFLOW_ID}?user_id=${USER_ID}" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\n"

echo ""
echo "================================================"
echo ""
echo "💡 直接使用的 curl 命令："
echo ""
echo "curl -X GET \"http://localhost:8002/v1/workflows/${WORKFLOW_ID}?user_id=${USER_ID}\" \\"
echo "  -H \"Content-Type: application/json\""