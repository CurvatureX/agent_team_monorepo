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

## 迁移策略

### 第一阶段：Workflow Agent 迁移（优先级 1）

**理由**: Workflow Agent 具有最复杂的 gRPC 接口，从 Pydantic 的验证和序列化功能中受益最多。

#### 目标架构
```python
# 从 gRPC proto:
service WorkflowAgent {
  rpc GenerateWorkflow(WorkflowGenerationRequest) returns (WorkflowGenerationResponse);
  rpc RefineWorkflow(WorkflowRefinementRequest) returns (WorkflowRefinementResponse);
  rpc ValidateWorkflow(WorkflowValidationRequest) returns (WorkflowValidationResponse);
}

# 迁移到 FastAPI + Pydantic:
@app.post("/v1/workflows/generate", response_model=WorkflowGenerationResponse)
async def generate_workflow(request: WorkflowGenerationRequest) -> WorkflowGenerationResponse

@app.post("/v1/workflows/{workflow_id}/refine", response_model=WorkflowRefinementResponse)
async def refine_workflow(workflow_id: str, request: WorkflowRefinementRequest) -> WorkflowRefinementResponse

@app.post("/v1/workflows/validate", response_model=WorkflowValidationResponse)
async def validate_workflow(request: WorkflowValidationRequest) -> WorkflowValidationResponse
```

#### 迁移步骤

1. **创建统一的 Pydantic 模型**（集中在 shared/models 中）
```python
# apps/backend/shared/models/__init__.py
from .workflow import *
from .agent import *
from .common import *

# apps/backend/shared/models/agent.py
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from .workflow import WorkflowData

class WorkflowGenerationRequest(BaseModel):
    description: str = Field(..., description="自然语言工作流描述")
    context: Dict[str, str] = Field(default_factory=dict, description="附加上下文")
    user_preferences: Dict[str, str] = Field(default_factory=dict, description="用户偏好")

class WorkflowGenerationResponse(BaseModel):
    success: bool
    workflow: Optional[WorkflowData] = None
    suggestions: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

class WorkflowRefinementRequest(BaseModel):
    workflow_id: str
    feedback: str
    original_workflow: WorkflowData

class WorkflowRefinementResponse(BaseModel):
    success: bool
    updated_workflow: WorkflowData
    changes: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

class WorkflowValidationRequest(BaseModel):
    workflow_data: Dict[str, str]

class WorkflowValidationResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
```

2. **实现 FastAPI Router**
```python
# workflow_agent/api/v1/workflows.py
from fastapi import APIRouter, HTTPException
from workflow_agent.agents.workflow_agent import WorkflowAgentGraph
from shared.models.agent import (
    WorkflowGenerationRequest,
    WorkflowGenerationResponse,
    WorkflowRefinementRequest,
    WorkflowRefinementResponse,
    WorkflowValidationRequest,
    WorkflowValidationResponse
)

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])

@router.post("/generate", response_model=WorkflowGenerationResponse)
async def generate_workflow(request: WorkflowGenerationRequest) -> WorkflowGenerationResponse:
    try:
        # 使用现有的 LangGraph agent 逻辑
        agent = WorkflowAgentGraph()
        result = await agent.generate_workflow(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/refine", response_model=WorkflowRefinementResponse)
async def refine_workflow(workflow_id: str, request: WorkflowRefinementRequest) -> WorkflowRefinementResponse:
    try:
        agent = WorkflowAgentGraph()
        result = await agent.refine_workflow(workflow_id, request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate", response_model=WorkflowValidationResponse)
async def validate_workflow(request: WorkflowValidationRequest) -> WorkflowValidationResponse:
    try:
        agent = WorkflowAgentGraph()
        result = await agent.validate_workflow(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

3. **更新 API Gateway 客户端**
```python
# api-gateway/services/workflow_service_client.py
import httpx
from shared.models.agent import (
    WorkflowGenerationRequest,
    WorkflowGenerationResponse,
    WorkflowRefinementRequest,
    WorkflowRefinementResponse,
    WorkflowValidationRequest,
    WorkflowValidationResponse
)

class WorkflowServiceClient:
    def __init__(self, base_url: str = "http://workflow-agent:8001"):
        self.client = httpx.AsyncClient(base_url=base_url)

    async def generate_workflow(self, request: WorkflowGenerationRequest) -> WorkflowGenerationResponse:
        response = await self.client.post("/v1/workflows/generate", json=request.dict())
        response.raise_for_status()
        return WorkflowGenerationResponse(**response.json())

    async def refine_workflow(self, workflow_id: str, request: WorkflowRefinementRequest) -> WorkflowRefinementResponse:
        response = await self.client.post(f"/v1/workflows/{workflow_id}/refine", json=request.dict())
        response.raise_for_status()
        return WorkflowRefinementResponse(**response.json())

    async def validate_workflow(self, request: WorkflowValidationRequest) -> WorkflowValidationResponse:
        response = await self.client.post("/v1/workflows/validate", json=request.dict())
        response.raise_for_status()
        return WorkflowValidationResponse(**response.json())
```

### 第二阶段：Workflow Engine 迁移（优先级 2）

#### 目标架构
```python
# 从 gRPC WorkflowService 迁移到 FastAPI 端点:
@app.post("/v1/workflows", response_model=CreateWorkflowResponse)
async def create_workflow(request: CreateWorkflowRequest) -> CreateWorkflowResponse

@app.get("/v1/workflows/{workflow_id}", response_model=GetWorkflowResponse)
async def get_workflow(workflow_id: str, user_id: str) -> GetWorkflowResponse

