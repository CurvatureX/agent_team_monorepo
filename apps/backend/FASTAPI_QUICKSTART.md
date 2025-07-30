# FastAPI Workflow Agent 快速启动指南

## ✅ 迁移完成

workflow_agent 已成功从 gRPC 迁移到 FastAPI + Pydantic，只保留 `ProcessConversation` 接口。

## 🚀 启动方式

### 方式 1: 本地开发启动 (推荐)

```bash
cd /Users/bytedance/personal/agent_team_monorepo/apps/backend

# 1. 启动完整服务栈 (workflow_agent + API Gateway)
./start_local.sh

# 2. 仅启动 workflow_agent
cd workflow_agent
python main_fastapi.py

# 3. 停止所有服务
./stop_local.sh
```

### 方式 2: Docker 启动

```bash
cd /Users/bytedance/personal/agent_team_monorepo/apps/backend

# 启动 Docker 服务栈
./start_docker.sh

# 或手动启动
docker-compose up --build
```

## 📋 服务信息

- **workflow_agent FastAPI**: http://localhost:8001
- **API 文档**: http://localhost:8001/docs
- **健康检查**: http://localhost:8001/health
- **API Gateway**: http://localhost:8000

## 🔧 接口信息

### ProcessConversation 接口

**HTTP 端点**: `POST /process-conversation`

**请求格式**:
```json
{
  "session_id": "test_session_123",
  "user_id": "user_123", 
  "access_token": "jwt_token_here",
  "user_message": "帮我创建一个处理邮件的工作流",
  "workflow_context": {
    "origin": "create",
    "source_workflow_id": ""
  }
}
```

**响应格式**: Server-Sent Events 流
```
data: {"session_id": "test_session_123", "response_type": "RESPONSE_TYPE_MESSAGE", "is_final": false, "message": "我来帮您创建工作流..."}

data: {"session_id": "test_session_123", "response_type": "RESPONSE_TYPE_WORKFLOW", "is_final": true, "workflow": "{...workflow_json...}"}
```

## 🧪 测试命令

```bash
# 健康检查
curl http://localhost:8001/health

# 测试 ProcessConversation 接口
curl -X POST "http://localhost:8001/process-conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_123",
    "user_id": "user_123",
    "access_token": "test_token", 
    "user_message": "帮我创建一个处理邮件的工作流"
  }'

# 通过 API Gateway 测试聊天流 (需要认证)
curl "http://localhost:8000/api/v1/app/chat/stream" \
  -H "Authorization: Bearer your_jwt_token"
```

## 📝 必需的环境变量

在 `.env` 文件中配置:

```bash
# AI API Keys (必需)
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Supabase (必需)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-secret-key
SUPABASE_ANON_KEY=your-anon-key

# 服务配置
FASTAPI_PORT=8001
DEBUG=true
```

## 🗑️ 已清理的文件

- ❌ `main.py` (gRPC 启动文件)
- ❌ `services/grpc_server.py` (gRPC 服务实现)
- ❌ `proto/` 目录
- ❌ gRPC 相关依赖 (`grpcio`, `protobuf` 等)

## ✅ 新增的文件

- ✅ `main_fastapi.py` (FastAPI 启动入口)
- ✅ `services/fastapi_server.py` (FastAPI 服务实现)
- ✅ `shared/models/conversation.py` (Pydantic 模型)

## 🎉 迁移优势

1. **简化部署**: 无需 protobuf 编译
2. **更好的文档**: 自动生成 OpenAPI 文档
3. **类型安全**: Pydantic 模型提供完整类型支持
4. **开发友好**: 更好的 IDE 支持和调试体验
5. **统一接口**: 只有一个 ProcessConversation 接口

现在可以使用 `python main_fastapi.py` 启动服务了！🚀