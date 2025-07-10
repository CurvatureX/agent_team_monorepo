---
id: tech-design-intro
title: Technical Design Documentation
sidebar_label: Tech Design
sidebar_position: 1
---

# Technical Design Documentation

This section contains technical design guidelines and resources for the Workflow Agent Team project.

## 📋 文档目录

- **[MVP 产品规划](./planning.md)** - 产品 MVP 规划和排期
- **[Workflow 数据结构定义](./[MVP]%20Workflow%20Data%20Structure%20Definition.md)** - 工作流数据结构设计
- **[节点结构定义](./node-structure.md)** - 节点类型和参数配置
- **[API Gateway 架构](./api-gateway-architecture.md)** - API Gateway 技术架构设计
- **[Workflow Agent 架构](./workflow-agent-architecture.md)** - Workflow Agent 技术架构设计

## 🐍 Python 开发基础知识

### Python 版本要求

项目使用 **Python 3.11+**，这是为了利用最新的性能优化和类型提示功能。

#### 安装 Python 3.11+

**macOS (推荐使用 Homebrew)**:

```bash
# 安装 Homebrew (如果还没有)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python 3.11
brew install python@3.11

# 验证安装
python3.11 --version
```

**Ubuntu/Debian**:

```bash
# 更新包管理器
sudo apt update

# 安装 Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev

# 验证安装
python3.11 --version
```

**Windows**:

