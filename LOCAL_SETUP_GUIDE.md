# 本地开发环境配置指南

## 🚀 快速开始

### 1. 环境变量配置

#### 后端配置
```bash
# 复制环境变量模板
cp apps/backend/.env.local.example apps/backend/.env

# 编辑环境变量
vim apps/backend/.env
```

#### 前端配置
```bash
# 复制前端环境变量模板
cp apps/frontend/agent_team_web/.env.local.example apps/frontend/agent_team_web/.env.local

# 编辑前端环境变量
vim apps/frontend/agent_team_web/.env.local
```

### 2. OAuth2应用设置

#### 🔵 Google Calendar OAuth2设置

1. **访问 Google Cloud Console**: https://console.cloud.google.com/
2. **创建项目或选择现有项目**
3. **启用Google Calendar API**:
   - 导航到 "APIs & Services" > "Library"
   - 搜索 "Google Calendar API"
   - 点击 "Enable"

4. **创建OAuth2凭据**:
   - 导航到 "APIs & Services" > "Credentials"
   - 点击 "Create Credentials" > "OAuth client ID"
   - 应用类型选择 "Web application"
   - 名称: `Agent Team Local Development`

5. **配置授权重定向URI**:
   ```
   http://localhost:3003/oauth-callback
   http://localhost:3003/auth/callback
   ```

6. **获取凭据**:
   - 复制 `Client ID` 到环境变量 `GOOGLE_CLIENT_ID` 和 `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
   - 复制 `Client Secret` 到环境变量 `GOOGLE_CLIENT_SECRET`

#### 🔴 GitHub OAuth2设置

1. **访问 GitHub Settings**: https://github.com/settings/developers
2. **创建新的OAuth App**:
   - 点击 "New OAuth App"
   - Application name: `Agent Team Local`
   - Homepage URL: `http://localhost:3003`
   - Authorization callback URL: `http://localhost:3003/oauth-callback`

3. **获取凭据**:
   - 复制 `Client ID` 到环境变量 `GITHUB_CLIENT_ID`
   - 生成并复制 `Client Secret` 到环境变量 `GITHUB_CLIENT_SECRET`

#### 🟣 Slack OAuth2设置

1. **访问 Slack API**: https://api.slack.com/apps
2. **创建新应用**:
   - 点击 "Create New App"
   - 选择 "From scratch"
   - App Name: `Agent Team Local`
   - 选择你的工作区

3. **配置OAuth & Permissions**:
   - 导航到 "OAuth & Permissions"
   - 在 "Redirect URLs" 添加:
     ```
     http://localhost:3003/oauth-callback
     ```

4. **设置OAuth Scopes**:
   - Bot Token Scopes:
     - `chat:write`
     - `channels:read`
     - `files:write`
     - `users:read`

5. **获取凭据**:
   - 复制 `Client ID` 到环境变量 `SLACK_CLIENT_ID`
   - 复制 `Client Secret` 到环境变量 `SLACK_CLIENT_SECRET`

### 3. 数据库设置

#### Supabase设置
1. **访问 Supabase**: https://supabase.com/dashboard
2. **创建新项目**或使用现有项目
3. **运行数据库迁移**:
   ```bash
   # 在项目根目录运行
   supabase migration up
   ```
4. **获取连接信息**:
   - Project URL → `SUPABASE_URL`
   - Service Role Key → `SUPABASE_SECRET_KEY`
   - Anon Key → `SUPABASE_ANON_KEY`

### 4. 启动服务

#### 后端服务
```bash
# 启动所有后端服务
cd apps/backend
docker-compose up --build

# 或者单独启动
cd apps/backend/api-gateway && python main.py
cd apps/backend/workflow_agent && python main.py
cd apps/backend/workflow_engine && python main.py
```

#### 前端服务
```bash
cd apps/frontend/agent_team_web

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 5. 验证配置

#### 访问测试页面
1. **主页**: http://localhost:3003
2. **Google Calendar测试**: http://localhost:3003/google-calendar-test
3. **综合API测试**: http://localhost:3003/external-apis-test

#### 测试OAuth2流程
1. 打开 Google Calendar 测试页面
2. 点击 "Test Google Calendar Node with OAuth2"
3. 应该弹出 Google 授权窗口
4. 完成授权后应该自动执行 API 调用

## 🔧 故障排除

### 常见问题

#### 1. "redirect_uri_mismatch" 错误
- 检查 Google Cloud Console 中的重定向URI配置
- 确认URI完全匹配: `http://localhost:3003/oauth-callback`

#### 2. "Failed to store credentials" 错误
- 检查 Supabase 数据库迁移是否完成
- 确认 `SUPABASE_SECRET_KEY` 配置正确

#### 3. 前端无法连接后端
- 检查后端服务是否在正确端口运行
- 确认 `NEXT_PUBLIC_API_GATEWAY_URL` 配置正确

#### 4. OAuth2 popup被阻止
- 允许浏览器弹窗
- 或在Chrome中添加例外: chrome://settings/content/popups

### 环境变量检查

```bash
# 检查后端环境变量
cd apps/backend && python -c "
import os
print('GOOGLE_CLIENT_ID:', os.getenv('GOOGLE_CLIENT_ID', 'NOT SET'))
print('SUPABASE_URL:', os.getenv('SUPABASE_URL', 'NOT SET'))
"

# 检查前端环境变量
cd apps/frontend/agent_team_web && npm run build 2>&1 | grep NEXT_PUBLIC
```

### 日志查看

```bash
# 查看后端服务日志
cd apps/backend && docker-compose logs -f

# 查看前端开发日志
cd apps/frontend/agent_team_web && npm run dev
```

## 📋 配置清单

- [ ] Google Cloud Console OAuth2 应用已创建
- [ ] GitHub OAuth App 已创建  
- [ ] Slack App 已创建
- [ ] 后端 `.env` 文件已配置
- [ ] 前端 `.env.local` 文件已配置
- [ ] Supabase 项目已设置
- [ ] 数据库迁移已运行
- [ ] 后端服务启动成功 (端口 8000, 8001, 8002)
- [ ] 前端服务启动成功 (端口 3003)
- [ ] OAuth2 授权流程测试通过

完成以上配置后，你就可以在本地演示完整的External API Integration功能了！

## 🎯 下一步

配置完成后，你可以：
1. 测试 Google Calendar OAuth2 集成
2. 创建包含外部API节点的工作流
3. 体验 N8N 风格的授权流程
4. 查看 API 调用日志和监控数据