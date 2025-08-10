# AWS ECS 上的 gRPC 服务发现方案

## 🏗️ 当前架构分析

当前代码使用硬编码的主机和端口：
```python
self.host = settings.WORKFLOW_SERVICE_HOST  # "localhost"
self.port = settings.WORKFLOW_SERVICE_PORT  # 50051
self.channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")
```

在 AWS ECS 上，这种方式需要改进以支持动态服务发现。

## 🚀 AWS ECS 服务发现方案

### 方案 1: AWS Cloud Map + ECS Service Discovery (推荐)

**优点**: AWS 原生，自动服务注册和健康检查，DNS 自动解析
**缺点**: 稍微复杂的配置，需要 VPC

#### 架构图:
```
┌─────────────────┐    DNS查询     ┌─────────────────┐
│   API Gateway   │───────────────▶│   Cloud Map     │
│     (ECS)       │                │   (DNS-based)   │
└─────────────────┘                └─────────────────┘
         │                                   │
         │ gRPC调用                          │ 服务注册
         ▼                                   ▼
┌─────────────────┐                ┌─────────────────┐
│ Workflow Agent  │◀───────────────│  ECS Service    │
│     (ECS)       │   自动注册      │   Discovery     │
└─────────────────┘                └─────────────────┘
```

### 方案 2: Application Load Balancer (ALB) + Target Groups

**优点**: 简单，支持健康检查，可以处理 HTTP/2
**缺点**: 需要 gRPC-Web 或 HTTP/2，额外的网络跳跃

### 方案 3: Network Load Balancer (NLB) + Target Groups

**优点**: 原生 gRPC 支持，低延迟，高性能
**缺点**: Layer 4 负载均衡，功能较少

### 方案 4: AWS App Mesh + Envoy Proxy

**优点**: 服务网格，丰富的流量管理，可观测性
**缺点**: 复杂度高，学习成本

### 方案 5: 环境变量 + 内部负载均衡器

**优点**: 简单，直接
**缺点**: 需要手动管理，不够动态

## 🎯 推荐实现方案

基于你的项目需求，推荐使用 **方案 1 (Cloud Map) + 方案 3 (NLB) 的组合**：

1. **Cloud Map** 用于服务发现
2. **NLB** 用于负载均衡和健康检查
3. **ECS Service Discovery** 自动注册服务

## 🛠️ 具体实现步骤

### 步骤 1: Terraform 基础设施配置

```hcl
# 1. Cloud Map 命名空间
resource "aws_service_discovery_private_dns_namespace" "workflow" {
  name        = "workflow.local"
  description = "Private DNS namespace for workflow services"
  vpc         = var.vpc_id
}

# 2. Cloud Map 服务
resource "aws_service_discovery_service" "workflow_agent" {
  name = "workflow-agent"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.workflow.id
    
    dns_records {
      ttl  = 10
      type = "A"
    }
    
    routing_policy = "MULTIVALUE"
  }

  health_check_grace_period_seconds = 30
  
  health_check_custom_config {
    failure_threshold = 1
  }
}

# 3. Network Load Balancer
resource "aws_lb" "workflow_agent_nlb" {
  name               = "workflow-agent-nlb"
  internal           = true
  load_balancer_type = "network"
  subnets            = var.private_subnet_ids
  
  enable_deletion_protection = false
}

# 4. Target Group for gRPC
resource "aws_lb_target_group" "workflow_agent_grpc" {
  name     = "workflow-agent-grpc"
  port     = 50051
  protocol = "TCP"
  vpc_id   = var.vpc_id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "0-99"  # gRPC status codes
    port                = "traffic-port"
    protocol            = "TCP"
    timeout             = 10
    unhealthy_threshold = 2
  }
}

# 5. NLB Listener
resource "aws_lb_listener" "workflow_agent_grpc" {
  load_balancer_arn = aws_lb.workflow_agent_nlb.arn
  port              = "50051"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.workflow_agent_grpc.arn
  }
}
```

### 步骤 2: ECS Service 配置

