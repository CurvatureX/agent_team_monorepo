#!/bin/bash

# Workflow Agent 快速启动脚本 (最小化版本)
# 适用于已经配置好环境变量的情况

set -e

echo "🚀 Workflow Agent 快速启动"

# 检查环境变量
if [ -z "$OPENAI_API_KEY" ] || [ -z "$SUPABASE_URL" ]; then
    echo "❌ 请先设置环境变量或运行完整脚本: ./start_docker.sh"
    exit 1
fi

# 清理旧容器
docker stop workflow-redis workflow-agent 2>/dev/null || true
docker rm workflow-redis workflow-agent 2>/dev/null || true

# 启动 Redis
echo "🔴 启动 Redis..."
docker run -d --name workflow-redis -p 6379:6379 redis:7-alpine

# 构建并启动 workflow_agent
echo "🤖 构建并启动 workflow_agent..."
cd ..  # 切换到 backend 目录

docker build -f workflow_agent/Dockerfile -t workflow-agent-fastapi .

docker run -d \
    --name workflow-agent \
    -p 8001:8001 \
    --link workflow-redis:redis \
    -e OPENAI_API_KEY="$OPENAI_API_KEY" \
    -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    -e SUPABASE_URL="$SUPABASE_URL" \
    -e SUPABASE_SECRET_KEY="$SUPABASE_SECRET_KEY" \
    -e REDIS_URL="redis://redis:6379/0" \
    -e FASTAPI_PORT="8001" \
    -e DEBUG="true" \
    workflow-agent-fastapi

echo "⏳ 等待启动..."
sleep 8

# 检查健康状态
if curl -f -s http://localhost:8001/health >/dev/null; then
    echo "✅ 启动成功! http://localhost:8001"
else
    echo "❌ 启动失败，查看日志:"
    docker logs workflow-agent
fi