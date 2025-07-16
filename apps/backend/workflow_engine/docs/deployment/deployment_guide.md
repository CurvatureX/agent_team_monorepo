# Workflow Engine 部署指南

## 概述

本文档详细说明如何在不同环境中部署 Workflow Engine，包括开发环境、测试环境和生产环境的配置与部署流程。

## 系统要求

### 最低要求

- **操作系统**: Linux (Ubuntu 20.04+, CentOS 7+) 或 macOS 10.15+
- **Python**: 3.9+
- **内存**: 4GB RAM
- **存储**: 20GB 可用空间
- **网络**: 稳定的互联网连接

### 推荐配置

- **CPU**: 4 cores+
- **内存**: 8GB+ RAM
- **存储**: 50GB+ SSD
- **数据库**: PostgreSQL 14+
- **缓存**: Redis 6+

### 依赖服务

- **PostgreSQL 14+**: 主数据库
- **Redis 6+**: 缓存和会话存储
- **Docker**: 容器化部署（可选）
- **Nginx**: 反向代理（生产环境推荐）

## 环境配置

### 1. 开发环境

#### 本地开发设置

```bash
# 1. 克隆项目
git clone <repository-url>
cd agent_team_monorepo/apps/backend/workflow_engine

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 环境变量配置
cp .env.example .env
# 编辑 .env 文件配置数据库连接等信息

# 5. 数据库初始化
alembic upgrade head

# 6. 启动服务
python -m workflow_engine.main
```

#### 开发环境变量

```bash
# .env.development
DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_engine_dev
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=DEBUG
DEBUG=true

# API Keys (开发测试用)
OPENAI_API_KEY=your_openai_api_key
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_google_client_secret
GITHUB_OAUTH_CLIENT_ID=your_github_client_id
GITHUB_OAUTH_CLIENT_SECRET=your_github_client_secret
SLACK_OAUTH_CLIENT_ID=your_slack_client_id
SLACK_OAUTH_CLIENT_SECRET=your_slack_client_secret

# 安全配置
SECRET_KEY=dev-secret-key-change-in-production
CREDENTIAL_ENCRYPTION_KEY=dev-encryption-key-32-chars-long
```

### 2. Docker 环境

#### Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  workflow-engine:
    build: .
    ports:
      - "50051:50051"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/workflow_engine
      - REDIS_URL=redis://redis:6379/0
      - LOG_LEVEL=INFO
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:14
    environment:
      POSTGRES_DB: workflow_engine
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/001_schema.sql
      - ./database/migrations/002_audit_logs.sql:/docker-entrypoint-initdb.d/002_audit_logs.sql
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - workflow-engine
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

#### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 设置环境变量
ENV PYTHONPATH=/app
ENV GRPC_PORT=50051

# 暴露端口
EXPOSE 50051

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); channel.close()" || exit 1

# 启动命令
CMD ["python", "-m", "workflow_engine.main"]
```

#### 启动 Docker 环境

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f workflow-engine

# 停止服务
docker-compose down
```

### 3. 生产环境

#### 生产环境架构

```
                    Load Balancer
                         |
                    ┌────┴────┐
                    │  Nginx  │
                    └────┬────┘
                         |
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐     ┌────▼────┐     ┌────▼────┐
   │ Engine  │     │ Engine  │     │ Engine  │
   │Instance │     │Instance │     │Instance │
   │   #1    │     │   #2    │     │   #3    │
   └────┬────┘     └────┬────┘     └────┬────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                 ┌───────┴───────┐
                 │               │
            ┌────▼────┐     ┌───▼───┐
            │PostgreSQL│     │ Redis │
            │ Cluster │     │Cluster│
            └─────────┘     └───────┘
```

#### 生产环境变量

```bash
# .env.production
DATABASE_URL=postgresql://username:password@db-cluster:5432/workflow_engine
REDIS_URL=redis://redis-cluster:6379/0
LOG_LEVEL=INFO
DEBUG=false

# gRPC 配置
GRPC_HOST=0.0.0.0
GRPC_PORT=50051

# 安全配置
SECRET_KEY=your-production-secret-key-64-chars
CREDENTIAL_ENCRYPTION_KEY=your-production-encryption-key-32-chars

# API Keys (生产环境)
OPENAI_API_KEY=prod_openai_api_key
GOOGLE_OAUTH_CLIENT_ID=prod_google_client_id
GOOGLE_OAUTH_CLIENT_SECRET=prod_google_client_secret
GITHUB_OAUTH_CLIENT_ID=prod_github_client_id
GITHUB_OAUTH_CLIENT_SECRET=prod_github_client_secret
SLACK_OAUTH_CLIENT_ID=prod_slack_client_id
SLACK_OAUTH_CLIENT_SECRET=prod_slack_client_secret

# 性能配置
MAX_CONCURRENT_REQUESTS_PER_USER=50
MAX_RESPONSE_SIZE_MB=50
API_TIMEOUT_CONNECT=10
API_TIMEOUT_READ=60
API_MAX_RETRIES=3

# 监控配置
ENABLE_METRICS=true
METRICS_PORT=9090
```

