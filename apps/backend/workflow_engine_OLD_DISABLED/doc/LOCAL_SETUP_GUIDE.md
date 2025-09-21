# Workflow Engine 本地启动指南

## 快速开始

### 1. 环境准备

#### 1.1 安装依赖
```bash
# 确保安装了 Python 3.9+
python --version

# 安装 Docker 和 Docker Compose
docker --version
docker-compose --version
```

#### 1.2 进入工作目录
```bash
cd apps/backend/workflow_engine
```

### 2. 环境配置

#### 2.1 创建环境变量文件
```bash
# 复制环境变量模板
cp env.example .env

# 编辑环境变量（重要！）
nano .env
```

#### 2.2 配置 .env 文件
```bash
# Database Configuration
DATABASE_URL=postgresql://workflow_user:workflow_password@localhost:5432/workflow_agent
REDIS_URL=redis://localhost:6379/0

# gRPC Configuration
GRPC_HOST=0.0.0.0
GRPC_PORT=50051

# AI API Keys (必须配置才能使用AI功能)
OPENAI_API_KEY=sk-your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME=Workflow Engine
```

### 3. 启动支持服务

#### 3.1 启动数据库和Redis
```bash
# 进入 backend 目录
cd ../

# 启动 PostgreSQL 和 Redis
docker-compose up -d postgres redis

# 检查服务状态
docker-compose ps
```

#### 3.2 等待服务就绪
```bash
# 检查 PostgreSQL
docker-compose exec postgres pg_isready -U workflow_user -d workflow_agent

# 检查 Redis
docker-compose exec redis redis-cli ping
```

### 4. 初始化 Workflow Engine

#### 4.1 回到 workflow_engine 目录
```bash
cd workflow_engine/
```

#### 4.2 安装 Python 依赖
```bash
# 使用 pip 安装
pip install -e .

# 或者如果有 requirements.txt
pip install -r requirements.txt
```

#### 4.3 生成 Protobuf 代码
```bash
# 生成 Python protobuf 代码
make proto

# 或者手动执行
python scripts/generate_proto.py
```

#### 4.4 初始化数据库
```bash
# 初始化数据库表结构
make db-upgrade

# 或者手动执行
alembic upgrade head
```

### 5. 启动 gRPC 服务

#### 5.1 启动服务
```bash
# 方式1: 使用 Make 命令
make run

# 方式2: 直接运行 Python
python -m workflow_engine.main

# 方式3: 开发模式（推荐）
python workflow_engine/main.py
```

#### 5.2 验证服务启动
你应该看到类似以下的日志输出：
```
2024-01-01 12:00:00,000 - workflow_engine.main - INFO - Starting Workflow Engine gRPC Server
2024-01-01 12:00:00,000 - workflow_engine.main - INFO - Initializing database...
2024-01-01 12:00:00,000 - workflow_engine.main - INFO - gRPC server configured to listen on 0.0.0.0:50051
2024-01-01 12:00:00,000 - workflow_engine.main - INFO - gRPC server started successfully
```

## 测试 gRPC 接口

### 1. 安装 gRPC 客户端工具

#### 1.1 安装 grpcurl
```bash
# macOS
brew install grpcurl

# Ubuntu/Debian
apt-get install grpcurl

# 或者使用 go install
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest
```

### 2. 测试健康检查

```bash
# 测试服务是否正常运行
grpcurl -plaintext localhost:50051 grpc.health.v1.Health/Check

# 预期输出:
# {
#   "status": "SERVING"
# }
```

### 3. 列出所有可用服务

```bash
# 列出所有 gRPC 服务
grpcurl -plaintext localhost:50051 list

# 预期输出:
# grpc.health.v1.Health
# workflow_engine.WorkflowService
```

### 4. 列出服务方法