@app.post("/v1/workflows/{workflow_id}/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow(workflow_id: str, request: ExecuteWorkflowRequest) -> ExecuteWorkflowResponse

# 触发器管理端点:
@app.post("/v1/triggers", response_model=CreateTriggerResponse)
async def create_trigger(request: CreateTriggerRequest) -> CreateTriggerResponse

@app.post("/v1/triggers/{trigger_id}/fire", response_model=FireTriggerResponse)
async def fire_trigger(trigger_id: str, request: FireTriggerRequest) -> FireTriggerResponse
```

#### Pydantic 模型设计（统一在 shared/models 中）
```python
# apps/backend/shared/models/workflow.py
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from enum import Enum

class PositionData(BaseModel):
    x: float
    y: float

class RetryPolicyData(BaseModel):
    max_tries: int = Field(default=3, ge=1, le=10)
    wait_between_tries: int = Field(default=5, ge=1, le=300)  # seconds

class NodeData(BaseModel):
    id: str
    name: str
    type: str
    subtype: Optional[str] = None
    type_version: int = Field(default=1)
    position: PositionData
    parameters: Dict[str, str] = Field(default_factory=dict)
    credentials: Dict[str, str] = Field(default_factory=dict)
    disabled: bool = False
    on_error: str = Field(default="continue", regex="^(continue|stop)$")
    retry_policy: Optional[RetryPolicyData] = None
    notes: Dict[str, str] = Field(default_factory=dict)
    webhooks: List[str] = Field(default_factory=list)

class ConnectionData(BaseModel):
    node: str
    type: str
    index: int = Field(default=0)

class ConnectionArrayData(BaseModel):
    connections: List[ConnectionData] = Field(default_factory=list)

class NodeConnectionsData(BaseModel):
    connection_types: Dict[str, ConnectionArrayData] = Field(default_factory=dict)

class ConnectionsMapData(BaseModel):
    connections: Dict[str, NodeConnectionsData] = Field(default_factory=dict)

class WorkflowSettingsData(BaseModel):
    timezone: Dict[str, str] = Field(default_factory=dict)
    save_execution_progress: bool = True
    save_manual_executions: bool = True
    timeout: int = Field(default=3600, ge=60, le=86400)  # 1 hour default, max 24 hours
    error_policy: str = Field(default="continue", regex="^(continue|stop)$")
    caller_policy: str = Field(default="workflow", regex="^(workflow|user)$")

class WorkflowData(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    nodes: List[NodeData]
    connections: ConnectionsMapData
    settings: WorkflowSettingsData
    static_data: Dict[str, str] = Field(default_factory=dict)
    pin_data: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    active: bool = True
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    version: str = Field(default="1.0")

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('工作流名称不能为空')
        return v.strip()

    @validator('nodes')
    def validate_nodes(cls, v):
        if not v:
            raise ValueError('工作流必须包含至少一个节点')
        node_ids = [node.id for node in v]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError('节点ID必须唯一')
        return v

# Engine specific models
class CreateWorkflowRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    nodes: List[NodeData] = Field(..., min_items=1)
    connections: ConnectionsMapData
    settings: Optional[WorkflowSettingsData] = None
    static_data: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None

class CreateWorkflowResponse(BaseModel):
    workflow: WorkflowData
    success: bool = True
    message: str = "工作流创建成功"

class GetWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)

class GetWorkflowResponse(BaseModel):
    workflow: Optional[WorkflowData] = None
    found: bool
    message: str = ""

class UpdateWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    nodes: Optional[List[NodeData]] = None
    connections: Optional[ConnectionsMapData] = None
    settings: Optional[WorkflowSettingsData] = None
    static_data: Optional[Dict[str, str]] = None
    tags: Optional[List[str]] = None
    active: Optional[bool] = None
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None

class UpdateWorkflowResponse(BaseModel):
    workflow: WorkflowData
    success: bool = True
    message: str = "工作流更新成功"

class DeleteWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)

class DeleteWorkflowResponse(BaseModel):
    success: bool = True
    message: str = "工作流删除成功"

class ListWorkflowsRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    active_only: bool = True
    tags: List[str] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

class ListWorkflowsResponse(BaseModel):
    workflows: List[WorkflowData]
    total_count: int
    has_more: bool

class ExecuteWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1)
    trigger_data: Dict[str, str] = Field(default_factory=dict)
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None

class ExecuteWorkflowResponse(BaseModel):
    execution_id: str
    status: str = "running"
    success: bool = True
    message: str = "工作流执行已启动"
```

## 实现细节

### 1. 端口配置更改

```yaml
# docker-compose.yml 更新
services:
  workflow-agent:
    ports:
      - "8001:8000"  # 从 gRPC 50051 改为 HTTP 8000
    environment:
      - PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]  # HTTP 健康检查

  workflow-engine:
    ports:
      - "8002:8000"  # 从 gRPC 50050 改为 HTTP 8000
    environment:
      - PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]  # HTTP 健康检查
```

### 2. 服务通信架构更新

#### 从 gRPC 到 HTTP 的服务发现策略

当前 API Gateway 使用复杂的 gRPC 服务发现机制，包括：
- 环境变量策略
- AWS Cloud Map DNS 策略
- 负载均衡器策略
- 熔断器和健康监控

迁移后的 HTTP 服务通信大大简化了这些复杂性：

```python
# apps/backend/api-gateway/app/services/service_discovery.py
import os
import asyncio
import httpx
from typing import Dict, Optional
from enum import Enum

class ServiceDiscoveryMode(str, Enum):
    LOCAL = "local"                    # 本地开发
    DOCKER_COMPOSE = "docker_compose"  # Docker Compose 环境
    AWS_ALB = "aws_alb"               # AWS ALB 路径路由
    AWS_SERVICE_DISCOVERY = "aws_service_discovery"  # AWS ECS 服务发现

class ServiceDiscovery:
    """简化的服务发现管理器"""

    def __init__(self):
        self.mode = ServiceDiscoveryMode(
            os.getenv("SERVICE_DISCOVERY_MODE", "docker_compose")
        )
        self._service_urls: Optional[Dict[str, str]] = None

    async def discover_services(self) -> Dict[str, str]:
        """发现服务 URL - 根据环境自动选择策略"""
        if self._service_urls is None:
            self._service_urls = await self._do_discovery()
        return self._service_urls

    async def _do_discovery(self) -> Dict[str, str]:
        """执行服务发现"""
        if self.mode == ServiceDiscoveryMode.LOCAL:
            return {
                "workflow_agent": "http://localhost:8001",
                "workflow_engine": "http://localhost:8002"
            }

        elif self.mode == ServiceDiscoveryMode.DOCKER_COMPOSE:
            return {
                "workflow_agent": "http://workflow-agent:8001",
                "workflow_engine": "http://workflow-engine:8002"
            }

        elif self.mode == ServiceDiscoveryMode.AWS_ALB:
            alb_dns = os.getenv("AWS_ALB_DNS_NAME", "")
            return {
                "workflow_agent": f"http://{alb_dns}/agent",
                "workflow_engine": f"http://{alb_dns}/engine"
            }

        elif self.mode == ServiceDiscoveryMode.AWS_SERVICE_DISCOVERY:
            return {
                "workflow_agent": os.getenv("WORKFLOW_AGENT_INTERNAL_URL", ""),
                "workflow_engine": os.getenv("WORKFLOW_ENGINE_INTERNAL_URL", "")
            }
