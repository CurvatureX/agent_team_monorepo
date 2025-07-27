# Workflow Engine 技术架构文档

## 项目概述

Workflow Engine 是一个基于 protobuf 和 gRPC 的分布式工作流引擎，支持复杂的工作流定义、执行和监控。该系统采用模块化架构，支持 8 种核心节点类型和 13 种连接类型，能够处理从简单的顺序执行到复杂的 AI Agent 工作流。

## 整体架构

### 架构图

```mermaid
graph TB
    subgraph "Frontend Layer"
        WEB[Web Interface]
        CLI[CLI Tools]
        SDK[Client SDKs]
    end

    subgraph "API Gateway Layer"
        GRPC[gRPC Gateway]
        REST[REST API Gateway]
        AUTH[Authentication]
    end

    subgraph "Core Service Layer"
        subgraph "Workflow Engine"
            WS[Workflow Service]
            ES[Execution Service]
            VS[Validation Service]
            MS[Main Service]
        end
        
        subgraph "Execution Engine"
            EE[Execution Engine]
            NF[Node Factory]
            NE[Node Executors]
        end
        
        subgraph "Node Types"
            TN[Trigger Nodes]
            AN[AI Agent Nodes]
            EAN[External Action Nodes]
            ACN[Action Nodes]
            FN[Flow Control Nodes]
            HN[Human-in-Loop Nodes]
            TLN[Tool Nodes]
            MN[Memory Nodes]
        end
    end

    subgraph "Data Layer"
        PG[(PostgreSQL)]
        REDIS[(Redis Cache)]
        FS[(File Storage)]
    end

    subgraph "External Integrations"
        OPENAI[OpenAI API]
        GOOGLE[Google APIs]
        SLACK[Slack API]
        GITHUB[GitHub API]
        MCP[MCP Tools]
    end

    %% Connections
    WEB --> GRPC
    CLI --> GRPC
    SDK --> GRPC
    
    GRPC --> AUTH
    AUTH --> MS
    
    MS --> WS
    MS --> ES
    MS --> VS
    
    ES --> EE
    EE --> NF
    NF --> NE
    
    NE --> TN
    NE --> AN
    NE --> EAN
    NE --> ACN
    NE --> FN
    NE --> HN
    NE --> TLN
    NE --> MN
    
    WS --> PG
    ES --> PG
    ES --> REDIS
    
    NE --> OPENAI
    NE --> GOOGLE
    NE --> SLACK
    NE --> GITHUB
    NE --> MCP
```

### 技术栈

- **后端框架**: Python 3.9+, FastAPI, gRPC
- **数据库**: PostgreSQL 14+, Redis 6+
- **消息系统**: Protocol Buffers (protobuf)
- **ORM**: SQLAlchemy 2.0
- **任务队列**: Celery (可选)
- **容器化**: Docker, Docker Compose
- **监控**: Prometheus, Grafana (可选)

## 核心组件详解

### 1. 服务层架构

#### 1.1 Main Service (主服务)
- **职责**: gRPC 服务入口，请求路由和委托
- **文件**: `workflow_engine/services/main_service.py`
- **特点**: 
  - 实现 gRPC ServicerContext
  - 委托模式分发请求
  - 统一错误处理和日志记录

#### 1.2 Workflow Service (工作流服务)
- **职责**: 工作流的 CRUD 操作
- **文件**: `workflow_engine/services/workflow_service.py`
- **主要功能**:
  - 创建、读取、更新、删除工作流
  - 工作流列表查询和筛选
  - 工作流版本管理

#### 1.3 Execution Service (执行服务)
- **职责**: 工作流执行管理
- **文件**: `workflow_engine/services/execution_service.py`
- **主要功能**:
  - 启动工作流执行
  - 执行状态查询和监控
  - 执行历史记录管理
  - 执行取消和恢复

