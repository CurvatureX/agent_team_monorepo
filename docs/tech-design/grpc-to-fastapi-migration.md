# gRPC 迁移到 FastAPI + Pydantic 技术方案

## 概述

本文档详细描述了将基于 gRPC 的服务迁移到 FastAPI + Pydantic 架构的技术设计和迁移策略。该迁移方案旨在解决关键的部署挑战，包括 protobuf 导入问题和请求/响应结构的可见性限制。

## 当前架构

### 服务概览
```
API Gateway (FastAPI) → [gRPC clients] → Workflow Services (gRPC)
└── Port 8000 (HTTP/REST)              ├── Workflow Engine (Port 50050)
                                       └── Workflow Agent (Port 50051)
```

### 当前的 gRPC 服务

#### 1. Workflow Engine (端口 50050)
- **服务**: `WorkflowService`, `TriggerService`, `HealthService`
- **主要功能**:
  - 工作流 CRUD 操作（创建、读取、更新、删除、列表）
  - 工作流执行和状态管理
  - 触发器管理（创建、触发、事件列表）
  - 健康检查
- **依赖项**: PostgreSQL, Redis, Supabase, AI APIs

#### 2. Workflow Agent (端口 50051)
- **服务**: `WorkflowAgent`
- **主要功能**:
  - `GenerateWorkflow` - AI 驱动的工作流生成
  - `RefineWorkflow` - 迭代式工作流改进
  - `ValidateWorkflow` - 工作流验证
- **依赖项**: LangGraph, Supabase (RAG), OpenAI, Anthropic APIs

### 当前部署问题

1. **Protobuf 导入复杂性**
   - 多个 proto 文件依赖和循环引用
   - Docker 部署路径问题: `from . import workflow_pb2 as workflow__pb2`
   - 平台特定的导入解析（本地 vs AWS ECS）

2. **开发体验问题**
   - 生成的请求/响应结构缺乏 IDE 支持
   - proto 消息内容的调试能力有限
   - API 文档和测试困难

3. **运维复杂性**
   - gRPC 健康检查需要自定义配置
   - 服务发现与 DNS 和负载均衡器的复杂性
   - 相比 HTTP 服务的可观测性有限

## Migration Strategy

### Phase 1: Workflow Agent Migration (Priority 1)

**Rationale**: Workflow Agent has the most complex gRPC interface and benefits most from Pydantic's validation and serialization capabilities.

#### Target Architecture
```python
# From gRPC proto:
service WorkflowAgent {
  rpc GenerateWorkflow(WorkflowGenerationRequest) returns (WorkflowGenerationResponse);
  rpc RefineWorkflow(WorkflowRefinementRequest) returns (WorkflowRefinementResponse);
  rpc ValidateWorkflow(WorkflowValidationRequest) returns (WorkflowValidationResponse);
}

# To FastAPI + Pydantic:
@app.post("/v1/workflows/generate", response_model=WorkflowGenerationResponse)
async def generate_workflow(request: WorkflowGenerationRequest) -> WorkflowGenerationResponse

@app.post("/v1/workflows/{workflow_id}/refine", response_model=WorkflowRefinementResponse)
async def refine_workflow(workflow_id: str, request: WorkflowRefinementRequest) -> WorkflowRefinementResponse

@app.post("/v1/workflows/validate", response_model=WorkflowValidationResponse)
async def validate_workflow(request: WorkflowValidationRequest) -> WorkflowValidationResponse
```

#### Migration Steps

1. **Create Pydantic Models** (replacing proto definitions)
```python
# workflow_agent/models/requests.py
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class WorkflowGenerationRequest(BaseModel):
    description: str = Field(..., description="Natural language workflow description")
    context: Dict[str, str] = Field(default_factory=dict, description="Additional context")
    user_preferences: Dict[str, str] = Field(default_factory=dict, description="User preferences")

class WorkflowGenerationResponse(BaseModel):
    success: bool
    workflow: Optional['WorkflowData'] = None
    suggestions: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
```

2. **Implement FastAPI Router**
```python
# workflow_agent/api/v1/workflows.py
from fastapi import APIRouter, HTTPException
from workflow_agent.agents.workflow_agent import WorkflowAgentGraph
from workflow_agent.models.requests import WorkflowGenerationRequest, WorkflowGenerationResponse

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])

@router.post("/generate", response_model=WorkflowGenerationResponse)
async def generate_workflow(request: WorkflowGenerationRequest) -> WorkflowGenerationResponse:
    try:
        # Use existing LangGraph agent logic
        agent = WorkflowAgentGraph()
        result = await agent.generate_workflow(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

3. **Update API Gateway Client**
```python
# api-gateway/services/workflow_service_client.py
import httpx
from api_gateway.models.workflow import WorkflowGenerationRequest, WorkflowGenerationResponse

