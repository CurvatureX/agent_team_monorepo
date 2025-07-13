# Workflow Engine

基于 planning.md 设计的工作流引擎项目。

## 项目结构

```
workflow_engine/
├── workflow_engine/          # 主包
│   ├── __init__.py
│   ├── core/                # 核心配置
│   ├── models/              # 数据模型
│   ├── schemas/             # Pydantic 模式
│   ├── api/                 # API 路由
│   ├── services/            # 业务逻辑
│   ├── nodes/               # 节点实现
│   └── utils/               # 工具函数
├── tests/                   # 测试文件
├── alembic/                 # 数据库迁移
├── pyproject.toml           # 项目配置
└── README.md                # 项目文档
```

## 快速开始

### 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -e .

# 安装开发依赖
pip install -e ".[dev]"
```

### Protocol Buffers

项目包含基于 planning.md 设计的 protobuf 定义：

```bash
# 生成 Python 代码
make proto

# 查看 protobuf 文件
ls protobuf/*.proto
```

### Database Setup

The project uses PostgreSQL with Alembic for migrations:

```bash
# Initialize database
make db-init

# Create new migration
make db-migrate MSG="Add new table"

# Apply migrations
make db-upgrade

# Load complete schema (alternative to migrations)
make db-schema

# Load seed data for development
make db-seed

# Reset database completely
make db-reset
```

#### Database Structure

The database schema is designed to work with protobuf definitions:
- See `database/schema.sql` for complete schema
- See `database/README.md` for detailed documentation
- Protobuf structures are stored as JSONB for flexibility

### 开发工具

```bash
# 代码格式化
black workflow_engine/
isort workflow_engine/

# 运行测试
pytest

# 生成 protobuf 代码
make proto
``` 