```

#### 统一的 HTTP 服务客户端实现

替代复杂的 gRPC 客户端，使用简化的 HTTP 客户端：

```python
# apps/backend/api-gateway/app/services/service_http_client.py
import httpx
import asyncio
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from shared.models import *
from .service_discovery import ServiceDiscovery

logger = logging.getLogger(__name__)

class ServiceHTTPClient:
    """统一的 HTTP 服务客户端 - 替代 gRPC 复杂架构"""

    def __init__(self):
        self.discovery = ServiceDiscovery()

        # HTTP 客户端配置（简化版本，去除 gRPC 复杂性）
        self.timeout = httpx.Timeout(
            connect=5.0,    # 连接超时
            read=30.0,      # 读取超时
            write=10.0,     # 写入超时
            pool=2.0        # 连接池超时
        )

        # 重试配置（简化的指数退避）
        self.max_retries = 3
        self.retry_delay = 1.0

    @asynccontextmanager
    async def _get_client(self):
        """获取 HTTP 客户端上下文管理器"""
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5)
        ) as client:
            yield client

    async def _make_request(
        self,
        method: str,
        service_name: str,
        endpoint: str,
        **kwargs
    ) -> Optional[Dict[Any, Any]]:
        """执行 HTTP 请求，包含重试逻辑和服务发现"""
        service_urls = await self.discovery.discover_services()
        base_url = service_urls.get(service_name)

        if not base_url:
            raise ValueError(f"Service {service_name} not found in discovery")

        url = f"{base_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                async with self._get_client() as client:
                    response = await client.request(method, url, **kwargs)
                    response.raise_for_status()
                    return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP {e.response.status_code} error for {url}: {e.response.text}")
                if e.response.status_code < 500:  # 4xx 错误不重试
                    raise

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(f"Connection error for {url} (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))  # 指数退避

            except Exception as e:
                logger.error(f"Unexpected error for {url}: {e}")
                raise

        return None

    # Workflow Agent 方法
    async def generate_workflow(self, request: WorkflowGenerationRequest) -> WorkflowGenerationResponse:
        """生成工作流"""
        response_data = await self._make_request(
            "POST",
            "workflow_agent",
            "/v1/workflows/generate",
            json=request.dict(),
            headers={"Content-Type": "application/json"}
        )
        return WorkflowGenerationResponse(**response_data)

    async def refine_workflow(self, workflow_id: str, request: WorkflowRefinementRequest) -> WorkflowRefinementResponse:
        """优化工作流"""
        response_data = await self._make_request(
            "POST",
            "workflow_agent",
            f"/v1/workflows/{workflow_id}/refine",
            json=request.dict(),
            headers={"Content-Type": "application/json"}
        )
        return WorkflowRefinementResponse(**response_data)

    # Workflow Engine 方法
    async def create_workflow(self, request: CreateWorkflowRequest) -> CreateWorkflowResponse:
        """创建工作流"""
        response_data = await self._make_request(
            "POST",
            "workflow_engine",
            "/v1/workflows",
            json=request.dict(),
            headers={"Content-Type": "application/json"}
        )
        return CreateWorkflowResponse(**response_data)

    async def get_workflow(self, workflow_id: str, user_id: str) -> GetWorkflowResponse:
        """获取工作流"""
        response_data = await self._make_request(
            "GET",
            "workflow_engine",
            f"/v1/workflows/{workflow_id}",
            params={"user_id": user_id}
        )
        return GetWorkflowResponse(**response_data)

    async def execute_workflow(self, request: ExecuteWorkflowRequest) -> ExecuteWorkflowResponse:
        """执行工作流"""
        response_data = await self._make_request(
            "POST",
            "workflow_engine",
            f"/v1/workflows/{request.workflow_id}/execute",
            json=request.dict(exclude={'workflow_id'}),
            headers={"Content-Type": "application/json"}
        )
        return ExecuteWorkflowResponse(**response_data)

    # 健康检查方法 - 替代复杂的 gRPC 健康检查
    async def health_check_all_services(self) -> Dict[str, bool]:
        """检查所有服务健康状态"""
        return await self.discovery.health_check_services()

# 依赖注入函数
async def get_service_client() -> ServiceHTTPClient:
    """获取服务客户端实例"""
    return ServiceHTTPClient()
```

#### 环境配置管理

不同环境下的服务通信配置：

```python
# apps/backend/api-gateway/app/core/config.py 更新
class ServiceDiscoverySettings(BaseSettings):
    """服务发现配置"""

    # 服务发现模式
    SERVICE_DISCOVERY_MODE: str = Field(
        default="docker_compose",
        description="服务发现模式: local, docker_compose, aws_alb, aws_service_discovery"
    )

    # 本地开发环境
    WORKFLOW_AGENT_LOCAL_URL: str = Field(default="http://localhost:8001", description="Agent本地URL")
    WORKFLOW_ENGINE_LOCAL_URL: str = Field(default="http://localhost:8002", description="Engine本地URL")

    # Docker Compose 环境
    WORKFLOW_AGENT_DOCKER_URL: str = Field(default="http://workflow-agent:8001", description="Agent Docker URL")
    WORKFLOW_ENGINE_DOCKER_URL: str = Field(default="http://workflow-engine:8002", description="Engine Docker URL")

    # AWS 环境
    AWS_ALB_DNS_NAME: str = Field(default="", description="AWS ALB DNS名称")
    WORKFLOW_AGENT_INTERNAL_URL: str = Field(default="", description="Agent AWS内部URL")
    WORKFLOW_ENGINE_INTERNAL_URL: str = Field(default="", description="Engine AWS内部URL")

    def get_service_urls(self) -> Dict[str, str]:
        """根据发现模式获取服务URL"""
        mode_mapping = {
            "local": {
                "workflow_agent": self.WORKFLOW_AGENT_LOCAL_URL,
                "workflow_engine": self.WORKFLOW_ENGINE_LOCAL_URL
            },
            "docker_compose": {
                "workflow_agent": self.WORKFLOW_AGENT_DOCKER_URL,
                "workflow_engine": self.WORKFLOW_ENGINE_DOCKER_URL
            },
            "aws_alb": {
                "workflow_agent": f"http://{self.AWS_ALB_DNS_NAME}/agent",
                "workflow_engine": f"http://{self.AWS_ALB_DNS_NAME}/engine"
            },
            "aws_service_discovery": {
                "workflow_agent": self.WORKFLOW_AGENT_INTERNAL_URL,
                "workflow_engine": self.WORKFLOW_ENGINE_INTERNAL_URL
            }
        }

        return mode_mapping.get(self.SERVICE_DISCOVERY_MODE, mode_mapping["docker_compose"])
```

### 3. FastAPI 应用程序结构

#### 更新的项目结构（使用共享模型）
```
apps/backend/
├── shared/
│   └── models/
│       ├── __init__.py      # 导出所有模型
│       ├── common.py        # 通用基础模型
│       ├── workflow.py      # 工作流相关模型
│       ├── agent.py         # Agent 相关模型
│       ├── execution.py     # 执行相关模型
│       └── trigger.py       # 触发器相关模型
├── workflow_agent/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py          # 依赖注入
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── workflows.py # 工作流端点
│   ├── main.py              # FastAPI 应用初始化
│   ├── core/
│   │   ├── config.py        # 设置（不变）
│   │   └── exceptions.py    # HTTP 异常处理器
│   └── agents/              # 现有的 LangGraph 逻辑（不变）
├── workflow_engine/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── workflows.py
│   │       ├── triggers.py
│   │       └── executions.py
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── exceptions.py
│   └── services/            # 现有的业务逻辑（不变）
└── api-gateway/
    ├── services/
    │   └── enhanced_http_client.py  # 更新的 HTTP 客户端
    └── models/              # 移除，使用 shared.models
```

#### 共享模型结构设计
```python
# apps/backend/shared/models/common.py
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from enum import Enum

class BaseResponse(BaseModel):
    """所有响应的基础模型"""
    success: bool = True
    message: str = ""

class ErrorResponse(BaseResponse):
    """错误响应模型"""
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"

class HealthResponse(BaseModel):
    status: HealthStatus
    version: str = "1.0.0"
    timestamp: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
```

#### 主应用程序设置
```python
# workflow_agent/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from workflow_agent.api.v1.workflows import router as workflows_router
from workflow_agent.core.config import settings
from shared.models.common import HealthResponse, HealthStatus

app = FastAPI(
    title="Workflow Agent API",
    description="AI 驱动的工作流生成和咨询服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中适当配置
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflows_router)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        version="1.0.0",
        details={
            "service": "workflow-agent",
            "langraph": "connected",
            "supabase": "connected"
        }
    )

