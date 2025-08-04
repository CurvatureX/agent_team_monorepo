#!/bin/bash

# 查询指定的 workflow
WORKFLOW_ID="2cff4b71-ba69-49da-9106-f6b4ac6d9d5f"
USER_ID="00000000-0000-0000-0000-000000000123"

echo "🔍 查询 Workflow 详情..."
echo "================================================"
echo "📋 Workflow ID: $WORKFLOW_ID"
echo ""

# GET 请求查询 workflow
curl -X GET "http://localhost:8002/v1/workflows/${WORKFLOW_ID}?user_id=${USER_ID}" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\n" \
  | python -m json.tool

echo ""
echo "✅ 查询完成"