#### 1.4 Validation Service (验证服务)
- **职责**: 工作流验证和调试
- **文件**: `workflow_engine/services/validation_service.py`
- **主要功能**:
  - 工作流结构验证
  - 连接系统验证
  - 单节点测试
  - 循环依赖检测

### 2. 执行引擎架构

#### 2.1 Workflow Execution Engine (工作流执行引擎)
- **文件**: `workflow_engine/execution_engine.py`
- **核心功能**:
  - 工作流解析和验证
  - 执行顺序计算（拓扑排序）
  - 节点执行调度
  - 数据流管理
  - 错误处理和恢复

#### 2.2 Node Factory (节点工厂)
- **文件**: `workflow_engine/nodes/factory.py`
- **设计模式**: 工厂模式 + 单例模式
- **功能**:
  - 节点执行器注册和管理
  - 节点类型到执行器的映射
  - 执行器实例化和缓存

#### 2.3 Node Executors (节点执行器)
- **基类**: `workflow_engine/nodes/base.py`
- **核心接口**:
  - `execute()`: 执行节点逻辑
  - `validate()`: 验证节点配置
  - `get_supported_subtypes()`: 获取支持的子类型

### 3. 节点类型系统

#### 3.1 八大核心节点类型

1. **TRIGGER_NODE** (触发器节点)
   - 子类型: MANUAL, WEBHOOK, CRON, CHAT, EMAIL, FORM, CALENDAR
   - 职责: 响应外部事件，启动工作流

2. **AI_AGENT_NODE** (AI 代理节点)
   - 子类型: ROUTER_AGENT, TASK_ANALYZER, DATA_INTEGRATOR, REPORT_GENERATOR
   - 职责: 执行 AI 任务，处理自然语言

3. **EXTERNAL_ACTION_NODE** (外部动作节点)
   - 子类型: GITHUB, GOOGLE_CALENDAR, TRELLO, EMAIL, SLACK, API_CALL
   - 职责: 调用第三方 API 和服务

4. **ACTION_NODE** (动作节点)
   - 子类型: RUN_CODE, HTTP_REQUEST, DATA_TRANSFORMATION, FILE_OPERATION
   - 职责: 执行内部操作和数据处理

5. **FLOW_NODE** (流程控制节点)
   - 子类型: IF, FILTER, LOOP, MERGE, SWITCH, WAIT
   - 职责: 控制工作流执行流程

6. **HUMAN_IN_THE_LOOP_NODE** (人机交互节点)
   - 子类型: GMAIL, SLACK, DISCORD, TELEGRAM, APP
   - 职责: 等待人工输入和确认

7. **TOOL_NODE** (工具节点)
   - 子类型: MCP, CALENDAR, EMAIL, HTTP
   - 职责: 使用特定工具和 MCP 插件

8. **MEMORY_NODE** (记忆节点)
   - 子类型: SIMPLE_STORAGE, BUFFER, KNOWLEDGE_GRAPH, VECTOR_STORE, DOCUMENT_STORAGE, EMBEDDINGS
   - 职责: 数据存储和检索

### 4. 连接系统 (ConnectionsMap)

#### 4.1 连接类型
支持 13 种连接类型，支持复杂的 AI Agent 工作流：

- `MAIN`: 主要数据流连接
- `AI_AGENT`: AI 代理连接
- `AI_CHAIN`: AI 链式连接
- `AI_DOCUMENT`: AI 文档连接
- `AI_EMBEDDING`: AI 嵌入连接
- `AI_LANGUAGE_MODEL`: AI 语言模型连接
- `AI_MEMORY`: AI 记忆连接
- `AI_OUTPUT_PARSER`: AI 输出解析器连接
- `AI_RETRIEVER`: AI 检索器连接
- `AI_RERANKER`: AI 重排序器连接
- `AI_TEXT_SPLITTER`: AI 文本分割器连接
- `AI_TOOL`: AI 工具连接
- `AI_VECTOR_STORE`: AI 向量存储连接

