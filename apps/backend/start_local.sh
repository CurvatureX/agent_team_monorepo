#!/bin/bash

# 本地启动脚本 - workflow_agent FastAPI 服务 + API Gateway
# 启动顺序：workflow_agent (8001) -> API Gateway (8000)

set -e

echo "🚀 启动 workflow_agent 和 API Gateway 服务"

# 检查端口是否被占用
check_port() {
    local port=$1
    local service=$2
    if lsof -i :$port >/dev/null 2>&1; then
        echo "❌ 端口 $port 被占用，请先停止占用 $port 端口的进程"
        echo "可以运行: lsof -ti :$port | xargs kill -9"
        exit 1
    fi
}

echo "🔍 检查端口占用情况..."
check_port 8001 "workflow_agent"
check_port 8000 "api-gateway"

# 设置环境变量
export PYTHONPATH="$(pwd)"
export DEBUG=true
export LOG_LEVEL=DEBUG

# workflow_agent 必需的环境变量
export WORKFLOW_AGENT_HTTP_PORT=8001
export SUPABASE_URL=${SUPABASE_URL:-"https://your-project.supabase.co"}
export SUPABASE_SECRET_KEY=${SUPABASE_SECRET_KEY:-"your-secret-key"}
export OPENAI_API_KEY=${OPENAI_API_KEY:-"your-openai-key"} 
export ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-"your-anthropic-key"}

# API Gateway 环境变量
export WORKFLOW_AGENT_HOST=localhost
export WORKFLOW_AGENT_HTTP_PORT=8001
export USE_HTTP_CLIENT=true

echo "📝 环境变量设置完成"
echo "   - PYTHONPATH: $PYTHONPATH"
echo "   - workflow_agent 端口: 8001"
echo "   - API Gateway 端口: 8000"

# 创建日志目录
mkdir -p logs

# 启动 workflow_agent FastAPI 服务器
echo "🤖 启动 workflow_agent FastAPI 服务器 (端口 8001)..."
cd workflow_agent
python main_fastapi.py > ../logs/workflow_agent.log 2>&1 &
WORKFLOW_AGENT_PID=$!
echo "   - workflow_agent PID: $WORKFLOW_AGENT_PID"
cd ..

# 等待 workflow_agent 启动
echo "⏳ 等待 workflow_agent 启动..."
sleep 3

# 检查 workflow_agent 是否启动成功
if ! curl -f http://localhost:8001/health >/dev/null 2>&1; then
    echo "❌ workflow_agent 启动失败，检查日志: logs/workflow_agent.log"
    kill $WORKFLOW_AGENT_PID 2>/dev/null || true
    exit 1
fi
echo "✅ workflow_agent 启动成功 (http://localhost:8001)"

# 启动 API Gateway
echo "🌐 启动 API Gateway (端口 8000)..."
cd api-gateway
python -m app.main > ../logs/api_gateway.log 2>&1 &
API_GATEWAY_PID=$!
echo "   - API Gateway PID: $API_GATEWAY_PID"
cd ..

# 等待 API Gateway 启动
echo "⏳ 等待 API Gateway 启动..."
sleep 3

# 检查 API Gateway 是否启动成功
if ! curl -f http://localhost:8000/api/v1/public/health >/dev/null 2>&1; then
    echo "❌ API Gateway 启动失败，检查日志: logs/api_gateway.log"
    kill $WORKFLOW_AGENT_PID $API_GATEWAY_PID 2>/dev/null || true
    exit 1
fi
echo "✅ API Gateway 启动成功 (http://localhost:8000)"

# 创建停止脚本
cat > stop_local.sh << 'EOF'
#!/bin/bash
echo "🛑 停止服务..."
if [ -f pids.txt ]; then
    while read pid name; do
        if kill -0 $pid 2>/dev/null; then
            echo "停止 $name (PID: $pid)"
            kill $pid
        fi
    done < pids.txt
    rm pids.txt
fi

# 确保端口被释放
lsof -ti :8001 | xargs kill -9 2>/dev/null || true
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
echo "✅ 所有服务已停止"
EOF
chmod +x stop_local.sh

# 保存 PID 到文件
echo "$WORKFLOW_AGENT_PID workflow_agent" > pids.txt
echo "$API_GATEWAY_PID api_gateway" >> pids.txt

echo ""
echo "🎉 所有服务启动成功！"
echo ""
echo "📋 服务信息："
echo "   - workflow_agent: http://localhost:8001"
echo "   - workflow_agent 健康检查: http://localhost:8001/health"
echo "   - workflow_agent 文档: http://localhost:8001/docs"
echo "   - API Gateway: http://localhost:8000"
echo "   - API Gateway 健康检查: http://localhost:8000/api/v1/public/health"
echo "   - API Gateway 文档: http://localhost:8000/docs"
echo ""
echo "📄 日志文件："
echo "   - workflow_agent: logs/workflow_agent.log"  
echo "   - API Gateway: logs/api_gateway.log"
echo ""
echo "🛑 停止服务: ./stop_local.sh"
echo ""
echo "按 Ctrl+C 停止脚本（服务将继续在后台运行）"

# 实时显示日志
trap 'echo ""; echo "🛑 脚本停止，服务继续运行。使用 ./stop_local.sh 停止服务"; exit 0' INT

echo "📄 实时日志输出 (Ctrl+C 退出)："
tail -f logs/workflow_agent.log logs/api_gateway.log