class WorkflowServiceClient:
    def __init__(self, base_url: str = "http://workflow-agent:8001"):
        self.client = httpx.AsyncClient(base_url=base_url)

    async def generate_workflow(self, request: WorkflowGenerationRequest) -> WorkflowGenerationResponse:
        response = await self.client.post("/v1/workflows/generate", json=request.dict())
        response.raise_for_status()
        return WorkflowGenerationResponse(**response.json())
```

### Phase 2: Workflow Engine Migration (Priority 2)

#### Target Architecture
```python
# From gRPC WorkflowService to FastAPI endpoints:
@app.post("/v1/workflows", response_model=CreateWorkflowResponse)
async def create_workflow(request: CreateWorkflowRequest) -> CreateWorkflowResponse

@app.get("/v1/workflows/{workflow_id}", response_model=GetWorkflowResponse)
async def get_workflow(workflow_id: str, user_id: str) -> GetWorkflowResponse

@app.post("/v1/workflows/{workflow_id}/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow(workflow_id: str, request: ExecuteWorkflowRequest) -> ExecuteWorkflowResponse

# Trigger management endpoints:
@app.post("/v1/triggers", response_model=CreateTriggerResponse)
async def create_trigger(request: CreateTriggerRequest) -> CreateTriggerResponse

@app.post("/v1/triggers/{trigger_id}/fire", response_model=FireTriggerResponse)
async def fire_trigger(trigger_id: str, request: FireTriggerRequest) -> FireTriggerResponse
```

#### Pydantic Models Design
```python
# workflow_engine/models/workflow.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum

class NodeData(BaseModel):
    id: str
    name: str
    type: str
    subtype: Optional[str] = None
    position: 'PositionData'
    parameters: Dict[str, str] = Field(default_factory=dict)
    disabled: bool = False
    on_error: str = "continue"

class WorkflowData(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    nodes: List[NodeData]
    connections: 'ConnectionsMapData'
    settings: 'WorkflowSettingsData'
    static_data: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    active: bool = True
    created_at: Optional[int] = None
    updated_at: Optional[int] = None

class CreateWorkflowRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    nodes: List[NodeData] = Field(..., min_items=1)
    connections: 'ConnectionsMapData'
    settings: Optional['WorkflowSettingsData'] = None
    static_data: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None

class CreateWorkflowResponse(BaseModel):
    workflow: WorkflowData
    success: bool = True
    message: str = "Workflow created successfully"
```

## Implementation Details

### 1. Port Configuration Changes

```yaml
# docker-compose.yml updates
services:
  workflow-agent:
    ports:
      - "8001:8000"  # Changed from gRPC 50051 to HTTP 8000
    environment:
      - PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]  # HTTP health check

  workflow-engine:
    ports:
      - "8002:8000"  # Changed from gRPC 50050 to HTTP 8000
    environment:
      - PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]  # HTTP health check
```

### 2. Service Communication Updates

#### API Gateway Client Changes
```python
# api-gateway/services/enhanced_http_client.py
class WorkflowServiceHTTPClient:
    def __init__(self):
        self.workflow_agent_url = os.getenv("WORKFLOW_AGENT_URL", "http://workflow-agent:8000")
        self.workflow_engine_url = os.getenv("WORKFLOW_ENGINE_URL", "http://workflow-engine:8000")
        self.timeout = httpx.Timeout(30.0, connect=5.0)

    async def generate_workflow(self, request: WorkflowGenerationRequest) -> WorkflowGenerationResponse:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.workflow_agent_url}/v1/workflows/generate",
                json=request.dict(),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return WorkflowGenerationResponse(**response.json())

    async def create_workflow(self, request: CreateWorkflowRequest) -> CreateWorkflowResponse:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.workflow_engine_url}/v1/workflows",
                json=request.dict(),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return CreateWorkflowResponse(**response.json())
```

### 3. FastAPI Application Structure

#### Workflow Agent Structure
```
workflow_agent/
├── api/
│   ├── __init__.py
│   ├── deps.py          # Dependency injection
│   └── v1/
│       ├── __init__.py
│       └── workflows.py # Workflow endpoints
├── models/
│   ├── __init__.py
│   ├── requests.py      # Request models
│   ├── responses.py     # Response models
│   └── workflow.py      # Workflow data models
├── main.py              # FastAPI app initialization
└── core/
    ├── config.py        # Settings (unchanged)
    └── exceptions.py    # HTTP exception handlers
