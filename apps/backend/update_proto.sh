#!/bin/bash

# Proto 更新脚本
# 自动生成和分发 protobuf 文件到各个服务
# 使用方法: ./update_proto.sh

set -e  # 遇到错误立即退出

echo "🚀 Proto 更新脚本启动"
echo "========================================"

# 检查是否在正确的目录
if [ ! -f "shared/proto/workflow_agent.proto" ]; then
    echo "❌ 错误: 请在 apps/backend 目录下运行此脚本"
    echo "当前目录: $(pwd)"
    exit 1
fi

# 检查依赖
echo "🔍 检查依赖..."

# 检查 Python
if ! command -v python &> /dev/null; then
    echo "❌ Python 未安装"
    exit 1
fi

# 检查 grpcio-tools
if ! python -c "import grpc_tools.protoc" &> /dev/null; then
    echo "⚠️ grpcio-tools 未安装，正在安装..."
    pip install grpcio-tools
fi

echo "✅ 依赖检查完成"

# 设置路径
BACKEND_ROOT=$(pwd)
SHARED_PROTO_DIR="$BACKEND_ROOT/shared/proto"
API_GATEWAY_PROTO_DIR="$BACKEND_ROOT/api-gateway/proto"
WORKFLOW_AGENT_ROOT="$BACKEND_ROOT/workflow_agent"

echo "📂 工作目录:"
echo "  Backend Root: $BACKEND_ROOT"
echo "  Shared Proto: $SHARED_PROTO_DIR"
echo "  API Gateway Proto: $API_GATEWAY_PROTO_DIR"
echo "  Workflow Agent: $WORKFLOW_AGENT_ROOT"

# 创建目标目录（如果不存在）
echo "🏗️ 创建目标目录..."
mkdir -p "$API_GATEWAY_PROTO_DIR"

# 生成 protobuf Python 代码
echo "🔧 生成 protobuf Python 代码..."

cd "$BACKEND_ROOT"

# 生成到 shared/proto 目录
echo "  -> 生成到 shared/proto/"
python -m grpc_tools.protoc \
    --python_out=shared/proto \
    --grpc_python_out=shared/proto \
    --proto_path=shared/proto \
    shared/proto/workflow_agent.proto

if [ $? -eq 0 ]; then
    echo "✅ shared/proto 生成成功"
else
    echo "❌ shared/proto 生成失败"
    exit 1
fi

# 复制到 api-gateway
echo "📋 复制到 api-gateway..."
cp "$SHARED_PROTO_DIR/workflow_agent_pb2.py" "$API_GATEWAY_PROTO_DIR/"
cp "$SHARED_PROTO_DIR/workflow_agent_pb2_grpc.py" "$API_GATEWAY_PROTO_DIR/"

if [ $? -eq 0 ]; then
    echo "✅ api-gateway proto 文件复制成功"
else
    echo "❌ api-gateway proto 文件复制失败"
    exit 1
fi

# 复制到 workflow_agent
echo "📋 复制到 workflow_agent..."
cp "$SHARED_PROTO_DIR/workflow_agent_pb2.py" "$WORKFLOW_AGENT_ROOT/"
cp "$SHARED_PROTO_DIR/workflow_agent_pb2_grpc.py" "$WORKFLOW_AGENT_ROOT/"

if [ $? -eq 0 ]; then
    echo "✅ workflow_agent proto 文件复制成功"
else
    echo "❌ workflow_agent proto 文件复制失败"
    exit 1
fi

# 验证生成的文件
echo "🔍 验证生成的文件..."

files_to_check=(
    "$SHARED_PROTO_DIR/workflow_agent_pb2.py"
    "$SHARED_PROTO_DIR/workflow_agent_pb2_grpc.py"
    "$API_GATEWAY_PROTO_DIR/workflow_agent_pb2.py"
    "$API_GATEWAY_PROTO_DIR/workflow_agent_pb2_grpc.py"
    "$WORKFLOW_AGENT_ROOT/workflow_agent_pb2.py"
    "$WORKFLOW_AGENT_ROOT/workflow_agent_pb2_grpc.py"
)

all_files_exist=true
for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file 不存在"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = false ]; then
    echo "❌ 部分文件生成失败"
    exit 1
fi

# 检查文件内容（基本验证）
echo "🔍 检查文件完整性..."

# 检查是否包含基本的类和服务定义
if grep -q "class.*pb2" "$SHARED_PROTO_DIR/workflow_agent_pb2.py" && \
   grep -q "WorkflowAgent" "$SHARED_PROTO_DIR/workflow_agent_pb2_grpc.py"; then
    echo "✅ 生成的文件内容验证通过"
else
    echo "❌ 生成的文件内容可能有问题"
    exit 1
fi

# 输出文件信息
echo "📊 生成文件信息:"
for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        size=$(wc -c < "$file")
        echo "  $(basename "$file"): ${size} bytes"
    fi
done

# 显示使用说明
echo "
🎉 Proto 更新完成！

📝 更新摘要:
  - workflow_agent.proto 已编译为 Python 代码
  - 文件已分发到 api-gateway 和 workflow_agent
  - 所有依赖服务现在可以使用最新的 proto 定义

🔄 下一步:
  1. 重启 api-gateway 服务: cd api-gateway && uvicorn app.main:app --reload
  2. 重启 workflow_agent 服务: cd workflow_agent && python main.py
  3. 运行集成测试: python test_new_workflow_integration.py

⚠️ 注意事项:
  - 如果修改了 proto 文件结构，请检查相关的状态转换代码
  - 确保 api-gateway 和 workflow_agent 都使用相同版本的 proto 文件
  - 在生产环境部署前，请运行完整的测试套件

🛠️ 如需重新生成，只需运行: ./update_proto.sh
"

echo "========================================"
echo "✅ Proto 更新脚本执行完成"