## Kubernetes 部署

### 1. Namespace 配置

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: workflow-engine
  labels:
    name: workflow-engine
```

### 2. ConfigMap 配置

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: workflow-engine-config
  namespace: workflow-engine
data:
  LOG_LEVEL: "INFO"
  GRPC_PORT: "50051"
  MAX_CONCURRENT_REQUESTS_PER_USER: "50"
  ENABLE_METRICS: "true"
  METRICS_PORT: "9090"
```

### 3. Secret 配置

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: workflow-engine-secrets
  namespace: workflow-engine
type: Opaque
data:
  DATABASE_URL: <base64-encoded-database-url>
  REDIS_URL: <base64-encoded-redis-url>
  SECRET_KEY: <base64-encoded-secret-key>
  CREDENTIAL_ENCRYPTION_KEY: <base64-encoded-encryption-key>
  OPENAI_API_KEY: <base64-encoded-openai-key>
  GOOGLE_OAUTH_CLIENT_SECRET: <base64-encoded-google-secret>
  GITHUB_OAUTH_CLIENT_SECRET: <base64-encoded-github-secret>
  SLACK_OAUTH_CLIENT_SECRET: <base64-encoded-slack-secret>
```

### 4. Deployment 配置

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: workflow-engine
  namespace: workflow-engine
  labels:
    app: workflow-engine
spec:
  replicas: 3
  selector:
    matchLabels:
      app: workflow-engine
  template:
    metadata:
      labels:
        app: workflow-engine
    spec:
      containers:
      - name: workflow-engine
        image: workflow-engine:latest
        ports:
        - containerPort: 50051
          name: grpc
        - containerPort: 9090
          name: metrics
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: workflow-engine-secrets
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: workflow-engine-secrets
              key: REDIS_URL
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: workflow-engine-secrets
              key: SECRET_KEY
        envFrom:
        - configMapRef:
            name: workflow-engine-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import grpc; channel = grpc.insecure_channel('localhost:50051'); channel.close()"
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - python
            - -c
            - "import grpc; channel = grpc.insecure_channel('localhost:50051'); channel.close()"
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: logs
        emptyDir: {}
      imagePullSecrets:
      - name: registry-secret
```

### 5. Service 配置

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: workflow-engine-service
  namespace: workflow-engine
  labels:
    app: workflow-engine
spec:
  selector:
    app: workflow-engine
  ports:
  - name: grpc
    port: 50051
    targetPort: 50051
    protocol: TCP
  - name: metrics
    port: 9090
    targetPort: 9090
    protocol: TCP
  type: LoadBalancer
```

### 6. HPA 配置

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: workflow-engine-hpa
  namespace: workflow-engine
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: workflow-engine
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 部署到 Kubernetes

```bash
# 创建 namespace
kubectl apply -f namespace.yaml

# 部署配置
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f hpa.yaml

# 查看部署状态
kubectl get pods -n workflow-engine
kubectl get services -n workflow-engine

# 查看日志
kubectl logs -f deployment/workflow-engine -n workflow-engine
```

## 监控和日志

### 1. Prometheus 监控

```yaml
# prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'workflow-engine'
      static_configs:
      - targets: ['workflow-engine-service:9090']
      metrics_path: /metrics
      scrape_interval: 5s