```bash
# 列出 WorkflowService 的所有方法
grpcurl -plaintext localhost:50051 list workflow_engine.WorkflowService

# 预期输出:
# workflow_engine.WorkflowService.CreateWorkflow
# workflow_engine.WorkflowService.GetWorkflow
# workflow_engine.WorkflowService.UpdateWorkflow
# workflow_engine.WorkflowService.DeleteWorkflow
# workflow_engine.WorkflowService.ListWorkflows
# workflow_engine.WorkflowService.ExecuteWorkflow
# workflow_engine.WorkflowService.GetExecutionStatus
# workflow_engine.WorkflowService.CancelExecution
# workflow_engine.WorkflowService.GetExecutionHistory
# workflow_engine.WorkflowService.ValidateWorkflow
# workflow_engine.WorkflowService.TestNode
```

### 5. 测试创建工作流

```bash
# 创建一个简单的工作流
grpcurl -plaintext -d '{
  "name": "Test Workflow",
  "description": "A simple test workflow",
  "user_id": "user-123",
  "nodes": [
    {
      "id": "trigger-1",
      "name": "Manual Trigger",
      "type": "TRIGGER_NODE",
      "subtype": "TRIGGER_MANUAL",
      "parameters": {}
    }
  ],
  "connections": {}
}' localhost:50051 workflow_engine.WorkflowService/CreateWorkflow
```

### 6. 测试执行工作流

```bash
# 假设创建的工作流ID是 "workflow-123"
grpcurl -plaintext -d '{
  "workflow_id": "workflow-123",
  "mode": "MANUAL",
  "triggered_by": "user-123"
}' localhost:50051 workflow_engine.WorkflowService/ExecuteWorkflow
```

## Python 客户端示例

### 1. 创建测试客户端

创建文件 `test_client.py`:

```python
#!/usr/bin/env python3
"""
gRPC 客户端测试脚本
"""

import grpc
import json
from workflow_engine.proto import workflow_service_pb2
from workflow_engine.proto import workflow_service_pb2_grpc
from workflow_engine.proto import workflow_pb2
from workflow_engine.proto import execution_pb2


def create_grpc_client():
    """创建 gRPC 客户端"""
    channel = grpc.insecure_channel('localhost:50051')
    return workflow_service_pb2_grpc.WorkflowServiceStub(channel)


def test_health_check():
    """测试健康检查"""
    from grpc_health.v1 import health_pb2_grpc
    from grpc_health.v1 import health_pb2

    channel = grpc.insecure_channel('localhost:50051')
    health_stub = health_pb2_grpc.HealthStub(channel)

    request = health_pb2.HealthCheckRequest()
    response = health_stub.Check(request)

    print(f"Health check status: {response.status}")
    return response.status == health_pb2.HealthCheckResponse.SERVING


def test_create_workflow():
    """测试创建工作流"""
    client = create_grpc_client()

    # 创建工作流请求
    request = workflow_service_pb2.CreateWorkflowRequest()
    request.name = "Python Test Workflow"
    request.description = "A test workflow created from Python client"
    request.user_id = "python-user-123"

    # 添加一个触发器节点
    trigger_node = workflow_pb2.Node()
    trigger_node.id = "trigger-1"
    trigger_node.name = "Manual Trigger"
    trigger_node.type = workflow_pb2.NodeType.TRIGGER_NODE
    trigger_node.subtype = workflow_pb2.NodeSubtype.TRIGGER_MANUAL

    request.nodes.append(trigger_node)

    # 发送请求
    try:
        response = client.CreateWorkflow(request)
        print(f"Workflow created successfully!")
        print(f"Workflow ID: {response.workflow.id}")
        print(f"Workflow Name: {response.workflow.name}")
        return response.workflow.id
    except grpc.RpcError as e:
        print(f"Error creating workflow: {e}")
        return None


def test_execute_workflow(workflow_id):
    """测试执行工作流"""
    client = create_grpc_client()

    # 创建执行请求
    request = execution_pb2.ExecuteWorkflowRequest()
    request.workflow_id = workflow_id
    request.mode = execution_pb2.ExecutionMode.MANUAL
    request.triggered_by = "python-user-123"

    try:
        response = client.ExecuteWorkflow(request)
        print(f"Workflow execution started!")
        print(f"Execution ID: {response.execution_id}")
        print(f"Status: {response.status}")
        return response.execution_id
    except grpc.RpcError as e:
        print(f"Error executing workflow: {e}")
        return None


def test_get_execution_status(execution_id):
    """测试获取执行状态"""
    client = create_grpc_client()

    request = execution_pb2.GetExecutionStatusRequest()
    request.execution_id = execution_id

    try:
        response = client.GetExecutionStatus(request)
        print(f"Execution status retrieved!")
        print(f"Status: {response.execution.status}")
        print(f"Start time: {response.execution.start_time}")
        return response.execution
    except grpc.RpcError as e:
        print(f"Error getting execution status: {e}")
        return None


def main():
    """主测试函数"""
    print("=== Workflow Engine gRPC Client Test ===")

    # 1. 测试健康检查
    print("\n1. Testing health check...")
    if test_health_check():
        print("✅ Health check passed")
    else:
        print("❌ Health check failed")
        return

    # 2. 测试创建工作流
    print("\n2. Testing workflow creation...")
    workflow_id = test_create_workflow()
    if not workflow_id:
        print("❌ Workflow creation failed")
        return

    # 3. 测试执行工作流
    print("\n3. Testing workflow execution...")
    execution_id = test_execute_workflow(workflow_id)
    if not execution_id:
        print("❌ Workflow execution failed")
        return

    # 4. 测试获取执行状态
    print("\n4. Testing execution status...")
    execution = test_get_execution_status(execution_id)
    if execution:
        print("✅ All tests passed!")
    else:
        print("❌ Execution status test failed")


if __name__ == "__main__":
    main()
```

