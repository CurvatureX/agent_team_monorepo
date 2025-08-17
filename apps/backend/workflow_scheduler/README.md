# Workflow Scheduler

Workflow Scheduler 是一个专门用于管理和调度工作流触发器的服务，支持多种触发器类型包括 Cron、Manual、Webhook、Email 和 GitHub 等。

## 功能特性

### 触发器类型

1. **Cron 触发器**
   - 基于 cron 表达式的定时执行
   - 支持时区配置
   - 哈希分散机制避免同时执行
   - 分布式锁防止重复执行

2. **Manual 触发器**
   - 用户手动触发
   - 支持确认机制
   - 实时响应用户操作

3. **Webhook 触发器**
   - HTTP 端点触发
   - 每个 workflow 独立路径
   - 支持多种 HTTP 方法
   - 可配置身份验证

4. **Email 触发器**
   - IMAP 邮件监控
   - 支持邮件过滤器
   - 附件处理
   - 自动标记已读

5. **GitHub 触发器**
   - GitHub App 集成
   - 支持私有仓库访问
   - 高级过滤器（分支、路径、作者等）
   - 自动获取仓库上下文

### 核心组件

- **DeploymentService**: 管理工作流部署生命周期
- **TriggerManager**: 统一管理所有类型触发器
- **DistributedLockManager**: Redis 分布式锁管理
- **BaseTrigger**: 所有触发器的基础类

## ⚠️ 测试模式说明

**当前版本处于内测阶段**，系统配置为发送邮件通知而非实际执行 workflow：

- 🔔 **通知目标**: z1771485029@gmail.com
- 📧 **行为**: 当触发条件满足时，发送详细的邮件通知
- 🚫 **不执行**: workflow_engine 调用已被注释掉
- 📝 **日志**: 所有触发事件都会被详细记录

要恢复正常执行模式，请参考 `BaseTrigger._trigger_workflow_original()` 方法。

## 快速开始

### 本地开发

```bash
# 安装依赖
uv sync

# 运行服务
python -m workflow_scheduler.main

# 或使用 uvicorn
uvicorn workflow_scheduler.main:app --host 0.0.0.0 --port 8003 --reload
```

### Docker 运行

```bash
# 构建镜像
docker build -t workflow-scheduler --platform linux/amd64 .

# 运行容器
docker run -p 8003:8003 --env-file .env workflow-scheduler
```

### 环境变量

创建 `.env` 文件：

```bash
# 核心服务配置
PORT=8003
HOST=0.0.0.0
DEBUG=false

# 外部服务地址
WORKFLOW_ENGINE_URL=http://workflow-engine:8002
API_GATEWAY_URL=http://api-gateway:8000

# 数据库配置
DATABASE_URL=postgresql://user:pass@postgres/workflow_scheduler
REDIS_URL=redis://redis:6379/1

# 邮件监控配置
IMAP_SERVER=imap.gmail.com
EMAIL_USER=workflow@example.com
EMAIL_PASSWORD=app_password
EMAIL_CHECK_INTERVAL=60

# GitHub App 配置
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=secure_webhook_secret_here

# APScheduler 配置
SCHEDULER_TIMEZONE=UTC
SCHEDULER_MAX_WORKERS=10
```

## API 接口

### 部署管理

```bash
# 部署 workflow
POST /api/v1/deployment/workflows/{workflow_id}/deploy

# 取消部署
DELETE /api/v1/deployment/workflows/{workflow_id}/undeploy

# 更新部署
PUT /api/v1/deployment/workflows/{workflow_id}/deploy

# 获取部署状态
GET /api/v1/deployment/workflows/{workflow_id}/status

# 列出所有部署
GET /api/v1/deployment/workflows
```

### 触发器管理

```bash
# 手动触发
POST /api/v1/triggers/workflows/{workflow_id}/manual

# Webhook 触发
POST /api/v1/triggers/workflows/{workflow_id}/webhook

# 获取触发器状态
GET /api/v1/triggers/workflows/{workflow_id}/status

# 健康检查
GET /api/v1/triggers/health
```

### Webhook 端点

```bash
# 通用 webhook（通过 API Gateway）
POST /api/v1/public/webhook/workflow/{workflow_id}

# GitHub webhook（通过 API Gateway）
POST /api/v1/public/webhooks/github

# Webhook 状态
GET /api/v1/public/webhooks/status
```

## 架构设计

