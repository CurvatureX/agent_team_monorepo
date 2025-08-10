# Agent Team Backend - Centralized Docker Orchestration

Production-ready three-layer API Gateway with AI workflow agent services.

## 🏗️ Architecture Overview

### **Services Architecture**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │    │ Workflow Agent  │    │ Workflow Engine │
│   (FastAPI)     │◄──►│   (LangGraph)   │◄──►│   (gRPC)       │
│   Port: 8000    │    │   Port: 50051   │    │   Port: 8001    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         │                       └───────────────────────┼─────► ☁️ Supabase
         │                                               │      PostgreSQL + Vector Store
         │                                               │      Authentication + RLS
         └─────────────────┐                             │
                           │                             │
         ┌─────────────────┴─────────────────┐          │
         │            Redis                  │          │
         │        (Local Cache)              │          │
         │  • Rate Limiting (DB 2)           │          │
         │  • JWT Caching (DB 2)             │          │
         │  • LangGraph State (DB 0)         │          │
         │  • Workflow Engine State (DB 1)   │          │
         │         Port: 6379                │          │
         └───────────────────────────────────┘          │
                                                        │
         ☁️ External Services ◄─────────────────────────┘
         • OpenAI/Anthropic APIs
         • Supabase (Database + Auth + Vector Store)
