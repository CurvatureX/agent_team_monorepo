#!/bin/bash

# 测试获取之前创建的旧 workflow
OLD_WORKFLOW_ID="2cff4b71-ba69-49da-9106-f6b4ac6d9d5f"
USER_ID="00000000-0000-0000-0000-000000000123"

echo "🔍 获取旧的 Workflow（简化前创建的）..."
echo "================================================"

curl -s -X GET "http://localhost:8002/v1/workflows/${OLD_WORKFLOW_ID}?user_id=${USER_ID}" | jq '.workflow.connections'