```

#### Main Application Setup
```python
# workflow_agent/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from workflow_agent.api.v1.workflows import router as workflows_router
from workflow_agent.core.config import settings

app = FastAPI(
    title="Workflow Agent API",
    description="AI-powered workflow generation and consultation service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflows_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "Workflow Agent API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
```

### 4. Data Validation Benefits

#### Pydantic Validation Examples
```python
# Automatic validation and documentation
class CreateWorkflowRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Workflow name")
    nodes: List[NodeData] = Field(..., min_items=1, description="At least one node required")

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty or whitespace only')
        return v.strip()

    @validator('nodes')
    def validate_node_connections(cls, v, values):
        node_ids = {node.id for node in v}
        # Custom validation logic for node relationships
        return v

# Automatic OpenAPI documentation generation with examples
class WorkflowGenerationRequest(BaseModel):
    description: str = Field(
        ...,
        description="Natural language description of the desired workflow",
        example="Create a workflow that processes incoming emails, extracts important information using AI, and sends notifications to Slack"
    )

    class Config:
        schema_extra = {
            "example": {
                "description": "Process customer feedback emails and categorize them",
                "context": {
                    "domain": "customer_service",
                    "priority": "high"
                }
            }
        }
```

## Local Docker Deployment Strategy

### 1. Updated Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Infrastructure (unchanged)
  redis:
    image: redis:7-alpine
    container_name: agent-team-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Workflow Agent - Migrated to FastAPI
  workflow-agent:
    build:
      context: .
      dockerfile: ./workflow_agent/Dockerfile.fastapi  # New Dockerfile
      target: production
    container_name: agent-team-workflow-agent
    ports:
      - "8001:8000"  # Changed from gRPC 50051
    environment:
      # FastAPI configuration
      PORT: "8000"
      DEBUG: "${DEBUG:-false}"

      # Database and cache (unchanged)
      SUPABASE_URL: "${SUPABASE_URL}"
      SUPABASE_SECRET_KEY: "${SUPABASE_SECRET_KEY}"
      REDIS_URL: "redis://redis:6379/0"

      # AI APIs (unchanged)
      OPENAI_API_KEY: "${OPENAI_API_KEY}"
      ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s  # Reduced from gRPC's 240s
    depends_on:
      - redis
    networks:
      - agent-team-network

  # Workflow Engine - Migrated to FastAPI
  workflow-engine:
    build:
      context: .
      dockerfile: ./workflow_engine/Dockerfile.fastapi  # New Dockerfile
      target: production
    container_name: agent-team-workflow-engine
    ports:
      - "8002:8000"  # Changed from gRPC 50050
    environment:
      PORT: "8000"
      DEBUG: "${DEBUG:-false}"
      DATABASE_URL: "${DATABASE_URL}"
      REDIS_URL: "redis://redis:6379/0"
      OPENAI_API_KEY: "${OPENAI_API_KEY}"
      ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 45s  # Reduced from gRPC's 180s
    depends_on:
      - redis
    networks:
      - agent-team-network

  # API Gateway - Updated client configuration
  api-gateway:
    build:
      context: .
      dockerfile: ./api-gateway/Dockerfile
    container_name: api_gateway_service
    ports:
      - "8000:8000"
    environment:
      # Updated service URLs
      WORKFLOW_AGENT_URL: "http://workflow-agent:8000"
      WORKFLOW_ENGINE_URL: "http://workflow-engine:8000"
      REDIS_URL: "redis://redis:6379/0"
    depends_on:
      - redis
      - workflow-agent
      - workflow-engine
    networks:
      - agent-team-network

networks:
  agent-team-network:
    driver: bridge
```

### 2. New Dockerfiles for FastAPI Services

#### Workflow Agent Dockerfile
```dockerfile
# workflow_agent/Dockerfile.fastapi
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY workflow_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY workflow_agent/ ./workflow_agent/
COPY shared/ ./shared/

# Production stage
FROM base as production

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn
CMD ["python", "-m", "uvicorn", "workflow_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. Development Commands

```bash
# Start all services
docker-compose up -d

# Start individual services for development
docker-compose up -d redis
docker-compose up workflow-agent  # With live reload

# View logs
docker-compose logs -f workflow-agent
docker-compose logs -f workflow-engine

# API Documentation access
# Workflow Agent: http://localhost:8001/docs
# Workflow Engine: http://localhost:8002/docs
# API Gateway: http://localhost:8000/docs (existing)

# Health checks
curl http://localhost:8001/health  # Workflow Agent
curl http://localhost:8002/health  # Workflow Engine
curl http://localhost:8000/health  # API Gateway

# Test API endpoints
curl -X POST http://localhost:8001/v1/workflows/generate \
  -H "Content-Type: application/json" \
  -d '{"description": "Create a simple email notification workflow"}'
```

## AWS Deployment Strategy

### 1. ECS Task Definition Updates

#### Workflow Agent Task Definition Changes
```hcl
# infra/ecs.tf
resource "aws_ecs_task_definition" "workflow_agent" {
  family                   = "${local.name_prefix}-workflow-agent"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.workflow_agent_cpu
  memory                   = var.workflow_agent_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "workflow-agent"
      image = "${aws_ecr_repository.workflow_agent.repository_url}:${var.image_tag}"

      # Updated port mapping for HTTP
      portMappings = [
        {
          containerPort = 8000  # Changed from 50051
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "PORT"
          value = "8000"
        },
        {
          name  = "DEBUG"
          value = "false"
        },
        # ... other environment variables remain the same
      ]

      # Updated health check for HTTP
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60  # Reduced from 240s due to faster HTTP startup
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "workflow-agent"
        }
      }
    }
  ])

  tags = local.common_tags
}
```

### 2. Load Balancer Configuration Updates

#### Remove gRPC Network Load Balancer (No Longer Needed)
```hcl
# infra/load_balancer.tf - Remove this block
# resource "aws_lb" "grpc_internal" {
#   name               = "${local.name_prefix}-grpc-nlb"
#   internal           = true
#   load_balancer_type = "network"
#   subnets            = aws_subnet.private[*].id
# }
```

#### Update Application Load Balancer for All HTTP Services
```hcl
# infra/load_balancer.tf
# Target Group for Workflow Agent (now HTTP)
resource "aws_lb_target_group" "workflow_agent_http" {
  name        = "${local.name_prefix}-agent-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-workflow-agent-tg"
  })
}

