#!/bin/bash
echo "🛑 停止 Workflow Agent Docker 服务..."

docker stop "workflow-redis" "workflow-agent" 2>/dev/null || true
docker rm "workflow-redis" "workflow-agent" 2>/dev/null || true
docker network rm "workflow-network" 2>/dev/null || true

echo "✅ 所有容器已停止并清理完成"