```

### 2. Grafana 仪表板

```json
{
  "dashboard": {
    "title": "Workflow Engine Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(workflow_engine_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(workflow_engine_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

### 3. 日志聚合

```yaml
# fluentd-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /app/logs/*.log
      pos_file /fluentd/log/workflow-engine.log.pos
      tag workflow-engine.*
      format json
    </source>
    
    <match workflow-engine.**>
      @type elasticsearch
      host elasticsearch
      port 9200
      index_name workflow-engine
      type_name logs
    </match>
```

## 数据库管理

### 1. 数据库迁移

```bash
# 应用迁移
alembic upgrade head

# 创建新迁移
alembic revision --autogenerate -m "Add new feature"

# 回滚迁移
alembic downgrade -1
```

### 2. 数据备份

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="workflow_engine"

# 创建备份
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > $BACKUP_DIR/workflow_engine_$DATE.sql

# 压缩备份
gzip $BACKUP_DIR/workflow_engine_$DATE.sql

# 清理旧备份（保留7天）
find $BACKUP_DIR -name "workflow_engine_*.sql.gz" -mtime +7 -delete
```

### 3. 数据恢复

```bash
#!/bin/bash
# restore.sh
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# 恢复数据库
gunzip -c $BACKUP_FILE | psql -h $DB_HOST -U $DB_USER -d $DB_NAME
```

## 安全配置

### 1. SSL/TLS 配置

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    location / {
        grpc_pass grpc://workflow-engine-backend;
        grpc_set_header Host $host;
        grpc_set_header X-Real-IP $remote_addr;
        grpc_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}

upstream workflow-engine-backend {
    server workflow-engine:50051;
}
```

### 2. 防火墙配置

```bash
# UFW 配置
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 50051/tcp  # gRPC
sudo ufw enable
```

### 3. 网络策略

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: workflow-engine-network-policy
  namespace: workflow-engine
spec:
  podSelector:
    matchLabels:
      app: workflow-engine
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: nginx-ingress
    ports:
    - protocol: TCP
      port: 50051
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          name: redis
    ports:
    - protocol: TCP
      port: 6379
```

## 故障排除

### 1. 常见问题

#### 数据库连接失败

```bash
# 检查数据库连接
pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER

# 检查数据库日志
kubectl logs deployment/postgres -n database
```

#### gRPC 服务无法访问

```bash
# 检查端口是否监听
netstat -tlnp | grep 50051

# 检查防火墙
sudo ufw status

# 测试 gRPC 连接
grpcurl -plaintext localhost:50051 list
```

#### 内存不足

```bash
# 检查内存使用
free -h
kubectl top pods -n workflow-engine

# 增加内存限制
kubectl patch deployment workflow-engine -n workflow-engine -p '{"spec":{"template":{"spec":{"containers":[{"name":"workflow-engine","resources":{"limits":{"memory":"4Gi"}}}]}}}}'
```

### 2. 日志分析

```bash
# 查看应用日志
kubectl logs -f deployment/workflow-engine -n workflow-engine

# 查看系统日志
journalctl -u workflow-engine

# 查看 Nginx 日志
docker logs nginx
```

### 3. 性能调优

```bash
# 数据库性能调优
# postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# 连接池配置
max_connections = 100
```

## 更新和维护

### 1. 滚动更新

```bash
# 更新镜像
kubectl set image deployment/workflow-engine workflow-engine=workflow-engine:v1.1.0 -n workflow-engine

# 查看更新状态
kubectl rollout status deployment/workflow-engine -n workflow-engine

# 回滚更新
kubectl rollout undo deployment/workflow-engine -n workflow-engine
```

### 2. 定期维护任务

```bash
#!/bin/bash
# maintenance.sh

# 清理旧日志
find /app/logs -name "*.log" -mtime +30 -delete

# 清理审计日志
psql -c "SELECT cleanup_old_audit_logs(90);"

# 数据库统计信息更新
psql -c "ANALYZE;"

# 重启应用（如需要）
kubectl rollout restart deployment/workflow-engine -n workflow-engine
```

### 3. 健康检查

```bash
#!/bin/bash
# health-check.sh

# 检查服务状态
curl -f http://localhost:8080/health || exit 1

# 检查数据库连接
pg_isready -h $DB_HOST -p $DB_PORT || exit 1

# 检查 Redis 连接
redis-cli -h $REDIS_HOST ping || exit 1

echo "All services are healthy"
```

## 最佳实践

### 1. 部署流程

1. **测试环境验证**: 先在测试环境部署和验证
2. **逐步发布**: 使用蓝绿部署或金丝雀发布
3. **监控指标**: 部署后密切监控关键指标
4. **回滚准备**: 准备快速回滚方案

### 2. 配置管理

1. **环境隔离**: 不同环境使用不同的配置
2. **密钥管理**: 使用专门的密钥管理服务
3. **版本控制**: 配置文件纳入版本控制
4. **自动化**: 使用 CI/CD 自动化部署流程

### 3. 监控告警

1. **关键指标**: 监控 CPU、内存、响应时间等
2. **业务指标**: 监控工具执行成功率等
3. **告警规则**: 设置合理的告警阈值
4. **故障响应**: 建立故障响应流程

这个部署指南涵盖了从开发环境到生产环境的完整部署流程，包括容器化、Kubernetes 部署、监控、安全配置等各个方面。 