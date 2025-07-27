# ECS 部署环境配置指南

## 🏗️ 环境变量配置

### 开发环境 (.env.development)
```bash
# 直接连接到本地服务
WORKFLOW_SERVICE_HOST=localhost
WORKFLOW_SERVICE_PORT=50051
```

### 测试环境 (.env.testing)
```bash
# 连接到测试环境的负载均衡器
WORKFLOW_SERVICE_LB_ENDPOINT=workflow-agent-test-nlb.amazonaws.com:50051
```

### 生产环境 (.env.production)
```bash
# 使用 AWS Cloud Map 服务发现
WORKFLOW_SERVICE_DNS_NAME=workflow-agent.workflow.local

# 或者使用负载均衡器
WORKFLOW_SERVICE_LB_ENDPOINT=workflow-agent-prod-nlb.amazonaws.com:50051

# AWS 区域配置
AWS_REGION=us-west-2
AWS_DEFAULT_REGION=us-west-2
```

## 🚀 ECS Task Definition 示例

### API Gateway Task Definition
```json
{
  "family": "api-gateway",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "api-gateway",
      "image": "your-registry/api-gateway:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "WORKFLOW_SERVICE_DNS_NAME",
          "value": "workflow-agent.workflow.local"
        },
        {
          "name": "AWS_REGION",
          "value": "us-west-2"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/api-gateway",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Workflow Agent Task Definition
```json
{
  "family": "workflow-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "workflow-agent",
      "image": "your-registry/workflow-agent:latest",
      "portMappings": [
        {
          "containerPort": 50051,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "GRPC_HOST",
          "value": "0.0.0.0"
        },
        {
          "name": "GRPC_PORT",
          "value": "50051"
        }
      ],
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "grpc_health_probe -addr=localhost:50051 || exit 1"
        ],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 60
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/workflow-agent",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## 🔧 Docker 构建配置

### API Gateway Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY api-gateway/pyproject.toml .
COPY api-gateway/requirements.txt .

# 安装 Python 依赖
RUN pip install -r requirements.txt

# 复制应用代码
COPY api-gateway/ .

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Workflow Agent Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖和 grpc_health_probe
RUN apt-get update && apt-get install -y \
    gcc \
    wget \
    && wget -qO/bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.4.19/grpc_health_probe-linux-amd64 \
    && chmod +x /bin/grpc_health_probe \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY workflow_agent/pyproject.toml .
COPY workflow_agent/requirements.txt .

# 安装 Python 依赖
RUN pip install -r requirements.txt

# 复制应用代码
COPY workflow_agent/ .
COPY shared/ ../shared/

# 暴露端口
EXPOSE 50051

# 启动命令
CMD ["python", "main.py"]
```

## 📊 监控配置

### CloudWatch 日志组
```bash
# 创建日志组
aws logs create-log-group --log-group-name /ecs/api-gateway
aws logs create-log-group --log-group-name /ecs/workflow-agent

# 设置保留策略
aws logs put-retention-policy --log-group-name /ecs/api-gateway --retention-in-days 30
aws logs put-retention-policy --log-group-name /ecs/workflow-agent --retention-in-days 30
```

### CloudWatch 指标
```json
{
  "metrics": [
    {
      "metricName": "grpc_connections_total",
      "namespace": "WorkflowAgent/gRPC",
      "dimensions": [
        {"name": "ServiceName", "value": "workflow-agent"}
      ]
    },
    {
      "metricName": "grpc_request_duration_seconds", 
      "namespace": "WorkflowAgent/gRPC",
      "dimensions": [
        {"name": "ServiceName", "value": "workflow-agent"}
      ]
    }
  ]
}
```

## 🔐 IAM 权限配置

### ECS Task Role (生产环境需要 Service Discovery 权限)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "servicediscovery:DiscoverInstances",
        "servicediscovery:GetService",
        "servicediscovery:ListServices"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:DescribeTasks",
        "ecs:ListTasks"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🚀 部署脚本示例

### deploy.sh
```bash
#!/bin/bash

set -e

ENVIRONMENT=${1:-staging}
AWS_REGION=${2:-us-west-2}
CLUSTER_NAME="workflow-agent-cluster"

echo "Deploying to environment: $ENVIRONMENT"

# 构建和推送镜像
echo "Building and pushing images..."
docker build -t workflow-agent:latest -f workflow_agent/Dockerfile .
docker build -t api-gateway:latest -f api-gateway/Dockerfile .

# 标记和推送到 ECR
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

docker tag workflow-agent:latest $ECR_REGISTRY/workflow-agent:$ENVIRONMENT
docker tag api-gateway:latest $ECR_REGISTRY/api-gateway:$ENVIRONMENT

docker push $ECR_REGISTRY/workflow-agent:$ENVIRONMENT
docker push $ECR_REGISTRY/api-gateway:$ENVIRONMENT

# 更新 ECS 服务
echo "Updating ECS services..."
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service workflow-agent-$ENVIRONMENT \
  --force-new-deployment \
  --region $AWS_REGION

aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service api-gateway-$ENVIRONMENT \
  --force-new-deployment \
  --region $AWS_REGION

echo "Deployment completed!"
```

## 🔍 故障排查

### 常见问题和解决方案

1. **服务发现失败**
```bash
# 检查 Cloud Map 命名空间
aws servicediscovery list-namespaces

# 检查服务注册
aws servicediscovery list-services --filters Name=NAMESPACE_ID,Values=ns-xxx

# 测试 DNS 解析
nslookup workflow-agent.workflow.local
```

2. **连接超时**
```bash
# 检查安全组规则
aws ec2 describe-security-groups --group-ids sg-xxx

# 检查 ECS 服务状态
aws ecs describe-services --cluster workflow-agent-cluster --services workflow-agent
```

3. **负载均衡器健康检查失败**
```bash
# 检查目标组健康状态
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:...

# 检查 gRPC 健康检查
grpc_health_probe -addr=service-endpoint:50051
```

这个配置提供了完整的 AWS ECS 部署方案，支持多环境部署和生产级的可靠性！ 