```

### **Core Components**

1. **🌐 API Gateway** - Three-layer FastAPI service with Redis caching
   - **Public API** (`/api/v1/public/*`) - No auth, rate-limited
   - **App API** (`/api/v1/app/*`) - Supabase JWT authentication
   - **MCP API** (`/api/v1/mcp/*`) - API key authentication

2. **🤖 Workflow Agent** - LangGraph-based AI consultant (gRPC)
   - Natural language workflow generation
   - RAG-enhanced with Supabase vector store
   - Redis-backed state management

3. **⚙️ Workflow Engine** - Execution engine (gRPC)
   - Workflow execution and orchestration
   - Node-based workflow processing
   - PostgreSQL persistence

4. **🗄️ Infrastructure**
   - **Redis** - Local caching, rate limiting, LangGraph checkpoints
   - **Supabase** - PostgreSQL database, authentication, vector store, RLS
   - **Redis Commander** - Redis management UI (development only)

### **Technology Stack**

- **API Layer**: FastAPI + Pydantic + JWT Authentication
- **AI Services**: LangGraph + OpenAI/Anthropic + RAG (Supabase)
- **Communication**: gRPC (internal) + REST API (external)
- **Data**: Supabase (PostgreSQL + Vector Store + Auth) + Redis (local cache)
- **Infrastructure**: Docker Compose + AWS ECS (production)

## 🚀 Quick Start

### **Prerequisites**

- Docker & Docker Compose
- Python 3.11+ (for development)
- OpenAI and/or Anthropic API keys
- Supabase account (for authentication & RAG)

### **🐳 Docker Deployment (Recommended)**

1. **Setup Environment**
   ```bash
   cd apps/backend
   cp .env.example .env
   # Edit .env with your API keys and Supabase credentials
   ```

2. **Start All Services**
   ```bash
   # Full production stack
   docker-compose up --build

   # Development with Redis UI
   docker-compose --profile development up --build

   # Start specific services
   docker-compose up redis  # Local cache only (services use Supabase for data)
   ```
   # 编辑 .env 文件，添加Supabase配置
   cd ..
   ```

3. **启动所有服务**
   ```bash
   # 开发模式 (支持热重载)
   ./start-all.sh dev

   # 或生产模式 (后台运行)
   ./start-all.sh prod
   ```

4. **验证服务**
   - 🌐 API Gateway: http://localhost:8000
   - 📚 API文档: http://localhost:8000/docs
   - 🔍 健康检查: http://localhost:8000/health
   - 🗄️ 数据库管理: http://localhost:8080 (Adminer)
   - 🔧 Redis管理: http://localhost:8081 (Redis Commander)

5. **停止服务**
   ```bash
   ./stop-all.sh
   ```

### 开发模式启动

#### 选项1: 本地开发 (使用uv)

1. **安装uv包管理器**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **安装依赖**
   ```bash
   # 安装所有工作空间依赖
   uv sync --dev
   ```

3. **使用本地开发脚本**
   ```bash
   ./start-dev-local.sh
   ```

4. **启动服务**
   ```bash
   # 终端1: 启动Workflow Agent
   cd workflow_agent && uv run python -m main

   # 终端2: 启动API Gateway
   cd api-gateway && uv run uvicorn main:app --reload --port 8000
   ```

#### 选项2: 传统方式 (pip + 虚拟环境)

1. **安装依赖**
   ```bash
   # API Gateway
   cd api-gateway && python -m venv venv && source venv/bin/activate && pip install -e . && cd ..

   # Workflow Agent
   cd workflow_agent && python -m venv venv && source venv/bin/activate && pip install -e . && cd ..
   ```

2. **生成gRPC代码**
   ```bash
   cd shared && python scripts/generate_grpc.py && cd ..
   ```

3. **启动Redis和PostgreSQL**
   ```bash
   docker-compose up -d redis postgres
   ```

4. **启动服务**
   ```bash
   # 终端1: 启动Workflow Agent
   cd workflow_agent && source venv/bin/activate && python -m main

   # 终端2: 启动API Gateway
   cd api-gateway && source venv/bin/activate && uvicorn main:app --reload --port 8000
   ```

## API使用示例

### 1. 生成工作流

```bash
curl -X POST "http://localhost:8000/api/v1/workflow/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "创建一个每天早上9点检查日程，并发送Slack提醒的工作流",
    "context": {
      "slack_channel": "#reminders",
      "timezone": "Asia/Shanghai"
    }
  }'
```

### 2. 优化工作流

```bash
curl -X POST "http://localhost:8000/api/v1/workflow/refine" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "workflow-123",
    "feedback": "需要添加错误处理和邮件通知功能",
    "original_workflow": { ... }
  }'
```

### 3. 验证工作流

```bash
curl -X POST "http://localhost:8000/api/v1/workflow/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_data": { ... }
  }'
```

## 核心功能

### 🤖 AI Agent (LangGraph)

- **需求分析**: 解析自然语言描述，提取工作流要求
- **计划生成**: 基于需求分析生成详细的执行计划
- **知识检查**: 验证信息完整性，必要时询问用户
- **工作流生成**: 创建完整的工作流JSON结构
- **验证优化**: 验证工作流正确性并提供优化建议

### 🔄 支持的节点类型

基于技术设计文档定义的8大核心节点类型：

1. **Trigger Node** - 触发器节点
   - Slack Trigger, Webhook Trigger, Cron Trigger

2. **AI Agent Node** - AI代理节点
   - Router Agent, Task Analyzer

3. **External Action Node** - 外部动作节点
   - Google Calendar, Slack, Email, GitHub

4. **Action Node** - 动作节点
   - HTTP Request, Code Execution, File Operations

5. **Flow Node** - 流程控制节点
   - If/Else, Loop, Switch, Merge

6. **Human-In-The-Loop Node** - 人机交互节点
   - Approval workflows, User input

7. **Tool Node** - 工具节点
   - MCP Tools, External APIs

8. **Memory Node** - 记忆节点
   - Buffer Memory, Vector Store

## 开发指南

### 项目结构

```
apps/backend/
├── api-gateway/           # API Gateway服务
│   ├── core/             # 核心配置和gRPC客户端
│   ├── routers/          # FastAPI路由
│   ├── proto/            # 生成的gRPC代码
│   └── main.py           # 应用入口
├── workflow_agent/       # Workflow Agent服务
│   ├── agents/           # LangGraph Agent实现
│   ├── core/             # 核心配置和模型
│   ├── services/         # gRPC服务器
│   ├── proto/            # 生成的gRPC代码
│   └── main.py           # 应用入口
├── shared/               # 共享组件
│   ├── proto/            # Protobuf定义
│   └── scripts/          # 工具脚本
└── docker-compose.yml    # Docker编排文件
```

### 添加新的节点类型

1. 在 `workflow_agent/agents/nodes.py` 中添加节点模板
2. 更新 `workflow_agent/core/models.py` 中的枚举类型
3. 在生成逻辑中添加对应的处理代码

### 扩展API接口

1. 在 `api-gateway/routers/` 中添加新的路由文件
2. 在 `api-gateway/main.py` 中注册新路由
3. 相应地在Workflow Agent中添加gRPC服务方法

## 监控和调试

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f api-gateway
docker-compose logs -f workflow-agent
```

### 健康检查

```bash
# API Gateway健康检查
curl http://localhost:8000/health

# 检查gRPC连接
grpcurl -plaintext localhost:50051 list
```

### 开发工具

- **API文档**: http://localhost:8000/docs (Swagger UI)
- **Redis管理**: 可用redis-cli连接到localhost:6379
- **数据库**: 可用psql连接到localhost:5432

## 部署

### 生产环境

1. 修改 `docker-compose.yml` 中的环境变量
2. 设置适当的资源限制和健康检查
3. 配置反向代理 (nginx/traefik)
4. 启用HTTPS和认证

### 扩展性

- API Gateway可以水平扩展
- Workflow Agent支持多实例部署
- Redis和PostgreSQL可以配置集群

## 故障排除

### 常见问题

1. **gRPC连接失败**: 检查workflow-agent服务是否启动
2. **API密钥错误**: 确认.env文件中的密钥正确
3. **端口冲突**: 修改docker-compose.yml中的端口映射

### 性能优化

- 调整LangGraph的checkpoint后端设置
- 优化Redis和PostgreSQL配置
- 监控内存和CPU使用情况

## 贡献

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开Pull Request

## 许可证

此项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
