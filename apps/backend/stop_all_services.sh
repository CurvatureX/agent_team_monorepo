#!/bin/bash

# 停止所有后端服务的脚本

echo "🛑 停止所有后端服务"
echo "====================="

# 函数：停止服务
stop_service() {
    local service_name=$1
    local port=$2
    
    echo "🛑 停止 $service_name..."
    
    # 通过PID文件停止
    if [ -f "logs/${service_name}.pid" ]; then
        local pid=$(cat "logs/${service_name}.pid")
        if ps -p $pid > /dev/null 2>&1; then
            kill $pid
            echo "✅ $service_name (PID: $pid) 已停止"
        else
            echo "⚠️ $service_name PID $pid 不存在"
        fi
        rm -f "logs/${service_name}.pid"
    fi
    
    # 通过端口停止
    if lsof -i :$port >/dev/null 2>&1; then
        echo "🔧 强制停止端口 $port 上的进程..."
        pkill -f ":$port" || true
        sleep 1
    fi
    
    # 验证停止
    if lsof -i :$port >/dev/null 2>&1; then
        echo "❌ 端口 $port 仍被占用"
        lsof -i :$port
    else
        echo "✅ 端口 $port 已释放"
    fi
}

# 停止服务
stop_service "api_gateway" "8000"
stop_service "workflow_agent" "50051"

echo ""
echo "🧹 清理..."

# 清理日志文件（可选）
# rm -f logs/*.log

echo "✅ 所有服务已停止"