@app.get("/")
async def root():
    return {"message": "Workflow Agent API", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
```

### 4. 共享模型的优势

#### 统一数据验证和类型安全
```python
# apps/backend/shared/models/workflow.py - 集中的验证逻辑
from shared.models.common import BaseResponse

class CreateWorkflowRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="工作流名称")
    nodes: List[NodeData] = Field(..., min_items=1, description="至少需要一个节点")
    user_id: str = Field(..., min_length=1, description="用户ID")

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('工作流名称不能为空或仅包含空格')
        return v.strip()

    @validator('nodes')
    def validate_node_connections(cls, v):
        if not v:
            raise ValueError('工作流必须包含至少一个节点')
        node_ids = [node.id for node in v]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError('节点ID必须唯一')
        return v

class CreateWorkflowResponse(BaseResponse):
    workflow: WorkflowData

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "工作流创建成功",
                "workflow": {
                    "id": "wf_123456",
                    "name": "邮件处理工作流",
                    "description": "自动处理传入邮件",
                    "nodes": [],
                    "connections": {},
                    "settings": {}
                }
            }
        }

# apps/backend/shared/models/agent.py - Agent 特定模型
class WorkflowGenerationRequest(BaseModel):
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="期望工作流的自然语言描述",
        example="创建一个处理传入邮件、使用 AI 提取重要信息并发送 Slack 通知的工作流"
    )
    context: Dict[str, str] = Field(
        default_factory=dict,
        description="附加上下文信息",
        example={"domain": "customer_service", "priority": "high"}
    )
    user_preferences: Dict[str, str] = Field(
        default_factory=dict,
        description="用户偏好设置",
        example={"language": "zh-CN", "complexity": "simple"}
    )

    @validator('description')
    def validate_description(cls, v):
        if not v.strip():
            raise ValueError('工作流描述不能为空')
        # 检查是否包含有害内容
        prohibited_words = ['delete', 'remove', 'destroy']
        if any(word in v.lower() for word in prohibited_words):
            raise ValueError('工作流描述包含禁止的操作词汇')
        return v.strip()

class WorkflowGenerationResponse(BaseResponse):
    workflow: Optional[WorkflowData] = None
    suggestions: List[str] = Field(default_factory=list, description="改进建议")
    missing_info: List[str] = Field(default_factory=list, description="缺失信息")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="生成置信度")
```

#### 跨服务的类型一致性
```python
# 在 workflow_agent 中使用
from shared.models.agent import WorkflowGenerationRequest, WorkflowGenerationResponse
from shared.models.workflow import WorkflowData

# 在 workflow_engine 中使用
from shared.models.workflow import CreateWorkflowRequest, CreateWorkflowResponse
from shared.models.execution import ExecuteWorkflowRequest, ExecuteWorkflowResponse

# 在 api-gateway 中使用
from shared.models import *  # 导入所有模型

