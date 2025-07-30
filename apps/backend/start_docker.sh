#!/bin/bash

# Docker 启动脚本 - workflow_agent FastAPI + API Gateway
# 使用 Docker Compose 启动完整的后端服务栈

set -e

echo "🐳 启动 Backend Services (Docker)"

# 检查是否存在 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，正在从模板创建..."
    cp .env.example .env
    echo "📝 请编辑 .env 文件，填入正确的 API Keys 和 Supabase 配置"
    echo "   特别是以下必需变量："
    echo "   - OPENAI_API_KEY"
    echo "   - ANTHROPIC_API_KEY" 
    echo "   - SUPABASE_URL"
    echo "   - SUPABASE_SECRET_KEY"
    echo "   - SUPABASE_ANON_KEY"
    echo ""
    read -p "按回车键继续启动 (或 Ctrl+C 取消): "
fi

# 检查 Docker 是否运行
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi

# 检查 Docker Compose 版本
if ! docker-compose --version >/dev/null 2>&1; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi

echo "🔧 检查环境配置..."
source .env 2>/dev/null || true

# 验证必需的环境变量
missing_vars=()
[ -z "$OPENAI_API_KEY" ] && missing_vars+=("OPENAI_API_KEY")
[ -z "$SUPABASE_URL" ] && missing_vars+=("SUPABASE_URL")
[ -z "$SUPABASE_SECRET_KEY" ] && missing_vars+=("SUPABASE_SECRET_KEY")

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "⚠️  警告：以下环境变量未设置："
    printf "   - %s\n" "${missing_vars[@]}"
    echo "   服务可能无法正常工作，请检查 .env 文件"
    echo ""
fi

# 停止可能存在的旧容器
echo "🛑 停止旧容器..."
docker-compose down --remove-orphans 2>/dev/null || true

# 构建并启动服务
echo "🏗️  构建 Docker 镜像..."
docker-compose build --no-cache

echo "🚀 启动服务栈..."
echo "   - Redis (缓存)"
echo "   - workflow-agent (FastAPI 8001)"
echo "   - api-gateway (FastAPI 8000)"

docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务健康状态
echo "🔍 检查服务状态..."

check_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "   检查 $service: "
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" >/dev/null 2>&1; then
            echo "✅ 健康"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo " ❌ 超时"
    return 1
}

# 检查各服务
services_ok=true

if ! check_service "Redis" "redis://localhost:6379"; then
    echo "   ℹ️  Redis 检查跳过 (需要 redis-cli)"
fi

if ! check_service "workflow-agent" "http://localhost:8001/health"; then
    echo "   查看日志: docker-compose logs workflow-agent"
    services_ok=false
fi

if ! check_service "api-gateway" "http://localhost:8000/api/v1/public/health"; then
    echo "   查看日志: docker-compose logs api-gateway"
    services_ok=false
fi

if [ "$services_ok" = true ]; then
    echo ""
    echo "🎉 所有服务启动成功！"
else
    echo ""
    echo "⚠️  部分服务启动失败，请检查日志"
fi

echo ""
echo "📋 服务信息："
echo "   - workflow-agent (FastAPI):  http://localhost:8001"
echo "   - workflow-agent 文档:       http://localhost:8001/docs"
echo "   - workflow-agent 健康检查:   http://localhost:8001/health"
echo "   - API Gateway:               http://localhost:8000"  
echo "   - API Gateway 文档:          http://localhost:8000/docs"
echo "   - API Gateway 健康检查:      http://localhost:8000/api/v1/public/health"
echo "   - Redis Commander:           http://localhost:8081 (admin/admin123)"
echo ""
echo "📄 日志命令："
echo "   - 查看所有日志:     docker-compose logs -f"
echo "   - workflow-agent:   docker-compose logs -f workflow-agent"
echo "   - api-gateway:      docker-compose logs -f api-gateway"
echo "   - Redis:            docker-compose logs -f redis"
echo ""
echo "🛑 停止服务:"
echo "   - 停止所有服务:     docker-compose down"
echo "   - 停止并删除数据:   docker-compose down -v"
echo "   - 重新构建:         docker-compose up --build -d"
echo ""

# 显示容器状态
echo "🐳 容器状态:"
docker-compose ps

echo ""
echo "✨ 服务已启动，可以开始测试 ProcessConversation 接口！"
echo ""

# 提供快捷测试命令
cat << 'EOF'
💡 快速测试命令:

# 测试 workflow-agent 健康检查
curl http://localhost:8001/health

# 测试 API Gateway 健康检查  
curl http://localhost:8000/api/v1/public/health

# 测试 ProcessConversation 接口 (需要认证 token)
curl -X POST "http://localhost:8001/process-conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_123",
    "user_id": "test_user",
    "access_token": "test_token",
    "user_message": "帮我创建一个处理邮件的工作流"
  }'

EOF