```hcl
# ECS Task Definition
resource "aws_ecs_task_definition" "workflow_agent" {
  family                   = "workflow-agent"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "workflow-agent"
      image = var.workflow_agent_image
      
      portMappings = [
        {
          containerPort = 50051
          protocol      = "tcp"
        }
      ]
      
      environment = [
        {
          name  = "GRPC_HOST"
          value = "0.0.0.0"
        },
        {
          name  = "GRPC_PORT"
          value = "50051"
        }
      ]
      
      logging = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.workflow_agent.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

# ECS Service with Service Discovery
resource "aws_ecs_service" "workflow_agent" {
  name            = "workflow-agent"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.workflow_agent.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.workflow_agent.id]
    assign_public_ip = false
  }

  # Service Discovery 配置
  service_registries {
    registry_arn = aws_service_discovery_service.workflow_agent.arn
  }

  # Load Balancer 配置
  load_balancer {
    target_group_arn = aws_lb_target_group.workflow_agent_grpc.arn
    container_name   = "workflow-agent"
    container_port   = 50051
  }

  depends_on = [aws_lb_listener.workflow_agent_grpc]
}
```

### 步骤 3: 更新 gRPC Client 代码

```python
import os
import asyncio
import grpc
import boto3
import json
from typing import Optional, List
from dataclasses import dataclass

@dataclass
class ServiceEndpoint:
    host: str
    port: int
    weight: int = 1

class AWSServiceDiscoveryClient:
    """AWS ECS 服务发现客户端"""
    
    def __init__(self):
        self.servicediscovery = boto3.client('servicediscovery')
        self.ecs = boto3.client('ecs')
    
    async def discover_workflow_service(self) -> List[ServiceEndpoint]:
        """通过 AWS Service Discovery 发现 workflow 服务实例"""
        try:
            # 方法 1: 通过 Cloud Map DNS 解析
            return await self._discover_via_dns()
        except Exception as e:
            print(f"DNS discovery failed: {e}")
            # 方法 2: 通过 ECS API 查询
            return await self._discover_via_ecs_api()
    
    async def _discover_via_dns(self) -> List[ServiceEndpoint]:
        """通过 DNS 解析发现服务"""
        import socket
        
        service_name = "workflow-agent.workflow.local"
        try:
            # 解析所有 A 记录
            addresses = socket.getaddrinfo(service_name, 50051, socket.AF_INET)
            endpoints = []
            
            for addr in addresses:
                endpoints.append(ServiceEndpoint(
                    host=addr[4][0],
                    port=50051
                ))
            
            return endpoints
        except socket.gaierror:
            return []
    
    async def _discover_via_ecs_api(self) -> List[ServiceEndpoint]:
        """通过 ECS API 发现服务实例"""
        try:
            # 获取服务详情
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.ecs.describe_services(
                    cluster='your-cluster-name',
                    services=['workflow-agent']
                )
            )
            
            # 获取任务详情
            tasks = response['services'][0]['runningCount']
            if tasks > 0:
                # 这里需要进一步查询任务的网络接口
                # 简化版本：返回 NLB 地址
                return [ServiceEndpoint(
                    host="workflow-agent-nlb-internal-dns-name.amazonaws.com",
                    port=50051
                )]
            
            return []
        except Exception as e:
            print(f"ECS API discovery failed: {e}")
            return []

class EnhancedWorkflowGRPCClient:
    """增强的 gRPC 客户端，支持 AWS ECS 服务发现"""
    
    def __init__(self):
        self.discovery_client = AWSServiceDiscoveryClient()
        self.channel = None
        self.stub = None
        self.connected = False
        self.current_endpoints: List[ServiceEndpoint] = []
    
    async def connect(self):
        """连接到 workflow 服务，支持服务发现"""
        try:
            # 1. 首先尝试环境变量配置（开发环境）
            if os.getenv("WORKFLOW_SERVICE_HOST"):
                await self._connect_direct()
                return
            
            # 2. 生产环境：使用服务发现
            await self._connect_via_service_discovery()
            
        except Exception as e:
            print(f"Connection failed: {e}")
            raise
    
    async def _connect_direct(self):
        """直接连接（开发环境）"""
        host = os.getenv("WORKFLOW_SERVICE_HOST", "localhost")
        port = int(os.getenv("WORKFLOW_SERVICE_PORT", "50051"))
        
        self.channel = grpc.aio.insecure_channel(f"{host}:{port}")
        self.stub = workflow_agent_pb2_grpc.WorkflowAgentStub(self.channel)
        
        await asyncio.wait_for(self.channel.channel_ready(), timeout=5.0)
        self.connected = True
        print(f"Connected directly to {host}:{port}")
    
    async def _connect_via_service_discovery(self):
        """通过服务发现连接"""
        endpoints = await self.discovery_client.discover_workflow_service()
        
        if not endpoints:
            raise Exception("No workflow service instances found")
        
        # 尝试连接到第一个可用的端点
        for endpoint in endpoints:
            try:
                self.channel = grpc.aio.insecure_channel(
                    f"{endpoint.host}:{endpoint.port}"
                )
                self.stub = workflow_agent_pb2_grpc.WorkflowAgentStub(self.channel)
                
                await asyncio.wait_for(self.channel.channel_ready(), timeout=5.0)
                self.connected = True
                self.current_endpoints = endpoints
                print(f"Connected via service discovery to {endpoint.host}:{endpoint.port}")
                return
                
            except Exception as e:
                print(f"Failed to connect to {endpoint.host}:{endpoint.port}: {e}")
                continue
        
        raise Exception("Failed to connect to any discovered service instances")
    
    async def reconnect_if_needed(self):
        """检查连接状态，必要时重新连接"""
        if not self.connected:
            await self.connect()
    
    async def process_conversation(self, request):
        """处理对话，包含自动重连逻辑"""
        await self.reconnect_if_needed()
        
        try:
            async for response in self.stub.ProcessConversation(request):
                yield response
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                print("Service unavailable, attempting reconnection...")
                self.connected = False
                await self.connect()
                # 重试一次
                async for response in self.stub.ProcessConversation(request):
                    yield response
            else:
                raise
```