1. 访问 [Python 官网](https://www.python.org/downloads/)
2. 下载 Python 3.11+ 安装包
3. 运行安装程序，记得勾选 "Add Python to PATH"

### 虚拟环境概念

Python 虚拟环境是一个独立的 Python 运行环境，用于隔离不同项目的依赖包。

#### 为什么需要虚拟环境？

1. **依赖隔离**: 不同项目可能需要同一个包的不同版本
2. **系统保护**: 避免污染系统级 Python 环境
3. **依赖管理**: 清晰地管理项目所需的包和版本
4. **部署一致性**: 确保开发、测试、生产环境的一致性

#### 传统的虚拟环境管理

```bash
# 创建虚拟环境
python3.11 -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 退出虚拟环境
deactivate
```

## 📦 现代 Python 依赖管理：uv

我们的项目使用 [uv](https://github.com/astral-sh/uv) 作为包管理器，这是一个极速的 Python 包管理工具。

### 为什么选择 uv？

1. **极速**: 比 pip 快 10-100 倍
2. **兼容性**: 与 pip 完全兼容
3. **简单**: 无需手动管理虚拟环境
4. **现代**: 支持 pyproject.toml 标准
5. **可靠**: 更好的依赖解析和锁定

### uv 安装

**macOS/Linux**:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**:

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**通过 pip 安装**:

```bash
pip install uv
```

### uv 基本使用

#### 项目初始化

```bash
# 创建新项目
uv init my-project
cd my-project

# 或者在现有项目中初始化
uv init
```

#### 依赖管理

```bash
# 安装依赖 (会自动创建虚拟环境)
uv sync

# 安装开发依赖
uv sync --dev

# 添加新依赖
uv add fastapi
uv add pytest --dev  # 添加开发依赖

# 移除依赖
uv remove package-name

# 更新依赖
uv sync --upgrade
```

#### 运行命令

```bash
# 在虚拟环境中运行命令
uv run python main.py
uv run pytest
uv run black .

# 启动 shell (激活虚拟环境)
uv shell
```

#### 锁定文件

```bash
# 生成锁定文件 (类似 package-lock.json)
uv lock

# 从锁定文件安装
uv sync --locked
```

### pyproject.toml 配置文件

项目使用 `pyproject.toml` 替代传统的 `requirements.txt`：

```toml
[project]
name = "my-project"
version = "1.0.0"
description = "Project description"
requires-python = ">=3.11"

dependencies = [
    "fastapi==0.104.1",
    "uvicorn[standard]==0.24.0",
    "pydantic==2.5.0",
]

[project.optional-dependencies]
dev = [
    "pytest==7.4.3",
    "black==23.11.0",
    "mypy==1.7.1",
]

[tool.black]
line-length = 100
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
warn_return_any = true
disallow_untyped_defs = true
```

## 🏗️ 项目结构和工作空间

### 工作空间配置

我们的后端项目使用工作空间来管理多个相关的包：

```toml
# 根目录的 pyproject.toml
[tool.uv.workspace]
members = ["api-gateway", "workflow_agent"]
```

这样可以：

- 统一管理多个服务的依赖
- 共享通用配置和工具
- 简化开发和部署流程

### 项目结构

```
apps/backend/
├── pyproject.toml          # 工作空间配置
├── api-gateway/            # API Gateway 服务
│   ├── pyproject.toml     # 服务特定依赖
│   ├── main.py            # 应用入口
│   └── ...
├── workflow_agent/         # Workflow Agent 服务
│   ├── pyproject.toml     # 服务特定依赖
│   ├── main.py            # 应用入口
│   └── ...
└── shared/                 # 共享代码
    └── proto/             # gRPC 定义
```

## 🚀 开发工作流

### 1. 克隆项目

```bash
git clone <repository-url>
cd agent_team_monorepo/apps/backend
```

### 2. 安装 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 安装依赖

```bash
# 安装所有工作空间的依赖
uv sync --dev
```

### 4. 启动开发服务

**选项 1: 使用 Docker (推荐)**

```bash
./start-dev.sh
```

**选项 2: 本地开发**

```bash
./start-dev-local.sh

# 然后在不同终端启动服务
cd workflow_agent && uv run python -m main
cd api-gateway && uv run uvicorn main:app --reload --port 8000
```

### 5. 开发工具

```bash
# 代码格式化
uv run black .

# 代码检查
uv run flake8 .

# 类型检查
uv run mypy .

# 运行测试
uv run pytest

# 安装新依赖
uv add some-package

# 更新依赖
uv sync --upgrade
```

## 🔧 常用命令速查

### uv 命令

```bash
uv sync              # 安装/更新依赖
uv sync --dev        # 包含开发依赖
uv add package       # 添加依赖
uv remove package    # 移除依赖
uv run command       # 在虚拟环境中运行命令
uv shell            # 激活虚拟环境
uv lock             # 生成锁定文件
```

### 开发命令

```bash
# 启动服务
uv run uvicorn main:app --reload --port 8000

# 运行测试
uv run pytest tests/

# 代码质量
uv run black .           # 格式化
uv run isort .           # 导入排序
uv run flake8 .          # 代码检查
uv run mypy .            # 类型检查

# 生成 gRPC 代码
cd shared && uv run python scripts/generate_grpc.py
```

## 🐛 常见问题解决

### Python 版本问题

```bash
# 检查 Python 版本
python3 --version

# 如果版本不匹配，指定 Python 路径
uv python install 3.11
uv python pin 3.11
```

### 依赖冲突

```bash
# 清理并重新安装
rm -rf .venv uv.lock
uv sync --dev

# 查看依赖树
uv tree
```

### 虚拟环境问题

```bash
# 手动重建虚拟环境
rm -rf .venv
uv sync --dev

# 检查虚拟环境位置
uv run which python
```

### gRPC 代码生成问题

```bash
# 确保安装了 grpcio-tools
uv add grpcio-tools --dev

# 重新生成 proto 文件
cd shared && uv run python scripts/generate_grpc.py
```

## 📚 学习资源

### Python 基础

- [Python 官方教程](https://docs.python.org/3/tutorial/)
- [Real Python](https://realpython.com/) - 高质量 Python 教程
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

### 项目相关技术

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [gRPC Python 文档](https://grpc.io/docs/languages/python/)
- [uv 文档](https://docs.astral.sh/uv/)

### 最佳实践

- [Python Packaging User Guide](https://packaging.python.org/)
- [PEP 8 代码风格指南](https://pep8.org/)
- [Python 类型提示最佳实践](https://typing.readthedocs.io/en/latest/)