# 所有服务都使用相同的类型定义，确保数据结构一致性
```

## 本地 Docker 部署策略

### 1. 更新的 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 基础设施（不变）
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

  # Workflow Agent - 迁移到 FastAPI
  workflow-agent:
    build:
      context: .
      dockerfile: ./workflow_agent/Dockerfile.fastapi  # 新的 Dockerfile
      target: production
    container_name: agent-team-workflow-agent
    ports:
      - "8001:8000"  # 从 gRPC 50051 更改
    environment:
      # FastAPI 配置
      PORT: "8000"
      DEBUG: "${DEBUG:-false}"

      # 数据库和缓存（不变）
      SUPABASE_URL: "${SUPABASE_URL}"
      SUPABASE_SECRET_KEY: "${SUPABASE_SECRET_KEY}"
      REDIS_URL: "redis://redis:6379/0"

      # AI APIs（不变）
      OPENAI_API_KEY: "${OPENAI_API_KEY}"
      ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s  # 从 gRPC 的 240s 减少
    depends_on:
      - redis
    networks:
      - agent-team-network

  # Workflow Engine - 迁移到 FastAPI
  workflow-engine:
    build:
      context: .
      dockerfile: ./workflow_engine/Dockerfile.fastapi  # 新的 Dockerfile
      target: production
    container_name: agent-team-workflow-engine
    ports:
      - "8002:8000"  # 从 gRPC 50050 更改
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
      start_period: 45s  # 从 gRPC 的 180s 减少
    depends_on:
      - redis
    networks:
      - agent-team-network

  # API Gateway - 更新客户端配置
  api-gateway:
    build:
      context: .
      dockerfile: ./api-gateway/Dockerfile
    container_name: api_gateway_service
    ports:
      - "8000:8000"
    environment:
      # 更新的服务 URL
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

### 2. FastAPI 服务的新 Dockerfiles

#### Workflow Agent Dockerfile
```dockerfile
# workflow_agent/Dockerfile.fastapi
FROM python:3.11-slim as base

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 首先复制 requirements 以便更好地缓存
COPY workflow_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码
COPY workflow_agent/ ./workflow_agent/
COPY shared/ ./shared/

