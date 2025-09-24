#!/bin/bash

# Workflow Engine 快速调试脚本

echo "=== Workflow Engine 快速调试 ==="
echo ""

# 检查Python环境
echo "1. 检查Python环境..."
python --version
if [ $? -ne 0 ]; then
    echo "❌ Python未安装或不在PATH中"
    exit 1
fi

# 检查依赖
echo ""
echo "2. 检查依赖..."
python -c "import grpc, google.protobuf" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 缺少必要的依赖，请安装：pip install grpcio grpcio-tools google-protobuf"
    exit 1
fi

# 生成protobuf文件（包含自动修复）
echo ""
echo "3. 生成protobuf文件..."
python generate_proto.py

# 启动gRPC服务器
echo ""
echo "4. 启动gRPC服务器..."
echo "   服务器将在后台启动，PID将显示在下方"
echo "   使用 'ps aux | grep simple_grpc_server' 查看进程"
echo "   使用 'kill <PID>' 停止服务器"
echo ""

python simple_grpc_server.py &
SERVER_PID=$!
echo "   服务器PID: $SERVER_PID"

# 等待服务器启动
echo ""
echo "5. 等待服务器启动..."
sleep 5

# 测试基本功能
echo ""
echo "6. 测试基本功能..."
python test_simple_server.py

# 显示调试信息
echo ""
echo "=== 调试信息 ==="
echo "gRPC服务器运行在: localhost:50051"
echo "服务器PID: $SERVER_PID"
echo ""
echo "可用的测试脚本:"
echo "  - test_simple_server.py     # 基本功能测试"
echo "  - debug_complete_system.py  # 完整系统调试"
echo "  - test_all_nodes.py         # 节点执行器测试"
echo ""
echo "调试指南: DEBUG_GUIDE.md"
echo ""
echo "停止服务器: kill $SERVER_PID"
echo "================"