### 步骤 4: 环境配置

```yaml
# docker-compose.yml (开发环境)
version: '3.8'
services:
  api-gateway:
    environment:
      - WORKFLOW_SERVICE_HOST=workflow-agent
      - WORKFLOW_SERVICE_PORT=50051
  
  workflow-agent:
    ports:
      - "50051:50051"

# ECS Task Definition (生产环境)
# 不设置 WORKFLOW_SERVICE_HOST，让客户端使用服务发现
```

### 步骤 5: 健康检查配置

```python
# 在 workflow_agent 中添加健康检查端点
from grpc_health.v1 import health_pb2, health_pb2_grpc
from grpc_health.v1.health import HealthServicer

class WorkflowAgentServicer(workflow_agent_pb2_grpc.WorkflowAgentServicer):
    # ... 现有代码 ...
    
    async def Check(self, request, context):
        """gRPC 健康检查"""
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.SERVING
        )

# 在 gRPC 服务器中注册健康检查
health_servicer = HealthServicer()
health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
```

## 🔧 部署配置

### 安全组配置

```hcl
resource "aws_security_group" "workflow_agent" {
  name_prefix = "workflow-agent-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 50051
    to_port     = 50051
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "api_gateway" {
  name_prefix = "api-gateway-"
  vpc_id      = var.vpc_id

  egress {
    from_port       = 50051
    to_port         = 50051
    protocol        = "tcp"
    security_groups = [aws_security_group.workflow_agent.id]
  }
}
```

## 📊 监控和可观测性

```python
# 添加连接指标
import time
from prometheus_client import Counter, Histogram, Gauge

GRPC_CONNECTIONS = Gauge('grpc_connections_total', 'Total gRPC connections')
GRPC_REQUEST_DURATION = Histogram('grpc_request_duration_seconds', 'gRPC request duration')
GRPC_FAILURES = Counter('grpc_failures_total', 'Total gRPC failures', ['reason'])

class MonitoredWorkflowGRPCClient(EnhancedWorkflowGRPCClient):
    async def process_conversation(self, request):
        start_time = time.time()
        GRPC_CONNECTIONS.inc()
        
        try:
            async for response in super().process_conversation(request):
                yield response
        except Exception as e:
            GRPC_FAILURES.labels(reason=type(e).__name__).inc()
            raise
        finally:
            GRPC_REQUEST_DURATION.observe(time.time() - start_time)
            GRPC_CONNECTIONS.dec()
```

## 🚀 部署总结

这个方案提供了：

1. **自动服务发现**: 通过 AWS Cloud Map
2. **负载均衡**: 通过 Network Load Balancer
3. **健康检查**: ECS + NLB 级别
4. **故障转移**: 自动重连和多实例支持
5. **可观测性**: 指标和日志
6. **环境兼容**: 开发和生产环境支持

使用这个架构，你的 gRPC 服务在 AWS ECS 上将具备生产级的可靠性和可扩展性！ 