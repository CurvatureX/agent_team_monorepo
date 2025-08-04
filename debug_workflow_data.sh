#!/bin/bash

# 调试查看 workflow 数据在数据库中的实际存储情况

WORKFLOW_ID="2cff4b71-ba69-49da-9106-f6b4ac6d9d5f"

echo "🔍 调试 Workflow 数据存储问题..."
echo "================================================"
echo ""

# 直接查看原始 JSON 响应，格式化输出
echo "📡 获取 Workflow 原始数据..."
curl -s -X GET "http://localhost:8002/v1/workflows/${WORKFLOW_ID}?user_id=00000000-0000-0000-0000-000000000123" | jq '.'

echo ""
echo "================================================"
echo "🔍 检查 connections 字段..."
curl -s -X GET "http://localhost:8002/v1/workflows/${WORKFLOW_ID}?user_id=00000000-0000-0000-0000-000000000123" | jq '.workflow.connections'

echo ""
echo "================================================"
echo "✅ 调试完成"