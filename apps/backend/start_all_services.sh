#!/bin/bash

# 启动所有后端服务的脚本
# 用于生产环境集成测试

echo "🚀 启动所有后端服务进行集成测试"
echo "======================================"

# 加载.env文件
if [ -f ".env" ]; then
    echo "📄 加载.env文件..."
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ .env文件加载完成"
else
    echo "⚠️ 未找到.env文件，请创建.env文件并配置环境变量"
    echo "参考env.example文件进行配置"
fi

# 检查环境变量
echo "🔍 检查环境变量..."
required_vars=("SUPABASE_URL" "SUPABASE_SECRET_KEY" "SUPABASE_ANON_KEY" "OPENAI_API_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ 缺少环境变量: ${missing_vars[*]}"
    echo "请设置所有必需的环境变量"
    exit 1
fi

echo "✅ 环境变量检查通过"

# 创建日志目录并清理旧日志
mkdir -p logs
echo "📝 准备日志文件..."

# 如果存在旧日志，备份到带时间戳的目录
if [ -f "logs/workflow_agent.log" ] || [ -f "logs/api_gateway.log" ]; then
    backup_dir="logs/backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    [ -f "logs/workflow_agent.log" ] && mv "logs/workflow_agent.log" "$backup_dir/"
    [ -f "logs/api_gateway.log" ] && mv "logs/api_gateway.log" "$backup_dir/"
    echo "📦 旧日志已备份到: $backup_dir"
fi

# 创建新的日志文件
touch logs/workflow_agent.log logs/api_gateway.log
echo "✅ 日志文件准备完成"

# 函数：启动服务
start_service() {
    local service_name=$1
    local service_dir=$2
    local start_command=$3
    local port=$4
    
    echo "🚀 启动 $service_name..."
    
    cd "$service_dir" || exit 1
    
    # 检查端口是否被占用
    if lsof -i :$port >/dev/null 2>&1; then
        echo "⚠️ 端口 $port 已被占用，尝试停止现有进程..."
        pkill -f ":$port" || true
        sleep 2
    fi
    
    # 启动服务并记录所有输出到日志文件
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 启动 $service_name 服务..." >> "../logs/${service_name}.log"
    (eval "$start_command" 2>&1 | while IFS= read -r line; do
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $line"
    done) >> "../logs/${service_name}.log" &
    local pid=$!
    echo "✅ $service_name 已启动 (PID: $pid, 端口: $port)"
    echo "$pid" > "../logs/${service_name}.pid"
    
    # 等待服务启动
    echo "⏳ 等待 $service_name 启动..."
    for i in {1..30}; do
        if [ "$service_name" = "workflow_agent" ]; then
            # gRPC服务使用nc检查端口
            if nc -z localhost $port >/dev/null 2>&1; then
                echo "✅ $service_name 健康检查通过"
                break
            fi
        else
            # HTTP服务使用curl检查健康端点
            if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
                echo "✅ $service_name 健康检查通过"
                break
            fi
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            echo "❌ $service_name 启动超时"
            return 1
        fi
    done
    
    cd - >/dev/null
}

# 启动 workflow_agent (gRPC服务)
echo ""
echo "=== 启动 workflow_agent ==="
# 先安装依赖
echo "📦 安装workflow_agent依赖..."
cd workflow_agent
if command -v uv &> /dev/null; then
    uv sync --quiet || true
else
    pip install -e . --quiet || true
fi
cd ..

start_service "workflow_agent" "workflow_agent" "python main_fastapi.py" "8001"

# 等待一下确保gRPC服务完全启动
sleep 3

# 启动 API Gateway
echo ""
echo "=== 启动 API Gateway ==="
# 先安装依赖
echo "📦 安装API Gateway依赖..."
cd api-gateway
if command -v uv &> /dev/null; then
    uv sync --quiet || true
    uv add "pydantic[email]" --quiet || true
else
    pip install -e . --quiet || true
    pip install "pydantic[email]" --quiet || true
fi
cd ..

start_service "api_gateway" "api-gateway" "uvicorn app.main:app --host 0.0.0.0 --port 8000" "8000"

echo ""
echo "🎉 所有服务启动完成！"
echo ""
echo "📋 服务状态:"
echo "  🤖 workflow_agent (gRPC): localhost:50051"
echo "  🌐 API Gateway (HTTP): http://localhost:8000"
echo ""
echo "📖 API文档: http://localhost:8000/docs"
echo "🏥 健康检查: http://localhost:8000/health"
echo ""
echo "📊 日志文件:"
echo "  workflow_agent: logs/workflow_agent.log"
echo "  api_gateway: logs/api_gateway.log"
echo ""
echo "📝 实时查看日志:"
echo "  tail -f logs/workflow_agent.log    # 查看workflow_agent日志"
echo "  tail -f logs/api_gateway.log       # 查看api_gateway日志"
echo "  tail -f logs/*.log                 # 查看所有服务日志"
echo ""
echo "🧪 运行集成测试:"
echo "  python test_production_integration.py"
echo ""
echo "🛑 停止所有服务:"
echo "  ./stop_all_services.sh"
echo ""
echo "❓ 是否要实时查看服务日志? (y/n)"
read -t 10 -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "📺 开始实时显示所有服务日志 (按 Ctrl+C 停止)..."
    sleep 1
    tail -f logs/*.log
fi