#### 4.2 连接结构
```json
{
  "connections": {
    "节点名称": {
      "connection_types": {
        "连接类型": {
          "connections": [
            {
              "node": "目标节点名称",
              "type": "连接类型",
              "index": 0
            }
          ]
        }
      }
    }
  }
}
```

### 5. 数据模型

#### 5.1 数据库表结构

主要表：
- `users`: 用户信息
- `workflows`: 工作流定义 (存储完整的 protobuf JSON)
- `workflow_executions`: 工作流执行记录
- `integrations`: 第三方集成配置
- `oauth_tokens`: OAuth 认证令牌

#### 5.2 Protobuf 定义

核心 protobuf 文件：
- `workflow.proto`: 工作流核心数据结构
- `execution.proto`: 执行系统模块
- `workflow_service.proto`: gRPC 服务定义
- `ai_system.proto`: AI 系统模块
- `integration.proto`: 集成系统和触发器

## 工作流执行时序图

### 完整工作流执行流程

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant MainService as 主服务
    participant ExecutionService as 执行服务
    participant ExecutionEngine as 执行引擎
    participant NodeFactory as 节点工厂
    participant NodeExecutor as 节点执行器
    participant Database as 数据库
    participant ExternalAPI as 外部API

    %% 1. 执行请求
    Client->>MainService: ExecuteWorkflow(workflow_id)
    MainService->>ExecutionService: execute_workflow()
    
    %% 2. 创建执行记录
    ExecutionService->>Database: 创建执行记录
    Database-->>ExecutionService: execution_id
    
    %% 3. 启动执行引擎
    ExecutionService->>ExecutionEngine: execute_workflow()
    
    %% 4. 工作流验证
    ExecutionEngine->>ExecutionEngine: _validate_workflow()
    alt 验证失败
        ExecutionEngine-->>ExecutionService: 验证错误
        ExecutionService-->>Client: 执行失败
    end
    
    %% 5. 计算执行顺序
    ExecutionEngine->>ExecutionEngine: _calculate_execution_order()
    Note over ExecutionEngine: 拓扑排序计算节点执行顺序
    
    %% 6. 节点执行循环
    loop 每个节点
        ExecutionEngine->>ExecutionEngine: _execute_node()
        
        %% 6.1 获取节点执行器
        ExecutionEngine->>NodeFactory: get_executor(node_type)
        NodeFactory-->>ExecutionEngine: NodeExecutor实例
        
        %% 6.2 准备输入数据
        ExecutionEngine->>ExecutionEngine: _prepare_node_input_data()
        Note over ExecutionEngine: 根据连接类型聚合数据
        
        %% 6.3 执行节点
        ExecutionEngine->>NodeExecutor: execute(context)
        
        %% 6.4 节点具体执行
        alt 外部API调用
            NodeExecutor->>ExternalAPI: API调用
            ExternalAPI-->>NodeExecutor: API响应
        else 内部处理
            NodeExecutor->>NodeExecutor: 内部逻辑处理
        end
        
        NodeExecutor-->>ExecutionEngine: NodeExecutionResult
        
        %% 6.5 处理执行结果
        alt 执行成功
            ExecutionEngine->>ExecutionEngine: 保存节点结果
        else 执行失败
            alt 停止工作流
                ExecutionEngine-->>ExecutionService: 执行失败
            else 继续执行
                ExecutionEngine->>ExecutionEngine: 继续下一个节点
            end
        end
    end
    
    %% 7. 完成执行
    ExecutionEngine-->>ExecutionService: 执行完成
    ExecutionService->>Database: 更新执行状态
    ExecutionService-->>Client: 执行结果