### 服务通信

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   API Gateway   │────▶│ Workflow Agent   │────▶│ Workflow Engine  │
│   (FastAPI)     │     │ (LangGraph/AI)   │     │ (Execution)      │
└─────────────────┘     └──────────────────┘     └──────────────────┘
        │                                                    │
        └────────────────── Supabase ────────────────────────┘
                    (Auth, State, Vector Store)
```

### 触发器工作流程

1. **部署阶段**
   - 验证 workflow 定义
   - 创建部署记录
   - 注册触发器

2. **监控阶段**
   - 持续监控触发条件
   - 应用过滤器规则
   - 分布式锁协调

3. **执行阶段**
   - 触发条件满足
   - 调用 workflow_engine
   - 记录执行历史

### 数据存储

- **PostgreSQL**: 部署记录、执行历史、触发器状态
- **Redis**: 分布式锁、缓存、状态同步

## 监控与日志

### 健康检查

```bash
curl http://localhost:8003/health
```

### 指标监控

```bash
curl http://localhost:8003/metrics
```

### 日志格式

```json
{
  "timestamp": "2025-01-28T10:30:00Z",
  "service": "workflow_scheduler",
  "trigger_type": "cron",
  "workflow_id": "wf_123",
  "execution_id": "exec_456",
  "event": "trigger_fired",
  "duration_ms": 1250,
  "status": "success"
}
```

## 测试

```bash
# 运行基础测试
pytest tests/test_basic.py -v

# 测试通知功能
python test_notification.py

# 运行所有测试
pytest tests/ -v

# 运行覆盖率测试
pytest tests/ --cov=workflow_scheduler
```

## 部署

### AWS ECS 部署

```bash
# 构建镜像
docker build --platform linux/amd64 -t workflow-scheduler .

# 标记镜像
docker tag workflow-scheduler 982081090398.dkr.ecr.us-east-1.amazonaws.com/agent-team/workflow-scheduler:latest

# 推送镜像
docker push 982081090398.dkr.ecr.us-east-1.amazonaws.com/agent-team/workflow-scheduler:latest
```

### ECS 任务定义

```json
{
  "family": "workflow-scheduler",
  "networkMode": "awsvpc",
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "workflow-scheduler",
      "image": "982081090398.dkr.ecr.us-east-1.amazonaws.com/agent-team/workflow-scheduler:latest",
      "portMappings": [
        {
          "containerPort": 8003,
          "protocol": "tcp"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8003/health || exit 1"],
        "interval": 30,
        "timeout": 30,
        "startPeriod": 120,
        "retries": 3
      }
    }
  ]
}
```

## 开发指南

### 添加新的触发器类型

1. 继承 `BaseTrigger` 类
2. 实现必要的抽象方法
3. 在 `TriggerManager` 中注册
4. 添加相应的配置模型

### 代码结构

```
workflow_scheduler/
├── app/
│   ├── main.py                    # FastAPI应用入口
│   ├── api/                       # REST API端点
│   │   ├── deployment.py         # 部署管理API
│   │   └── triggers.py           # 触发器管理API
│   ├── services/
│   │   ├── deployment_service.py # 部署服务
│   │   ├── trigger_manager.py    # 触发器管理器
│   │   └── lock_manager.py       # 分布式锁管理
│   ├── triggers/
│   │   ├── base.py               # 基础触发器类
│   │   ├── cron_trigger.py       # Cron触发器
│   │   ├── manual_trigger.py     # 手动触发器
│   │   ├── webhook_trigger.py    # Webhook触发器
│   │   ├── email_trigger.py      # 邮件触发器
│   │   └── github_trigger.py     # GitHub触发器
│   ├── models/                   # 数据模型
│   └── core/                     # 核心配置
├── tests/                        # 单元测试
├── pyproject.toml               # Python依赖
└── Dockerfile                   # 容器化配置
```

## 故障排除

### 常见问题

1. **触发器无法启动**
   - 检查配置参数
   - 验证外部服务连接
   - 查看错误日志

2. **分布式锁获取失败**
   - 检查 Redis 连接
   - 验证锁超时配置
   - 监控锁竞争情况

3. **GitHub 触发器问题**
   - 验证 App 权限配置
   - 检查 webhook 签名
   - 确认仓库访问权限

4. **邮件触发器问题**
   - 验证 IMAP 连接
   - 检查邮箱权限
   - 确认过滤器配置

## 许可证

MIT License
