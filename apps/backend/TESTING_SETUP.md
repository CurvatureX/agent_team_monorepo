# 生产环境集成测试设置指南

## 概述

本文档介绍如何配置和运行完整的生产环境集成测试，包括真实的Supabase认证和完整的API Gateway + workflow_agent集成测试。

## 环境配置

### 1. 创建.env文件

复制env.example文件为.env：

```bash
cp env.example .env
```

### 2. 配置环境变量

编辑.env文件，填入真实的配置信息：

```bash
# Supabase配置
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-public-key

# AI模型配置
OPENAI_API_KEY=sk-your-openai-api-key
DEFAULT_MODEL_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4o-mini

# 测试账号（用于集成测试）
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=your-test-password

# 服务配置
API_GATEWAY_PORT=8000
WORKFLOW_AGENT_PORT=50051

# 环境配置
ENVIRONMENT=development
DEBUG=true
```

### 3. 配置说明

- **SUPABASE_URL**: 你的Supabase项目URL
- **SUPABASE_SERVICE_KEY**: 服务角色密钥（用于RLS绕过）
- **SUPABASE_ANON_KEY**: 匿名公钥（用于认证API调用）
- **TEST_USER_EMAIL/PASSWORD**: 测试用户账号，需要在Supabase Auth中存在
- **OPENAI_API_KEY**: OpenAI API密钥

## 测试账号准备

### 在Supabase中创建测试用户

1. 进入Supabase Dashboard > Authentication > Users
2. 点击"Add user"
3. 输入测试邮箱和密码
4. 确认用户已创建并激活

## 运行测试

### 1. 启动所有服务

```bash
./start_all_services.sh
```

这个脚本会：
- 自动加载.env文件
- 检查环境变量
- 启动workflow_agent (gRPC服务)
- 启动API Gateway (HTTP服务)
- 进行健康检查

### 2. 运行集成测试

```bash
python test_production_integration.py
```

测试流程包括：
1. **代码结构验证** - 检查关键文件和模块导入
2. **workflow_agent直接测试** - 测试LangGraph工作流
3. **用户认证测试** - 通过Supabase获取真实JWT token
4. **API Gateway集成测试** - 测试完整的session创建和chat流程

### 3. 停止服务

```bash
./stop_all_services.sh
```

## 测试场景

集成测试包含以下场景：

### 场景1: 创建邮件处理工作流
- 创建新的session (action: create)
- 发送用户消息: "我需要创建一个自动处理Gmail邮件并发送Slack通知的工作流"
- 验证SSE流响应和状态变更

### 场景2: 编辑现有工作流
- 创建编辑session (action: edit)
- 发送修改请求: "我想修改这个工作流，增加邮件分类功能"
- 验证编辑流程

## 故障排除

### 常见问题

1. **认证失败**
   - 检查SUPABASE_URL、TEST_USER_EMAIL、TEST_USER_PASSWORD配置
   - 确认测试用户在Supabase中存在且已激活
   - 检查SUPABASE_ANON_KEY是否正确

2. **服务启动失败**
   - 检查端口8000和50051是否被占用
   - 查看logs/目录下的服务日志
   - 确认所有依赖包已安装

3. **OpenAI API错误**
   - 检查OPENAI_API_KEY是否有效
   - 确认API密钥有足够的配额

### 查看日志

服务日志保存在logs/目录：
- `logs/api_gateway.log` - API Gateway日志
- `logs/workflow_agent.log` - workflow_agent日志

## 预期结果

成功的测试运行应该显示：
- ✅ 代码结构验证通过
- ✅ workflow_agent直接测试通过
- ✅ 用户认证成功
- ✅ session创建成功
- ✅ chat流程完整响应

通过率应该达到80%以上才认为系统准备就绪。 