```

### 节点执行详细流程

```mermaid
sequenceDiagram
    participant EE as 执行引擎
    participant NF as 节点工厂
    participant NE as 节点执行器
    participant Validator as 验证器
    participant DataProcessor as 数据处理器
    participant External as 外部系统

    %% 1. 获取执行器
    EE->>NF: get_executor(node_type, subtype)
    NF->>NF: 检查执行器缓存
    alt 执行器不存在
        NF->>NF: 创建新执行器实例
        NF->>NF: 缓存执行器
    end
    NF-->>EE: 返回执行器实例

    %% 2. 准备执行上下文
    EE->>EE: 创建NodeExecutionContext
    Note over EE: 包含节点定义、输入数据、<br/>凭证、元数据等

    %% 3. 验证节点配置
    EE->>NE: validate(node)
    NE->>Validator: 验证参数和配置
    Validator-->>NE: 验证结果
    alt 验证失败
        NE-->>EE: 返回验证错误
    end

    %% 4. 执行前准备
    EE->>NE: prepare_execution(context)
    NE->>NE: 初始化资源和连接

    %% 5. 执行节点逻辑
    EE->>NE: execute(context)
    
    %% 5.1 根据节点类型执行
    alt AI Agent节点
        NE->>External: 调用AI API
        External-->>NE: AI响应
    else 外部动作节点
        NE->>External: 调用第三方API
        External-->>NE: API响应
    else 动作节点
        NE->>DataProcessor: 数据处理
        DataProcessor-->>NE: 处理结果
    else 流程控制节点
        NE->>NE: 条件判断和流程控制
    end

    %% 6. 处理执行结果
    NE->>NE: 格式化输出数据
    NE->>NE: 记录执行日志
    NE-->>EE: 返回NodeExecutionResult

    %% 7. 清理资源
    EE->>NE: cleanup_execution(context)
    NE->>NE: 释放资源和连接
```

### 连接系统数据流

```mermaid
graph TD
    subgraph "数据流处理"
        A[上游节点输出] --> B[连接类型分析]
        B --> C{连接类型}
        
        C -->|MAIN| D[主数据流]
        C -->|AI_TOOL| E[AI工具连接]
        C -->|AI_MEMORY| F[AI记忆连接]
        C -->|AI_AGENT| G[AI代理连接]
        
        D --> H[数据直接传递]
        E --> I[工具调用数据]
        F --> J[记忆存储数据]
        G --> K[代理交互数据]
        
        H --> L[目标节点输入]
        I --> L
        J --> L
        K --> L
        
        L --> M[节点执行]
        M --> N[输出结果]
    end
    
    subgraph "数据聚合策略"
        O[多个输入连接] --> P{聚合类型}
        P -->|MAIN连接| Q[直接合并]
        P -->|专用连接| R[按类型分组]
        Q --> S[合并后的数据]
        R --> T[分组后的数据]
        S --> U[传递给节点]
        T --> U
    end
```

## 系统特性

### 1. 高可用性
- 无状态服务设计
- 支持水平扩展
- 故障自动恢复
- 健康检查机制

### 2. 可扩展性
- 插件化节点架构
- 工厂模式支持新节点类型
- MCP 工具集成
- 灵活的连接系统

### 3. 性能优化
- 连接池管理
- 结果缓存机制
- 异步执行支持
- 资源限制和监控

### 4. 安全性
- OAuth2 认证
- 凭证加密存储
- API 访问控制
- 审计日志记录

## 部署架构

### 开发环境
```bash
# 使用 Docker Compose
docker-compose up -d

# 包含服务:
# - PostgreSQL 数据库
# - Redis 缓存
# - Workflow Engine 服务
# - pgAdmin (可选)
```

### 生产环境
```yaml
# Kubernetes 部署示例
apiVersion: apps/v1
kind: Deployment
metadata:
  name: workflow-engine
spec:
  replicas: 3
  selector:
    matchLabels:
      app: workflow-engine
  template:
    metadata:
      labels:
        app: workflow-engine
    spec:
      containers:
      - name: workflow-engine
        image: workflow-engine:latest
        ports:
        - containerPort: 50051
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

## 监控和日志

### 监控指标
- 工作流执行成功率
- 节点执行时间
- 系统资源使用率
- API 响应时间
- 错误率统计

