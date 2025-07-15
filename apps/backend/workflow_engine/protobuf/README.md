# Protocol Buffers 定义

这个目录包含了工作流引擎的 Protocol Buffers 定义文件，基于 `planning.md` 中的设计。

## 文件结构

```
protobuf/
├── workflow.proto          # 工作流核心数据结构
├── execution.proto         # 执行系统模块
├── ai_system.proto         # AI 系统模块
├── integration.proto       # 集成系统和触发器
├── workflow_service.proto  # gRPC 服务定义
├── generate_python.py      # Python 代码生成脚本
└── README.md              # 说明文档
```

## 主要模块

### 1. 工作流核心模块 (`workflow.proto`)

定义了工作流的基础数据结构：

- **Workflow**: 工作流定义
- **Node**: 节点定义（8大核心节点类型）
- **ConnectionsMap**: 节点连接系统
- **WorkflowSettings**: 工作流设置

#### 8大核心节点类型

1. **TRIGGER_NODE** - 触发器节点：响应外部事件
2. **AI_AGENT_NODE** - AI 代理节点：执行 AI 任务
3. **EXTERNAL_ACTION_NODE** - 外部动作节点：调用外部 API
4. **ACTION_NODE** - 动作节点：执行内部操作
5. **FLOW_NODE** - 流程控制节点：条件分支、循环等
6. **HUMAN_IN_THE_LOOP_NODE** - 人机交互节点：等待用户输入
7. **TOOL_NODE** - 工具节点：使用特定工具
8. **MEMORY_NODE** - 记忆节点：存储和检索数据

### 2. 执行系统模块 (`execution.proto`)

定义了工作流执行相关的数据结构：

- **ExecutionData**: 执行数据
- **RunData**: 运行数据
- **TaskData**: 任务数据
- **NodeExecutionData**: 节点执行数据

### 3. AI 系统模块 (`ai_system.proto`)

定义了 AI Agent 和相关组件：

- **AIAgentConfig**: AI Agent 配置
- **AILanguageModel**: AI 语言模型
- **AITool**: AI 工具
- **AIMemory**: AI 记忆系统
- **GenerateWorkflowRequest/Response**: 工作流生成

### 4. 集成系统模块 (`integration.proto`)

定义了第三方集成和触发器：

- **Integration**: 第三方集成
- **CredentialConfig**: 凭证配置
- **Trigger**: 触发器定义
- **MCPToolConfig**: MCP 工具配置

### 5. gRPC 服务定义 (`workflow_service.proto`)

定义了工作流引擎的 gRPC 服务：

- **WorkflowService**: 工作流管理服务
- **AIAgentService**: AI Agent 服务
- **IntegrationService**: 集成管理服务
- **TriggerService**: 触发器管理服务
- **HealthService**: 健康检查服务

## 使用方法

### 生成 Python 代码

1. 确保已安装 Protocol Buffers 编译器：
   ```bash
   # macOS
   brew install protobuf
   
   # Ubuntu
   sudo apt-get install protobuf-compiler
   
   # 或者下载二进制文件
   # https://github.com/protocolbuffers/protobuf/releases
   ```

2. 运行生成脚本：
   ```bash
   cd apps/backend/workflow_engine/protobuf
   python generate_python.py
   ```

3. 生成的 Python 文件将保存在 `workflow_engine/proto/` 目录中。

### 在代码中使用

```python
# 导入生成的 protobuf 模块
from workflow_engine.proto import workflow_pb2
from workflow_engine.proto import execution_pb2
from workflow_engine.proto import ai_system_pb2
from workflow_engine.proto import workflow_service_pb2_grpc

# 创建工作流对象
workflow = workflow_pb2.Workflow()
workflow.id = "workflow-001"
workflow.name = "My Workflow"
workflow.active = True

# 创建节点
node = workflow_pb2.Node()
node.id = "node-1"
node.name = "Trigger Node"
node.type = workflow_pb2.NodeType.TRIGGER_NODE
node.subtype = workflow_pb2.NodeSubtype.TRIGGER_CHAT

# 添加节点到工作流
workflow.nodes.append(node)

# 创建 gRPC 客户端
import grpc
from workflow_engine.proto import workflow_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = workflow_service_pb2_grpc.WorkflowServiceStub(channel)

# 调用服务
request = workflow_service_pb2.CreateWorkflowRequest()
request.name = "Test Workflow"
response = stub.CreateWorkflow(request)
```

## 设计特点

1. **模块化设计**: 按功能模块分离，便于维护和扩展
2. **类型安全**: 使用枚举类型确保类型安全
3. **向后兼容**: 使用 protobuf 的版本控制特性
4. **跨语言支持**: 可以生成多种语言的代码
5. **高性能**: 二进制序列化，性能优异

## 扩展指南

### 添加新的节点类型

1. 在 `workflow.proto` 中添加新的 `NodeType` 枚举值
2. 在 `NodeSubtype` 中添加相应的子类型
3. 更新相关的服务定义
4. 重新生成代码

### 添加新的服务

1. 在 `workflow_service.proto` 中定义新的服务
2. 添加相应的请求和响应消息
3. 重新生成代码
4. 实现服务端逻辑

## 注意事项

1. 修改 protobuf 定义后，需要重新生成代码
2. 保持向后兼容性，避免删除或修改现有字段
3. 新增字段应该是可选的，并提供默认值
4. 使用语义化的字段编号，避免冲突

## 相关文档

- [Protocol Buffers 官方文档](https://developers.google.com/protocol-buffers)
- [gRPC 官方文档](https://grpc.io/docs/)
- [Planning.md 设计文档](../../../docs/tech-design/planning.md) 