# Target Group for Workflow Engine (now HTTP)
resource "aws_lb_target_group" "workflow_engine_http" {
  name        = "${local.name_prefix}-engine-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-workflow-engine-tg"
  })
}

# ALB Listener Rules for Path-Based Routing
resource "aws_lb_listener_rule" "workflow_agent" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.workflow_agent_http.arn
  }

  condition {
    path_pattern {
      values = ["/v1/workflows/generate*", "/v1/workflows/*/refine*", "/v1/workflows/validate*"]
    }
  }

  tags = local.common_tags
}

resource "aws_lb_listener_rule" "workflow_engine" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.workflow_engine_http.arn
  }

  condition {
    path_pattern {
      values = ["/v1/workflows*", "/v1/triggers*", "/v1/executions*"]
    }
  }

  tags = local.common_tags
}
```

### 3. Service Discovery Simplification

#### Updated Service Discovery for HTTP Services
```hcl
# infra/service_discovery.tf
# Service Discovery Services can be simplified or removed
# Since HTTP services can use ALB-based service discovery through DNS

# Optional: Keep for internal service-to-service communication
resource "aws_service_discovery_service" "workflow_agent" {
  name = "workflow-agent"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  # HTTP services can use simpler health checks
  health_check_custom_config {
    failure_threshold = 1
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-workflow-agent-discovery"
  })
}
```

### 4. ECS Service Configuration Updates

```hcl
# infra/ecs.tf
# ECS Service for Workflow Agent (HTTP)
resource "aws_ecs_service" "workflow_agent" {
  name            = "workflow-agent-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.workflow_agent.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  # Updated load balancer configuration for HTTP
  load_balancer {
    target_group_arn = aws_lb_target_group.workflow_agent_http.arn
    container_name   = "workflow-agent"
    container_port   = 8000  # Changed from 50051
  }

  service_registries {
    registry_arn = aws_service_discovery_service.workflow_agent.arn
  }

  depends_on = [aws_lb_listener.main]

  tags = local.common_tags
}
```

### 5. Security Group Updates

```hcl
# infra/security_groups.tf
# ECS Tasks Security Group - Update for HTTP services
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${local.name_prefix}-ecs-tasks"
  vpc_id      = aws_vpc.main.id

  # HTTP traffic for all services
  ingress {
    protocol        = "tcp"
    from_port       = 8000
    to_port         = 8000
    security_groups = [aws_security_group.alb.id]
    description     = "HTTP traffic from ALB"
  }

  # Remove gRPC port rules (50050, 50051) - no longer needed

  # Redis access
  ingress {
    protocol    = "tcp"
    from_port   = 6379
    to_port     = 6379
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Redis access"
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-tasks-sg"
  })
}
```

### 6. GitHub Actions Deployment Updates

```yaml
# .github/workflows/deploy.yml
# Build and push section remains similar, but Dockerfile names change
      - name: Build, tag, and push image to Amazon ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          # Build and push Docker image - Updated Dockerfile names
          docker buildx build \
            --platform linux/amd64 \
            --target production \
            --file ${{ matrix.service.dockerfile }}.fastapi \  # New Dockerfile names
            --tag $ECR_REGISTRY/${{ matrix.service.repository }}:$IMAGE_TAG \
            --tag $ECR_REGISTRY/${{ matrix.service.repository }}:latest \
            --push \
            ${{ matrix.service.context }}

  deploy:
    # Deployment section simplified - no gRPC-specific service discovery cleanup needed
    steps:
      # ... existing steps ...

      # Remove service discovery cleanup step - no longer needed for HTTP services
      # - name: Handle Service Discovery cleanup if needed

      - name: Terraform Apply
        working-directory: infra
        env:
          TF_VAR_image_tag: ${{ github.sha }}
          # ... other environment variables
        run: terraform apply -auto-approve tfplan

      # Service updates remain the same
      - name: Update ECS Service - Workflow Agent
        run: |
          aws ecs update-service \
            --cluster agent-team-production-cluster \
            --service workflow-agent-service \
            --force-new-deployment \
            --region ${{ env.AWS_REGION }}
