# API Gateway Upgrade Guide

## 🚀 FastAPI + Supabase Auth Upgrade

本文档说明了API Gateway从MVP到带有Supabase认证的完整版本的升级过程。

## 📋 主要更新

### 1. ✅ FastAPI生命周期管理更新

**替换废弃的 `@app.on_event`**
```python
# ❌ 旧版本 (已废弃)
@app.on_event("startup")
async def startup_event():
    # 启动逻辑

@app.on_event("shutdown")
async def shutdown_event():
    # 关闭逻辑

# ✅ 新版本 (推荐)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动逻辑
    log_info("🚀 Starting API Gateway...")
    init_supabase()
    await workflow_client.connect()

    yield

    # 关闭逻辑
    await workflow_client.close()
    log_info("👋 API Gateway stopped")

app = FastAPI(lifespan=lifespan)
```

### 2. ✅ Supabase认证集成

**新增认证API端点**
```
POST /api/v1/auth/register    # 用户注册
POST /api/v1/auth/login       # 用户登录
POST /api/v1/auth/refresh     # 刷新令牌
POST /api/v1/auth/logout      # 用户登出
GET  /api/v1/auth/profile     # 获取用户资料
PUT  /api/v1/auth/profile     # 更新用户资料
```

**增强的认证中间件**
```python
# 自动验证JWT令牌
# 支持Bearer Token认证
# 用户数据注入到request.state
```

**更新的Session管理**
```
POST /api/v1/session          # 创建会话(支持认证和游客)
GET  /api/v1/session/{id}     # 获取会话(用户授权)
GET  /api/v1/sessions         # 列出用户所有会话
DELETE /api/v1/session/{id}   # 删除会话(用户授权)
```

## 🔧 环境变量配置

创建 `.env` 文件，添加以下配置：

```bash
# Supabase配置
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key

# gRPC配置
WORKFLOW_SERVICE_HOST=localhost
WORKFLOW_SERVICE_PORT=50051

# 应用配置
DEBUG=true
LOG_LEVEL=INFO

# 认证配置
ENABLE_AUTH=true
REQUIRE_EMAIL_VERIFICATION=false
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# 安全配置
JWT_SECRET_KEY=your-additional-jwt-secret

# 速率限制
RATE_LIMIT_PER_MINUTE=60
```

## 📊 数据库Schema更新

数据库已支持用户关联，sessions表结构：

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),  -- 关联Supabase Auth用户ID
    meta_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## 🌟 新功能特性

### 认证流程
1. **用户注册** → Supabase Auth创建用户
2. **用户登录** → 获取JWT访问令牌
3. **API调用** → Bearer Token验证
4. **会话管理** → 与用户关联的会话

### 用户隔离
- 用户只能访问自己的会话
- 支持游客会话（未认证用户）
- 防止跨用户数据访问

### 安全增强
- JWT令牌验证
- 用户授权检查
- 会话所有权验证

## 🔗 API使用示例

### 用户注册
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure123",
    "metadata": {"name": "John Doe"}
  }'
```

### 用户登录
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure123"
  }'
```

### 认证API调用
```bash
# 使用返回的access_token
curl -X POST http://localhost:8000/api/v1/session \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 聊天API
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<session_id>",
    "message": "Hello with auth!"
  }'
```

## 📖 API文档

启动服务后访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

现在API文档包含完整的认证端点和增强的会话管理。

## 🔄 迁移步骤

1. **更新代码**：已完成FastAPI和认证更新
2. **配置环境变量**：添加Supabase配置到.env
3. **数据库初始化**：运行sql/init_tables.sql
4. **测试认证**：验证注册/登录流程
5. **更新前端**：适配新的认证API

## 🎯 测试清单

- [ ] FastAPI应用正常启动（使用新的lifespan）
- [ ] 用户注册API工作正常
- [ ] 用户登录API工作正常
- [ ] JWT令牌验证工作正常
- [ ] 认证用户可以创建会话
- [ ] 用户只能访问自己的会话
- [ ] 游客会话仍然工作（可选）
- [ ] API文档显示所有端点

## 🚨 注意事项

- Supabase Service Role Key权限很高，仅用于后端
- 生产环境需要配置具体的CORS源
- 考虑启用Supabase RLS（行级安全）
- 监控JWT令牌过期和刷新

## 📞 故障排除

**常见问题：**

1. **Supabase连接失败**
   ```bash
   # 检查环境变量
   echo $SUPABASE_URL
   echo $SUPABASE_SECRET_KEY
   ```

2. **JWT验证失败**
   - 确认使用正确的Service Role Key
   - 检查令牌格式（Bearer <token>）

3. **用户会话访问问题**
   - 验证用户ID匹配
   - 检查会话所有权

升级完成后，你的API Gateway现在支持完整的Supabase认证系统！🎉