### 2. 运行测试客户端

```bash
# 运行 Python 客户端测试
python test_client.py
```

## 故障排除

### 常见问题

1. **端口占用错误**
   ```bash
   # 检查端口占用
   lsof -i :50051

   # 杀死占用进程
   kill -9 <PID>
   ```

2. **数据库连接错误**
   ```bash
   # 检查数据库是否运行
   docker-compose ps postgres

   # 重启数据库
   docker-compose restart postgres
   ```

3. **Redis 连接错误**
   ```bash
   # 检查 Redis 是否运行
   docker-compose ps redis

   # 重启 Redis
   docker-compose restart redis
   ```

4. **Protobuf 代码未生成**
   ```bash
   # 重新生成 protobuf 代码
   make clean
   make proto
   ```

5. **依赖包缺失**
   ```bash
   # 重新安装依赖
   pip install -e .

   # 或者安装特定包
   pip install grpcio grpcio-tools
   ```

### 调试技巧

1. **启用详细日志**
   ```bash
   export LOG_LEVEL=DEBUG
   python workflow_engine/main.py
   ```

2. **检查 gRPC 反射**
   ```bash
   # 启用 gRPC 反射（如果支持）
   grpcurl -plaintext localhost:50051 describe
   ```

3. **使用 gRPC GUI 工具**
   - 推荐使用 [BloomRPC](https://github.com/bloomrpc/bloomrpc)
   - 或者 [Postman](https://www.postman.com/) 的 gRPC 功能

## 下一步

现在你的 Workflow Engine gRPC 服务已经成功启动，你可以：

1. **集成前端**: 在前端应用中调用 gRPC 接口
2. **添加更多节点**: 实现自定义的节点执行器
3. **扩展功能**: 添加认证、监控等企业级功能
4. **性能测试**: 使用压测工具测试系统性能
5. **部署生产**: 配置生产环境的部署方案

## 相关文档

- [Workflow Engine 技术架构文档](./WORKFLOW_ENGINE_ARCHITECTURE.md)
- [连接系统升级文档](./CONNECTIONS_MAP_UPGRADE.md)
- [服务重构总结](./SERVICE_REFACTOR_SUMMARY.md)
