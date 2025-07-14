# Workflow Engine

基于 protobuf 定义的工作流引擎项目，protobuf 文件位于 `apps/backend/shared/proto/engine/`。

## 项目结构

```
workflow_engine/
├── workflow_engine/          # 主包
│   ├── __init__.py
│   ├── core/                # 核心配置
│   │   └── config.py        # 应用配置
│   ├── models/              # 数据模型
│   │   ├── database.py      # 数据库连接
│   │   ├── workflow.py      # 工作流模型
│   │   └── execution.py     # 执行模型
│   ├── services/            # gRPC 服务实现
│   │   └── workflow_service.py  # 工作流服务
│   ├── proto/               # 生成的 protobuf 代码 (自动生成)
│   ├── nodes/               # 节点实现
│   ├── api/                 # REST API (可选)
│   ├── schemas/             # Pydantic 模式
│   └── utils/               # 工具函数
├── scripts/                 # 脚本文件
│   └── generate_proto.py    # protobuf 代码生成脚本
├── tests/                   # 测试文件
├── database/                # 数据库相关文件
├── pyproject.toml           # 项目配置
├── Makefile                 # 开发工具
└── README.md                # 项目文档
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或者 venv\Scripts\activate  # Windows

# 安装依赖
make install
```

### 2. 生成 Protobuf 代码

```bash
# 从 shared/proto/engine/ 生成 Python 代码
make proto
```

这会从 `apps/backend/shared/proto/engine/` 中的 protobuf 文件生成 Python 代码到 `workflow_engine/proto/` 目录。

### 3. 数据库设置

```bash
# 设置数据库连接
export DATABASE_URL="postgresql://username:password@localhost:5432/workflow_engine"

# 初始化数据库
make db-init

# 应用迁移
make db-upgrade
```

### 4. 启动服务

```bash
# 启动 gRPC 服务器
make run

# 或者开发模式
make dev
```

## Protobuf 文件结构

项目使用的 protobuf 文件位于 `apps/backend/shared/proto/engine/`：

- `workflow.proto` - 工作流核心数据结构
- `execution.proto` - 执行系统模块
- `workflow_service.proto` - gRPC 服务定义
- `integration.proto` - 集成系统和触发器

### 生成的 Python 文件

运行 `make proto` 后，会在 `workflow_engine/proto/` 目录生成：

- `workflow_pb2.py` - 工作流数据结构
- `execution_pb2.py` - 执行相关消息
- `workflow_service_pb2.py` - 服务请求/响应消息
- `workflow_service_pb2_grpc.py` - gRPC 服务存根
- `integration_pb2.py` - 集成系统消息

## 服务实现

### gRPC 服务

项目实现了以下 gRPC 服务：

1. **WorkflowService** - 工作流管理
   - `CreateWorkflow` - 创建工作流
   - `GetWorkflow` - 获取工作流
   - `UpdateWorkflow` - 更新工作流
   - `DeleteWorkflow` - 删除工作流
   - `ListWorkflows` - 列出工作流
   - `ExecuteWorkflow` - 执行工作流
   - `GetExecutionStatus` - 获取执行状态
   - `CancelExecution` - 取消执行
   - `GetExecutionHistory` - 获取执行历史

2. **AIAgentService** - AI Agent 服务 (待实现)
3. **IntegrationService** - 集成管理服务 (待实现)
4. **TriggerService** - 触发器管理服务 (待实现)

### 数据库模型

- `Workflow` - 工作流定义，存储完整的 protobuf 数据
- `WorkflowExecution` - 工作流执行记录

## 开发工具

### Makefile 命令

```bash
make help          # 显示帮助信息
make install       # 安装依赖
make proto         # 生成 protobuf 代码
make clean         # 清理生成的文件
make test          # 运行测试
make run           # 运行应用
make dev           # 开发模式运行
make db-init       # 初始化数据库
make db-migrate    # 创建数据库迁移
make db-upgrade    # 应用数据库迁移
make db-reset      # 重置数据库
```

### 环境变量

创建 `.env` 文件配置环境变量：

```env
DATABASE_URL=postgresql://username:password@localhost:5432/workflow_engine
DATABASE_ECHO=false
GRPC_HOST=0.0.0.0
GRPC_PORT=50051
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

## 客户端使用示例

```python
import grpc
from workflow_engine.proto import workflow_service_pb2_grpc
from workflow_engine.proto import workflow_service_pb2
from workflow_engine.proto import workflow_pb2
from workflow_engine.proto import execution_pb2

# 创建 gRPC 客户端
channel = grpc.insecure_channel('localhost:50051')
stub = workflow_service_pb2_grpc.WorkflowServiceStub(channel)

# 创建工作流
request = workflow_service_pb2.CreateWorkflowRequest()
request.name = "Test Workflow"
request.description = "A test workflow"
request.user_id = "user-123"

response = stub.CreateWorkflow(request)
if response.success:
    print(f"Workflow created: {response.workflow.id}")

# 执行工作流
exec_request = execution_pb2.ExecuteWorkflowRequest()
exec_request.workflow_id = response.workflow.id
exec_request.mode = execution_pb2.ExecutionMode.MANUAL
exec_request.triggered_by = "user-123"

exec_response = stub.ExecuteWorkflow(exec_request)
print(f"Execution started: {exec_response.execution_id}")
```

## 架构特点

1. **Protobuf-First 设计** - 所有数据结构基于 protobuf 定义
2. **gRPC 服务** - 高性能的 RPC 通信
3. **模块化架构** - 清晰的服务分离
4. **数据库集成** - PostgreSQL + SQLAlchemy
5. **类型安全** - 通过 protobuf 保证类型安全

## 下一步开发

1. **实现 AI Agent 服务** - 自然语言生成工作流
2. **实现集成服务** - 第三方工具集成
3. **实现触发器服务** - 事件驱动的工作流
4. **节点执行引擎** - 实际的工作流执行逻辑
5. **REST API 网关** - 提供 HTTP API 接口
6. **前端集成** - 与前端应用集成

## 测试

```bash
# 运行所有测试
make test

# 运行特定测试
pytest tests/test_workflow_service.py -v
```

## 部署

项目支持 Docker 部署：

```bash
# 构建镜像
docker build -t workflow-engine .

# 运行容器
docker run -p 50051:50051 workflow-engine
```

---

更多详细信息请参考各个模块的文档和代码注释。 