#!/bin/bash

# Workflow Agent Docker 启动脚本
# 单独启动 workflow_agent FastAPI 服务

set -e

echo "🤖 Workflow Agent Docker 启动脚本"
echo "=================================="

# 获取脚本所在目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
WORKFLOW_AGENT_DIR="$SCRIPT_DIR"

echo "📁 目录信息:"
echo "   - 脚本目录: $SCRIPT_DIR"
echo "   - Backend目录: $BACKEND_DIR"
echo "   - workflow_agent目录: $WORKFLOW_AGENT_DIR"

# 检查是否在正确的目录
if [ ! -f "$WORKFLOW_AGENT_DIR/main_fastapi.py" ]; then
    echo "❌ 错误: 未找到 main_fastapi.py 文件"
    echo "   请确保在 workflow_agent 目录下运行此脚本"
    exit 1
fi

# 检查是否存在 .env 文件
ENV_FILE="$BACKEND_DIR/.env"
LOCAL_ENV_FILE="$WORKFLOW_AGENT_DIR/.env"

if [ -f "$LOCAL_ENV_FILE" ]; then
    ENV_FILE="$LOCAL_ENV_FILE"
    echo "📝 使用本地环境文件: $LOCAL_ENV_FILE"
elif [ -f "$ENV_FILE" ]; then
    echo "📝 使用Backend环境文件: $ENV_FILE"
else
    echo "⚠️  未找到 .env 文件，正在创建模板文件..."
    cat > "$LOCAL_ENV_FILE" << 'EOF'
# Workflow Agent 环境变量配置

# AI API Keys (必需)
OPENAI_API_KEY=sk-your-openai-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# Supabase 配置 (必需)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SECRET_KEY=your-service-role-secret-key

# 服务配置
FASTAPI_PORT=8001
DEBUG=true
LOG_LEVEL=DEBUG

# RAG 配置
EMBEDDING_MODEL=text-embedding-ada-002
RAG_SIMILARITY_THRESHOLD=0.3
RAG_MAX_RESULTS=5

# AI 模型配置
DEFAULT_MODEL_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4
EOF
    
    ENV_FILE="$LOCAL_ENV_FILE"
    echo "✅ 已创建环境变量模板: $LOCAL_ENV_FILE"
    echo ""
    echo "⚠️  请编辑 $LOCAL_ENV_FILE 文件，填入正确的 API Keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - SUPABASE_URL"
    echo "   - SUPABASE_SECRET_KEY"
    echo ""
    read -p "按回车键继续 (或 Ctrl+C 取消): "
fi

# 读取环境变量
echo "🔧 加载环境变量..."
if [ -f "$ENV_FILE" ]; then
    # 导出环境变量供 docker run 使用
    set -a  # 自动导出变量
    source "$ENV_FILE"
    set +a
    echo "✅ 环境变量加载完成"
else
    echo "❌ 未找到环境变量文件"
    exit 1
fi

# 验证必需的环境变量
echo "🔍 验证必需的环境变量..."
missing_vars=()

[ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-openai-api-key-here" ] && missing_vars+=("OPENAI_API_KEY")
[ -z "$SUPABASE_URL" ] || [ "$SUPABASE_URL" = "https://your-project-id.supabase.co" ] && missing_vars+=("SUPABASE_URL")
[ -z "$SUPABASE_SECRET_KEY" ] || [ "$SUPABASE_SECRET_KEY" = "your-service-role-secret-key" ] && missing_vars+=("SUPABASE_SECRET_KEY")

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "❌ 以下环境变量未正确设置:"
    printf "   - %s\n" "${missing_vars[@]}"
    echo ""
    echo "请编辑 $ENV_FILE 文件并重新运行脚本"
    exit 1
fi

echo "✅ 环境变量验证通过"

# 检查 Docker 是否运行
echo "🐳 检查 Docker 环境..."
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi
echo "✅ Docker 运行正常"

# 设置容器和镜像名称
REDIS_CONTAINER_NAME="workflow-redis"
AGENT_CONTAINER_NAME="workflow-agent"
AGENT_IMAGE_NAME="workflow-agent-fastapi"
NETWORK_NAME="workflow-network"

# 检查端口占用
echo "🔍 检查端口占用情况..."
check_port() {
    local port=$1
    local service=$2
    if lsof -i :$port >/dev/null 2>&1; then
        echo "⚠️  端口 $port 被占用 ($service)"
        
        # 检查是否是我们的容器占用
        if docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -q ":$port->"; then
            echo "   由现有 Docker 容器占用，将停止相关容器"
            # 找到占用端口的容器并停止
            local containers=$(docker ps --format "{{.Names}}" --filter "publish=$port")
            if [ ! -z "$containers" ]; then
                echo "   停止占用端口 $port 的容器: $containers"
                docker stop $containers 2>/dev/null || true
                docker rm $containers 2>/dev/null || true
            fi
        else
            echo "   端口被其他进程占用，显示占用进程信息:"
            lsof -i :$port
            echo ""
            echo "   请手动停止占用端口的进程，或者修改端口配置"
            echo "   停止进程命令: kill -9 <PID>"
            read -p "   按回车键继续 (脚本将尝试强制启动) 或 Ctrl+C 取消: "
        fi
        return 1
    fi
    return 0
}

check_port 8001 "workflow_agent"

# 清理现有容器
echo "🧹 清理现有容器..."
docker stop "$REDIS_CONTAINER_NAME" "$AGENT_CONTAINER_NAME" 2>/dev/null || true
docker rm "$REDIS_CONTAINER_NAME" "$AGENT_CONTAINER_NAME" 2>/dev/null || true

# 强制清理可能占用端口的容器
echo "🔧 强制清理端口占用的容器..."
docker ps -a --filter "publish=8001" --format "{{.Names}}" | xargs -r docker rm -f 2>/dev/null || true

# 创建 Docker 网络
echo "🌐 创建 Docker 网络..."
docker network create "$NETWORK_NAME" 2>/dev/null || echo "网络已存在"



# 构建 workflow_agent 镜像
echo "🏗️  构建 workflow_agent 镜像..."
cd "$BACKEND_DIR"  # 切换到 backend 目录以访问 shared 目录

docker build \
    -f workflow_agent/Dockerfile \
    -t "$AGENT_IMAGE_NAME" \
    --build-arg PYTHON_VERSION=3.11 \
    .

if [ $? -ne 0 ]; then
    echo "❌ 镜像构建失败"
    exit 1
fi
echo "✅ 镜像构建成功"

# 启动 workflow_agent 容器
echo "🤖 启动 workflow_agent 容器..."

# 构建环境变量参数 - 修复环境变量传递问题
ENV_ARGS=""
if [ -f "$ENV_FILE" ]; then
    echo "📝 从 $ENV_FILE 加载环境变量..."
    while IFS='=' read -r key value; do
        # 跳过注释和空行
        [[ $key =~ ^#.*$ ]] && continue
        [[ -z $key ]] && continue
        
        # 移除值中的引号
        value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
        
        # 确保值不为空且不是模板值
        if [ ! -z "$value" ] && [ "$value" != "sk-your-openai-api-key-here" ] && [ "$value" != "https://your-project-id.supabase.co" ] && [ "$value" != "your-service-role-secret-key" ]; then
            # 对于布尔值和 API Keys，不要加引号
            if [ "$key" = "DEBUG" ] || [ "$key" = "true" ] || [ "$key" = "false" ] || [ "$key" = "OPENAI_API_KEY" ] || [ "$key" = "ANTHROPIC_API_KEY" ]; then
                ENV_ARGS="$ENV_ARGS -e $key=$value"
            else
                ENV_ARGS="$ENV_ARGS -e $key=\"$value\""
            fi
            echo "   ✅ $key"
        else
            echo "   ⚠️  跳过 $key (未设置或为模板值)"
        fi
    done < "$ENV_FILE"
else
    echo "❌ 环境变量文件不存在: $ENV_FILE"
    exit 1
fi

# 添加默认环境变量
ENV_ARGS="$ENV_ARGS -e FASTAPI_PORT=8001"
ENV_ARGS="$ENV_ARGS -e PYTHONUNBUFFERED=1"
ENV_ARGS="$ENV_ARGS -e PYTHONPATH=/app"

echo "🔧 环境变量参数: $ENV_ARGS"

docker run -d \
    --name "$AGENT_CONTAINER_NAME" \
    --network "$NETWORK_NAME" \
    -p 8001:8001 \
    $ENV_ARGS \
    "$AGENT_IMAGE_NAME"

if [ $? -ne 0 ]; then
    echo "❌ workflow_agent 容器启动失败"
    exit 1
fi

# 等待服务启动
echo "⏳ 等待 workflow_agent 启动..."
sleep 10

# 检查服务健康状态
echo "🔍 检查服务健康状态..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
        echo "✅ workflow_agent 健康检查通过"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ workflow_agent 健康检查超时"
        echo "查看容器日志:"
        docker logs "$AGENT_CONTAINER_NAME"
        exit 1
    fi
    
    echo -n "."
    sleep 2
    attempt=$((attempt + 1))
done

echo ""
echo "🎉 Workflow Agent 启动成功！"
echo ""
echo "📋 服务信息:"
echo "   - workflow_agent:     http://localhost:8001"
echo "   - API 文档:           http://localhost:8001/docs"
echo "   - 健康检查:           http://localhost:8001/health"
echo "   - ProcessConversation: POST http://localhost:8001/process-conversation"
echo ""
echo "📄 容器信息:"
echo "   - workflow_agent 容器: $AGENT_CONTAINER_NAME"
echo "   - Redis 容器:          $REDIS_CONTAINER_NAME"
echo "   - Docker 网络:         $NETWORK_NAME"
echo ""
echo "📝 管理命令:"
echo "   - 查看日志:       docker logs -f $AGENT_CONTAINER_NAME"
echo "   - 停止服务:       docker stop $AGENT_CONTAINER_NAME $REDIS_CONTAINER_NAME"
echo "   - 删除容器:       docker rm $AGENT_CONTAINER_NAME $REDIS_CONTAINER_NAME"
echo "   - 删除网络:       docker network rm $NETWORK_NAME"
echo "   - 完全清理:       $SCRIPT_DIR/stop_docker.sh"
echo ""

# 创建停止脚本
cat > "$SCRIPT_DIR/stop_docker.sh" << EOF
#!/bin/bash
echo "🛑 停止 Workflow Agent Docker 服务..."

docker stop "$REDIS_CONTAINER_NAME" "$AGENT_CONTAINER_NAME" 2>/dev/null || true
docker rm "$REDIS_CONTAINER_NAME" "$AGENT_CONTAINER_NAME" 2>/dev/null || true
docker network rm "$NETWORK_NAME" 2>/dev/null || true

echo "✅ 所有容器已停止并清理完成"
EOF

chmod +x "$SCRIPT_DIR/stop_docker.sh"

echo "💡 快速测试命令:"
echo ""
echo "# 健康检查"
echo "curl http://localhost:8001/health"
echo ""
echo "# 测试 ProcessConversation 接口"
echo "curl -X POST \"http://localhost:8001/process-conversation\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{"
echo "    \"session_id\": \"test_123\","
echo "    \"user_id\": \"user_123\","
echo "    \"access_token\": \"test_token\","
echo "    \"user_message\": \"帮我创建一个处理邮件的工作流\""
echo "  }'"
echo ""
echo "🎯 服务已启动完成，可以开始使用！"