# 生产阶段
FROM base as production

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash app
USER app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 使用 uvicorn 运行 FastAPI
CMD ["python", "-m", "uvicorn", "workflow_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. 开发命令

```bash
# 启动所有服务
docker-compose up -d

# 为开发启动单个服务
docker-compose up -d redis
docker-compose up workflow-agent  # 支持实时重载

# 查看日志
docker-compose logs -f workflow-agent
docker-compose logs -f workflow-engine

# API 文档访问
# Workflow Agent: http://localhost:8001/docs
# Workflow Engine: http://localhost:8002/docs
# API Gateway: http://localhost:8000/docs（现有）

# 健康检查
curl http://localhost:8001/health  # Workflow Agent
curl http://localhost:8002/health  # Workflow Engine
curl http://localhost:8000/health  # API Gateway

# 测试 API 端点
curl -X POST http://localhost:8001/v1/workflows/generate \
  -H "Content-Type: application/json" \
  -d '{"description": "创建一个简单的邮件通知工作流"}'
```

## AWS 部署策略 - 分离Gateway架构

### 1. 双Gateway架构设计（推荐方案）

#### 🏗️ 架构概览
```
┌─────────────────────────────────────────────────────────────┐
│                      用户/前端应用                             │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS/WSS
┌─────────────────────▼───────────────────────────────────────┐
│             外部 AWS ALB (api.yourdomain.com)               │
│                      🌐 面向公网                              │
│  /api/public/*  → API Gateway (Public API)                 │
│  /api/app/*     → API Gateway (App API)                    │
│  /api/mcp/*     → API Gateway (MCP API)                    │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP (VPC内部)
                      │
┌─────────────────────▼───────────────────────────────────────┐
│           内部 AWS ALB (internal-api.yourdomain.com)        │
│                     🔒 仅VPC内访问                           │
│  /agent/*       → workflow_agent (内部API + Swagger)        │
│  /engine/*      → workflow_engine (内部API + Swagger)      │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP (VPC内部)
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼──┐        ┌────▼────┐      ┌─────▼─────┐
│ API  │  HTTP  │workflow │      │ workflow  │
│Gateway│◄──────►│ _agent  │      │ _engine   │
└──────┘        └─────────┘      └───────────┘
```

#### 🔒 外部API Gateway（公网访问）
```hcl
# infra/external_alb.tf - 外部ALB配置
resource "aws_lb" "external_api" {
  name               = "${local.name_prefix}-external-api"
  internal           = false  # 公网访问
  load_balancer_type = "application"
  security_groups    = [aws_security_group.external_alb.id]
  subnets           = var.public_subnet_ids

  enable_deletion_protection = var.environment == "production"

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-external-api"
    Type        = "external-api"
    Visibility  = "public"
  })
}

# HTTPS 监听器
resource "aws_lb_listener" "external_https" {
  load_balancer_arn = aws_lb.external_api.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = aws_acm_certificate_validation.api_cert.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_gateway.arn
  }
}

# API Gateway 路由规则（所有/api/*路径）
resource "aws_lb_listener_rule" "api_gateway_external" {
  listener_arn = aws_lb_listener.external_https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_gateway.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }

  tags = local.common_tags
}
```

#### 🔒 内部API Gateway（VPC内访问）
```hcl
# infra/internal_alb.tf - 内部ALB配置
resource "aws_lb" "internal_api" {
  name               = "${local.name_prefix}-internal-api"
  internal           = true   # VPC内部访问
  load_balancer_type = "application"
  security_groups    = [aws_security_group.internal_alb.id]
  subnets           = var.private_subnet_ids

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-internal-api"
    Type        = "internal-api"
    Visibility  = "private"
  })
}

# HTTP 监听器（VPC内部通信）
resource "aws_lb_listener" "internal_http" {
  load_balancer_arn = aws_lb.internal_api.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Internal API Gateway - Use specific service paths"
      status_code  = "404"
    }
  }
}

# Workflow Agent 路由
resource "aws_lb_listener_rule" "workflow_agent_internal" {
  listener_arn = aws_lb_listener.internal_http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.workflow_agent_http.arn
  }

  condition {
    path_pattern {
      values = ["/agent/*"]
    }
  }

  tags = local.common_tags
}

# Workflow Engine 路由
resource "aws_lb_listener_rule" "workflow_engine_internal" {
  listener_arn = aws_lb_listener.internal_http.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.workflow_engine_http.arn
  }

  condition {
    path_pattern {
      values = ["/engine/*"]
    }
  }

  tags = local.common_tags
}
```

#### 🔒 安全组配置
```hcl
# infra/security_groups.tf - 分离Gateway安全策略
# 外部ALB安全组 - 允许公网HTTPS访问
resource "aws_security_group" "external_alb" {
  name_prefix = "${local.name_prefix}-external-alb"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from internet"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP redirect to HTTPS"
  }

  egress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.api_gateway.id]
    description     = "To API Gateway"
  }

  tags = local.common_tags
}

# 内部ALB安全组 - 仅允许VPC和开发者IP访问
resource "aws_security_group" "internal_alb" {
  name_prefix = "${local.name_prefix}-internal-alb"
  vpc_id      = var.vpc_id

  # VPC内部访问
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "HTTP from VPC"
  }

  # 开发者调试访问（通过VPN或跳板机）
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.developer_ip_ranges  # 配置开发者IP范围
    description = "HTTP from developer IPs"
  }

  egress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [
      aws_security_group.workflow_agent.id,
      aws_security_group.workflow_engine.id
    ]
    description = "To internal services"
  }

  tags = local.common_tags
}
```

#### 📊 简化的环境变量配置（静态URL方案）

**核心理念：用2个环境变量替代复杂的服务发现**

| 环境类型 | 外部API访问 | WORKFLOW_AGENT_URL | WORKFLOW_ENGINE_URL |
|---------|------------|-------------------|-------------------|
| **本地开发** | `http://localhost:8000` | `http://localhost:8001` | `http://localhost:8002` |
| **Docker Compose** | `http://api-gateway:8000` | `http://workflow-agent:8001` | `http://workflow-engine:8002` |
| **AWS 分离ALB** | `https://api.yourdomain.com` | `http://internal-alb-dns/agent` | `http://internal-alb-dns/engine` |

#### 🎯 环境变量配置示例

**开发环境 (.env.local):**
```bash
# API Gateway 配置
PORT=8000
DEBUG=true

# 🎯 后端服务URL (本地开发)
WORKFLOW_AGENT_URL=http://localhost:8001
WORKFLOW_ENGINE_URL=http://localhost:8002

# 其他配置...
SUPABASE_URL=https://your-project.supabase.co
REDIS_URL=redis://localhost:6379/0
```

**Docker Compose (.env.docker):**
```bash
# API Gateway 配置
PORT=8000
DEBUG=false

# 🎯 后端服务URL (Docker容器名)
WORKFLOW_AGENT_URL=http://workflow-agent:8001
WORKFLOW_ENGINE_URL=http://workflow-engine:8002

# 其他配置...
SUPABASE_URL=https://your-project.supabase.co
REDIS_URL=redis://redis:6379/0
```

**AWS ECS生产环境:**
```bash
# API Gateway 配置
PORT=8000
DEBUG=false

# 🎯 后端服务URL (内部ALB)
WORKFLOW_AGENT_URL=http://internal-alb-12345.us-east-1.elb.amazonaws.com/agent
WORKFLOW_ENGINE_URL=http://internal-alb-12345.us-east-1.elb.amazonaws.com/engine

# 其他配置...
SUPABASE_URL=${SUPABASE_URL}  # 从SSM参数获取
REDIS_URL=${REDIS_URL}        # 从SSM参数获取
```

### 2. 🎯 极简化的静态配置方案

#### ❌ 不再需要复杂的服务发现
**原因：**
- ALB已经提供负载均衡和健康检查
- 只有2个固定的后端服务，地址不会动态变化
- 环境变量配置更简单可靠

#### ✅ 超简化HTTP客户端（50行 vs 777行）
```python
# apps/backend/api-gateway/app/services/simple_http_client.py
import os
import httpx
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SimpleHTTPClient:
    """极简HTTP客户端 - 无需复杂服务发现"""

    def __init__(self):
        # 🎯 直接从环境变量获取固定URL
        self.workflow_agent_url = os.getenv(
            "WORKFLOW_AGENT_URL",
            "http://localhost:8001"  # 默认开发环境
        )
        self.workflow_engine_url = os.getenv(
            "WORKFLOW_ENGINE_URL",
            "http://localhost:8002"  # 默认开发环境
        )

        # 单个HTTP客户端，复用连接
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=100)
        )

        logger.info(f"Initialized HTTP client:")
        logger.info(f"  Workflow Agent: {self.workflow_agent_url}")
        logger.info(f"  Workflow Engine: {self.workflow_engine_url}")

    async def call_workflow_agent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """调用workflow agent"""
        try:
            response = await self.client.post(
                f"{self.workflow_agent_url}/v1/process",
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to call workflow agent: {e}")
            raise

    async def call_workflow_engine(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """调用workflow engine"""
        try:
            response = await self.client.post(
                f"{self.workflow_engine_url}/v1/execute",
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to call workflow engine: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """检查后端服务健康状态"""
        status = {}

        try:
            agent_resp = await self.client.get(f"{self.workflow_agent_url}/health")
            status["workflow_agent"] = "healthy" if agent_resp.status_code == 200 else "unhealthy"
        except:
            status["workflow_agent"] = "unreachable"

        try:
            engine_resp = await self.client.get(f"{self.workflow_engine_url}/health")
            status["workflow_engine"] = "healthy" if engine_resp.status_code == 200 else "unhealthy"
        except:
            status["workflow_engine"] = "unreachable"

        return status

    async def close(self):
        """清理资源"""
        await self.client.aclose()

# 全局客户端实例
_http_client: Optional[SimpleHTTPClient] = None

async def get_http_client() -> SimpleHTTPClient:
    """获取HTTP客户端实例"""
    global _http_client
    if _http_client is None:
        _http_client = SimpleHTTPClient()
    return _http_client

async def close_http_client():
    """关闭HTTP客户端"""
    global _http_client
    if _http_client:
        await _http_client.close()
        _http_client = None
```

### 3. API Gateway ECS 任务定义更新（分离ALB配置）

#### API Gateway 任务定义 - 双ALB模式配置
```hcl
# infra/ecs.tf - API Gateway 任务定义
resource "aws_ecs_task_definition" "api_gateway" {
  family                   = "${local.name_prefix}-api-gateway"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_gateway_cpu
  memory                   = var.api_gateway_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "api-gateway"
      image = "${aws_ecr_repository.api_gateway.repository_url}:${var.image_tag}"

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "PORT"
          value = "8000"
        },
        # 🎯 简化配置：直接指定后端服务URL
        {
          name  = "WORKFLOW_AGENT_URL"
          value = "http://${aws_lb.internal_api.dns_name}/agent"
        },
        {
          name  = "WORKFLOW_ENGINE_URL"
          value = "http://${aws_lb.internal_api.dns_name}/engine"
        },
        # 📊 内部API文档访问地址（可选）
        {
          name  = "INTERNAL_API_DOCS_BASE_URL"
          value = "http://${aws_lb.internal_api.dns_name}"
        },
        # 其他环境变量...
        {
          name  = "DEBUG"
          value = "false"
        }
      ]

      # 简化的 HTTP 健康检查
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60  # HTTP 服务启动更快
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api-gateway"
        }
      }
    }
  ])

  tags = local.common_tags
}
```

#### 后端服务任务定义（Workflow Agent & Engine）
```hcl
# Workflow Agent 任务定义更新
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

      # HTTP 端口映射（从 gRPC 50051 改为 HTTP 8000）
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "PORT"
          value = "8000"
        },
        {
          name  = "SERVICE_NAME"
          value = "workflow-agent"
        },
        # 其他服务特定环境变量...
      ]

      # HTTP 健康检查（替代 gRPC 健康检查）
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60  # 从 gRPC 的 240s 大幅减少
      }

      # 日志配置不变...
    }
  ])

  tags = local.common_tags
}
```

### 2. 负载均衡器配置更新

#### 移除 gRPC 网络负载均衡器（不再需要）
```hcl
# infra/load_balancer.tf - 移除此块
# resource "aws_lb" "grpc_internal" {
#   name               = "${local.name_prefix}-grpc-nlb"
#   internal           = true
#   load_balancer_type = "network"
#   subnets            = aws_subnet.private[*].id
# }
```

#### 为所有 HTTP 服务更新应用程序负载均衡器
```hcl
# infra/load_balancer.tf
# Workflow Agent 的目标组（现在是 HTTP）
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

# Workflow Engine 的目标组（现在是 HTTP）
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

# 基于路径路由的 ALB 监听器规则
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

### 3. 服务发现简化

#### HTTP 服务的更新服务发现
```hcl
# infra/service_discovery.tf
# 服务发现服务可以简化或移除
# 因为 HTTP 服务可以通过 DNS 使用 ALB 基础的服务发现

# 可选：保留用于内部服务间通信
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

  # HTTP 服务可以使用更简单的健康检查
  health_check_custom_config {
    failure_threshold = 1
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-workflow-agent-discovery"
  })
}
```

### 4. ECS 服务配置更新

```hcl
# infra/ecs.tf
# Workflow Agent 的 ECS 服务（HTTP）
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

  # HTTP 的更新负载均衡器配置
  load_balancer {
    target_group_arn = aws_lb_target_group.workflow_agent_http.arn
    container_name   = "workflow-agent"
    container_port   = 8000  # 从 50051 更改
  }

  service_registries {
    registry_arn = aws_service_discovery_service.workflow_agent.arn
  }

  depends_on = [aws_lb_listener.main]

  tags = local.common_tags
}
```

### 5. 安全组更新

```hcl
# infra/security_groups.tf
# ECS 任务安全组 - 为 HTTP 服务更新
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${local.name_prefix}-ecs-tasks"
  vpc_id      = aws_vpc.main.id

  # 所有服务的 HTTP 流量
  ingress {
    protocol        = "tcp"
    from_port       = 8000
    to_port         = 8000
    security_groups = [aws_security_group.alb.id]
    description     = "来自 ALB 的 HTTP 流量"
  }

  # 移除 gRPC 端口规则（50050、50051）- 不再需要

  # Redis 访问
  ingress {
    protocol    = "tcp"
    from_port   = 6379
    to_port     = 6379
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Redis 访问"
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
    description = "所有出站流量"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-tasks-sg"
  })
}
```

### 6. GitHub Actions 部署更新

```yaml
# .github/workflows/deploy.yml
# 构建和推送部分保持相似，但 Dockerfile 名称更改
      - name: Build, tag, and push image to Amazon ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          # 构建和推送 Docker 镜像 - 更新的 Dockerfile 名称
          docker buildx build \
            --platform linux/amd64 \
            --target production \
            --file ${{ matrix.service.dockerfile }}.fastapi \  # 新的 Dockerfile 名称
            --tag $ECR_REGISTRY/${{ matrix.service.repository }}:$IMAGE_TAG \
            --tag $ECR_REGISTRY/${{ matrix.service.repository }}:latest \
            --push \
            ${{ matrix.service.context }}

  deploy:
    # 部署部分简化 - HTTP 服务不需要 gRPC 特定的服务发现清理
    steps:
      # ... 现有步骤 ...

      # 移除服务发现清理步骤 - HTTP 服务不再需要
      # - name: Handle Service Discovery cleanup if needed

      - name: Terraform Apply
        working-directory: infra
        env:
          TF_VAR_image_tag: ${{ github.sha }}
          # ... 其他环境变量
        run: terraform apply -auto-approve tfplan

      # 服务更新保持不变
      - name: Update ECS Service - Workflow Agent
        run: |
          aws ecs update-service \
            --cluster agent-team-production-cluster \
            --service workflow-agent-service \
            --force-new-deployment \
            --region ${{ env.AWS_REGION }}