```

## Migration Timeline and Rollback Strategy

### Phase 1: Workflow Agent Migration (Week 1-2)
1. **Day 1-3**: Create Pydantic models and FastAPI endpoints
2. **Day 4-5**: Update local Docker environment and testing
3. **Day 6-7**: Deploy to staging environment
4. **Week 2**: Production deployment with monitoring

### Phase 2: Workflow Engine Migration (Week 3-4)
1. **Day 1-4**: Implement FastAPI endpoints for workflow CRUD operations
2. **Day 5-6**: Implement trigger management endpoints
3. **Day 7**: Integration testing and local deployment
4. **Week 4**: Staging and production deployment

### Rollback Strategy
1. **Code Rollback**: Maintain gRPC implementation alongside FastAPI during migration
2. **Infrastructure Rollback**: Keep existing ECS task definitions as backups
3. **DNS/Load Balancer Rollback**: Quick switch between gRPC and HTTP target groups
4. **Feature Flags**: Use environment variables to toggle between gRPC and HTTP clients

## Benefits Assessment

### Development Experience Improvements
1. **IDE Support**: Full IntelliSense and type checking for request/response models
2. **API Documentation**: Automatic OpenAPI/Swagger documentation generation
3. **Testing**: Standard HTTP testing tools (curl, Postman, pytest-httpx)
4. **Debugging**: Clear JSON request/response bodies in logs

### Operational Improvements
1. **Simplified Health Checks**: HTTP health endpoints vs. gRPC health probes
2. **Load Balancing**: Standard ALB path-based routing vs. NLB + service discovery
3. **Monitoring**: Standard HTTP metrics and logging
4. **Troubleshooting**: HTTP status codes vs. gRPC status codes

### Deployment Simplifications
1. **No Protobuf Dependencies**: Eliminates import path issues in Docker
2. **Faster Startup**: HTTP services start faster than gRPC services
3. **Platform Independence**: No platform-specific protobuf compilation
4. **Simplified Networking**: Single load balancer instead of ALB + NLB

## Risk Mitigation

### Performance Considerations
- **HTTP vs gRPC Overhead**: Minimal impact for current request volumes
- **JSON vs Protobuf Serialization**: Pydantic provides efficient JSON handling
- **Load Testing**: Comprehensive testing before production migration

### Data Compatibility
- **Schema Evolution**: Maintain backward compatibility during transition
- **Validation Parity**: Ensure Pydantic models match proto field validations
- **Error Handling**: Map gRPC status codes to appropriate HTTP status codes

### Service Dependencies
- **Graceful Migration**: Support both protocols during transition period
- **Client Updates**: Update API Gateway clients with proper error handling
- **Monitoring**: Enhanced monitoring during migration phases

## Conclusion

The migration from gRPC to FastAPI + Pydantic addresses critical development and deployment challenges while maintaining system functionality. The phased approach minimizes risk while providing immediate benefits in development experience and operational simplicity.

Key advantages:
- ✅ Eliminates protobuf import issues in Docker deployments
- ✅ Provides full IDE support and type safety with Pydantic
- ✅ Simplifies AWS ECS deployment configuration
- ✅ Enables standard HTTP monitoring and debugging tools
- ✅ Generates automatic API documentation
- ✅ Reduces service startup time and health check complexity

The migration plan ensures system reliability while modernizing the service architecture for improved developer productivity and operational efficiency.