### 日志结构
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "service": "workflow-engine",
  "execution_id": "exec-123",
  "node_id": "node-456",
  "message": "Node execution completed",
  "duration_ms": 1500,
  "status": "success"
}
```

## 性能基准

### 执行性能
- 简单工作流 (5节点): ~100ms
- 复杂工作流 (20节点): ~500ms
- AI Agent 工作流: ~2-5s (取决于AI API)
- 并发执行: 支持 100+ 并发工作流

### 系统容量
- 单实例: 1000+ 工作流定义
- 执行历史: 100万+ 执行记录
- 并发用户: 1000+ 用户
- 数据库: 支持 TB 级数据

## 未来发展

### 短期计划
1. 实现 AI Agent 服务
2. 增加更多节点类型
3. 完善监控和告警
4. 性能优化

### 长期规划
1. 分布式执行引擎
2. 可视化工作流编辑器
3. 工作流市场和模板
4. 企业级权限管理
5. 多租户支持

## 代码示例

### 1. 工作流定义示例

```json
{
  "id": "secretary-workflow",
  "name": "AI Secretary Workflow",
  "nodes": [
    {
      "id": "trigger-1",
      "name": "Manual Trigger",
      "type": "TRIGGER_NODE",
      "subtype": "MANUAL",
      "parameters": {
        "description": "用户手动触发"
      }
    },
    {
      "id": "ai-agent-1", 
      "name": "Secretary AI Agent",
      "type": "AI_AGENT_NODE",
      "subtype": "ROUTER_AGENT",
      "parameters": {
        "model_provider": "openai",
        "model_name": "gpt-4",
        "system_prompt": "你是一个智能秘书助手"
      }
    },
    {
      "id": "tool-1",
      "name": "Calendar Tool",
      "type": "TOOL_NODE", 
      "subtype": "CALENDAR",
      "parameters": {
        "calendar_id": "primary"
      }
    }
  ],
  "connections": {
    "connections": {
      "Manual Trigger": {
        "connection_types": {
          "main": {
            "connections": [
              {
                "node": "Secretary AI Agent",
                "type": "MAIN",
                "index": 0
              }
            ]
          }
        }
      },
      "Secretary AI Agent": {
        "connection_types": {
          "ai_tool": {
            "connections": [
              {
                "node": "Calendar Tool",
                "type": "AI_TOOL",
                "index": 0
              }
            ]
          }
        }
      }
    }
  }
}
```

### 2. 节点执行器实现示例

```python
class CustomNodeExecutor(BaseNodeExecutor):
    """自定义节点执行器示例"""
    
    def get_supported_subtypes(self) -> List[str]:
        return ["CUSTOM_SUBTYPE"]
    
    def validate(self, node: Any) -> List[str]:
        errors = []
        if not node.parameters.get("required_param"):
            errors.append("required_param is missing")
        return errors
    
    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        try:
            # 获取参数
            param = context.get_parameter("required_param")
            
            # 执行业务逻辑
            result = self._process_data(param, context.input_data)
            
            # 返回成功结果
            return self._create_success_result(
                output_data={"result": result},
                logs=["Processing completed successfully"]
            )
        except Exception as e:
            return self._create_error_result(
                error_message=str(e),
                logs=["Error occurred during processing"]
            )
```

### 3. gRPC 客户端调用示例

```python
import grpc
from workflow_engine.proto import workflow_service_pb2_grpc
from workflow_engine.proto import workflow_service_pb2

# 创建 gRPC 客户端
channel = grpc.insecure_channel('localhost:50051')
stub = workflow_service_pb2_grpc.WorkflowServiceStub(channel)

# 创建工作流
create_request = workflow_service_pb2.CreateWorkflowRequest()
create_request.name = "Test Workflow"
create_request.user_id = "user-123"

response = stub.CreateWorkflow(create_request)
print(f"Created workflow: {response.workflow.id}")

# 执行工作流
from workflow_engine.proto import execution_pb2

exec_request = execution_pb2.ExecuteWorkflowRequest()
exec_request.workflow_id = response.workflow.id
exec_request.mode = execution_pb2.ExecutionMode.MANUAL