```

## 迁移时间表和回滚策略

### 第一阶段：Workflow Agent 迁移（第 1-2 周）
1. **第 1-3 天**：创建 Pydantic 模型和 FastAPI 端点
2. **第 4-5 天**：更新本地 Docker 环境和测试
3. **第 6-7 天**：部署到预发布环境
4. **第 2 周**：生产部署和监控

### 第二阶段：Workflow Engine 迁移（第 3-4 周）
1. **第 1-4 天**：实现工作流 CRUD 操作的 FastAPI 端点
2. **第 5-6 天**：实现触发器管理端点
3. **第 7 天**：集成测试和本地部署
4. **第 4 周**：预发布和生产部署

### 回滚策略
1. **代码回滚**：在迁移期间维护 gRPC 实现与 FastAPI 并行
2. **基础设施回滚**：保留现有 ECS 任务定义作为备份
3. **DNS/负载均衡器回滚**：在 gRPC 和 HTTP 目标组之间快速切换
4. **功能标记**：使用环境变量在 gRPC 和 HTTP 客户端之间切换

## 优势评估

### 开发体验改进
1. **IDE 支持**：请求/响应模型的完整 IntelliSense 和类型检查
2. **API 文档**：自动 OpenAPI/Swagger 文档生成
3. **测试**：标准 HTTP 测试工具（curl、Postman、pytest-httpx）
4. **调试**：日志中清晰的 JSON 请求/响应体

### 运维改进
1. **简化的健康检查**：HTTP 健康端点 vs gRPC 健康探针
2. **负载均衡**：标准 ALB 基于路径的路由 vs NLB + 服务发现
3. **监控**：标准 HTTP 指标和日志记录
4. **故障排除**：HTTP 状态码 vs gRPC 状态码

### 部署简化
1. **无 Protobuf 依赖**：消除 Docker 中的导入路径问题
2. **更快启动**：HTTP 服务比 gRPC 服务启动更快
3. **平台独立性**：无需平台特定的 protobuf 编译
4. **简化网络**：单一负载均衡器而不是 ALB + NLB

## 风险缓解

### 性能考虑
- **HTTP vs gRPC 开销**：对当前请求量的影响最小
- **JSON vs Protobuf 序列化**：Pydantic 提供高效的 JSON 处理
- **负载测试**：生产迁移前的全面测试

### 数据兼容性
- **模式演进**：在过渡期间保持向后兼容性
- **验证一致性**：确保 Pydantic 模型匹配 proto 字段验证
- **错误处理**：将 gRPC 状态码映射到适当的 HTTP 状态码

### 服务依赖
- **优雅迁移**：在过渡期间支持两种协议
- **客户端更新**：使用适当错误处理更新 API Gateway 客户端
- **监控**：在迁移阶段加强监控

## 🏆 分离Gateway架构优势总结

### 📊 架构对比分析

| 特性维度 | 单一Gateway | 🏆 分离Gateway |
|---------|------------|---------------|
| **🔐 安全隔离** | ⚠️ 内部API暴露在公网 | ✅ 完全网络隔离 |
| **🛡️ 访问控制** | ❌ 依赖复杂的路径规则 | ✅ 域名级别控制 |
| **📊 监控审计** | ⚠️ 内外部流量混合 | ✅ 独立监控体系 |
| **🔧 运维复杂度** | ✅ 单点管理 | ⚠️ 双ALB管理 |
| **💰 成本** | ✅ $16/月 | ❌ $32/월 |
| **📈 扩展性** | ❌ 单点瓶颈 | ✅ 独立扩展 |

### 🔒 核心安全收益

**1. 网络隔离**
- 内部API完全隔离于公网，只能通过VPC或授权IP访问
- 外部API仅暴露必要的业务接口

**2. 威胁面减少**
- 内部调试端点不再暴露给攻击者
- Swagger文档分离，避免敏感API泄露

**3. 合规友好**
- 符合企业零信任安全架构
- 满足内部API不得公网访问的合规要求

### 📚 API文档策略

```yaml
外部API文档: https://api.yourdomain.com/docs
  - ✅ 面向用户的业务API
  - ✅ 公开安全的接口文档

