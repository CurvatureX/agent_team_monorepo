# 重构后的测试套件

本测试套件是为重构后的 api-gateway 和 workflow_agent 服务设计的，基于最新的 workflow_agent.proto 定义。

## 🏗️ 测试架构

```
tests/
├── auth/                   # 认证功能测试
│   └── test_authentication.py
├── session/                # 会话管理测试
│   └── test_session_management.py
├── chat/                   # 聊天功能测试
│   ├── test_streaming_response.py
│   └── test_response_types.py
├── integration/            # 集成测试
│   ├── test_complete_workflow.py
│   ├── test_legacy_quick.py (旧测试)
│   └── test_simple.py (旧测试)
├── utils/                  # 测试工具
│   └── test_config.py
└── README.md              # 本文档
```

## 🚀 快速开始

### 运行完整测试套件（推荐）
```bash
python run_tests.py --all
```

### 运行快速测试
```bash
python run_tests.py --quick
```

### 运行特定测试
```bash
python run_tests.py --test auth        # 认证测试
python run_tests.py --test session     # 会话管理测试
python run_tests.py --test streaming   # 流式响应测试
python run_tests.py --test types       # 三种返回类型测试
```

### 查看所有可用测试
```bash
python run_tests.py --list
```

## 📋 前置条件

### 必需条件
- API Gateway 运行在 `localhost:8000`
- 有效的 `.env` 文件配置

### 环境变量配置
```bash
# Supabase 配置（完整测试需要）
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SECRET_KEY=your-secret-key

# 测试用户账号（完整测试需要）
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=your-test-password

# OpenAI API（工作流生成需要）
OPENAI_API_KEY=sk-your-openai-key
```

## 🧪 测试类型说明

### 1. 认证功能测试 (`tests/auth/`)
- **目标**: 验证 Supabase JWT 认证流程
- **覆盖**: 
  - 健康检查
  - 用户登录认证
  - 无效凭据处理
  - 受保护端点访问控制
  - JWT token 验证

### 2. 会话管理测试 (`tests/session/`)
- **目标**: 验证会话生命周期管理
- **覆盖**:
  - 会话创建（create/edit/copy actions）
  - 会话获取和列表
  - 动作验证（edit需要workflow_id）
  - 错误处理（无效动作，不存在的会话）

### 3. 流式响应测试 (`tests/chat/test_streaming_response.py`)
- **目标**: 验证 Server-Sent Events 流式响应
- **覆盖**:
  - 基本 SSE 流式响应
  - SSE 格式验证（Content-Type, data: 前缀）
  - 并发流式连接
  - 超时处理

### 4. 三种返回类型测试 (`tests/chat/test_response_types.py`)
- **目标**: 验证升级后的三种返回类型架构
- **覆盖**:
  - **AI Message 响应**: 纯文本AI回复
  - **Workflow 响应**: 工作流数据结构
  - **Error 响应**: 错误消息和代码
  - **Status 响应**: 状态更新信息
  - **混合场景**: 多种类型组合

### 5. 完整集成测试 (`tests/integration/`)
- **目标**: 端到端完整系统验证
- **覆盖**: 所有上述测试的组合，验证整体系统稳定性

## 🎯 测试重点

### 核心升级验证
- ✅ 新的 `workflow_agent.proto` 文件正常工作
- ✅ gRPC 客户端和服务端升级成功
- ✅ 三种返回类型（ai_message, workflow, error）正常
- ✅ 状态管理：只在 `is_final=true` 时保存数据库
- ✅ LangGraph 节点状态累积逻辑正常

### 系统稳定性验证  
- ✅ 流式响应稳定性
- ✅ 并发处理能力
- ✅ 错误处理和恢复
- ✅ 超时和边界条件处理

## 📊 测试报告解读

### 成功指标
- **通过率 100%**: 所有核心功能正常
- **通过率 80-99%**: 系统基本正常，部分功能需检查
- **通过率 < 80%**: 系统存在问题，需要修复

### 常见问题和解决方案

#### 认证测试失败
```bash
❌ 认证测试失败
```
**解决方案**: 检查 `.env` 文件中的 Supabase 配置

#### 流式响应超时
```bash  
❌ 流式响应测试超时
```
**解决方案**: 检查 API Gateway 和 workflow_agent 服务状态

#### 三种返回类型异常
```bash
❌ 未收到期望的响应类型
```
**解决方案**: 检查 gRPC 客户端和服务端升级是否正确

## 🔧 开发和调试

### 添加新测试
1. 在相应目录下创建测试文件
2. 继承基础测试类或使用 `test_config`
3. 在 `run_tests.py` 中注册新测试

### 调试失败的测试
1. 运行单个测试：`python run_tests.py --test <test_name>`
2. 检查 API Gateway 日志
3. 检查环境变量配置
4. 使用简化测试验证基本功能

### 性能优化
- 所有测试都有独立的超时控制
- 响应数量限制防止无限循环
- 测试间有适当的等待时间

## 📈 测试数据

### 典型运行时间
- 快速测试: ~30秒
- 完整测试: ~2-3分钟
- 单个测试: ~15-60秒

### 资源使用
- 网络连接: HTTP/HTTPS + SSE 流式连接
- 内存使用: 轻量级，主要用于JSON处理
- 数据库: 创建测试会话，不影响生产数据

## 🎉 成功标准

完整测试通过表示：
- ✅ 升级后的工作流系统完全可用
- ✅ 三种返回类型架构工作正常  
- ✅ 所有核心功能验证通过
- ✅ 系统满足生产使用要求

## 📞 支持

如果测试失败或有问题：
1. 检查此文档的故障排除部分
2. 确认环境配置正确
3. 查看具体测试的错误输出
4. 使用简化测试隔离问题