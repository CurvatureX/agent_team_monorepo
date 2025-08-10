# 🚀 Local Demo Guide - 外部API集成演示指南

## 📋 概述

本指南帮助您在本地环境演示完整的外部API集成功能，特别是Google Calendar OAuth2集成流程。

## ✅ 预配置检查清单

### 1. **环境变量配置** ✅ 已完成
- **后端**: `apps/backend/.env` - 包含完整的OAuth2凭证
- **前端**: `apps/frontend/agent_team_web/.env.local` - 包含客户端ID

### 2. **Google Cloud Console配置** ⚠️ 需要验证

请确保以下重定向URI已添加到您的Google OAuth2应用：

```
http://localhost:3000/oauth-callback
```

**配置步骤**:
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 导航: `APIs & Services` → `Credentials`
3. 编辑客户端ID: `180114411774-u2a1ndcatao2q8l5ajolceg5t7t22mjj`
4. 在 "Authorized redirect URIs" 添加上述URI
5. 保存配置

## 🖥️ 本地启动步骤

### 方法一：仅前端演示（推荐）

如果您只需要演示OAuth2流程和前端功能：

```bash
# 1. 启动前端服务
cd apps/frontend/agent_team_web
npm run dev

# 2. 打开浏览器访问
http://localhost:3000/google-calendar-test
```

### 方法二：完整后端+前端

如果需要完整的后端集成：

```bash
# 1. 启动后端工作流引擎
cd apps/backend/workflow_engine
export PYTHONPATH=/Users/bytedance/personal/curvaturex/agent_team_monorepo/apps/backend
python3 -m workflow_engine.main

# 2. 在另一个终端启动前端
cd apps/frontend/agent_team_web  
npm run dev

# 3. 访问演示页面
http://localhost:3000/google-calendar-test
```

## 🎯 演示流程

### Google Calendar事件创建演示

1. **访问测试页面**
   - URL: http://localhost:3000/google-calendar-test
   - 页面会显示当前OAuth2授权状态

2. **填写事件详情**
   - **事件标题**: 输入事件名称 (默认: "Test Event from Agent Team")
   - **地点**: 输入事件地点 (默认: "Virtual Meeting") 
   - **事件描述**: 输入详细描述
   - **开始时间**: 选择日期和时间 (默认: 今天 10:00)
   - **结束时间**: 选择日期和时间 (默认: 今天 11:00)

3. **创建事件**
   - 点击 "创建 Google Calendar 事件" 按钮
   - 系统自动检测是否需要OAuth2授权

4. **自动授权流程** (仅首次需要)
   - 如需授权，自动弹出Google授权页面
   - 选择您的Google账户并授予日历权限
   - 完成授权后自动关闭弹窗
   - 系统自动存储凭据并重新执行事件创建

5. **查看结果**
   - 成功后显示事件创建确认信息
   - 包含事件ID和Google Calendar链接
   - 失败时显示详细的错误信息和日志

6. **验证创建结果**
   - 点击结果中的 "查看事件" 链接，或
   - 直接打开 [Google Calendar](https://calendar.google.com)
   - 查找刚创建的事件并确认详情是否正确

## 🔧 功能特性演示

### 1. **事件创建功能**
- 完整的事件表单，支持标题、描述、地点、时间设置
- 真实的Google Calendar事件创建
- 创建成功后可直接在Google Calendar中查看

### 2. **智能检测**
- 自动检测用户是否已有有效的OAuth2凭据
- 无需授权时直接执行事件创建
- 首次使用自动引导授权流程

### 3. **弹窗授权**
- N8N风格的弹窗授权体验
- 支持跨域安全处理
- 自动状态验证和错误处理
- 授权完成后自动重新创建事件

### 4. **凭据管理**
- AES-256加密存储OAuth2 token
- 自动token刷新机制
- 用户级别的凭据隔离
- 一次授权，永久使用

### 5. **结果验证**
- 显示创建事件的详细信息
- 提供Google Calendar直达链接
- 完整的错误处理和重试机制
- 结构化的响应数据展示

## 📊 API端点测试

如果后端正常运行，您也可以直接测试API端点：

### 检查凭据状态
```bash
curl -X POST "http://localhost:8002/api/v1/credentials/check" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "7ba36345-a2bb-4ec9-a001-bb46d79d629d",
    "provider": "google_calendar"
  }'
```

### 创建事件测试工作流
```bash
curl -X POST "http://localhost:8002/v1/workflows" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "7ba36345-a2bb-4ec9-a001-bb46d79d629d",
    "name": "Google Calendar Create Event Test",
    "nodes": [{
      "id": "google_create_test",
      "type": "EXTERNAL_ACTION_NODE",
      "subtype": "GOOGLE_CALENDAR",
      "parameters": {
        "action": "create_event",
        "calendar_id": "primary",
        "summary": "API Test Event",
        "description": "Event created via direct API call",
        "location": "Test Location"
      }
    }]
  }'
```

## ❌ 常见问题解决

### 1. "redirect_uri_mismatch" 错误
- **原因**: Google Cloud Console中未配置正确的重定向URI
- **解决**: 添加 `http://localhost:3000/oauth-callback` 到授权重定向URI

### 2. 前端无法连接后端
- **原因**: 后端服务未启动或端口冲突
- **解决**: 确保后端运行在8002端口，或只使用前端演示

### 3. OAuth2弹窗被阻止
- **原因**: 浏览器阻止弹窗
- **解决**: 允许此站点的弹窗，然后重试

### 4. "Invalid client" 错误
- **原因**: Google客户端配置不正确
- **解决**: 验证客户端ID和密钥是否匹配

## 🎉 预期演示效果

成功演示后，您将看到：

1. **授权状态显示**: 绿色"已授权"或红色"未授权"状态
2. **智能创建流程**: 填写表单→一键创建→自动检测授权→弹窗授权（如需）→事件创建成功
3. **真实事件创建**: 在您的Google Calendar中创建真实的日历事件
4. **创建结果确认**: 
   - 事件ID和详细信息展示
   - Google Calendar直达链接
   - 创建时间和参数确认
5. **即时验证**: 点击链接直接在Google Calendar中查看创建的事件
6. **完整日志**: 详细的执行步骤和API调用日志

这个演示完美展示了与N8N等平台相同的用户体验：用户只需关注业务逻辑（填写事件详情），系统会智能处理所有OAuth2授权细节，并创建真实可用的外部API资源。

## 📞 技术支持

如果在演示过程中遇到问题：
1. 检查浏览器控制台的错误信息
2. 验证Google Cloud Console配置
3. 确认环境变量配置正确
4. 检查网络连接和防火墙设置