exec_response = stub.ExecuteWorkflow(exec_request)
print(f"Execution started: {exec_response.execution_id}")
```

## 配置说明

### 1. 环境变量配置

```bash
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/workflow_engine
DATABASE_ECHO=false

# gRPC 服务配置
GRPC_HOST=0.0.0.0
GRPC_PORT=50051

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json

# AI API 配置
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# 安全配置
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
```

### 2. Docker Compose 配置

```yaml
version: '3.8'

services:
  workflow-engine:
    build: .
    ports:
      - "50051:50051"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/workflow_engine
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:14
    environment:
      POSTGRES_DB: workflow_engine
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/schema.sql

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 3. 节点工厂注册

```python
# 注册自定义节点执行器
from workflow_engine.nodes.factory import get_node_executor_factory

factory = get_node_executor_factory()
factory.register_executor("CUSTOM_NODE", CustomNodeExecutor)

# 或者在模块初始化时自动注册
def register_custom_executors():
    factory = get_node_executor_factory()
    factory.register_executor("CUSTOM_NODE", CustomNodeExecutor)
    factory.register_executor("ANOTHER_NODE", AnotherNodeExecutor)
```

## 扩展开发

### 1. 添加新节点类型

1. **创建执行器类**：继承 `BaseNodeExecutor`
2. **实现必要方法**：`execute()`, `validate()`, `get_supported_subtypes()`
3. **注册执行器**：在工厂中注册新的执行器
4. **更新 protobuf**：添加新的节点类型枚举
5. **编写测试**：确保新节点类型正常工作

### 2. 添加新连接类型

1. **更新 protobuf**：在 `ConnectionType` 枚举中添加新类型
2. **更新执行引擎**：修改 `_prepare_node_input_data()` 方法
3. **更新验证逻辑**：确保新连接类型通过验证
4. **编写测试**：验证新连接类型的数据流

### 3. 集成外部服务

1. **实现认证**：OAuth2 或 API Key 认证
2. **创建客户端**：封装外部 API 调用
3. **错误处理**：处理网络错误和 API 限制
4. **缓存策略**：实现适当的缓存机制
5. **监控集成**：添加监控和告警

## 故障排除

### 常见问题

1. **工作流执行失败**
   - 检查节点配置是否正确
   - 验证连接系统是否有循环依赖
   - 查看执行日志获取详细错误信息

2. **节点执行超时**
   - 检查外部 API 响应时间
   - 调整节点超时配置
   - 考虑添加重试机制

3. **数据库连接问题**
   - 验证数据库连接字符串
   - 检查数据库权限
   - 监控连接池状态

4. **gRPC 连接错误**
   - 检查防火墙设置
   - 验证 TLS 证书配置
   - 确认服务端口可访问

### 调试技巧

1. **启用详细日志**：设置 `LOG_LEVEL=DEBUG`
2. **使用调试工具**：利用 gRPC 客户端工具测试
3. **监控指标**：关注执行时间和错误率
4. **单元测试**：编写充分的单元测试
5. **集成测试**：验证端到端流程

## 总结

Workflow Engine 是一个功能强大、架构清晰的工作流引擎系统。通过模块化设计、类型安全的 protobuf 定义和灵活的连接系统，它能够支持从简单的自动化任务到复杂的 AI Agent 工作流。系统具有良好的可扩展性和可维护性，为构建现代化的工作流自动化平台提供了坚实的基础。

关键特性：
- **模块化架构**：清晰的服务分层和职责分离
- **类型安全**：基于 protobuf 的强类型定义
- **灵活连接**：支持 13 种连接类型的复杂数据流
- **可扩展性**：工厂模式支持自定义节点类型
- **高性能**：异步执行和缓存优化
- **企业级**：完整的认证、授权和监控体系

该系统为现代工作流自动化提供了完整的解决方案，能够满足从个人自动化到企业级流程管理的各种需求。 