内部API文档: http://internal-api.yourdomain.com/agent/docs
              http://internal-api.yourdomain.com/engine/docs
  - 🔒 仅开发者和运维人员访问
  - 🔒 完整的内部服务API文档
  - 🔧 调试和故障排查工具
```

### 🚀 部署建议

**推荐采用分离Gateway架构**，因为：

1. **安全优先**：内部API完全隔离，符合现代安全实践
2. **清晰职责**：外部Gateway专注用户服务，内部Gateway专注开发运维
3. **长期收益**：随着微服务扩展，分离架构更易管理和扩展
4. **合规需求**：满足企业级安全和合规要求

## 📋 结论

从 gRPC 迁移到 FastAPI + Pydantic + 分离Gateway架构解决了关键的开发、部署和安全挑战。

### 🏆 主要优势：
- ✅ **开发体验**：消除 protobuf 导入问题，提供完整 IDE 支持
- ✅ **安全隔离**：内外部API完全分离，减少威胁面
- ✅ **运维简化**：简化 AWS ECS 部署，减少启动时间
- ✅ **监控调试**：标准 HTTP 工具支持，独立监控体系
- ✅ **API文档**：自动生成的分层文档策略
- ✅ **类型安全**：Pydantic 模型提供完整类型检查
- ✅ **架构简化**：从777行复杂服务发现减少到50行静态配置
- ✅ **维护容易**：依赖ALB内置功能，减少自定义逻辑

### 💡 成本效益分析：
- 额外的 ALB 成本（$16/月）相比安全风险和开发效率提升是明智投资
- **大幅减少代码复杂度**：移除不必要的服务发现、circuit breaker、健康监控
- **依赖AWS托管服务**：ALB提供负载均衡、健康检查、故障转移
- 长期维护成本显著降低，开发者生产力大幅提升

### 🎯 架构简化对比：

| 组件 | 原有复杂度 | 🏆 简化后 | 减少 |
|------|-----------|---------|------|
| **HTTP客户端** | 777行enhanced_grpc_client | 50行simple_http_client | **93%** |
| **服务发现** | 多策略动态发现 | 2个环境变量 | **95%** |
| **健康检查** | 自定义监控逻辑 | ALB内置检查 | **100%** |
| **负载均衡** | 客户端实现 | ALB内置功能 | **100%** |
| **故障转移** | Circuit breaker模式 | ALB自动处理 | **100%** |

分离Gateway + 静态配置架构确保系统安全可靠且易于维护，完美体现了**简单即美**的设计哲学。
