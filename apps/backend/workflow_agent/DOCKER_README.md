# Workflow Agent Docker 启动指南

## 🚀 启动方式

### 方式 1: 完整启动脚本 (推荐)

```bash
cd /Users/bytedance/personal/agent_team_monorepo/apps/backend/workflow_agent

# 运行完整启动脚本
./start_docker.sh
```

**特性:**
- ✅ 自动检查和创建环境变量文件
- ✅ 验证必需的配置
- ✅ 自动构建镜像
- ✅ 启动 Redis 和 workflow_agent
- ✅ 健康检查验证
- ✅ 创建停止脚本
- ✅ 提供完整的使用说明

### 方式 2: 快速启动 (适合重复使用)

```bash
cd /Users/bytedance/personal/agent_team_monorepo/apps/backend/workflow_agent

# 设置环境变量
export OPENAI_API_KEY="sk-your-key"
export ANTHROPIC_API_KEY="sk-ant-your-key"  
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SECRET_KEY="your-secret-key"

# 快速启动
./quick_start.sh
```

## 📝 环境变量配置

首次运行 `./start_docker.sh` 会自动创建 `.env` 模板文件，您需要编辑以下必需变量：

```bash
# AI API Keys (必需)
OPENAI_API_KEY=sk-your-openai-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# Supabase 配置 (必需)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SECRET_KEY=your-service-role-secret-key

# 服务配置 (可选)
FASTAPI_PORT=8001
DEBUG=true
LOG_LEVEL=DEBUG
```

## 📋 启动的服务

| 容器名称 | 端口 | 描述 |
|----------|------|------|
| workflow-redis | 6379 | Redis 缓存服务 |
| workflow-agent | 8001 | FastAPI 工作流代理服务 |

## 🧪 验证和测试

启动后可以进行以下测试：

```bash
# 健康检查
curl http://localhost:8001/health

# 查看 API 文档
open http://localhost:8001/docs

# 测试 ProcessConversation 接口
curl -X POST "http://localhost:8001/process-conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_123",
    "user_id": "user_123", 
    "access_token": "test_token",
    "user_message": "帮我创建一个处理邮件的工作流"
  }'
```

## 🛑 停止服务

```bash
# 使用自动生成的停止脚本
./stop_docker.sh

# 或手动停止
docker stop workflow-agent workflow-redis
docker rm workflow-agent workflow-redis
docker network rm workflow-network
```

## 📄 日志和调试

```bash
# 查看 workflow_agent 日志
docker logs -f workflow-agent

# 查看 Redis 日志  
docker logs -f workflow-redis

# 进入容器调试
docker exec -it workflow-agent bash

# 查看容器状态
docker ps
```

## 🔧 常见问题

### 1. 端口已被占用
```bash
# 检查端口占用
lsof -i :8001
lsof -i :6379

# 停止占用端口的进程
kill -9 <PID>
```

### 2. 环境变量未设置
确保 `.env` 文件中的 API Keys 已正确填写，不是默认的占位符值。

### 3. 镜像构建失败
```bash
# 清理 Docker 缓存
docker system prune -f

# 重新构建
docker build --no-cache -f workflow_agent/Dockerfile -t workflow-agent-fastapi .
```

### 4. Redis 连接失败
检查 Redis 容器是否正常运行：
```bash
docker exec workflow-redis redis-cli ping
```

## 📁 文件结构

```
workflow_agent/
├── start_docker.sh      # 完整启动脚本
├── quick_start.sh       # 快速启动脚本  
├── stop_docker.sh       # 停止脚本 (自动生成)
├── .env                 # 环境变量文件 (自动生成)
├── main_fastapi.py      # FastAPI 启动入口
├── services/
│   └── fastapi_server.py # FastAPI 服务实现
└── Dockerfile           # Docker 构建文件
```

## 🎯 下一步

启动成功后，您可以：

1. 访问 API 文档: http://localhost:8001/docs
2. 测试 ProcessConversation 接口
3. 集成到您的应用程序中
4. 查看实时日志进行调试

现在您已经有了一个完全独立的 workflow_agent Docker 服务！🎉