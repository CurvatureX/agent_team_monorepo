# Cursor IDE 设置指南 - 解决 workflow_agent 导入问题

## 问题描述

在使用 backend 目录下的 `.venv` 虚拟环境时，Cursor IDE 无法正确解析 `workflow_agent` 中的模块导入，导致以下错误：
- `无法解析导入 "core.config"`
- `无法解析导入 "agents.workflow_agent"`
- `无法解析导入 "agents.state"`
- 等等...

## 解决方案

### 1. 项目结构配置

已创建以下配置文件来解决导入问题：

#### A. 根目录 `pyrightconfig.json`
```json
{
  "typeCheckingMode": "basic",
  "reportAttributeAccessIssue": false,
  "reportArgumentType": false,
  "reportOptionalMemberAccess": false,
  "venvPath": "apps/backend",
  "venv": ".venv",
  "extraPaths": [
    "apps/backend/workflow_agent",
    "apps/backend/api-gateway",
    "apps/backend/shared"
  ],
  "executionEnvironments": [
    {
      "root": "apps/backend/workflow_agent",
      "pythonPath": "apps/backend/.venv/bin/python",
      "extraPaths": [
        "apps/backend/workflow_agent",
        "apps/backend/shared"
      ]
    },
    {
      "root": "apps/backend/api-gateway", 
      "pythonPath": "apps/backend/.venv/bin/python",
      "extraPaths": [
        "apps/backend/api-gateway",
        "apps/backend/shared"
      ]
    }
  ]
}
```

#### B. workflow_agent 目录下的 `pyrightconfig.json`
```json
{
  "typeCheckingMode": "basic",
  "reportAttributeAccessIssue": false,
  "reportArgumentType": false,
  "reportOptionalMemberAccess": false,
  "venvPath": "..",
  "venv": ".venv",
  "pythonPath": "../.venv/bin/python",
  "extraPaths": [
    ".",
    "../shared"
  ],
  "include": [
    "."
  ],
  "exclude": [
    "**/__pycache__",
    "**/.mypy_cache",
    "**/node_modules"
  ]
}
```

#### C. 工作区配置 `agent_team_monorepo.code-workspace`
```json
{
  "folders": [
    {
      "name": "Root",
      "path": "."
    },
    {
      "name": "Workflow Agent",
      "path": "./apps/backend/workflow_agent"
    },
    {
      "name": "API Gateway", 
      "path": "./apps/backend/api-gateway"
    },
    {
      "name": "Frontend",
      "path": "./apps/frontend"
    }
  ],
  "settings": {
    "python.defaultInterpreterPath": "./apps/backend/.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.analysis.extraPaths": [
      "./apps/backend/workflow_agent",
      "./apps/backend/api-gateway", 
      "./apps/backend/shared"
    ],
    "python.analysis.autoSearchPaths": true,
    "python.analysis.autoImportCompletions": true,
    "pyright.include": [
      "./apps/backend/workflow_agent",
      "./apps/backend/api-gateway"
    ],
    "pyright.extraPaths": [
      "./apps/backend/workflow_agent",
      "./apps/backend/api-gateway",
      "./apps/backend/shared"
    ]
  }
}
```

### 2. 虚拟环境设置

确保 `workflow_agent` 包正确安装到虚拟环境中：

```bash
cd apps/backend
source .venv/bin/activate

# 安装 workflow_agent 包 (开发模式)
cd workflow_agent
uv pip install -e '.[dev]'
cd ..

# 同步所有依赖
uv sync --all-extras
```

### 3. 验证安装

运行测试脚本验证所有导入都正常工作：

```bash
cd apps/backend
python test_imports.py
```

应该看到所有导入都成功：
```
🧪 Testing Python Environment Setup
==================================================
Test 1: workflow_agent as installed package
✅ workflow_agent found at: /path/to/workflow_agent/__init__.py

Test 2: Direct imports from workflow_agent directory
✅ core.config imported successfully
✅ agents.workflow_agent imported successfully
✅ agents.state imported successfully
✅ agents.state_converter imported successfully
✅ proto.workflow_agent_pb2 imported successfully
✅ proto.workflow_agent_pb2_grpc imported successfully
✅ services.grpc_server imported successfully
```

## 使用指南

### 步骤 1: 打开工作区
在 Cursor 中打开 `agent_team_monorepo.code-workspace` 文件

### 步骤 2: 选择 Python 解释器
1. 按 `Cmd+Shift+P` (macOS) 或 `Ctrl+Shift+P` (Windows/Linux)
2. 输入 "Python: Select Interpreter"
3. 选择 `./apps/backend/.venv/bin/python`

### 步骤 3: 重启 IDE
如果导入错误仍然存在，重启 Cursor IDE

### 步骤 4: 验证
在 `apps/backend/workflow_agent/services/grpc_server.py` 中，所有导入应该不再显示错误：
- `from core.config import settings` ✅
- `from agents.workflow_agent import WorkflowAgent` ✅
- `from agents.state import WorkflowStage, WorkflowOrigin` ✅
- `from agents.state_converter import StateConverter` ✅

## 故障排除

### 如果导入仍然不工作：

1. **检查虚拟环境激活**：
   ```bash
   cd apps/backend
   source .venv/bin/activate
   which python  # 应该指向 .venv/bin/python
   ```

2. **重新安装包**：
   ```bash
   cd workflow_agent
   uv pip uninstall workflow-agent
   uv pip install -e '.[dev]'
   ```

3. **清理缓存**：
   ```bash
   find . -name "__pycache__" -type d -exec rm -rf {} +
   find . -name "*.pyc" -delete
   ```

4. **重启 Python 语言服务器**：
   - 在 Cursor 中按 `Cmd+Shift+P`
   - 运行 "Python: Restart Language Server"

## 技术说明

这个解决方案解决了以下技术问题：

1. **Python 路径解析**: 通过 `extraPaths` 确保 Pyright 能找到所有模块
2. **虚拟环境识别**: 通过 `venvPath` 和 `pythonPath` 确保使用正确的解释器
3. **工作区配置**: 通过多文件夹工作区支持复杂的 monorepo 结构
4. **包安装**: 通过开发模式安装确保代码更改立即可见

现在 Cursor IDE 应该能够正确解析所有 workflow_agent 的导入了！ 