# Workflow Engine Unified Server

## 概述

这是一个统一的gRPC服务器，整合了工作流引擎的所有服务，确保所有数据操作都通过真实的数据库完成。

## 🚀 快速开始

### 1. 启动服务器

```bash
# 启动服务器
./start_server.sh start

# 查看服务器状态
./start_server.sh status

# 查看日志
./start_server.sh logs

# 测试服务器
./start_server.sh test
```

### 2. 停止服务器

```bash
# 停止服务器
./start_server.sh stop

# 重启服务器
./start_server.sh restart
```

## 📁 文件结构

```
workflow_engine/
├── server.py              # 统一服务器主文件
├── start_server.sh        # 服务器管理脚本
├── database_service.py    # 数据库服务
├── database_grpc_server.py # 数据库版本gRPC服务器
├── simple_grpc_server.py  # 内存版本gRPC服务器（仅用于测试）
└── workflow_engine/
    ├── main.py            # 原始主服务器
    ├── services/          # 服务层
    ├── models/            # 数据模型
    └── core/              # 核心配置
```

## 🔧 服务器管理

### 启动脚本命令

| 命令 | 描述 |
|------|------|
| `start` | 启动服务器 |
| `stop` | 停止服务器 |
| `restart` | 重启服务器 |
| `status` | 查看服务器状态 |
| `logs` | 查看服务器日志 |
| `test` | 测试服务器连接 |
| `help` | 显示帮助信息 |

### 示例

```bash
# 启动服务器
./start_server.sh start

# 查看状态
./start_server.sh status

# 查看实时日志
./start_server.sh logs

# 测试连接
./start_server.sh test
```

## 🗄️ 数据库配置

服务器会自动：

1. **连接数据库** - 使用配置文件中的数据库URL
2. **初始化表结构** - 创建必要的数据表
3. **验证连接** - 确保数据库连接正常

### 数据库要求

- PostgreSQL 14+
- 支持SSL连接（Supabase）
- 必要的扩展：`uuid-ossp`

## 🔍 服务检查

### 健康检查

```bash
# gRPC健康检查
python -c "
import grpc
from grpc_health.v1 import health_pb2_grpc, health_pb2

channel = grpc.insecure_channel('localhost:50051')
stub = health_pb2_grpc.HealthStub(channel)
response = stub.Check(health_pb2.HealthCheckRequest())
print(f'Health status: {response.status}')
"
```

### 服务列表

- **WorkflowService** - 工作流CRUD操作
- **HealthService** - 健康检查服务

## 🐛 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查数据库配置
   python test_database.py
   ```

2. **服务器启动失败**
   ```bash
   # 查看详细日志
   tail -f workflow_engine.log
   ```

3. **端口被占用**
   ```bash
   # 查找占用端口的进程
   lsof -i :50051
   ```

### 日志文件

- **主日志**: `workflow_engine.log`
- **PID文件**: `workflow_engine.pid`

## 🔄 从旧版本迁移

### 停止旧服务器

```bash
# 停止内存版本服务器
pkill -f simple_grpc_server

# 停止其他版本服务器
pkill -f workflow_engine
```

### 启动新服务器

```bash
# 启动统一服务器
./start_server.sh start
```

## 📊 监控

### 服务器状态

```bash
# 查看进程状态
ps aux | grep server.py

# 查看端口监听
netstat -tlnp | grep 50051
```

### 性能监控

```bash
# 查看内存使用
ps -o pid,ppid,cmd,%mem,%cpu --sort=-%mem | grep server.py

# 查看日志大小
ls -lh workflow_engine.log
```

## 🔒 安全注意事项

1. **数据库安全**
   - 使用强密码
   - 启用SSL连接
   - 限制数据库访问权限

2. **网络安全**
   - 配置防火墙规则
   - 使用HTTPS/gRPC-TLS
   - 限制服务器访问

3. **日志安全**
   - 定期清理日志文件
   - 避免记录敏感信息
   - 设置日志轮转

## 📝 开发说明

### 添加新服务

1. 在 `server.py` 中添加服务导入
2. 注册服务到gRPC服务器
3. 更新健康检查配置

### 修改配置

编辑 `workflow_engine/core/config.py` 或设置环境变量：

```bash
export DATABASE_URL="postgresql://user:pass@host:port/db"
export GRPC_HOST="0.0.0.0"
export GRPC_PORT="50051"
```

## 🤝 贡献

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。 